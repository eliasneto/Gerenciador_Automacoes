from django.db import migrations


def remove_seed_automacoes(apps, schema_editor):
    Model = apps.get_model('comercial', 'AutomacaoComercial')
    Model.objects.filter(identificador='processar-leads').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('comercial', '0003_seed_automacoes'),
    ]

    operations = [
        migrations.RunPython(remove_seed_automacoes, migrations.RunPython.noop),
    ]
