import csv
import time
from pathlib import Path


def executar(input_path=None, input_paths=None, attachments=None, output_dir=None, should_stop=None, log=None, parametros='', parametros_json=None):
    attachments = attachments or []
    input_paths = input_paths or ([] if input_path is None else [input_path])
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = Path(output_dir) / 'conciliacao_financeira.csv'

    linhas = [
        ['tipo', 'nome_arquivo'],
        ['entrada', input_path.name if input_path else 'sem_arquivo'],
    ]
    linhas.extend([['entrada_principal', primary.name] for primary in input_paths[1:]])
    linhas.extend([['anexo', attachment.name] for attachment in attachments])

    for etapa in range(1, 5):
        if should_stop:
            should_stop()
        if log:
            log(f'Etapa {etapa}/4: conciliando registros financeiros.')
        time.sleep(1)

    with output_file.open('w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(linhas)

    return {'message': 'Conciliacao financeira concluida com sucesso.'}
