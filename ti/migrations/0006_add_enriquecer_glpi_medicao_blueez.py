from django.db import migrations


def add_enriquecer_glpi_medicao_blueez(apps, schema_editor):
    AutomacaoTI = apps.get_model("ti", "AutomacaoTI")
    AutomacaoTI.objects.update_or_create(
        identificador="enriquecer-glpi-medicao-blueez",
        defaults={
            "nome": "Enriquecer GLPI Medicao BlueEZ",
            "descricao": "Recebe a planilha de saida da Medicao BlueEZ e completa os dados de GLPI pelo numero da solicitacao.",
            "executor_path": "ti.automacoes.enriquecer_glpi_medicao_blueez.executar",
            "aceita_arquivo_entrada": True,
            "aceita_anexos": False,
            "ativa": True,
        },
    )


def remove_enriquecer_glpi_medicao_blueez(apps, schema_editor):
    AutomacaoTI = apps.get_model("ti", "AutomacaoTI")
    AutomacaoTI.objects.filter(identificador="enriquecer-glpi-medicao-blueez").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("ti", "0005_add_medicao_blueez"),
    ]

    operations = [
        migrations.RunPython(add_enriquecer_glpi_medicao_blueez, remove_enriquecer_glpi_medicao_blueez),
    ]
