import csv
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path


SEARCH_URL = 'https://www.youtube.com/results?search_query={query}'
USER_AGENT = (
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
)


def _read_text_file(file_path):
    for encoding in ('utf-8', 'utf-8-sig', 'latin-1'):
        try:
            return file_path.read_text(encoding=encoding).strip()
        except UnicodeDecodeError:
            continue
    raise ValueError('Nao foi possivel ler o arquivo de tema. Salve-o como texto UTF-8 ou Latin-1.')


def _extract_initial_data(html_content):
    patterns = [
        r'var ytInitialData = (\{.*?\});',
        r'window\["ytInitialData"\] = (\{.*?\});',
        r'ytInitialData = (\{.*?\});',
    ]

    for pattern in patterns:
        match = re.search(pattern, html_content, re.DOTALL)
        if match:
            return json.loads(match.group(1))

    raise ValueError('Nao foi possivel localizar os dados da pesquisa do YouTube na pagina retornada.')


def _walk_video_renderers(node):
    if isinstance(node, dict):
        if 'videoRenderer' in node:
            yield node['videoRenderer']
        for value in node.values():
            yield from _walk_video_renderers(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_video_renderers(item)


def _pick_text(value):
    if not value:
        return ''
    if isinstance(value, str):
        return value
    runs = value.get('runs') or []
    if runs:
        return ''.join(run.get('text', '') for run in runs).strip()
    return value.get('simpleText', '')


def _video_to_row(video, tema):
    video_id = video.get('videoId', '')
    title = _pick_text(video.get('title'))
    channel = _pick_text(video.get('ownerText'))
    views = _pick_text(video.get('viewCountText'))
    published = _pick_text(video.get('publishedTimeText'))
    duration = _pick_text(video.get('lengthText'))

    return {
        'tema': tema,
        'titulo': title,
        'canal': channel,
        'visualizacoes': views,
        'publicado': published,
        'duracao': duration,
        'url': f'https://www.youtube.com/watch?v={video_id}' if video_id else '',
    }


def _fetch_search_results(tema, should_stop=None, log=None):
    encoded_query = urllib.parse.quote_plus(tema)
    request = urllib.request.Request(
        SEARCH_URL.format(query=encoded_query),
        headers={'User-Agent': USER_AGENT},
    )

    if should_stop:
        should_stop()
    if log:
        log(f'Pesquisando no YouTube pelo tema: {tema}')

    with urllib.request.urlopen(request, timeout=30) as response:
        html_content = response.read().decode('utf-8', errors='ignore')

    if should_stop:
        should_stop()

    data = _extract_initial_data(html_content)
    rows = []
    seen_urls = set()

    for video in _walk_video_renderers(data):
        row = _video_to_row(video, tema)
        if not row['url'] or row['url'] in seen_urls:
            continue
        rows.append(row)
        seen_urls.add(row['url'])
        if len(rows) >= 15:
            break

    return rows


def executar(
    input_path=None,
    input_paths=None,
    attachments=None,
    output_dir=None,
    should_stop=None,
    log=None,
    parametros='',
    parametros_json=None,
):
    attachments = attachments or []
    input_paths = input_paths or ([] if input_path is None else [input_path])

    if not input_paths:
        raise ValueError('Envie um arquivo principal com o tema da pesquisa, por exemplo: tema.txt')

    tema_path = Path(input_paths[0])
    if not tema_path.exists():
        raise ValueError('O arquivo principal informado nao foi encontrado na execucao.')

    tema = _read_text_file(tema_path)
    if not tema:
        raise ValueError('O arquivo tema.txt esta vazio. Informe o assunto que deseja pesquisar.')

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if log:
        log(f'Arquivo principal lido: {tema_path.name}')
        if len(input_paths) > 1:
            log(f'Segundo arquivo principal recebido: {Path(input_paths[1]).name}')
        if attachments:
            log(f'{len(attachments)} arquivo(s) secundario(s) recebido(s).')

    rows = _fetch_search_results(tema, should_stop=should_stop, log=log)
    if not rows:
        raise ValueError('Nenhum video foi encontrado para o tema informado.')

    output_file = output_dir / 'resultado_youtube.csv'
    with output_file.open('w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=['tema', 'titulo', 'canal', 'visualizacoes', 'publicado', 'duracao', 'url'],
        )
        writer.writeheader()
        writer.writerows(rows)

    if log:
        log(f'Pesquisa concluida com {len(rows)} video(s) encontrados.')
        log(f'Arquivo de saida salvo em: {output_file.name}')

    return {
        'message': f'Pesquisa no YouTube concluida com {len(rows)} resultado(s).',
    }
