import re
from html import escape

from django.utils import timezone

from django.contrib.contenttypes.models import ContentType

from core.sector_registry import SECTOR_REGISTRY

from .models import DocumentationAuditLog, DocumentationPage, DocumentationViewAudit


HTML_TAG_PATTERN = re.compile(
    r'<(html|head|body|style|table|thead|tbody|tr|th|td|pre|code|p|div|h1|h2|h3|ul|ol|li|strong|em|u|span|a|img|blockquote|br)\b',
    re.IGNORECASE,
)


def normalize_html_document(raw_text):
    if not raw_text:
        return ''

    style_blocks = re.findall(r'<style\b[^>]*>.*?</style>', raw_text, flags=re.IGNORECASE | re.DOTALL)
    body_match = re.search(r'<body\b[^>]*>(.*?)</body>', raw_text, flags=re.IGNORECASE | re.DOTALL)
    body_content = body_match.group(1).strip() if body_match else raw_text.strip()
    return '\n'.join(style_blocks + [body_content]).strip()


def render_natural_document(raw_text):
    if not raw_text:
        return ''

    if HTML_TAG_PATTERN.search(raw_text):
        return normalize_html_document(raw_text)

    lines = (raw_text or '').splitlines()
    html_parts = []
    list_items = []

    def flush_list():
        nonlocal list_items
        if list_items:
            html_parts.append('<ul>' + ''.join(f'<li>{item}</li>' for item in list_items) + '</ul>')
            list_items = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            flush_list()
            continue

        if line.startswith('- '):
            list_items.append(escape(line[2:].strip()))
            continue

        flush_list()
        html_parts.append(f'<p>{escape(line)}</p>')

    flush_list()
    return '\n'.join(html_parts)


def get_documentation_page(automation):
    if automation is None:
        return None

    content_type = ContentType.objects.get_for_model(automation)
    return DocumentationPage.objects.filter(
        content_type=content_type,
        object_id=automation.pk,
    ).first()


def get_published_documentation_page(automation):
    page = get_documentation_page(automation)
    if not page:
        return None

    if page.status != DocumentationPage.Status.PUBLISHED:
        return None

    if not page.rendered_html.strip():
        return None

    return page


def resolve_automation_link(value):
    if not value:
        return None, None

    sector_key, identificador = value.split(':', 1)
    registry = SECTOR_REGISTRY.get(sector_key)
    if not registry:
        return None, None

    automation = registry['model'].objects.filter(identificador=identificador).first()
    if not automation:
        return None, None

    return registry, automation


def create_audit_log(page, user, action, changed_fields=None, note=''):
    automation = page.automacao
    DocumentationAuditLog.objects.create(
        documentacao=page,
        acao=action,
        usuario=user,
        titulo_snapshot=page.titulo,
        raw_content_snapshot=page.raw_content,
        rendered_html_snapshot=page.rendered_html,
        status_snapshot=page.status,
        versao_snapshot=page.versao,
        content_type_snapshot=page.content_type,
        object_id_snapshot=page.object_id,
        automacao_nome_snapshot=getattr(automation, 'nome', '') if automation else '',
        campos_alterados=changed_fields or [],
        observacao=note,
    )


def save_documentation_page(page, automation, user, cleaned_data):
    created = page.pk is None
    previous_raw_content = page.raw_content
    previous_title = page.titulo
    previous_status = page.status
    previous_rendered_html = page.rendered_html
    previous_publication_section = getattr(page, 'publication_section', DocumentationPage.PublicationSection.SYSTEM)
    previous_version = page.versao
    previous_content_type_id = page.content_type_id
    previous_object_id = page.object_id
    first_real_content = not page.raw_content.strip() and not page.rendered_html.strip() and page.atualizado_por is None

    if automation is not None:
        page.content_type = ContentType.objects.get_for_model(automation)
        page.object_id = automation.pk
    else:
        page.content_type = None
        page.object_id = None

    page.titulo = cleaned_data['titulo']
    page.raw_content = cleaned_data.get('raw_content', '')
    page.rendered_html = render_natural_document(page.raw_content)
    if automation is None:
        page.publication_section = cleaned_data.get(
            'publication_section',
            DocumentationPage.PublicationSection.SYSTEM,
        )
    else:
        page.publication_section = DocumentationPage.PublicationSection.SYSTEM
    if created:
        page.status = cleaned_data.get('status', DocumentationPage.Status.DRAFT)
    else:
        page.status = DocumentationPage.Status.DRAFT
    if created and page.criado_por is None:
        page.criado_por = user
    page.atualizado_por = user

    if not created and not first_real_content and (previous_raw_content != page.raw_content or previous_title != page.titulo):
        page.versao += 1

    page.save()
    changed_fields = []
    if created or previous_title != page.titulo:
        changed_fields.append('titulo')
    if created or previous_raw_content != page.raw_content:
        changed_fields.append('raw_content')
    if created or previous_rendered_html != page.rendered_html:
        changed_fields.append('rendered_html')
    if created or previous_publication_section != page.publication_section:
        changed_fields.append('secao_publicacao')
    if created or previous_status != page.status:
        changed_fields.append('status')
    if created or previous_version != page.versao:
        changed_fields.append('versao')
    if created or previous_content_type_id != page.content_type_id or previous_object_id != page.object_id:
        changed_fields.append('vinculo_automacao')

    create_audit_log(
        page=page,
        user=user,
        action=DocumentationAuditLog.Action.CREATED if created else DocumentationAuditLog.Action.UPDATED,
        changed_fields=changed_fields,
        note='Documento criado.' if created else 'Documento salvo pela tela de edição.',
    )
    return page


def create_documentation_page(user, cleaned_data):
    _, automation = resolve_automation_link(cleaned_data.get('automation_link', ''))
    page = get_documentation_page(automation) if automation is not None else None
    created = page is None

    if page is None:
        page = DocumentationPage(criado_por=user)

    page = save_documentation_page(page, automation, user, cleaned_data)
    return page, created


def start_view_audit(page, request):
    if request.session.session_key is None:
        request.session.create()

    return DocumentationViewAudit.objects.create(
        documentacao=page,
        usuario=request.user if request.user.is_authenticated else None,
        session_key=request.session.session_key or '',
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:1000],
    )


def finish_view_audit(view_audit, duration_seconds=None):
    now = timezone.now()
    view_audit.ultima_interacao_em = now
    view_audit.encerrado_em = now
    if duration_seconds is not None and duration_seconds >= 0:
        view_audit.tempo_permanencia_segundos = int(duration_seconds)
    elif view_audit.aberto_em:
        view_audit.tempo_permanencia_segundos = int((now - view_audit.aberto_em).total_seconds())

    view_audit.save(update_fields=['ultima_interacao_em', 'encerrado_em', 'tempo_permanencia_segundos'])
    return view_audit
