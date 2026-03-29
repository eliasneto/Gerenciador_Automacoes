from core.module_views import ExecutionLogView, ModuleHomeView, StartAutomationView, StopAutomationView

from .models import AutomacaoTI


class TIHomeView(ModuleHomeView):
    template_name = 'ti/home.html'
    automation_model = AutomacaoTI
    module_key = 'ti'
    module_name = 'TI'
    module_description = 'Prepare automacoes para chamados, acessos, infraestrutura e monitoramento.'
    module_status_label = 'Operacao e suporte'


class TIStartAutomationView(StartAutomationView):
    automation_model = AutomacaoTI
    module_key = 'ti'
    module_name = 'TI'
    namespace = 'ti'


class TIStopAutomationView(StopAutomationView):
    module_key = 'ti'
    module_name = 'TI'
    namespace = 'ti'


class TIExecutionLogView(ExecutionLogView):
    module_key = 'ti'
    module_name = 'TI'
