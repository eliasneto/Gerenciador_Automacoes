# AutoControllers

Plataforma Django para gerenciamento de automacoes por setor, com execucao manual, controle de arquivos, logs, documentacao operacional e auditoria.

## Visao geral

O sistema foi organizado para separar claramente:

- autenticacao de usuarios
- modulos de negocio por setor
- cadastro administrativo de automacoes
- execucao manual de automacoes Python
- documentacao funcional das automacoes
- auditoria de documentos e de visualizacao
- fila de execucao de automacoes
- API separada para integracao externa
- controle de acesso por grupo e por dashboard

Os setores atuais sao:

- Comercial
- Financeiro
- TI

Cada setor continua como um app Django independente e possui sua propria pasta `automacoes/` para armazenar os arquivos Python executores.

## Principais funcionalidades

### Autenticacao e layout

- tela de login no padrao visual Speed
- menu lateral com navegacao por modulos
- dashboard principal
- layout responsivo para uso interno
- logout automatico por inatividade de 20 minutos

### Automacoes

- cadastro de automacoes por setor
- uma automacao pode ser criada para um ou varios setores pelo app `administrador`
- execucao manual por botao
- interrupcao de execucao por botao `Parar`
- suporte a:
  - ate 2 arquivos principais
  - arquivos auxiliares
  - arquivos de saida
- logs de execucao em modal tipo terminal
- download dos arquivos de saida no frontend
- limpeza automatica dos arquivos de entrada/anexos quando a execucao termina com sucesso e sem interrupcao
- fila de execucao com limite configuravel de concorrencia
- tela administrativa com todas as execucoes das automacoes
- monitoramento administrativo do ambiente e do consumo das execucoes em andamento
- automacoes de exemplo removidas da esteira de producao

### Dashboard

- cards com metricas consolidadas
- resumo de automacoes por setor
- grafico de barras com execucoes diarias dos ultimos 5 dias
- filtro por area e por automacao
- visao controlada por grupos de dashboard
- secoes vazias nao sao exibidas

### Documentacao

- `Documentacao Sistema` no menu principal para todos os usuarios autenticados
- criacao de documentos pelo modulo `documentacao`
- editor visual com:
  - negrito, italico e sublinhado
  - fonte e tamanho de fonte
  - alinhamento
  - listas
  - cores e destaque
  - links
  - imagens por URL ou do computador
- componentes prontos no editor:
  - bloco `Sucesso`
  - bloco `Aviso`
  - bloco `Atencao`
  - tabela
  - bloco de codigo
- modo `HTML avancado` para colar documentos completos com:
  - `style`
  - `table`
  - `pre`
  - `html`
  - `head`
  - `body`
- pagina de leitura simplificada para o usuario final
- documentos gerais do sistema e documentos vinculados a automacoes
- documentos publicados sem vinculo com automacao podem aparecer em:
  - `Sistema`
  - `Administracao`
  - `Comercial`
  - `Financeiro`
  - `TI`
- regra de negocio:
  - o documento so aparece para o usuario na automacao quando estiver com status `Publicado`
- ao editar um documento existente, ele volta automaticamente para `Rascunho`
- alteracao de status direto no grid de documentacoes
- ao salvar criacao ou edicao, o usuario volta direto para o grid
- seletor de vinculo com automacao por modal com filtro e grid
- pre-visualizacao do documento no grid administrativo

### API

- camada separada em `/api/`, sem substituir o fluxo web atual
- autenticacao por token do tipo `Bearer`
- endpoints para:
  - autenticacao
  - consulta de usuario autenticado
  - modulos
  - automacoes
  - execucoes
  - documentacoes publicadas
- paginação nativa nos endpoints de lista com:
  - `page`
  - `per_page`
- permissao alinhada com os mesmos grupos do sistema web

### Operacao administrativa

- `Painel Admin`
- `Criar Automacao`
- `Execuções`
- `Monitoramento`

Na area administrativa agora e possivel:

- ver todas as execucoes em uma grade unica
- filtrar por automacao, modulo, status e usuario
- abrir logs rapidamente
- acompanhar memoria, load average e storage visiveis no ambiente
- ver metricas por execucao em andamento:
  - PID
  - memoria atual
  - pico de memoria
  - CPU acumulada
  - duracao

### Auditoria de documentacao

- auditoria de criacao de documento
- auditoria de alteracoes de documento
- auditoria de mudanca de status
- snapshots com:
  - titulo
  - conteudo
  - status
  - versao
  - usuario
  - data e hora
  - vinculo com automacao
  - campos alterados
- comparacao de versoes no Django Admin com:
  - versao anterior
  - versao atual
  - comparacao lado a lado
  - diff visual do conteudo

### Auditoria de visualizacao

- registro de abertura do documento
- usuario que abriu
- data e hora de abertura
- data e hora de encerramento
- tempo de permanencia estimado
- sessao e user agent
- consulta pelo Django Admin

### Django Admin

- admin customizado com identidade visual do sistema
- logo no topo do admin
- nomes de modelos principais em portugues
- auditorias consultaveis diretamente pelo admin
- configuracao de fila de automacoes no admin

### Seguranca por grupo

Grupos de modulo:

- `Modulo Comercial`
- `Modulo Financeiro`
- `Modulo TI`
- `Modulo Documentacao`
- `Modulo Administracao`

Grupos de dashboard:

- `Dashboard Comercial`
- `Dashboard Financeiro`
- `Dashboard TI`

Regras:

- usuario so ve o modulo se estiver no grupo correspondente
- se nao estiver no grupo, o modulo nao aparece no frontend
- `superuser` ve tudo, mesmo sem grupo

## Estrutura principal do projeto

```text
accounts/
api/
administrador/
comercial/
  automacoes/
config/
core/
  management/
documentacao/
docker/
financeiro/
  automacoes/
ti/
  automacoes/
media/
  entradas/
  saidas/
  automacoes/
static/
  css/
  img/
templates/
Dockerfile
docker-compose.yml
.dockerignore
.env.example
```

## Onde colocar os arquivos das automacoes

Cada automacao Python deve ficar dentro da pasta `automacoes` do setor correspondente.

Exemplos:

```text
comercial/automacoes/pesquisar_youtube.py
financeiro/automacoes/conciliar_pagamentos.py
ti/automacoes/processar_inventario.py
```

O campo `executor_path` deve apontar para a funcao `executar` do arquivo.

Exemplo:

```text
comercial.automacoes.pesquisar_youtube.executar
```

## Contrato esperado de uma automacao

Cada automacao deve expor uma funcao `executar(...)`.

Exemplo simplificado:

```python
def executar(
    input_path=None,
    input_paths=None,
    attachments=None,
    output_dir=None,
    should_stop=None,
    log=None,
    parametros=None,
    parametros_json=None,
):
    if log:
        log("Iniciando automacao")

    arquivo_principal_1 = input_paths[0] if input_paths else None
    arquivo_principal_2 = input_paths[1] if input_paths and len(input_paths) > 1 else None
    anexos = attachments or []

    return {
        "message": "Automacao executada com sucesso."
    }
```

## Fluxo de uso das automacoes

1. Acesse o modulo desejado.
2. Escolha a automacao.
3. Abra o modal de arquivos.
4. Envie arquivos principais e auxiliares.
5. Clique em `Executar automacao`.
6. Se necessario, clique em `Parar automacao` durante a execucao.
7. Consulte o historico, os logs e os arquivos de saida no proprio modulo.

## Fluxo de documentacao

1. Acesse `Documentacao > Criar Documentacao`.
2. Crie um novo documento e, se quiser, vincule a uma automacao pelo seletor em modal.
3. Edite o conteudo no editor visual.
4. Ao salvar uma edicao, o documento volta para `Rascunho`.
5. Publique o documento pelo grid de documentacoes.
6. Quando estiver `Publicado`, ele passa a aparecer para o usuario na automacao.

## Docker e producao

### O sistema esta pronto para Docker?

Sim. O projeto agora possui base para rodar em container com:

- `Dockerfile`
- `docker-compose.yml`
- `.env.docker`
- `.env.server.example`
- `gunicorn`
- `whitenoise` para arquivos estaticos
- configuracao por variaveis de ambiente
- suporte a MySQL via `DATABASE_URL`
- `entrypoint` com `migrate` e `collectstatic`
- separacao entre container `web` e container `worker` para execucao das automacoes
- criacao automatica do superusuario inicial no container `web`
- tela administrativa de monitoramento preparada para ler metricas do ambiente Linux/Docker visiveis para a app

### O que foi ajustado para isso

- `config/settings.py` agora le configuracoes por ambiente
- `DEBUG`, `SECRET_KEY` e `ALLOWED_HOSTS` nao ficam mais presos ao modo local
- `DATABASE_URL` pode apontar para MySQL
- `STATIC_ROOT` e `WhiteNoise` foram configurados
- `media` pode ser servido pelo proprio Django quando necessario
- a fila foi reforcada para bancos transacionais e usa tratamento especifico para PostgreSQL quando aplicavel

### Como subir via Docker

```bash
docker-compose up --build -d
```

Depois acesse:

```text
http://127.0.0.1:8190/contas/login/
```

O `web` atende a aplicacao e o `worker` consome a fila de automacoes em paralelo.

Para acompanhar os logs:

```bash
docker-compose logs -f web
docker-compose logs -f worker
docker-compose logs -f db
```

Para parar tudo:

```bash
docker-compose down
```

### Usuario inicial no Docker

Ao subir o container `web`, o sistema cria ou atualiza automaticamente o superusuario inicial com base nas variaveis de ambiente.

No ambiente local Docker, o padrao atual e:

- usuario: `admin`
- email: `admin@local.test`
- senha: `admin123`

Esses valores ficam em `.env.docker` e devem ser alterados depois do primeiro acesso.

### Variaveis importantes

Use `.env.example` como referencia.

Principais variaveis:

- `DJANGO_DEBUG`
- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DATABASE_URL`
- `DJANGO_SESSION_COOKIE_SECURE`
- `DJANGO_CSRF_COOKIE_SECURE`
- `DJANGO_SERVE_MEDIA`
- `AUTOMATION_SCHEDULER_ENABLED`
- `AUTOMATION_WORKER_POLL_INTERVAL`
- `DJANGO_SUPERUSER_USERNAME`
- `DJANGO_SUPERUSER_EMAIL`
- `DJANGO_SUPERUSER_PASSWORD`

### Banco configurado em Docker

O projeto agora esta configurado para subir com MySQL no Docker.

O projeto ainda pode rodar com SQLite localmente, mas no container a configuracao padrao ficou apontada para MySQL.

Para separar responsabilidades, o compose usa:

- `web`: interface Django/Gunicorn
- `worker`: consumo da fila de automacoes
- `db`: MySQL 8.4

## RPA dentro de Docker

### O que roda bem em Docker

Esses tipos de automacao sao os mais adequados para container:

- leitura e escrita de Excel
- leitura de CSV
- leitura de PDF
- consumo de API
- scraping HTTP
- automacao web headless com `Playwright`
- automacao web com `Selenium` em modo headless
- geracao de arquivos de saida
- integracoes entre sistemas

### O que exige cuidado

Automacoes desktop com bibliotecas como `pyautogui` nao sao a melhor opcao para rodar em Docker de servidor.

Motivo:

- `pyautogui` depende de ambiente grafico
- em container, nao existe desktop real do usuario
- mesmo com `xvfb`, o robo interage com uma tela virtual do container, nao com a maquina fisica do usuario

Em resumo:

- para RPA web: prefira `Playwright`
- para integracoes e processamento de arquivos: Python puro, `requests`, `pandas`, `openpyxl`
- para RPA desktop tradicional: o ideal e um worker dedicado com GUI, VM Windows ou servidor com sessao grafica controlada

### Biblioteca mais indicada para Docker

A melhor escolha para automacoes em Docker, de forma geral, e:

- `Playwright`

Porque ele funciona muito bem em ambiente headless, e mais previsivel em container que automacao baseada em mouse e teclado.

`Selenium` tambem funciona, mas para novas automacoes web, `Playwright` costuma ser a opcao mais estavel no contexto de container.

## URLs principais

### Aplicacao

- `http://127.0.0.1:8190/contas/login/`
- `http://127.0.0.1:8190/dashboard/`
- `http://127.0.0.1:8190/comercial/`
- `http://127.0.0.1:8190/financeiro/`
- `http://127.0.0.1:8190/ti/`

### Administrador

- `http://127.0.0.1:8190/administrador/`
- `http://127.0.0.1:8190/administrador/automacoes/nova/`
- `http://127.0.0.1:8190/administrador/execucoes/`
- `http://127.0.0.1:8190/administrador/monitoramento/`

### API

- `http://127.0.0.1:8190/api/health/`
- `http://127.0.0.1:8190/api/auth/token/`
- `http://127.0.0.1:8190/api/me/`
- `http://127.0.0.1:8190/api/modules/`
- `http://127.0.0.1:8190/api/automacoes/`
- `http://127.0.0.1:8190/api/execucoes/`
- `http://127.0.0.1:8190/api/documentacoes/`

### Documentacao

- `http://127.0.0.1:8190/documentacao/`
- `http://127.0.0.1:8190/documentacao/criar/`
- `http://127.0.0.1:8190/documentacao/criar/nova/`

### Django Admin

- `http://127.0.0.1:8190/admin/`
- `http://127.0.0.1:8190/admin/documentacao/documentationpage/`
- `http://127.0.0.1:8190/admin/documentacao/documentationauditlog/`
- `http://127.0.0.1:8190/admin/documentacao/documentationviewaudit/`

## Como rodar localmente

1. Ative a virtualenv.
2. Instale as dependencias:

```bash
.venv/bin/pip install -r requirements.txt
```

3. Aplique as migracoes:

```bash
.venv/bin/python manage.py migrate
```

4. Crie um superusuario:

```bash
.venv/bin/python manage.py createsuperuser
```

5. Inicie o servidor:

```bash
.venv/bin/python manage.py runserver
```

## Bibliotecas principais do sistema

- `Django`
- `rpaframework`
- `playwright`
- `selenium`
- `requests`
- `httpx`
- `pandas`
- `openpyxl`
- `XlsxWriter`
- `xlrd`
- `python-docx`
- `beautifulsoup4`
- `lxml`
- `pyautogui`
- `Pillow`
- `tenacity`
- `gunicorn`
- `whitenoise`
- `dj-database-url`
- `mysqlclient`

## Migrations importantes recentes

- `documentacao 0005`: setor de publicacao de documentos
- `api 0001`: tabela de tokens de API
- `core 0005`: metricas de consumo por execucao

## Arquivos importantes

### Base de execucao

- `core/models.py`: modelos base de execucao, arquivos e ativos
- `core/services.py`: disparo, parada, fila e fluxo das automacoes
- `core/management/commands/run_automation.py`: runner em background e coleta de metricas da execucao
- `core/management/commands/run_automation_worker.py`: worker da fila de automacoes

### Cadastro administrativo

- `administrador/views.py`
- `administrador/forms.py`
- `administrador/services.py`
- `administrador/templates/administrador/executions.html`
- `administrador/templates/administrador/monitoring.html`

### Documentacao

- `documentacao/views.py`
- `documentacao/forms.py`
- `documentacao/services.py`
- `documentacao/admin.py`
- `documentacao/templates/documentacao/_automation_link_picker.html`

### API

- `api/models.py`
- `api/auth.py`
- `api/views.py`
- `api/urls.py`
- `api/admin.py`

### Infra Docker

- `Dockerfile`
- `docker-compose.yml`
- `docker/entrypoint.sh`
- `.env.example`
- `.env.docker`
- `.env.server.example`

## Observacao final

Hoje o sistema esta preparado para rodar em Docker e executar bem automacoes baseadas em web, arquivos e integracoes.

Para automacoes de desktop tradicional, o recomendado e tratar como uma esteira separada, com um worker apropriado para GUI. Isso evita que o container vire uma falsa promessa de RPA visual e te da uma arquitetura mais segura para crescer.

Para documentos mais ricos, o modulo de documentacao tambem esta preparado para trabalhar com HTML completo, tabelas, blocos estilizados e codigo, sem depender apenas de texto simples.
