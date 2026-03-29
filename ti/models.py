from django.db import models

from core.models import AutomationBaseModel


class AutomacaoTI(AutomationBaseModel):
    identificador = models.SlugField(max_length=120, default='ti')
    executor_path = models.CharField(
        max_length=255,
        default='ti.automacoes.processar_inventario.executar',
    )

    class Meta:
        verbose_name = 'Automacao de TI'
        verbose_name_plural = 'Automacoes de TI'
        ordering = ['nome']
