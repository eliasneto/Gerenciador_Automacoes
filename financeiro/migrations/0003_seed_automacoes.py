from django.db import migrations


def seed_automacoes(apps, schema_editor):
    Model = apps.get_model('financeiro', 'AutomacaoFinanceira')
    if not Model.objects.filter(identificador='conciliar-pagamentos').exists():
        Model.objects.create(
            nome='Conciliar Pagamentos',
            identificador='conciliar-pagamentos',
            descricao='Exemplo base para cruzar dados financeiros a partir de planilhas e gerar um arquivo de saida.',
            executor_path='financeiro.automacoes.conciliar_pagamentos.executar',
            aceita_arquivo_entrada=True,
            aceita_anexos=True,
            ativa=True,
        )


def rollback_automacoes(apps, schema_editor):
    Model = apps.get_model('financeiro', 'AutomacaoFinanceira')
    Model.objects.filter(identificador='conciliar-pagamentos').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('financeiro', '0002_automacaofinanceira_aceita_anexos_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_automacoes, rollback_automacoes),
    ]
