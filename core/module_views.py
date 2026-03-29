from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import TemplateView

from .models import AutomationExecution, AutomationExecutionFile
from .security import user_has_module_access
from .services import build_success_url, start_automation_request, stop_automation_request


class ModuleAccessMixin:
    module_key = ''
    module_name = ''

    def dispatch(self, request, *args, **kwargs):
        if not user_has_module_access(request.user, self.module_key):
            messages.error(
                request,
                f'Voce nao possui permissao para acessar o modulo {self.module_name or self.module_key.title()}.',
            )
            return redirect('core:dashboard')
        return super().dispatch(request, *args, **kwargs)


class ModuleHomeView(LoginRequiredMixin, ModuleAccessMixin, TemplateView):
    template_name = 'module_base.html'
    automation_model = None
    module_key = ''
    module_name = ''
    module_description = ''
    module_status_label = ''
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        automacoes_queryset = self.automation_model.objects.all()
        automacoes_page_obj = Paginator(automacoes_queryset, self.paginate_by).get_page(
            self.request.GET.get('automacoes_page')
        )
        automacoes = list(automacoes_page_obj.object_list)
        for automacao in automacoes:
            automacao.execucao_ativa = automacao.execucoes.filter(status=AutomationExecution.Status.RUNNING).first()
            automacao.ultima_execucao = automacao.execucoes.first()
            automacao.arquivos_modal = list(automacao.arquivos_salvos.all())

        context['modulo'] = {
            'nome': self.module_name,
            'descricao': self.module_description,
            'contador': automacoes_queryset.count(),
            'status_label': self.module_status_label,
            'namespace': self.request.resolver_match.namespace,
        }
        context['automacoes'] = automacoes
        execucoes_queryset = AutomationExecution.objects.filter(modulo=self.module_key).prefetch_related('arquivos')
        execucoes_page_obj = Paginator(execucoes_queryset, self.paginate_by).get_page(
            self.request.GET.get('execucoes_page')
        )
        execucoes_recentes = list(execucoes_page_obj.object_list)

        for execucao in execucoes_recentes:
            arquivos_execucao = list(execucao.arquivos.all())
            execucao.output_files = [
                arquivo for arquivo in arquivos_execucao if arquivo.tipo == AutomationExecutionFile.Tipo.OUTPUT
            ]
            execucao.support_files = [
                arquivo for arquivo in arquivos_execucao if arquivo.tipo != AutomationExecutionFile.Tipo.OUTPUT
            ]
            execucao.primary_output_file = execucao.output_files[0] if execucao.output_files else None

        context['execucoes_recentes'] = execucoes_recentes
        context['automacoes_page_obj'] = automacoes_page_obj
        context['execucoes_page_obj'] = execucoes_page_obj
        return context


class StartAutomationView(LoginRequiredMixin, ModuleAccessMixin, View):
    automation_model = None
    module_key = ''
    module_name = ''
    namespace = ''

    def post(self, request, pk):
        automation = get_object_or_404(self.automation_model, pk=pk)
        redirect_url = start_automation_request(request, automation, self.module_key, self.namespace)
        return redirect(redirect_url or build_success_url(self.namespace))


class StopAutomationView(LoginRequiredMixin, ModuleAccessMixin, View):
    module_key = ''
    module_name = ''
    namespace = ''

    def post(self, request, execution_id):
        execution = get_object_or_404(AutomationExecution, pk=execution_id, modulo=self.module_key)
        redirect_url = stop_automation_request(request, execution, self.namespace)
        return redirect(redirect_url)


class ExecutionLogView(LoginRequiredMixin, ModuleAccessMixin, View):
    module_key = ''
    module_name = ''

    def get(self, request, execution_id):
        execution = get_object_or_404(AutomationExecution, pk=execution_id, modulo=self.module_key)
        return JsonResponse(
            {
                'id': execution.id,
                'status': execution.status,
                'status_label': execution.get_status_display(),
                'log': execution.log_saida or '',
                'summary': execution.mensagem_resumo or '',
                'updated_at': (
                    execution.finalizado_em or execution.iniciado_em or execution.criado_em
                ).strftime('%d/%m/%Y %H:%M'),
                'is_finished': execution.status in {
                    AutomationExecution.Status.SUCCESS,
                    AutomationExecution.Status.ERROR,
                    AutomationExecution.Status.STOPPED,
                },
            }
        )
