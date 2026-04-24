from pathlib import Path

from django.test import SimpleTestCase

from ti.automacoes.medicao_blueez import localizar_anexo, normalizar_nome_anexo


class MedicaoBlueezAnexosTests(SimpleTestCase):
    def test_normalizar_nome_anexo_remove_separadores_entre_digitos(self):
        valor_planilha = "BOLETO TECNOVETTI 1.092,00 NF 362549"
        valor_arquivo = "BOLETO_TECNOVETTI_109200_NF_362549.pdf"

        self.assertEqual(
            normalizar_nome_anexo(valor_planilha),
            normalizar_nome_anexo(Path(valor_arquivo).stem),
        )

    def test_localizar_anexo_aceita_nome_planilha_sem_extensao_e_valor_com_virgula(self):
        attachment_index = {
            "boleto_tecnovetti_26582_nf_362555.pdf": Path(
                "BOLETO_TECNOVETTI_26582_NF_362555.pdf"
            )
        }

        encontrado = localizar_anexo(
            "BOLETO TECNOVETTI 265,82 NF 362555",
            attachment_index,
        )

        self.assertIsNotNone(encontrado)
        self.assertEqual(encontrado.name, "BOLETO_TECNOVETTI_26582_NF_362555.pdf")
