from django.db import migrations


def remove_seed_automacoes(apps, schema_editor):
    Model = apps.get_model('financeiro', 'AutomacaoFinanceira')
    Model.objects.filter(identificador='conciliar-pagamentos').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('financeiro', '0003_seed_automacoes'),
    ]

    operations = [
        migrations.RunPython(remove_seed_automacoes, migrations.RunPython.noop),
    ]
