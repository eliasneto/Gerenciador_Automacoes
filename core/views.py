from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views.generic import TemplateView

from .models import AutomationExecution
from .sector_registry import SECTOR_REGISTRY
from .security import user_has_dashboard_access


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        descriptions = {
            'comercial': 'Fluxos de vendas, prospecção, CRM e atendimento ao cliente.',
            'financeiro': 'Rotinas de contas, cobrança, relatórios e conciliações.',
            'ti': 'Automação de suporte, infraestrutura, monitoramento e acessos.',
        }
        modules = []
        sector_metrics = []
        automation_options = []
        total_active_automations = 0
        total_automations = 0
        total_executions = 0
        selected_area = self.request.GET.get('area', '').strip()
        selected_automation = self.request.GET.get('automacao', '').strip()
        visible_area_keys = []

        for key, registry in SECTOR_REGISTRY.items():
            if not user_has_dashboard_access(self.request.user, key):
                continue

            visible_area_keys.append(key)
            model = registry['model']
            sector_total = model.objects.count()
            sector_active = model.objects.filter(ativa=True).count()
            sector_executions = AutomationExecution.objects.filter(modulo=key).count()

            modules.append(
                {
                    'name': registry['label'],
                    'description': descriptions.get(key, 'Módulo disponível para sua operação.'),
                    'url_name': f'{key}:home',
                    'icon': registry['label'][:2].upper(),
                }
            )
            for automation in model.objects.all():
                automation_options.append(
                    {
                        'value': f'{key}:{automation.identificador}',
                        'label': f'{registry["label"]} / {automation.nome}',
                        'area': key,
                    }
                )
            sector_metrics.append(
                {
                    'key': key,
                    'label': registry['label'],
                    'icon': registry['icon'],
                    'total_automations': sector_total,
                    'active_automations': sector_active,
                    'execution_count': sector_executions,
                }
            )
            total_automations += sector_total
            total_active_automations += sector_active
            total_executions += sector_executions

        if selected_area not in visible_area_keys:
            selected_area = ''

        filtered_automation_options = [
            option for option in automation_options if not selected_area or option['area'] == selected_area
        ]
        if selected_automation and selected_automation not in {option['value'] for option in filtered_automation_options}:
            selected_automation = ''

        executions_queryset = AutomationExecution.objects.filter(modulo__in=visible_area_keys)

        if selected_area:
            executions_queryset = executions_queryset.filter(modulo=selected_area)

        if selected_automation:
            automation_area, automation_identifier = selected_automation.split(':', 1)
            registry = SECTOR_REGISTRY.get(automation_area)
            if registry and (not selected_area or selected_area == automation_area):
                automation = registry['model'].objects.filter(identificador=automation_identifier).first()
                if automation:
                    content_type = ContentType.objects.get_for_model(registry['model'])
                    executions_queryset = executions_queryset.filter(
                        modulo=automation_area,
                        content_type=content_type,
                        object_id=automation.pk,
                    )

        today = timezone.localdate()
        chart_days = [today - timedelta(days=offset) for offset in range(4, -1, -1)]
        chart_labels = [day.strftime('%d/%m') for day in chart_days]
        chart_counts = [executions_queryset.filter(criado_em__date=day).count() for day in chart_days]

        context['modules'] = modules
        context['module_count'] = len(modules)
        context['total_automations'] = total_automations
        context['total_active_automations'] = total_active_automations
        context['total_executions'] = total_executions
        context['sector_metrics'] = sector_metrics
        context['area_options'] = [
            {'value': key, 'label': SECTOR_REGISTRY[key]['label']} for key in visible_area_keys
        ]
        context['automation_options'] = filtered_automation_options
        context['selected_area'] = selected_area
        context['selected_automation'] = selected_automation
        context['chart_labels'] = chart_labels
        context['chart_counts'] = chart_counts
        context['chart_total'] = sum(chart_counts)
        return context
