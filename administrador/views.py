from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import FormView, TemplateView
import os
import shutil

from core.models import AutomationExecution
from core.security import user_has_area_access

from .catalog import SECTOR_REGISTRY
from .forms import AutomationCreateForm
from .services import create_automation_for_sectors


class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return user_has_area_access(self.request.user, 'administrador')

    def handle_no_permission(self):
        messages.error(self.request, 'A area administrativa esta disponivel apenas para administradores.')
        return redirect('core:dashboard')


class AdminHubView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    template_name = 'administrador/hub.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sector_cards = []

        for key, registry in SECTOR_REGISTRY.items():
            model = registry['model']
            sector_cards.append(
                {
                    'key': key,
                    'label': registry['label'],
                    'icon': registry['icon'],
                    'count': model.objects.count(),
                    'recent': list(model.objects.order_by('-criado_em')[:4]),
                }
            )

        context['sector_cards'] = sector_cards
        return context


class AutomationCreateView(LoginRequiredMixin, AdminRequiredMixin, FormView):
    template_name = 'administrador/automation_form.html'
    form_class = AutomationCreateForm

    def get_initial(self):
        initial = super().get_initial()
        initial.update(
            {
                'aceita_arquivo_entrada': True,
                'aceita_anexos': True,
                'ativa': True,
                'executor_path': 'comercial.automacoes.minha_automacao.executar',
            }
        )
        return initial

    def form_valid(self, form):
        created_items = create_automation_for_sectors(form.cleaned_data)
        sectors = ', '.join(item['label'] for item in created_items)
        messages.success(
            self.request,
            f'Automacao "{form.cleaned_data["nome"]}" criada com sucesso em: {sectors}.',
        )
        return redirect('administrador:automation-create')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sector_cards = []

        for key, registry in SECTOR_REGISTRY.items():
            model = registry['model']
            sector_cards.append(
                {
                    'key': key,
                    'label': registry['label'],
                    'icon': registry['icon'],
                    'count': model.objects.count(),
                    'recent': list(model.objects.order_by('-criado_em')[:5]),
                }
            )

        context['sector_cards'] = sector_cards
        context['sector_total'] = sum(card['count'] for card in sector_cards)
        return context


class ExecutionListView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    template_name = 'administrador/executions.html'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '').strip()
        module_filter = self.request.GET.get('module', '').strip()
        status_filter = self.request.GET.get('status', '').strip()
        user_filter = self.request.GET.get('user', '').strip()

        executions_queryset = AutomationExecution.objects.select_related('usuario', 'content_type').prefetch_related(
            'arquivos'
        )

        if query:
            executions_queryset = executions_queryset.filter(
                Q(automacao_nome__icontains=query)
                | Q(executor_path__icontains=query)
                | Q(mensagem_resumo__icontains=query)
            )

        if module_filter:
            executions_queryset = executions_queryset.filter(modulo=module_filter)

        if status_filter:
            executions_queryset = executions_queryset.filter(status=status_filter)

        if user_filter:
            executions_queryset = executions_queryset.filter(usuario__username__icontains=user_filter)

        page_obj = Paginator(executions_queryset, self.paginate_by).get_page(self.request.GET.get('page'))
        executions = list(page_obj.object_list)

        for execution in executions:
            execution.output_files = [file for file in execution.arquivos.all() if file.tipo == 'output']
            execution.has_output_files = bool(execution.output_files)
            execution.log_url = f'/{execution.modulo}/execucoes/{execution.pk}/logs/'

        context['executions'] = executions
        context['page_obj'] = page_obj
        context['filters'] = {
            'q': query,
            'module': module_filter,
            'status': status_filter,
            'user': user_filter,
        }
        context['module_choices'] = SECTOR_REGISTRY.items()
        context['status_choices'] = AutomationExecution.Status.choices
        context['summary'] = {
            'total': AutomationExecution.objects.count(),
            'running': AutomationExecution.objects.filter(status=AutomationExecution.Status.RUNNING).count(),
            'pending': AutomationExecution.objects.filter(status=AutomationExecution.Status.PENDING).count(),
            'success': AutomationExecution.objects.filter(status=AutomationExecution.Status.SUCCESS).count(),
            'error': AutomationExecution.objects.filter(status=AutomationExecution.Status.ERROR).count(),
            'stopped': AutomationExecution.objects.filter(status=AutomationExecution.Status.STOPPED).count(),
        }
        context['module_summary'] = (
            AutomationExecution.objects.values('modulo').annotate(total=Count('id')).order_by('modulo')
        )
        return context


class MonitoringView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    template_name = 'administrador/monitoring.html'

    @staticmethod
    def _read_meminfo():
        data = {}
        try:
            with open('/proc/meminfo', 'r', encoding='utf-8') as meminfo_file:
                for line in meminfo_file:
                    if ':' not in line:
                        continue
                    key, value = line.split(':', 1)
                    parts = value.strip().split()
                    if parts:
                        data[key] = int(parts[0])
        except (FileNotFoundError, OSError, ValueError):
            return None
        return data

    @staticmethod
    def _read_loadavg():
        try:
            with open('/proc/loadavg', 'r', encoding='utf-8') as loadavg_file:
                parts = loadavg_file.read().strip().split()
                return {
                    '1min': parts[0],
                    '5min': parts[1],
                    '15min': parts[2],
                }
        except (FileNotFoundError, OSError, IndexError):
            return {'1min': 'N/D', '5min': 'N/D', '15min': 'N/D'}

    @staticmethod
    def _read_cgroup_memory():
        candidates = [
            ('/sys/fs/cgroup/memory.current', '/sys/fs/cgroup/memory.max'),
            ('/sys/fs/cgroup/memory/memory.usage_in_bytes', '/sys/fs/cgroup/memory/memory.limit_in_bytes'),
        ]
        for current_path, max_path in candidates:
            try:
                with open(current_path, 'r', encoding='utf-8') as current_file:
                    current_bytes = int(current_file.read().strip())
                with open(max_path, 'r', encoding='utf-8') as max_file:
                    raw_max = max_file.read().strip()
                max_bytes = None if raw_max == 'max' else int(raw_max)
                return {
                    'current_mb': round(current_bytes / (1024 * 1024), 2),
                    'max_mb': round(max_bytes / (1024 * 1024), 2) if max_bytes else None,
                }
            except (FileNotFoundError, OSError, ValueError):
                continue
        return {'current_mb': None, 'max_mb': None}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        meminfo = self._read_meminfo() or {}
        memory_total_mb = round(meminfo.get('MemTotal', 0) / 1024, 2) if meminfo.get('MemTotal') else None
        memory_available_mb = round(meminfo.get('MemAvailable', 0) / 1024, 2) if meminfo.get('MemAvailable') else None
        memory_used_mb = (
            round(memory_total_mb - memory_available_mb, 2)
            if memory_total_mb is not None and memory_available_mb is not None
            else None
        )
        memory_usage_percent = (
            round((memory_used_mb / memory_total_mb) * 100, 2)
            if memory_total_mb and memory_used_mb is not None
            else None
        )

        root_disk = shutil.disk_usage('/')
        media_disk = shutil.disk_usage('/app/media') if os.path.exists('/app/media') else shutil.disk_usage('.')
        load_average = self._read_loadavg()
        cgroup_memory = self._read_cgroup_memory()

        running_executions = list(
            AutomationExecution.objects.filter(status=AutomationExecution.Status.RUNNING).select_related('usuario')
        )
        now = timezone.now()
        for execution in running_executions:
            execution.duration_seconds = (
                int((now - execution.iniciado_em).total_seconds()) if execution.iniciado_em else 0
            )

        context['server_metrics'] = {
            'memory_total_mb': memory_total_mb,
            'memory_used_mb': memory_used_mb,
            'memory_available_mb': memory_available_mb,
            'memory_usage_percent': memory_usage_percent,
            'root_disk_total_gb': round(root_disk.total / (1024 ** 3), 2),
            'root_disk_used_gb': round(root_disk.used / (1024 ** 3), 2),
            'root_disk_free_gb': round(root_disk.free / (1024 ** 3), 2),
            'media_disk_total_gb': round(media_disk.total / (1024 ** 3), 2),
            'media_disk_used_gb': round(media_disk.used / (1024 ** 3), 2),
            'media_disk_free_gb': round(media_disk.free / (1024 ** 3), 2),
            'load_average': load_average,
            'cpu_count': os.cpu_count(),
            'cgroup_memory': cgroup_memory,
        }
        context['running_executions'] = running_executions
        context['execution_summary'] = {
            'running': len(running_executions),
            'pending': AutomationExecution.objects.filter(status=AutomationExecution.Status.PENDING).count(),
            'success': AutomationExecution.objects.filter(status=AutomationExecution.Status.SUCCESS).count(),
            'error': AutomationExecution.objects.filter(status=AutomationExecution.Status.ERROR).count(),
            'stopped': AutomationExecution.objects.filter(status=AutomationExecution.Status.STOPPED).count(),
        }
        return context
