import json
import os
import re
import shutil
import time
import traceback
import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


BASE_URL = "https://app.blueez.com.br"
COLUNAS_OBRIGATORIAS = [
    "empresa",
    "estabelecimento",
    "fornecedor",
    "cnpj_fornecedor",
    "contrato",
    "data_inicio",
    "data_fim",
    "competencia",
    "emissao_nf",
    "vencimento_nf",
    "id_nf",
    "item_medido",
    "valor_item",
    "observacao",
    "arquivo_1",
    "arquivo_2",
]


class AbortarAutomacao(Exception):
    pass


class ErroRegistroEsperado(Exception):
    pass


def executar(
    input_path=None,
    input_paths=None,
    attachments=None,
    output_dir=None,
    should_stop=None,
    log=None,
    parametros="",
    parametros_json=None,
):
    logger = log or (lambda message: None)
    arquivos_principais = [Path(path) for path in (input_paths or ([] if input_path is None else [input_path]))]
    anexos = [Path(path) for path in (attachments or [])]
    pasta_saida = Path(output_dir or Path.cwd())
    pasta_saida.mkdir(parents=True, exist_ok=True)

    parametros_execucao = carregar_parametros(parametros, parametros_json)
    planilha_entrada = selecionar_planilha(arquivos_principais, input_path)
    planilha_trabalho = copiar_planilha(planilha_entrada, pasta_saida)
    logger(f"Planilha de trabalho criada: {planilha_trabalho.name}")
    logger(
        "Arquivos principais recebidos na execucao: "
        + (", ".join(path.name for path in arquivos_principais) if arquivos_principais else "nenhum")
    )
    logger(
        "Arquivos auxiliares recebidos na execucao: "
        + (", ".join(path.name for path in anexos) if anexos else "nenhum")
    )

    credenciais = resolver_credenciais(planilha_trabalho, parametros_execucao)
    df = pd.read_excel(planilha_trabalho)
    validar_planilha(df)
    numeros_solicitacao_conhecidos = carregar_numeros_solicitacao_existentes(df)
    attachment_index = indexar_anexos(anexos, logger)
    browser_timeout = int(parametros_execucao.get("browser_timeout", 40))
    pause_seconds = float(parametros_execucao.get("pause_seconds", 1))
    updates_excel = []
    updates_solicitacao = []
    resumo_execucao = {
        "ok": 0,
        "erro": 0,
        "teste": 0,
        "pulado_ok": 0,
    }
    driver = None
    wait = None

    def checkpoint():
        if should_stop:
            should_stop()

    def pause(seconds=None):
        checkpoint()
        time.sleep(pause_seconds if seconds is None else seconds)

    try:
        logger(
            "Inicializando navegador Chrome para o BlueEZ "
            f"(headless={bool(parametros_execucao.get('headless', True))}, timeout={browser_timeout}s)."
        )
        driver = iniciar_driver(parametros_execucao)
        wait = WebDriverWait(driver, browser_timeout)
        logger(
            "Sessao Selenium criada com sucesso "
            f"(browser={safe_capability(driver, 'browserName')}, version={safe_capability(driver, 'browserVersion')})."
        )
        login_blueez(driver, wait, pause, credenciais, logger, parametros_execucao)
        for idx, registro in enumerate(df.to_dict(orient="records")):
            checkpoint()
            linha_excel = idx + 2
            status_atual = ler_status(df, idx).strip().upper()
            if deve_pular_registro(status_atual):
                mensagem = f"Registro nao processado (pulado por status final: {status_atual})"
                resumo_execucao["pulado_ok"] += 1
                logger(f"Linha {linha_excel}: {mensagem}")
                continue

            try:
                logger(f"Iniciando registro {idx + 1}/{len(df)}.")
                resultado_registro = processar_registro(
                    driver,
                    wait,
                    pause,
                    registro,
                    attachment_index,
                    parametros_execucao,
                    logger,
                    numeros_solicitacao_conhecidos,
                )
                if resultado_registro["enviado"]:
                    numero_solicitacao = resultado_registro["numero_solicitacao"]
                    updates_excel.append((linha_excel, "OK", "Processado com sucesso"))
                    updates_solicitacao.append((linha_excel, numero_solicitacao))
                    numeros_solicitacao_conhecidos.add(numero_solicitacao)
                    resumo_execucao["ok"] += 1
                    logger(f"Linha {linha_excel}: OK | solicitacao={numero_solicitacao or 'nao capturada'}")
                else:
                    updates_excel.append((linha_excel, "TESTE", "Fluxo executado ate antes do envio final."))
                    updates_solicitacao.append((linha_excel, ""))
                    resumo_execucao["teste"] += 1
                    logger(f"Linha {linha_excel}: TESTE | envio final bloqueado propositalmente.")
            except ErroRegistroEsperado as exc:
                mensagem = str(exc) or "Falha sem mensagem"
                updates_excel.append((linha_excel, "ERRO", mensagem))
                resumo_execucao["erro"] += 1
                logger(f"Linha {linha_excel}: ERRO | {mensagem}")
            except Exception as exc:
                mensagem = str(exc) or "Falha sem mensagem"
                updates_excel.append((linha_excel, "ERRO", mensagem))
                resumo_execucao["erro"] += 1
                logger(f"Linha {linha_excel}: ERRO | {mensagem}")
                logger(traceback.format_exc().strip())
    except Exception as exc:
        logger(f"Falha antes ou durante a fase inicial da automacao: {exc}")
        logger(traceback.format_exc().strip())
        if driver is not None:
            logger(
                "Estado do navegador no momento da falha inicial "
                f"(url_atual={safe_current_url(driver)}, titulo={safe_title(driver)!r})."
            )
        raise
    finally:
        try:
            if driver is not None:
                driver.quit()
        except Exception:
            pass

    atualizar_status_mensagem_no_excel(planilha_trabalho, updates_excel)
    atualizar_numero_solicitacao_no_excel(planilha_trabalho, updates_solicitacao)
    salvar_resumo(
        pasta_saida,
        planilha_trabalho,
        updates_excel,
        updates_solicitacao,
        resumo_execucao,
    )
    logger(
        "Resumo final da execucao: "
        f"OK={resumo_execucao['ok']}, "
        f"ERRO={resumo_execucao['erro']}, "
        f"TESTE={resumo_execucao['teste']}, "
        f"PULADO_OK={resumo_execucao['pulado_ok']}."
    )
    modo_envio = "habilitado" if envio_final_habilitado(parametros_execucao) else "bloqueado"
    return {
        "message": (
            f"Medicao BlueEZ concluida. Arquivo gerado: {planilha_trabalho.name}. "
            f"Envio final estava {modo_envio}. "
            f"Resumo: OK={resumo_execucao['ok']}, ERRO={resumo_execucao['erro']}, "
            f"TESTE={resumo_execucao['teste']}, PULADO_OK={resumo_execucao['pulado_ok']}."
        )
    }


def carregar_parametros(parametros, parametros_json):
    if isinstance(parametros_json, dict):
        return dict(parametros_json)
    texto = (parametros or "").strip()
    if not texto:
        return {}
    try:
        valor = json.loads(texto)
        return valor if isinstance(valor, dict) else {"raw": valor}
    except json.JSONDecodeError:
        return {"raw": texto}


def resolver_credenciais(caminho_planilha, parametros_execucao):
    credenciais_planilha = ler_credenciais_da_planilha(caminho_planilha)
    if credenciais_planilha.get("username") and credenciais_planilha.get("password"):
        return credenciais_planilha

    username = parametros_execucao.get("username") or parametros_execucao.get("usuario") or os.getenv("BLUEEZ_USERNAME")
    password = parametros_execucao.get("password") or parametros_execucao.get("senha") or os.getenv("BLUEEZ_PASSWORD")
    if username and password:
        return {"username": username, "password": password}

    raise AbortarAutomacao(
        "Credenciais do BlueEZ ausentes. Coloque usuario e senha em uma aba separada da planilha principal "
        "ou informe username/password em parametros_texto (JSON) / variaveis de ambiente."
    )


def ler_credenciais_da_planilha(caminho_planilha):
    try:
        workbook = load_workbook(caminho_planilha, read_only=True, data_only=True)
    except Exception as exc:
        raise AbortarAutomacao(f"Nao foi possivel ler a planilha principal: {exc}") from exc

    sheet = None
    for nome in workbook.sheetnames:
        if nome.strip().lower() in {"credenciais", "login", "acesso", "usuario"}:
            sheet = workbook[nome]
            break

    if sheet is None:
        if len(workbook.sheetnames) >= 2:
            sheet = workbook[workbook.sheetnames[1]]
        else:
            return {}

    header_row = next(sheet.iter_rows(min_row=1, max_row=1, values_only=True), None)
    if not header_row:
        return {}

    headers = [normalizar_chave_excel(valor) for valor in header_row]
    values_row = next(sheet.iter_rows(min_row=2, max_row=2, values_only=True), None)
    if not values_row:
        return {}

    data = {headers[idx]: values_row[idx] for idx in range(min(len(headers), len(values_row))) if headers[idx]}
    username = (
        data.get("usuario")
        or data.get("username")
        or data.get("login")
        or data.get("user")
    )
    password = (
        data.get("senha")
        or data.get("password")
        or data.get("pass")
    )
    return {
        "username": "" if username is None else str(username).strip(),
        "password": "" if password is None else str(password).strip(),
    }


def selecionar_planilha(arquivos_principais, input_path):
    candidatos = list(arquivos_principais)
    if input_path:
        candidatos.insert(0, Path(input_path))
    for arquivo in candidatos:
        if arquivo.suffix.lower() in {".xlsx", ".xlsm", ".xls"}:
            return arquivo
    raise AbortarAutomacao("Nenhuma planilha Excel foi enviada como arquivo principal.")


def copiar_planilha(planilha_entrada, pasta_saida):
    destino = pasta_saida / f"entrada_processada_{datetime.now().strftime('%Y%m%d_%H%M%S')}{planilha_entrada.suffix}"
    shutil.copy2(planilha_entrada, destino)
    return destino


def validar_planilha(df):
    faltando = [coluna for coluna in COLUNAS_OBRIGATORIAS if coluna not in df.columns]
    if faltando:
        raise AbortarAutomacao("Planilha invalida. Colunas ausentes: " + ", ".join(sorted(faltando)))


def carregar_numeros_solicitacao_existentes(df):
    numeros = set()
    for coluna in df.columns:
        if str(coluna).strip().lower() != "numero_solicitacao":
            continue
        for valor in df[coluna].tolist():
            if pd.isna(valor):
                continue
            numero = str(valor).strip()
            if numero:
                numeros.add(numero)
    return numeros


def deve_pular_registro(status_atual):
    return status_atual == "OK"




def normalizar_chave_excel(valor):
    texto = "" if valor is None else str(valor).strip().lower()
    texto = texto.replace(" ", "_")
    texto = re.sub(r"[^a-z0-9_]", "", texto)
    return texto


def iniciar_driver(parametros_execucao):
    options = Options()
    if bool(parametros_execucao.get("headless", True)):
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--lang=pt-BR")
    options.add_argument("--accept-lang=pt-BR,pt")
    options.add_argument(f'--window-size={parametros_execucao.get("window_size", "1280,900")}')
    options.add_argument("--disable-extensions")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    chrome_binary = parametros_execucao.get("chrome_binary")
    if chrome_binary:
        options.binary_location = chrome_binary
    elif os.name != "nt":
        options.binary_location = "/usr/bin/chromium"

    driver_path = parametros_execucao.get("driver_path")
    if not driver_path and os.name != "nt" and Path("/usr/bin/chromedriver").exists():
        driver_path = "/usr/bin/chromedriver"

    service = Service(executable_path=driver_path) if driver_path else Service()
    return webdriver.Chrome(service=service, options=options)


def login_blueez(driver, wait, pause, credenciais, logger, parametros_execucao):
    target_url = parametros_execucao.get("base_url", BASE_URL) + "/"
    logger(f"Abrindo portal BlueEZ em {target_url}")
    driver.get(target_url)
    pause()
    logger(
        "Pagina inicial carregada "
        f"(url_atual={safe_current_url(driver)}, titulo={safe_title(driver)!r})."
    )
    try:
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[name="j_username"]')))
        logger("Formulario de login detectado. Preenchendo credenciais da planilha.")
    except TimeoutException:
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#sidebarMenu, nav#sidebarMenu, .wrapperSidebarMenu")))
        logger(
            "Sessao reaproveitada detectada no BlueEZ "
            f"(url_atual={safe_current_url(driver)}, titulo={safe_title(driver)!r})."
        )
        return

    preencher_input(wait, 'input[name="j_username"]', credenciais["username"], pause)
    preencher_input(wait, 'input[name="j_password"]', credenciais["password"], pause)
    logger(f"Credenciais preenchidas para o usuario {credenciais['username']}. Enviando formulario.")
    driver.execute_script("const form = document.querySelector('form'); if (form) form.submit();")
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#sidebarMenu, nav#sidebarMenu, .wrapperSidebarMenu")))
    logger(
        f"Login realizado com sucesso para o usuario {credenciais['username']} "
        f"(url_atual={safe_current_url(driver)}, titulo={safe_title(driver)!r})."
    )


def processar_registro(
    driver,
    wait,
    pause,
    registro,
    attachment_index,
    parametros_execucao,
    logger,
    numeros_solicitacao_conhecidos,
):
    logger("Abrindo tela inicial do BlueEZ para o registro atual.")
    driver.get(BASE_URL)
    pause()
    logger("Entrando no menu Medicao.")
    entrar_medicao(driver, wait, pause)
    numero_topo_anterior = capturar_numero_topo_grid_atual(driver)
    logger(
        "Ultimo numero visivel no grid antes do envio: "
        f"{numero_topo_anterior or 'nenhum registro visivel'}"
    )
    logger("Tela de Medicao aberta. Iniciando novo fluxo.")
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#new_flow"))).click()
    pause()
    reentrar_iframe(driver, wait, pause)
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".modal.fade.show, .modal.show")))
    logger("Formulario de medicao aberto com sucesso.")

    logger(f"Selecionando empresa: {str(registro['empresa']).strip()}")
    selecionar_modal(
        driver,
        wait,
        pause,
        'button[data-target="#modal_zoom_empresa_medicao_1"]',
        str(registro["empresa"]).strip(),
        "Empresa",
        "#id_descricao_empresa",
    )
    logger("Empresa selecionada com sucesso.")
    logger(f"Selecionando estabelecimento: {str(registro['estabelecimento']).strip()}")
    selecionar_modal(
        driver,
        wait,
        pause,
        'button[data-target="#modal_zoom_estabelecimento_medicao_1"]',
        str(registro["estabelecimento"]).strip(),
        "Estabelecimento",
        "#id_descricao_estabelecimento",
    )
    logger("Estabelecimento selecionado com sucesso.")
    logger(f"Selecionando fornecedor pelo CNPJ: {registro['cnpj_fornecedor']}")
    selecionar_fornecedor(driver, wait, pause, registro["cnpj_fornecedor"])
    logger("Fornecedor selecionado com sucesso.")
    logger(f"Selecionando contrato: {registro['contrato']}")
    selecionar_contrato(driver, wait, pause, registro["contrato"])
    logger("Contrato selecionado com sucesso.")
    logger("Preenchendo datas da medicao.")
    preencher_datas(driver, wait, pause, registro)
    logger(
        "Datas preenchidas com sucesso "
        f"(inicio={formatar_data(registro['data_inicio'])}, "
        f"fim={formatar_data(registro['data_fim'])}, "
        f"competencia={formatar_competencia(registro['competencia'])})."
    )
    logger(f"Preenchendo numero da NF: {registro['id_nf']}")
    preencher_input_tab(wait, "#id_nf_medicao", str(registro["id_nf"]), pause)
    logger("Numero da NF preenchido com sucesso.")
    logger(
        "Preenchendo item medido "
        f"(item={registro['item_medido']}, valor={registro['valor_item']})."
    )
    preencher_item_medido(driver, wait, pause, registro["item_medido"], registro["valor_item"])
    logger("Item medido preenchido com sucesso.")
    logger("Preenchendo observacao.")
    preencher_observacao(wait, pause, registro["observacao"])
    logger("Observacao preenchida com sucesso.")
    nomes_esperados = listar_nomes_anexos_registro(registro)
    if nomes_esperados:
        logger("Resolvendo anexos do registro: " + ", ".join(nomes_esperados))
    else:
        logger("Registro sem anexos informados na planilha.")
    arquivos_upload = resolver_arquivos_registro(registro, attachment_index, logger)
    if arquivos_upload:
        logger(
            "Anexos localizados para upload: "
            + ", ".join(arquivo.name for arquivo in arquivos_upload)
        )
    fazer_upload(wait, pause, arquivos_upload, logger)
    if not envio_final_habilitado(parametros_execucao):
        logger("Teste seguro: clique final de envio bloqueado por configuracao.")
        return {"enviado": False, "numero_solicitacao": ""}
    logger("Clique final habilitado. Enviando solicitacao.")
    clicar_enviar(driver, wait, pause)
    logger("Solicitacao enviada. Validando criacao do novo registro no grid.")
    numero_solicitacao = validar_e_capturar_nova_solicitacao(
        driver,
        wait,
        pause,
        numero_topo_anterior,
        numeros_solicitacao_conhecidos,
        logger,
    )
    return {"enviado": True, "numero_solicitacao": numero_solicitacao}


def entrar_medicao(driver, wait, pause):
    driver.switch_to.default_content()
    dropdown = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a.dropdownSidebar-toggle[aria-controls="pageSubmenu30"]')))
    submenu_visivel = driver.execute_script("const el = document.querySelector('#pageSubmenu30'); return !!(el && el.offsetParent !== null);")
    if not submenu_visivel:
        dropdown.click()
        pause()
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#pageSubmenu30")))
    wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="pageSubmenu30"]//span[normalize-space()="Medição"]'))).click()
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#iframeContent")))
    driver.switch_to.frame(driver.find_element(By.CSS_SELECTOR, "iframe#iframeContent"))
    pause()


def reentrar_iframe(driver, wait, pause):
    driver.switch_to.default_content()
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#iframeContent")))
    driver.switch_to.frame(driver.find_element(By.CSS_SELECTOR, "iframe#iframeContent"))
    pause()


def selecionar_modal(driver, wait, pause, seletor_botao, termo_busca, label, seletor_resultado=None):
    botao = obter_elemento_clicavel(
        driver,
        wait,
        seletor_botao,
        f"botao de selecao de {label}",
    )
    driver.execute_script("arguments[0].click();", botao)
    pause()
    modal_id = botao.get_attribute("data-target") or ""
    modal_selector = f"{modal_id} input.form-control[placeholder=\"Procurar\"]" if modal_id else 'input.form-control[placeholder="Procurar"]'
    campo = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, modal_selector)))
    campo.clear()
    campo.send_keys(termo_busca)
    campo.send_keys(Keys.ENTER)
    pause()

    linhas = []
    if modal_id:
        linhas = [
            linha
            for linha in driver.find_elements(By.CSS_SELECTOR, f"{modal_id} table tbody tr")
            if linha.is_displayed() and termo_busca.lower() in normalizar_texto(linha.text)
        ]
    if not linhas:
        sugestoes = coletar_amostra_modal(driver, modal_id)
        raise ValueError(montar_erro_busca(label, termo_busca, sugestoes))

    driver.execute_script("arguments[0].click();", linhas[0])
    pause()
    if seletor_resultado:
        wait.until(
            lambda d: termo_busca.lower() in normalizar_texto(
                d.find_element(By.CSS_SELECTOR, seletor_resultado).get_attribute("value") or ""
            )
        )


def selecionar_fornecedor(driver, wait, pause, cnpj):
    botao = obter_elemento_clicavel(
        driver,
        wait,
        'button[data-target="#modal_zoom_fornecedor_medicao_1"]',
        "botao de selecao de Fornecedor",
    )
    driver.execute_script("arguments[0].click();", botao)
    pause()
    cnpj_formatado = formatar_cnpj(cnpj)
    campo = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '#tabela_zoom_fornecedor_medicao_1_wrapper input.form-control[placeholder="Procurar"]')))
    campo.clear()
    campo.send_keys(cnpj_formatado)
    campo.send_keys(Keys.ENTER)
    pause(2)
    linhas = driver.find_elements(
        By.XPATH,
        f'//*[@id="tabela_zoom_fornecedor_medicao_1"]//tbody/tr[td[1][normalize-space()="{cnpj_formatado}"]]'
    )
    if not linhas:
        sugestoes = coletar_amostra_tabela(driver, "#tabela_zoom_fornecedor_medicao_1 tbody tr")
        raise ValueError(
            montar_erro_busca(
                "Fornecedor",
                cnpj_formatado,
                sugestoes,
                detalhe_extra="Verifique se o CNPJ da planilha existe e esta vinculado no BlueEZ.",
            )
        )
    linha = wait.until(EC.visibility_of(linhas[0]))
    driver.execute_script("arguments[0].click();", linha)
    pause()


def selecionar_contrato(driver, wait, pause, contrato):
    botao = obter_elemento_clicavel(
        driver,
        wait,
        'button[data-target="#modal_zoom_contrato_medicao_1"]',
        "botao de selecao de Contrato",
    )
    driver.execute_script("arguments[0].click();", botao)
    pause()
    numero_contrato = limpar_codigo_excel(contrato)
    seletores_busca = [
        '#tabela_zoom_contrato_medicao_1_wrapper input.form-control[placeholder="Procurar"]',
        '#modal_zoom_contrato_medicao_1 input.form-control[placeholder="Procurar"]',
        '#modal_zoom_contrato_medicao_1 input[type="text"]',
    ]
    campo = None
    for seletor in seletores_busca:
        elementos = driver.find_elements(By.CSS_SELECTOR, seletor)
        elementos_visiveis = [elemento for elemento in elementos if elemento.is_displayed() and elemento.is_enabled()]
        if elementos_visiveis:
            campo = elementos_visiveis[0]
            break
    if campo is None:
        raise ValueError(
            "Campo de busca do Contrato nao apareceu no BlueEZ apos abrir o modal. "
            f"url_atual={safe_current_url(driver)} | titulo={safe_title(driver)!r}"
        )
    campo.clear()
    campo.send_keys(numero_contrato)
    campo.send_keys(Keys.ENTER)
    pause()
    linhas = [
        linha
        for linha in driver.find_elements(By.CSS_SELECTOR, "#tabela_zoom_contrato_medicao_1 tbody tr")
        if linha.is_displayed()
    ]
    if not linhas:
        sugestoes = coletar_amostra_tabela(driver, "#tabela_zoom_contrato_medicao_1 tbody tr")
        raise ValueError(
            montar_erro_busca(
                "Contrato",
                numero_contrato,
                sugestoes,
                detalhe_extra="Confirme se o numero do contrato esta correto e disponivel para o usuario logado.",
            )
        )
    driver.execute_script("arguments[0].click();", linhas[0])
    pause()


def preencher_datas(driver, wait, pause, registro):
    for seletor, valor in {
        "#id_data_inicio": formatar_data(registro["data_inicio"]),
        "#id_data_fim": formatar_data(registro["data_fim"]),
        "#id_competencia": formatar_competencia(registro["competencia"]),
        "#id_data_emissao": formatar_data(registro["emissao_nf"]),
        "#id_data_vencimento": formatar_data(registro["vencimento_nf"]),
    }.items():
        preencher_input_tab(wait, seletor, valor, pause)


def preencher_item_medido(driver, wait, pause, item_medido, valor_item):
    campos = driver.find_elements(By.CSS_SELECTOR, 'div[class^="linha_valor_"] input.form-control.input-blueez')
    indice = int(float(item_medido)) - 1
    if indice < 0 or indice >= len(campos):
        raise ValueError(f"item_medido invalido: {item_medido}")
    valor = f"{float(valor_item):.2f}".replace(".", ",")
    for posicao, campo in enumerate(campos):
        preencher_elemento_tab(campo, valor if posicao == indice else "0,00", pause)


def preencher_observacao(wait, pause, observacao):
    campo = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#id_observacao_medicao")))
    campo.clear()
    pause()
    campo.send_keys("" if pd.isna(observacao) else str(observacao))
    pause()


def fazer_upload(wait, pause, arquivos, logger=None):
    if not arquivos:
        if logger:
            logger("Nenhum anexo para enviar neste registro.")
        return
    if logger:
        logger("Abrindo aba de anexos.")
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[href="#content_tab_1_50"]'))).click()
    pause()
    if logger:
        logger("Aba de anexos aberta. Clicando em novo anexo.")
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn-orange-componente"))).click()
    pause()
    if logger:
        logger("Campo de upload localizado. Enviando arquivos para o navegador.")
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#upload-file"))).send_keys("\n".join(str(arquivo) for arquivo in arquivos))
    pause()
    if logger:
        logger("Arquivos enviados ao input. Acionando upload no BlueEZ.")
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn-upload-files"))).click()
    pause(2)
    if logger:
        logger("Comando de upload executado. Prosseguindo para a proxima etapa.")


def clicar_enviar(driver, wait, pause):
    driver.switch_to.default_content()
    pause()
    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#iframeContent")))
        driver.switch_to.frame(driver.find_element(By.CSS_SELECTOR, "iframe#iframeContent"))
    except Exception:
        pass
    for seletor in ["#botao_enviar_solicitacao_0", 'button[id^="botao_enviar_solicitacao_"]', "button.btn-success", 'button[type="submit"]']:
        botoes = driver.find_elements(By.CSS_SELECTOR, seletor)
        for botao in botoes:
            if botao.is_displayed() and botao.is_enabled():
                driver.execute_script("arguments[0].click();", botao)
                pause(2)
                return
    raise TimeoutException("Botao de enviar nao encontrado no contexto atual.")


def capturar_numero_solicitacao(driver, wait, pause):
    reentrar_iframe(driver, wait, pause)
    linha = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#DataTables_Table_0 tbody tr")))
    colunas = linha.find_elements(By.TAG_NAME, "td")
    return (colunas[0].text or "").strip() if colunas else ""


def capturar_numero_topo_grid_atual(driver):
    try:
        linhas = driver.find_elements(By.CSS_SELECTOR, "#DataTables_Table_0 tbody tr")
        for linha in linhas:
            if not linha.is_displayed():
                continue
            colunas = linha.find_elements(By.TAG_NAME, "td")
            if not colunas:
                continue
            numero = (colunas[0].text or "").strip()
            if numero:
                return numero
    except Exception:
        return ""
    return ""


def validar_e_capturar_nova_solicitacao(
    driver,
    wait,
    pause,
    numero_topo_anterior,
    numeros_solicitacao_conhecidos,
    logger,
    timeout=25,
):
    fim = time.time() + timeout
    ultimo_numero_lido = ""

    while time.time() < fim:
        numero_atual = capturar_numero_solicitacao(driver, wait, pause)
        ultimo_numero_lido = numero_atual

        if not numero_atual:
            time.sleep(1)
            continue

        if numero_topo_anterior and numero_atual == numero_topo_anterior:
            time.sleep(1)
            continue

        if numero_atual in numeros_solicitacao_conhecidos:
            raise ValueError(
                "O BlueEZ retornou um numero de solicitacao que ja existe na planilha/execucao: "
                f"{numero_atual}. Isso indica que o novo registro provavelmente nao foi criado."
            )

        logger(f"Novo numero de solicitacao capturado com sucesso: {numero_atual}")
        return numero_atual

    if numero_topo_anterior and ultimo_numero_lido == numero_topo_anterior:
        raise ValueError(
            "O BlueEZ voltou para o grid, mas o ultimo numero visivel permaneceu igual ao registro anterior "
            f"({numero_topo_anterior}). Isso indica que a medicao atual provavelmente nao foi salva."
        )

    raise ValueError(
        "Nao foi possivel confirmar a criacao de um novo registro no grid do BlueEZ apos o envio."
    )


def preencher_input(wait, seletor, valor, pause):
    campo = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, seletor)))
    campo.clear()
    pause()
    campo.send_keys(valor)
    pause()


def preencher_input_tab(wait, seletor, valor, pause):
    campo = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, seletor)))
    preencher_elemento_tab(campo, valor, pause)


def preencher_elemento_tab(campo, valor, pause):
    campo.click()
    pause()
    campo.send_keys(Keys.CONTROL, "a")
    pause()
    campo.send_keys(Keys.BACKSPACE)
    pause()
    campo.send_keys(valor)
    pause()
    campo.send_keys(Keys.TAB)
    pause()


def indexar_anexos(anexos, logger=None):
    indexed = {}
    for anexo in anexos:
        anexo_normalizado = normalizar_extensao_minuscula(anexo, logger)
        indexed[anexo_normalizado.name.lower()] = anexo_normalizado
    return indexed


def resolver_arquivos_registro(registro, attachment_index, logger=None):
    arquivos = []
    anexos_disponiveis = listar_anexos_disponiveis(attachment_index)
    sem_anexos_enviados = not attachment_index
    for chave in ["arquivo_1", "arquivo_2"]:
        nome = registro.get(chave)
        if not isinstance(nome, str) or not nome.strip():
            continue
        nome_limpo = nome.strip()
        if logger:
            logger(f"Procurando anexo informado na planilha: {nome_limpo}")
        encontrado = localizar_anexo(nome_limpo, attachment_index, logger)
        if not encontrado:
            if sem_anexos_enviados:
                raise ErroRegistroEsperado(
                    "A linha exige arquivo auxiliar, mas nenhum anexo foi enviado nesta execucao. "
                    f"Arquivo esperado pela planilha: {nome_limpo}. "
                    "Envie os arquivos no campo 'Arquivos auxiliares' para processar esta linha."
                )
            raise ErroRegistroEsperado(
                "Arquivo auxiliar nao localizado para esta linha. "
                f"Arquivo esperado pela planilha: {nome_limpo}. "
                f"Anexos recebidos na execucao: {anexos_disponiveis}"
            )
        arquivos.append(encontrado)
    return arquivos


def localizar_anexo(nome, attachment_index, logger=None):
    chave = nome.lower()
    if chave in attachment_index:
        if logger:
            logger(f"Anexo localizado por nome exato: {attachment_index[chave].name}")
        return attachment_index[chave]

    base, extensao = os.path.splitext(nome)
    if not extensao:
        chave_pdf = f"{base}.pdf".lower()
        if chave_pdf in attachment_index:
            if logger:
                logger(
                    "Anexo localizado assumindo extensao .pdf ausente na planilha: "
                    f"{attachment_index[chave_pdf].name}"
                )
            return attachment_index[chave_pdf]

    nome_normalizado = normalizar_nome_anexo(nome)
    stem_normalizado = normalizar_nome_anexo(base or nome)

    candidatos_nome = []
    candidatos_stem = []
    candidatos_parciais = []
    for caminho in attachment_index.values():
        nome_arquivo_normalizado = normalizar_nome_anexo(caminho.name)
        stem_arquivo_normalizado = normalizar_nome_anexo(caminho.stem)

        if nome_normalizado and nome_normalizado == nome_arquivo_normalizado:
            candidatos_nome.append(caminho)
            continue

        if stem_normalizado and stem_normalizado == stem_arquivo_normalizado:
            candidatos_stem.append(caminho)
            continue

        pontuacao = pontuar_correspondencia_anexo(stem_normalizado, stem_arquivo_normalizado)
        if pontuacao > 0:
            candidatos_parciais.append((pontuacao, caminho))

    if len(candidatos_nome) == 1:
        if logger:
            logger(
                "Anexo localizado por normalizacao de nome "
                f"(acentos/espacos/caracteres): {candidatos_nome[0].name}"
            )
        return candidatos_nome[0]

    if len(candidatos_stem) == 1:
        if logger:
            logger(
                "Anexo localizado por nome base, ignorando extensao: "
                f"{candidatos_stem[0].name}"
            )
        return candidatos_stem[0]

    if candidatos_parciais:
        candidatos_parciais.sort(
            key=lambda item: (
                item[0],
                len(normalizar_nome_anexo(item[1].stem)),
            ),
            reverse=True,
        )
        melhor_pontuacao, melhor_caminho = candidatos_parciais[0]
        if len(candidatos_parciais) == 1 or (
            len(candidatos_parciais) > 1 and melhor_pontuacao > candidatos_parciais[1][0]
        ):
            if logger:
                logger(
                    "Anexo localizado por correspondencia parcial inteligente: "
                    f"{melhor_caminho.name} (score={melhor_pontuacao})"
                )
            return melhor_caminho
    return None


def listar_nomes_anexos_registro(registro):
    nomes = []
    for chave in ["arquivo_1", "arquivo_2"]:
        valor = registro.get(chave)
        if isinstance(valor, str) and valor.strip():
            nomes.append(valor.strip())
    return nomes


def listar_anexos_disponiveis(attachment_index):
    nomes = sorted(caminho.name for caminho in attachment_index.values())
    return ", ".join(nomes) if nomes else "nenhum arquivo auxiliar foi enviado"


def normalizar_extensao_minuscula(anexo, logger=None):
    sufixo = anexo.suffix
    if not sufixo or sufixo == sufixo.lower():
        return anexo

    destino = anexo.with_name(f"{anexo.stem}{sufixo.lower()}")
    if destino == anexo:
        return anexo

    if destino.exists():
        if logger:
            logger(
                "Extensao em maiuscula detectada, mas ja existe arquivo com extensao minuscula. "
                f"Usando {destino.name} no lugar de {anexo.name}."
            )
        return destino

    anexo.rename(destino)
    if logger:
        logger(
            "Extensao do anexo ajustada para minuscula: "
            f"{anexo.name} -> {destino.name}"
        )
    return destino


def normalizar_nome_anexo(valor):
    texto = normalizar_texto(valor)
    texto = re.sub(r"\s+", " ", texto).strip()
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def pontuar_correspondencia_anexo(nome_buscado, nome_candidato):
    if not nome_buscado or not nome_candidato:
        return 0
    if nome_buscado == nome_candidato:
        return 1000
    if nome_buscado in nome_candidato:
        return 900 - abs(len(nome_candidato) - len(nome_buscado))

    tokens_buscados = [token for token in nome_buscado.split() if token]
    tokens_candidato = [token for token in nome_candidato.split() if token]
    if not tokens_buscados or not tokens_candidato:
        return 0

    conjunto_candidato = set(tokens_candidato)
    intersecao = [token for token in tokens_buscados if token in conjunto_candidato]
    if not intersecao:
        return 0

    if all(token in conjunto_candidato for token in tokens_buscados):
        return 800 - abs(len(tokens_candidato) - len(tokens_buscados))

    score = len(intersecao) * 100
    if tokens_buscados[0] in conjunto_candidato:
        score += 25
    if tokens_buscados[-1] in conjunto_candidato:
        score += 25
    return score if len(intersecao) >= max(2, len(tokens_buscados) - 1) else 0


def ler_status(df, idx):
    for coluna in df.columns:
        chave = str(coluna).strip().lower()
        if chave == "status" or chave.startswith("status."):
            valor = df.loc[idx, coluna]
            if pd.notna(valor) and str(valor).strip():
                return str(valor)
    return ""


def atualizar_status_mensagem_no_excel(caminho_xlsx, updates):
    wb = load_workbook(caminho_xlsx)
    ws = wb.active
    col_status = garantir_coluna(ws, "status")
    col_mensagem = garantir_coluna(ws, "mensagem")
    for linha, status, mensagem in updates:
        ws.cell(row=int(linha), column=col_status).value = str(status)
        ws.cell(row=int(linha), column=col_mensagem).value = str(mensagem)
    wb.save(caminho_xlsx)


def atualizar_numero_solicitacao_no_excel(caminho_xlsx, updates):
    wb = load_workbook(caminho_xlsx)
    ws = wb.active
    col_solicitacao = garantir_coluna(ws, "numero_solicitacao")
    for linha, numero in updates:
        ws.cell(row=int(linha), column=col_solicitacao).value = str(numero)
    wb.save(caminho_xlsx)


def garantir_coluna(ws, nome):
    for coluna in range(1, ws.max_column + 1):
        valor = ws.cell(row=1, column=coluna).value
        if valor is not None and str(valor).strip().lower() == nome:
            return coluna
    coluna = ws.max_column + 1
    ws.cell(row=1, column=coluna).value = nome
    return coluna


def envio_final_habilitado(parametros_execucao):
    valor = parametros_execucao.get("confirm_submission")
    if valor is None:
        valor = parametros_execucao.get("submit")
    if valor is None:
        valor = parametros_execucao.get("modo_producao")
    return str(valor).strip().lower() in {"1", "true", "t", "yes", "y", "on"}


def salvar_resumo(pasta_saida, planilha_trabalho, updates_excel, updates_solicitacao, resumo_execucao):
    resumo = {
        "planilha_saida": planilha_trabalho.name,
        "gerado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "resumo_execucao": {
            "ok": resumo_execucao.get("ok", 0),
            "erro": resumo_execucao.get("erro", 0),
            "teste": resumo_execucao.get("teste", 0),
            "pulado_ok": resumo_execucao.get("pulado_ok", 0),
            "total_processado": (
                resumo_execucao.get("ok", 0)
                + resumo_execucao.get("erro", 0)
                + resumo_execucao.get("teste", 0)
            ),
        },
        "status": updates_excel,
        "solicitacoes": updates_solicitacao,
    }
    (pasta_saida / "resumo_execucao.json").write_text(json.dumps(resumo, ensure_ascii=True, indent=2), encoding="utf-8")
    salvar_resumo_em_aba_planilha(planilha_trabalho, resumo, updates_excel, updates_solicitacao)


def salvar_resumo_em_aba_planilha(planilha_trabalho, resumo, updates_excel, updates_solicitacao):
    wb = load_workbook(planilha_trabalho)
    nome_aba = "Resumo_Execucao"
    if nome_aba in wb.sheetnames:
        ws = wb[nome_aba]
        ws.delete_rows(1, ws.max_row)
    else:
        ws = wb.create_sheet(nome_aba)

    resumo_execucao = resumo.get("resumo_execucao", {})
    linhas = [
        ("planilha_saida", resumo.get("planilha_saida", "")),
        ("gerado_em", resumo.get("gerado_em", "")),
        ("ok", resumo_execucao.get("ok", 0)),
        ("erro", resumo_execucao.get("erro", 0)),
        ("teste", resumo_execucao.get("teste", 0)),
        ("pulado_ok", resumo_execucao.get("pulado_ok", 0)),
        ("total_processado", resumo_execucao.get("total_processado", 0)),
    ]

    ws["A1"] = "campo"
    ws["B1"] = "valor"
    for indice, (campo, valor) in enumerate(linhas, start=2):
        ws.cell(row=indice, column=1).value = campo
        ws.cell(row=indice, column=2).value = valor

    inicio_status = len(linhas) + 4
    ws.cell(row=inicio_status, column=1).value = "linha_planilha"
    ws.cell(row=inicio_status, column=2).value = "status"
    ws.cell(row=inicio_status, column=3).value = "mensagem"
    for offset, (linha, status, mensagem) in enumerate(updates_excel, start=1):
        ws.cell(row=inicio_status + offset, column=1).value = linha
        ws.cell(row=inicio_status + offset, column=2).value = status
        ws.cell(row=inicio_status + offset, column=3).value = mensagem

    inicio_solic = inicio_status + len(updates_excel) + 3
    ws.cell(row=inicio_solic, column=1).value = "linha_planilha"
    ws.cell(row=inicio_solic, column=2).value = "numero_solicitacao"
    for offset, (linha, numero) in enumerate(updates_solicitacao, start=1):
        ws.cell(row=inicio_solic + offset, column=1).value = linha
        ws.cell(row=inicio_solic + offset, column=2).value = numero

    wb.save(planilha_trabalho)


def coletar_amostra_modal(driver, modal_id, limite=5):
    if not modal_id:
        return []
    seletor = f"{modal_id} table tbody tr"
    return coletar_amostra_tabela(driver, seletor, limite=limite)


def coletar_amostra_tabela(driver, seletor, limite=5):
    amostra = []
    for linha in driver.find_elements(By.CSS_SELECTOR, seletor)[:limite]:
        try:
            texto = " | ".join(
                celula.text.strip()
                for celula in linha.find_elements(By.TAG_NAME, "td")
                if celula.text.strip()
            ).strip()
        except Exception:
            texto = ""
        if texto:
            amostra.append(texto)
    return amostra


def montar_erro_busca(label, termo_busca, sugestoes=None, detalhe_extra=""):
    mensagem = (
        f"{label} nao encontrado(a) no BlueEZ para o valor informado na planilha: '{termo_busca}'. "
        f"Revise o cadastro ou ajuste o texto enviado."
    )
    if detalhe_extra:
        mensagem += f" {detalhe_extra}"
    if sugestoes:
        mensagem += " Itens exibidos na busca: " + " || ".join(sugestoes)
    return mensagem


def obter_elemento_clicavel(driver, wait, seletor_css, descricao):
    try:
        return wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_css)))
    except TimeoutException as exc:
        candidatos = driver.find_elements(By.CSS_SELECTOR, seletor_css)
        detalhes = []
        if candidatos:
            for indice, elemento in enumerate(candidatos[:3], start=1):
                try:
                    detalhes.append(
                        (
                            f"candidato {indice}: exibido={elemento.is_displayed()} "
                            f"habilitado={elemento.is_enabled()} "
                            f"texto='{(elemento.text or '').strip()}' "
                            f"html='{(elemento.get_attribute('outerHTML') or '')[:180]}'"
                        )
                    )
                except Exception:
                    detalhes.append(f"candidato {indice}: estado indisponivel")
        else:
            detalhes.append("nenhum elemento encontrado com esse seletor")

        contexto = (
            f"url_atual={safe_current_url(driver)} | titulo={safe_title(driver)!r} | "
            f"seletor={seletor_css!r}"
        )
        raise ValueError(
            f"Nao foi possivel interagir com {descricao} no BlueEZ. "
            f"{contexto}. Detalhes: {' || '.join(detalhes)}"
        ) from exc


def safe_capability(driver, key):
    try:
        return driver.capabilities.get(key)
    except Exception:
        return None


def safe_current_url(driver):
    try:
        return driver.current_url
    except Exception:
        return "indisponivel"


def safe_title(driver):
    try:
        return driver.title
    except Exception:
        return "indisponivel"


def limpar_codigo_excel(valor):
    texto = "" if pd.isna(valor) else str(valor).strip()
    return texto[:-2] if texto.endswith(".0") else texto


def normaliza_nome(valor):
    return "".join(ch for ch in str(valor).lower() if ch.isalnum())


def normalizar_texto(valor):
    if valor is None:
        return ""
    texto = str(valor).replace("\n", " ").strip().lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(ch for ch in texto if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", texto)


def formatar_cnpj(valor):
    digitos = re.sub(r"\D+", "", str(valor or ""))
    if len(digitos) != 14:
        raise ValueError(f"CNPJ invalido: {valor!r}")
    return f"{digitos[:2]}.{digitos[2:5]}.{digitos[5:8]}/{digitos[8:12]}-{digitos[12:]}"


def formatar_data(valor):
    data = converter_data_excel(valor)
    if pd.isna(data):
        raise ValueError(f"Data invalida: {valor!r}")
    return data.strftime("%d/%m/%Y")


def formatar_competencia(valor):
    data = converter_data_excel(valor)
    if pd.isna(data):
        raise ValueError(f"Competencia invalida: {valor!r}")
    return data.strftime("%m/%Y")


def converter_data_excel(valor):
    if pd.isna(valor):
        return pd.NaT
    if isinstance(valor, (int, float)):
        numero = float(valor)
        if 1 <= numero <= 60000:
            return pd.to_datetime(numero, unit="D", origin="1899-12-30", errors="coerce")
    return pd.to_datetime(valor, dayfirst=True, errors="coerce")
