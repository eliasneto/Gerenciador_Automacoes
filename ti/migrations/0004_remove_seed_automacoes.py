from django.db import migrations


def remove_seed_automacoes(apps, schema_editor):
    Model = apps.get_model('ti', 'AutomacaoTI')
    Model.objects.filter(identificador='processar-inventario').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('ti', '0003_seed_automacoes'),
    ]

    operations = [
        migrations.RunPython(remove_seed_automacoes, migrations.RunPython.noop),
    ]
