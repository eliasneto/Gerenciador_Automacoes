from core.module_views import ExecutionLogView, ModuleHomeView, StartAutomationView, StopAutomationView

from .models import AutomacaoComercial


class ComercialHomeView(ModuleHomeView):
    template_name = 'comercial/home.html'
    automation_model = AutomacaoComercial
    module_key = 'comercial'
    module_name = 'Comercial'
    module_description = 'Centralize automacoes de prospeccao, funil, follow-up e atendimento.'
    module_status_label = 'Leads e relacionamento'


class ComercialStartAutomationView(StartAutomationView):
    automation_model = AutomacaoComercial
    module_key = 'comercial'
    module_name = 'Comercial'
    namespace = 'comercial'


class ComercialStopAutomationView(StopAutomationView):
    module_key = 'comercial'
    module_name = 'Comercial'
    namespace = 'comercial'


class ComercialExecutionLogView(ExecutionLogView):
    module_key = 'comercial'
    module_name = 'Comercial'
