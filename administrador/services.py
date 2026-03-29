from django.db import transaction

from .catalog import SECTOR_REGISTRY


@transaction.atomic
def create_automation_for_sectors(cleaned_data):
    created_items = []

    for setor in cleaned_data['setores']:
        registry = SECTOR_REGISTRY[setor]
        automation = registry['model'].objects.create(
            nome=cleaned_data['nome'],
            identificador=cleaned_data['identificador'],
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
