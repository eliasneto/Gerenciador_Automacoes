import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect
from django.http import Http404, HttpResponseBadRequest, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import FormView, TemplateView

from core.sector_registry import SECTOR_REGISTRY
from core.security import user_has_area_access, user_has_module_access

from .forms import DocumentationCreateForm, DocumentationEditForm, DocumentationPageForm
from .models import DocumentationAuditLog, DocumentationPage, DocumentationViewAudit
from .services import (
    create_audit_log,
    create_documentation_page,
    finish_view_audit,
    get_documentation_page,
    get_published_documentation_page,
    resolve_automation_link,
    save_documentation_page,
    start_view_audit,
)


class DocumentationModuleRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return user_has_area_access(self.request.user, 'documentacao')

    def handle_no_permission(self):
        messages.error(self.request, 'A area de documentacao nao esta liberada para o seu usuario.')
        return redirect('core:dashboard')


class DocumentationAdminRequiredMixin(DocumentationModuleRequiredMixin):
    def handle_no_permission(self):
        messages.error(self.request, 'A edição da documentação está disponível apenas para usuários autorizados.')
        return redirect('documentacao:home')


def get_automation_from_route(sector_key, identificador):
    registry = SECTOR_REGISTRY.get(sector_key)
    if not registry:
        raise Http404('Setor nao encontrado.')

    automation = registry['model'].objects.filter(identificador=identificador).first()
    if not automation:
        raise Http404('Automacao nao encontrada.')

    return registry, automation


class DocumentationHomeView(LoginRequiredMixin, TemplateView):
    template_name = 'documentacao/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sectors = []
        standalone_pages = list(
            DocumentationPage.objects.filter(
                status=DocumentationPage.Status.PUBLISHED,
                content_type__isnull=True,
                object_id__isnull=True,
            )
        )
        standalone_by_section = {
            DocumentationPage.PublicationSection.SYSTEM: [],
            DocumentationPage.PublicationSection.ADMINISTRATION: [],
            DocumentationPage.PublicationSection.COMMERCIAL: [],
            DocumentationPage.PublicationSection.FINANCIAL: [],
            DocumentationPage.PublicationSection.IT: [],
        }
        for page in standalone_pages:
            standalone_by_section.setdefault(page.publication_section, []).append(page)

        system_pages = standalone_by_section[DocumentationPage.PublicationSection.SYSTEM]
        if system_pages:
            sectors.append(
                {
                    'key': 'sistema',
                    'label': 'Sistema',
                    'icon': 'folders',
                    'count': len(system_pages),
                    'system_pages': system_pages,
                    'is_system': True,
                }
            )

        administration_pages = standalone_by_section[DocumentationPage.PublicationSection.ADMINISTRATION]
        if administration_pages and (
            user_has_area_access(self.request.user, 'administrador') or self.request.user.is_superuser
        ):
            sectors.append(
                {
                    'key': 'administracao',
                    'label': 'Administração',
                    'icon': 'shield-plus',
                    'count': len(administration_pages),
                    'system_pages': administration_pages,
                    'is_system': True,
                    'is_admin_section': True,
                }
            )

        for key, registry in SECTOR_REGISTRY.items():
            automations = list(registry['model'].objects.all())
            standalone_sector_pages = standalone_by_section.get(key, [])
            for automation in automations:
                documentation_page = get_documentation_page(automation)
                published_page = get_published_documentation_page(automation)
                automation.documentation_page = published_page
                automation.documentation_status = documentation_page.status if documentation_page else None
                automation.has_documentation = bool(published_page)
                automation.can_open_documentation = bool(published_page or self.request.user.is_superuser)

            can_view_standalone_sector_pages = bool(
                standalone_sector_pages and (
                    user_has_module_access(self.request.user, key)
                    or user_has_area_access(self.request.user, 'administrador')
                    or self.request.user.is_superuser
                )
            )
            sectors.append(
                {
                    'key': key,
                    'label': registry['label'],
                    'icon': registry['icon'],
                    'count': len(automations) + (len(standalone_sector_pages) if can_view_standalone_sector_pages else 0),
                    'automations': automations,
                    'standalone_pages': standalone_sector_pages if can_view_standalone_sector_pages else [],
                    'is_system': False,
                }
            )

        context['sectors'] = sectors
        context['total_automations'] = sum(sector['count'] for sector in sectors)
        return context


class DocumentationDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'documentacao/detail.html'

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sector_key = self.kwargs['sector']
        identificador = self.kwargs['identificador']

        registry, automation = get_automation_from_route(sector_key, identificador)
        documentation_page = get_documentation_page(automation)
        published_page = get_published_documentation_page(automation)
        can_view_document = bool(published_page or self.request.user.is_superuser)
        visible_page = documentation_page if self.request.user.is_superuser else published_page
        view_audit = start_view_audit(visible_page, self.request) if visible_page and can_view_document else None

        context['sector'] = {
            'key': sector_key,
            'label': registry['label'],
            'icon': registry['icon'],
        }
        context['automation'] = automation
        context['documentation_page'] = visible_page or DocumentationPage(
            titulo=f'Documentação - {automation.nome}',
            status=DocumentationPage.Status.DRAFT,
            versao=1,
        )
        context['document_is_published'] = bool(published_page)
        context['can_view_document'] = can_view_document
        context['view_audit'] = view_audit
        return context


class DocumentationStandaloneDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'documentacao/detail.html'

    def dispatch(self, request, *args, **kwargs):
        self.documentation_page = get_object_or_404(
            DocumentationPage,
            pk=kwargs['page_id'],
            content_type__isnull=True,
            object_id__isnull=True,
        )

        if self.documentation_page.status != DocumentationPage.Status.PUBLISHED and not request.user.is_superuser:
            messages.error(request, 'Esta documentação ainda não está disponível para consulta.')
            return redirect('documentacao:home')

        if (
            self.documentation_page.publication_section == DocumentationPage.PublicationSection.ADMINISTRATION
            and not user_has_area_access(request.user, 'administrador')
        ):
            messages.error(request, 'Esta documentação está publicada apenas para administradores do sistema.')
            return redirect('core:dashboard')

        if (
            self.documentation_page.publication_section in {'comercial', 'financeiro', 'ti'}
            and not (
                user_has_module_access(request.user, self.documentation_page.publication_section)
                or user_has_area_access(request.user, 'administrador')
                or request.user.is_superuser
            )
        ):
            messages.error(request, 'Esta documentação está publicada apenas para usuários autorizados deste setor.')
            return redirect('core:dashboard')

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        can_view_document = bool(
            self.documentation_page.status == DocumentationPage.Status.PUBLISHED or self.request.user.is_superuser
        )
        view_audit = (
            start_view_audit(self.documentation_page, self.request)
            if self.documentation_page and can_view_document
            else None
        )

        section_key = self.documentation_page.publication_section
        section_icons = {
            DocumentationPage.PublicationSection.SYSTEM: 'folders',
            DocumentationPage.PublicationSection.ADMINISTRATION: 'shield-plus',
            DocumentationPage.PublicationSection.COMMERCIAL: SECTOR_REGISTRY['comercial']['icon'],
            DocumentationPage.PublicationSection.FINANCIAL: SECTOR_REGISTRY['financeiro']['icon'],
            DocumentationPage.PublicationSection.IT: SECTOR_REGISTRY['ti']['icon'],
        }
        context['sector'] = {
            'key': section_key,
            'label': self.documentation_page.get_publication_section_display(),
            'icon': section_icons.get(section_key, 'folders'),
        }
        context['automation'] = None
        context['documentation_page'] = self.documentation_page
        context['document_is_published'] = self.documentation_page.status == DocumentationPage.Status.PUBLISHED
        context['can_view_document'] = can_view_document
        context['view_audit'] = view_audit
        context['is_standalone_document'] = True
        return context


class DocumentationEditView(LoginRequiredMixin, DocumentationAdminRequiredMixin, FormView):
    template_name = 'documentacao/edit.html'
    form_class = DocumentationEditForm

    def dispatch(self, request, *args, **kwargs):
        self.registry, self.automation = get_automation_from_route(kwargs['sector'], kwargs['identificador'])
        self.documentation_page = get_documentation_page(self.automation) or DocumentationPage(
            titulo=f'Documentação - {self.automation.nome}',
            status=DocumentationPage.Status.DRAFT,
            versao=1,
        )
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        initial.update(
            {
                'titulo': self.documentation_page.titulo or f'Documentação - {self.automation.nome}',
                'raw_content': self.documentation_page.raw_content,
                'automation_link': f'{self.kwargs["sector"]}:{self.automation.identificador}',
                'publication_section': self.documentation_page.publication_section,
            }
        )
        return initial

    def form_valid(self, form):
        _, selected_automation = resolve_automation_link(form.cleaned_data.get('automation_link', ''))
        target_automation = selected_automation or self.automation
        existing_page = get_documentation_page(target_automation) if target_automation else None
        if existing_page and existing_page.pk != self.documentation_page.pk:
            form.add_error(None, 'A automação selecionada já possui uma documentação vinculada.')
            return self.form_invalid(form)

        save_documentation_page(self.documentation_page, target_automation, self.request.user, form.cleaned_data)
        messages.success(self.request, 'Documentação salva e convertida para HTML com sucesso.')
        return redirect('documentacao:manage')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sector'] = {
            'key': self.kwargs['sector'],
            'label': self.registry['label'],
            'icon': self.registry['icon'],
        }
        context['automation'] = self.automation
        context['documentation_page'] = self.documentation_page
        return context


class DocumentationEditByPageView(LoginRequiredMixin, DocumentationAdminRequiredMixin, FormView):
    template_name = 'documentacao/edit_page.html'
    form_class = DocumentationEditForm

    def dispatch(self, request, *args, **kwargs):
        self.documentation_page = DocumentationPage.objects.select_related('criado_por', 'atualizado_por').get(pk=kwargs['page_id'])
        self.automation = self.documentation_page.automacao
        self.registry = None

        if self.automation:
            self.registry = next(
                (
                    {'key': key, 'label': data['label'], 'icon': data['icon']}
                    for key, data in SECTOR_REGISTRY.items()
                    if isinstance(self.automation, data['model'])
                ),
                None,
            )
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        initial.update(
            {
                'titulo': self.documentation_page.titulo,
                'raw_content': self.documentation_page.raw_content,
                'automation_link': (
                    f'{self.registry["key"]}:{self.automation.identificador}'
                    if self.automation and self.registry else ''
                ),
                'publication_section': self.documentation_page.publication_section,
            }
        )
        return initial

    def form_valid(self, form):
        _, selected_automation = resolve_automation_link(form.cleaned_data.get('automation_link', ''))
        target_automation = selected_automation
        existing_page = get_documentation_page(target_automation) if target_automation else None
        if existing_page and existing_page.pk != self.documentation_page.pk:
            form.add_error(None, 'A automação selecionada já possui uma documentação vinculada.')
            return self.form_invalid(form)

        save_documentation_page(self.documentation_page, target_automation, self.request.user, form.cleaned_data)
        messages.success(self.request, 'Documentação salva e convertida para HTML com sucesso.')
        return redirect('documentacao:manage')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sector'] = self.registry
        context['automation'] = self.automation
        context['documentation_page'] = self.documentation_page
        return context


class DocumentationManageView(LoginRequiredMixin, DocumentationAdminRequiredMixin, TemplateView):
    template_name = 'documentacao/manage.html'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pages_queryset = DocumentationPage.objects.select_related('criado_por', 'atualizado_por', 'content_type')
        page_obj = Paginator(pages_queryset, self.paginate_by).get_page(self.request.GET.get('documentos_page'))
        pages = list(page_obj.object_list)

        for page in pages:
            page.sector_key = next(
                (
                    key for key, registry in SECTOR_REGISTRY.items()
                    if page.automacao and isinstance(page.automacao, registry['model'])
                ),
                None,
            )
            page.linked_automation_name = page.automacao.nome if page.automacao else 'Sem vínculo'
            page.has_link = page.automacao is not None
            page.responsavel_nome = (
                page.atualizado_por.username if page.atualizado_por else (
                    page.criado_por.username if page.criado_por else 'Não informado'
                )
            )
            page.data_referencia = page.atualizado_em if page.atualizado_por else page.criado_em

        context['pages'] = pages
        context['page_obj'] = page_obj
        context['total_pages'] = pages_queryset.count()
        context['published_pages'] = pages_queryset.filter(status=DocumentationPage.Status.PUBLISHED).count()
        context['draft_pages'] = pages_queryset.filter(status=DocumentationPage.Status.DRAFT).count()
        return context


class DocumentationStatusUpdateView(LoginRequiredMixin, DocumentationAdminRequiredMixin, View):
    def post(self, request, page_id, *args, **kwargs):
        page = get_object_or_404(DocumentationPage, pk=page_id)
        new_status = request.POST.get('status')
        valid_statuses = {choice[0] for choice in DocumentationPage.Status.choices}

        if new_status not in valid_statuses:
            messages.error(request, 'Status de documentação inválido.')
            return redirect('documentacao:manage')

        if page.status != new_status:
            page.status = new_status
            page.atualizado_por = request.user
            page.save(update_fields=['status', 'atualizado_por', 'atualizado_em'])
            create_audit_log(
                page=page,
                user=request.user,
                action=DocumentationAuditLog.Action.STATUS_CHANGED,
                changed_fields=['status'],
                note=f'Status alterado para {page.get_status_display()}.',
            )
            messages.success(request, f'Status do documento atualizado para {page.get_status_display().lower()}.')
        else:
            messages.info(request, 'O documento já estava com esse status.')

        return redirect('documentacao:manage')


class DocumentationCreateView(LoginRequiredMixin, DocumentationAdminRequiredMixin, FormView):
    template_name = 'documentacao/create.html'
    form_class = DocumentationCreateForm

    def get_initial(self):
        initial = super().get_initial()
        initial.update(
            {
                'status': DocumentationPage.Status.DRAFT,
                'titulo': 'Nova documentação',
                'publication_section': DocumentationPage.PublicationSection.SYSTEM,
            }
        )
        return initial

    def form_valid(self, form):
        page, created = create_documentation_page(self.request.user, form.cleaned_data)
        if created:
            messages.success(self.request, 'Documentação criada com sucesso.')
        else:
            messages.info(self.request, 'A automação já possuía uma documentação vinculada. O documento existente foi atualizado no grid para continuação.')
        return redirect('documentacao:manage')


@method_decorator(csrf_exempt, name='dispatch')
class DocumentationViewAuditCloseView(LoginRequiredMixin, View):
    def post(self, request, audit_id, *args, **kwargs):
        audit = get_object_or_404(DocumentationViewAudit, pk=audit_id, usuario=request.user)

        try:
            payload = json.loads(request.body.decode('utf-8') or '{}')
        except json.JSONDecodeError:
            return HttpResponseBadRequest('Payload inválido.')

        duration_seconds = payload.get('duration_seconds')
        finish_view_audit(audit, duration_seconds=duration_seconds)
        return JsonResponse({'ok': True})
