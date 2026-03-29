from urllib.parse import urlencode

from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from core.models import AutomationExecution, AutomationExecutionFile
from core.sector_registry import SECTOR_REGISTRY
from core.security import (
    user_has_area_access,
    user_has_dashboard_access,
    user_has_module_access,
    visible_dashboard_keys_for_user,
    visible_module_keys_for_user,
)
from core.services import (
    create_execution,
    get_execution_automation,
    queue_position,
    save_automation_assets,
    schedule_pending_executions,
    stop_automation_request,
)
from documentacao.models import DocumentationPage

from .auth import (
    APITokenRequiredMixin,
    authenticate_api_user,
    get_or_create_default_token,
    json_error,
    parse_request_payload,
)


def automation_payload(module_key, automation):
    return {
        'module': module_key,
        'module_label': SECTOR_REGISTRY[module_key]['label'],
        'id': automation.pk,
        'nome': automation.nome,
        'identificador': automation.identificador,
        'descricao': automation.descricao,
        'executor_path': automation.executor_path,
        'ativa': automation.ativa,
        'aceita_arquivo_entrada': automation.aceita_arquivo_entrada,
        'aceita_anexos': automation.aceita_anexos,
        'em_execucao': automation.em_execucao,
        'criado_em': automation.criado_em.isoformat(),
        'atualizado_em': automation.atualizado_em.isoformat(),
    }


def execution_payload(execution):
    automation = get_execution_automation(execution)
    queue_pos = queue_position(execution)
    output_files = []
    for file in execution.arquivos.filter(tipo=AutomationExecutionFile.Tipo.OUTPUT):
        output_files.append(
            {
                'id': file.pk,
                'nome_original': file.nome_original,
                'url': file.arquivo.url if file.arquivo else '',
            }
        )
    return {
        'id': execution.pk,
        'modulo': execution.modulo,
        'automacao_nome': execution.automacao_nome,
        'automacao_identificador': getattr(automation, 'identificador', ''),
        'status': execution.status,
        'status_label': execution.get_status_display(),
        'mensagem_resumo': execution.mensagem_resumo,
        'log_saida': execution.log_saida,
        'parametros_texto': execution.parametros_texto,
        'interromper_solicitado': execution.interromper_solicitado,
        'queue_position': queue_pos,
        'criado_em': execution.criado_em.isoformat() if execution.criado_em else None,
        'iniciado_em': execution.iniciado_em.isoformat() if execution.iniciado_em else None,
        'finalizado_em': execution.finalizado_em.isoformat() if execution.finalizado_em else None,
        'output_files': output_files,
    }


def documentation_payload(page):
    automation = page.automacao
    return {
        'id': page.pk,
        'titulo': page.titulo,
        'status': page.status,
        'status_label': page.get_status_display(),
        'versao': page.versao,
        'publication_section': page.publication_section,
        'publication_section_label': page.get_publication_section_display(),
        'linked_automation': {
            'nome': getattr(automation, 'nome', None),
            'identificador': getattr(automation, 'identificador', None),
        },
        'updated_at': page.atualizado_em.isoformat(),
    }


def get_pagination_params(request):
    try:
        page = max(1, int(request.GET.get('page', 1)))
    except (TypeError, ValueError):
        page = 1

    try:
        per_page = int(request.GET.get('per_page', 20))
    except (TypeError, ValueError):
        per_page = 20

    per_page = max(1, min(per_page, 100))
    return page, per_page


def build_page_url(request, page_number):
    params = request.GET.copy()
    params['page'] = page_number
    return f'{request.path}?{urlencode(params, doseq=True)}'


def paginated_response(request, items):
    page, per_page = get_pagination_params(request)
    total = len(items)
    start = (page - 1) * per_page
    end = start + per_page
    sliced_items = items[start:end]
    total_pages = max(1, (total + per_page - 1) // per_page) if total else 1

    return {
        'count': total,
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages,
        'has_previous': page > 1,
        'has_next': end < total,
        'previous_page': build_page_url(request, page - 1) if page > 1 else None,
        'next_page': build_page_url(request, page + 1) if end < total else None,
        'results': sliced_items,
    }


def get_module_automation_or_404(module_key, identificador):
    registry = SECTOR_REGISTRY.get(module_key)
    if not registry:
        return None, json_error('Módulo não encontrado.', status=404)

    automation = registry['model'].objects.filter(identificador=identificador).first()
    if automation is None:
        return None, json_error('Automação não encontrada.', status=404)

    return automation, None


class APIHealthView(View):
    def get(self, request, *args, **kwargs):
        return JsonResponse(
            {
                'ok': True,
                'service': 'autocontrollers-api',
                'timestamp': timezone.now().isoformat(),
            }
        )


@method_decorator(csrf_exempt, name='dispatch')
class APITokenLoginView(View):
    def post(self, request, *args, **kwargs):
        payload = parse_request_payload(request)
        if payload is None:
            return json_error('Payload JSON inválido.')

        username = (payload.get('username') or '').strip()
        password = payload.get('password') or ''
        if not username or not password:
            return json_error('Informe username e password.', status=400)

        user = authenticate_api_user(username, password)
        if user is None:
            return json_error('Credenciais inválidas.', status=401)

        token = get_or_create_default_token(user)
        return JsonResponse(
            {
                'ok': True,
                'token_type': 'Bearer',
                'access_token': token.key,
                'user': {
                    'id': user.pk,
                    'username': user.username,
                    'is_superuser': user.is_superuser,
                },
            }
        )


class APITokenRevokeView(APITokenRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        self.api_token.is_active = False
        self.api_token.save(update_fields=['is_active', 'updated_at'])
        return JsonResponse({'ok': True, 'message': 'Token revogado com sucesso.'})


class APIMeView(APITokenRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        user = self.api_user
        return JsonResponse(
            {
                'ok': True,
                'user': {
                    'id': user.pk,
                    'username': user.username,
                    'email': user.email,
                    'is_superuser': user.is_superuser,
                    'visible_modules': visible_module_keys_for_user(user),
                    'visible_dashboards': visible_dashboard_keys_for_user(user),
                    'can_access_documentacao': user_has_area_access(user, 'documentacao'),
                    'can_access_administrador': user_has_area_access(user, 'administrador'),
                },
            }
        )


class APIModuleListView(APITokenRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        user = self.api_user
        modules = []
        for key, registry in SECTOR_REGISTRY.items():
            modules.append(
                {
                    'key': key,
                    'label': registry['label'],
                    'has_module_access': user_has_module_access(user, key),
                    'has_dashboard_access': user_has_dashboard_access(user, key),
                }
            )
        return JsonResponse({'ok': True, **paginated_response(request, modules)})


class APIAutomationListView(APITokenRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        user = self.api_user
        module_filter = request.GET.get('module', '').strip()
        modules = [module_filter] if module_filter else list(SECTOR_REGISTRY.keys())
        results = []

        for module_key in modules:
            registry = SECTOR_REGISTRY.get(module_key)
            if registry is None:
                continue
            if not user_has_module_access(user, module_key):
                continue
            for automation in registry['model'].objects.all():
                results.append(automation_payload(module_key, automation))

        return JsonResponse({'ok': True, **paginated_response(request, results)})


class APIAutomationExecuteView(APITokenRequiredMixin, View):
    def post(self, request, module_key, identificador, *args, **kwargs):
        if not user_has_module_access(self.api_user, module_key):
            return json_error('Você não possui acesso a este módulo.', status=403)

        automation, error_response = get_module_automation_or_404(module_key, identificador)
        if error_response:
            return error_response

        if not automation.ativa:
            return json_error('Esta automação está desativada no momento.', status=400)

        primary_files = request.FILES.getlist('arquivo_entrada')
        attachments = request.FILES.getlist('anexos')
        parametros_texto = request.POST.get('parametros_texto', '')

        if automation.aceita_arquivo_entrada is False and primary_files:
            return json_error('Esta automação não aceita arquivo de entrada.', status=400)
        if automation.aceita_anexos is False and attachments:
            return json_error('Esta automação não aceita anexos.', status=400)

        cleaned_data = {
            'arquivo_entrada': primary_files,
            'anexos': attachments,
            'parametros_texto': parametros_texto,
        }

        if primary_files or attachments:
            save_automation_assets(automation, cleaned_data)

        execution = create_execution(automation, self.api_user, cleaned_data, module_key)
        schedule_pending_executions()
        execution.refresh_from_db(fields=['status', 'pid', 'iniciado_em'])

        return JsonResponse(
            {
                'ok': True,
                'message': 'Automação iniciada.' if execution.status == AutomationExecution.Status.RUNNING else 'Automação adicionada na fila.',
                'execution': execution_payload(execution),
            },
            status=201,
        )


class APIExecutionListView(APITokenRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        user = self.api_user
        status_filter = request.GET.get('status', '').strip()
        module_filter = request.GET.get('module', '').strip()
        queryset = AutomationExecution.objects.all().prefetch_related('arquivos')

        allowed_modules = set(visible_module_keys_for_user(user))
        if user_has_area_access(user, 'administrador') or user.is_superuser:
            allowed_modules.update(SECTOR_REGISTRY.keys())

        queryset = queryset.filter(modulo__in=allowed_modules)

        if module_filter:
            queryset = queryset.filter(modulo=module_filter)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        results = [execution_payload(execution) for execution in queryset]
        return JsonResponse({'ok': True, **paginated_response(request, results)})


class APIExecutionDetailView(APITokenRequiredMixin, View):
    def get(self, request, execution_id, *args, **kwargs):
        execution = AutomationExecution.objects.filter(pk=execution_id).prefetch_related('arquivos').first()
        if execution is None:
            return json_error('Execução não encontrada.', status=404)

        allowed = (
            execution.modulo in visible_module_keys_for_user(self.api_user)
            or user_has_area_access(self.api_user, 'administrador')
            or self.api_user.is_superuser
        )
        if not allowed:
            return json_error('Você não possui acesso a esta execução.', status=403)

        return JsonResponse({'ok': True, 'execution': execution_payload(execution)})


class APIExecutionStopView(APITokenRequiredMixin, View):
    def post(self, request, execution_id, *args, **kwargs):
        execution = AutomationExecution.objects.filter(pk=execution_id).first()
        if execution is None:
            return json_error('Execução não encontrada.', status=404)

        allowed = (
            execution.modulo in visible_module_keys_for_user(self.api_user)
            or user_has_area_access(self.api_user, 'administrador')
            or self.api_user.is_superuser
        )
        if not allowed:
            return json_error('Você não possui acesso a esta execução.', status=403)

        stop_automation_request(request, execution, namespace=f'{execution.modulo}')
        execution.refresh_from_db()
        return JsonResponse({'ok': True, 'execution': execution_payload(execution)})


class APIDocumentationListView(APITokenRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        user = self.api_user
        pages = DocumentationPage.objects.filter(status=DocumentationPage.Status.PUBLISHED)
        results = []

        for page in pages:
            if page.possui_vinculo:
                automation = page.automacao
                module_key = None
                for key, registry in SECTOR_REGISTRY.items():
                    if automation and isinstance(automation, registry['model']):
                        module_key = key
                        break
                if module_key and not (
                    user_has_module_access(user, module_key)
                    or user_has_area_access(user, 'administrador')
                    or user.is_superuser
                ):
                    continue
                results.append(documentation_payload(page))
                continue

            section = page.publication_section
            if section == DocumentationPage.PublicationSection.ADMINISTRATION and not (
                user_has_area_access(user, 'administrador') or user.is_superuser
            ):
                continue
            if section in {'comercial', 'financeiro', 'ti'} and not (
                user_has_module_access(user, section)
                or user_has_area_access(user, 'administrador')
                or user.is_superuser
            ):
                continue
            results.append(documentation_payload(page))

        return JsonResponse({'ok': True, **paginated_response(request, results)})
