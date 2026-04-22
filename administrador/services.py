from django.db import transaction

from .catalog import SECTOR_REGISTRY


@transaction.atomic
def create_automation_for_sectors(cleaned_data):
    created_items = []
    icone = cleaned_data.get('icone') or 'sparkles'

    for setor in cleaned_data['setores']:
        registry = SECTOR_REGISTRY[setor]
        automation = registry['model'].objects.create(
            nome=cleaned_data['nome'],
            identificador=cleaned_data['identificador'],
            icone=icone,
            descricao=cleaned_data.get('descricao', ''),
            executor_path=cleaned_data['executor_path'],
            aceita_arquivo_entrada=cleaned_data.get('aceita_arquivo_entrada', False),
            aceita_anexos=cleaned_data.get('aceita_anexos', False),
            ativa=cleaned_data.get('ativa', False),
        )
        created_items.append(
            {
                'setor': setor,
                'label': registry['label'],
                'automation': automation,
            }
        )

    return created_items


@transaction.atomic
def update_automation(automation, current_sector_key, cleaned_data):
    updated_items = []
    automation.nome = cleaned_data['nome']
    automation.identificador = cleaned_data['identificador']
    automation.icone = cleaned_data.get('icone') or getattr(automation, 'icone', '') or 'sparkles'
    automation.descricao = cleaned_data.get('descricao', '')
    automation.executor_path = cleaned_data['executor_path']
    automation.aceita_arquivo_entrada = cleaned_data.get('aceita_arquivo_entrada', False)
    automation.aceita_anexos = cleaned_data.get('aceita_anexos', False)
    automation.ativa = cleaned_data.get('ativa', False)
    automation.save()
    updated_items.append({'setor': current_sector_key, 'label': SECTOR_REGISTRY[current_sector_key]['label'], 'automation': automation})

    selected_sectors = cleaned_data.get('setores') or []
    for setor in selected_sectors:
        if setor == current_sector_key:
            continue

        registry = SECTOR_REGISTRY[setor]
        model = registry['model']
        duplicate = model.objects.filter(identificador=automation.identificador).first()

        if duplicate:
            duplicate.nome = automation.nome
            duplicate.icone = automation.icone
            duplicate.descricao = automation.descricao
            duplicate.executor_path = automation.executor_path
            duplicate.aceita_arquivo_entrada = automation.aceita_arquivo_entrada
            duplicate.aceita_anexos = automation.aceita_anexos
            duplicate.ativa = automation.ativa
            duplicate.save()
            target = duplicate
        else:
            target = model.objects.create(
                nome=automation.nome,
                identificador=automation.identificador,
                icone=automation.icone,
                descricao=automation.descricao,
                executor_path=automation.executor_path,
                aceita_arquivo_entrada=automation.aceita_arquivo_entrada,
                aceita_anexos=automation.aceita_anexos,
                ativa=automation.ativa,
            )

        updated_items.append({'setor': setor, 'label': registry['label'], 'automation': target})

    return updated_items
