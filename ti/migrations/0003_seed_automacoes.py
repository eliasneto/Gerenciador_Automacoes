from django.db import migrations


def seed_automacoes(apps, schema_editor):
    Model = apps.get_model('ti', 'AutomacaoTI')
    if not Model.objects.filter(identificador='processar-inventario').exists():
        Model.objects.create(
            nome='Processar Inventario',
            identificador='processar-inventario',
            descricao='Exemplo base para ler um arquivo de inventario, anexos de apoio e gerar um relatorio textual.',
            executor_path='ti.automacoes.processar_inventario.executar',
            aceita_arquivo_entrada=True,
            aceita_anexos=True,
            ativa=True,
        )


def rollback_automacoes(apps, schema_editor):
    Model = apps.get_model('ti', 'AutomacaoTI')
    Model.objects.filter(identificador='processar-inventario').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('ti', '0002_automacaoti_aceita_anexos_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_automacoes, rollback_automacoes),
    ]
