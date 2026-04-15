from django.db import migrations


def add_medicao_blueez(apps, schema_editor):
    AutomacaoTI = apps.get_model("ti", "AutomacaoTI")
    AutomacaoTI.objects.update_or_create(
        identificador="medicao-blueez",
        defaults={
            "nome": "Medicao BlueEZ",
            "descricao": "Processa planilha de medicao no BlueEZ com anexos vinculados por linha.",
            "executor_path": "ti.automacoes.medicao_blueez.executar",
            "aceita_arquivo_entrada": True,
            "aceita_anexos": True,
            "ativa": True,
        },
    )


def remove_medicao_blueez(apps, schema_editor):
    AutomacaoTI = apps.get_model("ti", "AutomacaoTI")
    AutomacaoTI.objects.filter(identificador="medicao-blueez").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("ti", "0004_remove_seed_automacoes"),
    ]

    operations = [
        migrations.RunPython(add_medicao_blueez, remove_medicao_blueez),
    ]
