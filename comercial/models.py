from django.db import models

from core.models import AutomationBaseModel


class AutomacaoComercial(AutomationBaseModel):
    identificador = models.SlugField(max_length=120, default='comercial')
    executor_path = models.CharField(
        max_length=255,
        default='comercial.automacoes.processar_leads.executar',
    )

    class Meta:
        verbose_name = 'Automacao Comercial'
        verbose_name_plural = 'Automacoes Comerciais'
        ordering = ['nome']
