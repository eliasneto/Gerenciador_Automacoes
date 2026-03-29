import json
import time
from pathlib import Path


def executar(input_path=None, input_paths=None, attachments=None, output_dir=None, should_stop=None, log=None, parametros='', parametros_json=None):
    attachments = attachments or []
    input_paths = input_paths or ([] if input_path is None else [input_path])
    output_dir.mkdir(parents=True, exist_ok=True)
    resumo = {
        'arquivo_entrada': input_path.name if input_path else None,
        'arquivos_principais': [path.name for path in input_paths],
        'anexos': [path.name for path in attachments],
        'parametros': parametros_json if parametros_json is not None else parametros,
        'etapas': [],
    }

    for etapa in range(1, 6):
        if should_stop:
            should_stop()
        mensagem = f'Etapa {etapa}/5: processando leads comerciais.'
        if log:
            log(mensagem)
        resumo['etapas'].append(mensagem)
        time.sleep(1)

    output_file = Path(output_dir) / 'resumo_leads.json'
    output_file.write_text(json.dumps(resumo, indent=2, ensure_ascii=True), encoding='utf-8')
    return {'message': 'Leads comerciais processados com sucesso.'}
