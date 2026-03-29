from comercial.models import AutomacaoComercial
from financeiro.models import AutomacaoFinanceira
from ti.models import AutomacaoTI


SECTOR_REGISTRY = {
    'comercial': {
        'label': 'Comercial',
        'model': AutomacaoComercial,
        'default_executor': 'comercial.automacoes.processar_leads.executar',
        'icon': 'briefcase-business',
        'group_name': 'Modulo Comercial',
        'dashboard_group_name': 'Dashboard Comercial',
    },
    'financeiro': {
        'label': 'Financeiro',
        'model': AutomacaoFinanceira,
        'default_executor': 'financeiro.automacoes.conciliar_pagamentos.executar',
        'icon': 'wallet',
        'group_name': 'Modulo Financeiro',
        'dashboard_group_name': 'Dashboard Financeiro',
    },
    'ti': {
        'label': 'TI',
        'model': AutomacaoTI,
        'default_executor': 'ti.automacoes.processar_inventario.executar',
        'icon': 'cpu',
        'group_name': 'Modulo TI',
        'dashboard_group_name': 'Dashboard TI',
    },
}


def sector_choices():
    return [(key, value['label']) for key, value in SECTOR_REGISTRY.items()]
