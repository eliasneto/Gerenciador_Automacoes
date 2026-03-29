from django.contrib import admin

from .models import AutomacaoFinanceira


@admin.register(AutomacaoFinanceira)
class AutomacaoFinanceiraAdmin(admin.ModelAdmin):
    list_display = ('nome', 'identificador', 'ativa', 'atualizado_em')
    list_filter = ('ativa', 'aceita_arquivo_entrada', 'aceita_anexos')
    search_fields = ('nome', 'descricao', 'identificador', 'executor_path')
