from django.db import migrations


def seed_automacoes(apps, schema_editor):
    Model = apps.get_model('comercial', 'AutomacaoComercial')
    if not Model.objects.filter(identificador='processar-leads').exists():
        Model.objects.create(
            nome='Processar Leads',
            identificador='processar-leads',
            descricao='Exemplo base para importar um arquivo principal, anexos auxiliares e gerar um resumo final.',
            executor_path='comercial.automacoes.processar_leads.executar',
            aceita_arquivo_entrada=True,
            aceita_anexos=True,
            ativa=True,
        )


def rollback_automacoes(apps, schema_editor):
    Model = apps.get_model('comercial', 'AutomacaoComercial')
    Model.objects.filter(identificador='processar-leads').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('comercial', '0002_automacaocomercial_aceita_anexos_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_automacoes, rollback_automacoes),
    ]
