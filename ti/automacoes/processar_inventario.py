import time
from pathlib import Path


def executar(input_path=None, input_paths=None, attachments=None, output_dir=None, should_stop=None, log=None, parametros='', parametros_json=None):
    attachments = attachments or []
    input_paths = input_paths or ([] if input_path is None else [input_path])
    output_dir.mkdir(parents=True, exist_ok=True)

    for etapa in range(1, 7):
        if should_stop:
            should_stop()
        if log:
            log(f'Etapa {etapa}/6: verificando ativos de TI.')
        time.sleep(1)

    report_path = Path(output_dir) / 'inventario_ti.txt'
    report_lines = [
        'Inventario processado.',
        f'Arquivo principal: {input_path.name if input_path else "nenhum"}',
        f'Arquivos principais recebidos: {", ".join(path.name for path in input_paths) if input_paths else "nenhum"}',
        'Anexos recebidos:',
    ]
    report_lines.extend([f'- {attachment.name}' for attachment in attachments] or ['- nenhum'])
    report_path.write_text('\n'.join(report_lines), encoding='utf-8')

    return {'message': 'Inventario de TI processado com sucesso.'}
