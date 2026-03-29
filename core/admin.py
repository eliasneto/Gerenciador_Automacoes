from django.contrib import admin
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

from .models import AutomationExecution, AutomationExecutionFile, AutomationQueueSettings
from .services import schedule_pending_executions


class AutomationExecutionFileInline(admin.TabularInline):
    model = AutomationExecutionFile
    extra = 0
    readonly_fields = ('tipo', 'arquivo', 'nome_original', 'criado_em')


@admin.register(AutomationExecution)
class AutomationExecutionAdmin(admin.ModelAdmin):
    list_display = (
        'automacao_nome',
        'modulo',
        'usuario',
        'status',
        'fila',
        'criado_em',
        'iniciado_em',
        'finalizado_em',
    )
    list_filter = ('modulo', 'status')
    search_fields = ('automacao_nome', 'usuario__username', 'mensagem_resumo')
    readonly_fields = ('criado_em', 'iniciado_em', 'finalizado_em', 'pid')
    inlines = [AutomationExecutionFileInline]

    @admin.display(description='Fila')
    def fila(self, obj):
        if obj.status != AutomationExecution.Status.PENDING:
            return '-'

        position = AutomationExecution.objects.filter(
            status=AutomationExecution.Status.PENDING,
            criado_em__lte=obj.criado_em,
        ).count()
        return f'Na fila ({position}º)'


@admin.register(AutomationQueueSettings)
class AutomationQueueSettingsAdmin(admin.ModelAdmin):
    list_display = ('max_concurrent_executions', 'atualizado_em')
    readonly_fields = ('resumo_operacional', 'atualizado_em')
    fieldsets = (
        ('Fila de execução', {'fields': ('resumo_operacional', 'max_concurrent_executions', 'atualizado_em')}),
    )

    def changelist_view(self, request, extra_context=None):
        settings_obj = AutomationQueueSettings.objects.order_by('pk').first()
        if settings_obj:
            return redirect(reverse('admin:core_automationqueuesettings_change', args=[settings_obj.pk]))
        return super().changelist_view(request, extra_context)

    def has_add_permission(self, request):
        if AutomationQueueSettings.objects.exists():
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        context.update(
            {
                'show_save_and_continue': False,
                'show_delete': False,
                'show_save_as_new': False,
            }
        )
        return super().render_change_form(request, context, add, change, form_url, obj)

    def response_change(self, request, obj):
        schedule_pending_executions()
        messages.success(
            request,
            f'Limite salvo com sucesso. O sistema agora permite até {obj.max_concurrent_executions} automação(ões) rodando ao mesmo tempo.',
        )
        return redirect(reverse('admin:core_automationqueuesettings_change', args=[obj.pk]))

    @admin.display(description='Configuração ativa')
    def resumo_operacional(self, obj):
        return (
            f'Limite atual aplicado no sistema: {obj.max_concurrent_executions} automação(ões) simultânea(s). '
            'Quando esse limite é atingido, as próximas execuções entram na fila automaticamente.'
        )
