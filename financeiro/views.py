from core.module_views import ExecutionLogView, ModuleHomeView, StartAutomationView, StopAutomationView

from .models import AutomacaoFinanceira


class FinanceiroHomeView(ModuleHomeView):
    template_name = 'financeiro/home.html'
    automation_model = AutomacaoFinanceira
    module_key = 'financeiro'
    module_name = 'Financeiro'
    module_description = 'Organize automacoes de cobranca, faturamento, fluxo de caixa e auditoria.'
    module_status_label = 'Controle e previsibilidade'


class FinanceiroStartAutomationView(StartAutomationView):
    automation_model = AutomacaoFinanceira
    module_key = 'financeiro'
    module_name = 'Financeiro'
    namespace = 'financeiro'


class FinanceiroStopAutomationView(StopAutomationView):
    module_key = 'financeiro'
    module_name = 'Financeiro'
    namespace = 'financeiro'


class FinanceiroExecutionLogView(ExecutionLogView):
    module_key = 'financeiro'
    module_name = 'Financeiro'
