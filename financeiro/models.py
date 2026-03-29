from django.db import models

from core.models import AutomationBaseModel


class AutomacaoFinanceira(AutomationBaseModel):
    identificador = models.SlugField(max_length=120, default='financeiro')
    executor_path = models.CharField(
        max_length=255,
        default='financeiro.automacoes.conciliar_pagamentos.executar',
    )

    class Meta:
        verbose_name = 'Automacao Financeira'
        verbose_name_plural = 'Automacoes Financeiras'
        ordering = ['nome']
