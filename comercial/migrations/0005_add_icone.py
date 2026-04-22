from django.db import migrations


def add_icone_if_missing(apps, schema_editor):
    Model = apps.get_model('comercial', 'AutomacaoComercial')
    table_name = Model._meta.db_table
    with schema_editor.connection.cursor() as cursor:
        columns = [col.name for col in schema_editor.connection.introspection.get_table_description(cursor, table_name)]
    if 'icone' in columns:
        return
    schema_editor.execute(
        f"ALTER TABLE `{table_name}` ADD COLUMN `icone` varchar(80) NOT NULL DEFAULT 'sparkles'"
    )


def remove_icone_if_present(apps, schema_editor):
    Model = apps.get_model('comercial', 'AutomacaoComercial')
    table_name = Model._meta.db_table
    with schema_editor.connection.cursor() as cursor:
        columns = [col.name for col in schema_editor.connection.introspection.get_table_description(cursor, table_name)]
    if 'icone' not in columns:
        return
    schema_editor.execute(f"ALTER TABLE `{table_name}` DROP COLUMN `icone`")


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('comercial', '0004_remove_seed_automacoes'),
    ]

    operations = [
        migrations.RunPython(add_icone_if_missing, remove_icone_if_present),
    ]
