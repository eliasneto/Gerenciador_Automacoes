import difflib

from django.contrib import admin
from django.utils.html import format_html, strip_tags
from django.utils.safestring import mark_safe

from .models import DocumentationAuditLog, DocumentationPage, DocumentationViewAudit


class DocumentationAuditLogInline(admin.TabularInline):
    model = DocumentationAuditLog
    extra = 0
    can_delete = False
    fields = (
        'criado_em',
        'acao',
        'usuario',
        'status_snapshot',
        'versao_snapshot',
        'automacao_nome_snapshot',
        'observacao',
    )
    readonly_fields = fields
    ordering = ('-criado_em',)
    show_change_link = True


class DocumentationViewAuditInline(admin.TabularInline):
    model = DocumentationViewAudit
    extra = 0
    can_delete = False
    fields = (
        'aberto_em',
        'usuario',
        'tempo_permanencia_segundos',
        'encerrado_em',
    )
    readonly_fields = fields
    ordering = ('-aberto_em',)
    show_change_link = True


@admin.register(DocumentationPage)
class DocumentationPageAdmin(admin.ModelAdmin):
    list_display = (
        'titulo',
        'status',
        'versao',
        'automacao_nome',
        'criado_por',
        'atualizado_por',
        'atualizado_em',
    )
    list_filter = ('status', 'content_type', 'criado_em', 'atualizado_em')
    search_fields = ('titulo', 'raw_content', 'rendered_html')
    readonly_fields = (
        'criado_por',
        'atualizado_por',
        'criado_em',
        'atualizado_em',
        'preview_rendered_html',
    )
    inlines = [DocumentationAuditLogInline, DocumentationViewAuditInline]
    fieldsets = (
        ('Principal', {'fields': ('titulo', 'status', 'versao')}),
        ('Vínculo', {'fields': ('content_type', 'object_id')}),
        ('Conteúdo', {'fields': ('raw_content', 'preview_rendered_html')}),
        ('Auditoria', {'fields': ('criado_por', 'atualizado_por', 'criado_em', 'atualizado_em')}),
    )

    @admin.display(description='Automação vinculada')
    def automacao_nome(self, obj):
        return getattr(obj.automacao, 'nome', 'Sem vínculo')

    @admin.display(description='Pré-visualização do conteúdo')
    def preview_rendered_html(self, obj):
        if not obj.rendered_html:
            return 'Sem conteúdo renderizado.'
        content = strip_tags(obj.rendered_html).strip().replace('\n', '<br>')
        return format_html(
            '''
            <div style="max-width: 960px; padding: 0; color: #e5e7eb; line-height: 1.8;">
                <div>{}</div>
            </div>
            ''',
            mark_safe(content),
        )


@admin.register(DocumentationAuditLog)
class DocumentationAuditLogAdmin(admin.ModelAdmin):
    list_display = (
        'criado_em',
        'acao',
        'documento',
        'usuario',
        'status_snapshot',
        'versao_snapshot',
        'automacao_nome_snapshot',
    )
    list_filter = ('acao', 'status_snapshot', 'criado_em', 'content_type_snapshot')
    search_fields = (
        'titulo_snapshot',
        'raw_content_snapshot',
        'rendered_html_snapshot',
        'automacao_nome_snapshot',
        'observacao',
        'usuario__username',
    )
    readonly_fields = (
        'documentacao',
        'acao',
        'usuario',
        'titulo_registrado',
        'status_registrado',
        'versao_registrada',
        'tipo_de_conteudo_vinculado',
        'objeto_vinculado',
        'automacao_vinculada',
        'campos_alterados_formatados',
        'observacao',
        'criado_em',
        'preview_rendered_html_snapshot',
        'previous_snapshot_summary',
        'side_by_side_comparison',
        'raw_content_diff',
    )
    fieldsets = (
        ('Evento', {'fields': ('documentacao', 'acao', 'usuario', 'criado_em', 'observacao')}),
        ('Snapshot', {'fields': ('titulo_registrado', 'status_registrado', 'versao_registrada', 'campos_alterados_formatados')}),
        ('Vínculo', {'fields': ('tipo_de_conteudo_vinculado', 'objeto_vinculado', 'automacao_vinculada')}),
        ('Conteúdo', {'fields': ('preview_rendered_html_snapshot',)}),
        ('Versão Anterior', {'fields': ('previous_snapshot_summary',)}),
        ('Comparação Lado a Lado', {'fields': ('side_by_side_comparison',)}),
        ('Diff Visual do Conteúdo', {'fields': ('raw_content_diff',)}),
    )

    @admin.display(description='Documento')
    def documento(self, obj):
        return obj.documentacao.titulo

    @admin.display(description='Pré-visualização do conteúdo')
    def preview_rendered_html_snapshot(self, obj):
        if not obj.rendered_html_snapshot:
            return 'Sem conteúdo renderizado.'
        content = strip_tags(obj.rendered_html_snapshot).strip().replace('\n', '<br>')
        return format_html(
            '''
            <div style="max-width: 960px; padding: 0; color: #e5e7eb; line-height: 1.8;">
                <div>{}</div>
            </div>
            ''',
            mark_safe(content),
        )

    @admin.display(description='Título registrado')
    def titulo_registrado(self, obj):
        return obj.titulo_snapshot

    @admin.display(description='Status registrado')
    def status_registrado(self, obj):
        return obj.get_status_snapshot_display()

    @admin.display(description='Versão registrada')
    def versao_registrada(self, obj):
        return f'v{obj.versao_snapshot}'

    @admin.display(description='Tipo de conteúdo vinculado')
    def tipo_de_conteudo_vinculado(self, obj):
        return obj.content_type_snapshot or 'Sem vínculo'

    @admin.display(description='Objeto vinculado')
    def objeto_vinculado(self, obj):
        return obj.object_id_snapshot or 'Sem vínculo'

    @admin.display(description='Automação vinculada')
    def automacao_vinculada(self, obj):
        return obj.automacao_nome_snapshot or 'Sem vínculo'

    @admin.display(description='Campos alterados')
    def campos_alterados_formatados(self, obj):
        if not obj.campos_alterados:
            return 'Nenhum campo registrado.'
        labels = {
            'titulo': 'Título',
            'raw_content': 'Conteúdo bruto',
            'rendered_html': 'Conteúdo renderizado',
            'status': 'Status',
            'versao': 'Versão',
            'vinculo_automacao': 'Vínculo com automação',
        }
        return ', '.join(labels.get(item, item) for item in obj.campos_alterados)

    def _get_previous_log(self, obj):
        return (
            DocumentationAuditLog.objects.filter(
                documentacao=obj.documentacao,
                criado_em__lt=obj.criado_em,
            )
            .order_by('-criado_em')
            .first()
        )

    @admin.display(description='Resumo da versão anterior')
    def previous_snapshot_summary(self, obj):
        previous = self._get_previous_log(obj)
        if not previous:
            return 'Este é o primeiro registro de auditoria do documento.'

        return format_html(
            '''
            <div style="max-width: 960px; padding: 0; line-height: 1.9; color: #e5e7eb;">
                <p><strong>Título:</strong> {}</p>
                <p><strong>Status:</strong> {}</p>
                <p><strong>Versão:</strong> v{}</p>
                <p><strong>Usuário:</strong> {}</p>
                <p><strong>Data:</strong> {}</p>
            </div>
            ''',
            previous.titulo_snapshot,
            previous.get_status_snapshot_display(),
            previous.versao_snapshot,
            previous.usuario.username if previous.usuario else 'Não informado',
            previous.criado_em.strftime('%d/%m/%Y %H:%M'),
        )

    @admin.display(description='Versão anterior x versão atual')
    def side_by_side_comparison(self, obj):
        previous = self._get_previous_log(obj)
        if not previous:
            return 'Este é o primeiro registro de auditoria do documento.'

        previous_user = previous.usuario.username if previous.usuario else 'Não informado'
        current_user = obj.usuario.username if obj.usuario else 'Não informado'
        previous_content = strip_tags(previous.raw_content_snapshot or '').strip()
        current_content = strip_tags(obj.raw_content_snapshot or '').strip()

        return format_html(
            '''
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; max-width:1200px;">
                <div style="border:1px solid #374151; border-radius:16px; padding:20px; background:#111827; color:#e5e7eb;">
                    <div style="font-weight:700; font-size:12px; text-transform:uppercase; letter-spacing:0.12em; color:#93c5fd; margin-bottom:12px;">
                        Versão anterior
                    </div>
                    <p><strong>Título:</strong> {}</p>
                    <p><strong>Status:</strong> {}</p>
                    <p><strong>Versão:</strong> v{}</p>
                    <p><strong>Usuário:</strong> {}</p>
                    <p><strong>Conteúdo:</strong></p>
                    <pre style="white-space:pre-wrap; word-break:break-word; background:#0b1220; color:#e5e7eb; border:1px solid #374151; border-radius:12px; padding:16px; max-height:320px; overflow:auto;">{}</pre>
                </div>
                <div style="border:1px solid #1d4ed8; border-radius:16px; padding:20px; background:#0f172a; color:#e5e7eb;">
                    <div style="font-weight:700; font-size:12px; text-transform:uppercase; letter-spacing:0.12em; color:#60a5fa; margin-bottom:12px;">
                        Versão atual
                    </div>
                    <p><strong>Título:</strong> {}</p>
                    <p><strong>Status:</strong> {}</p>
                    <p><strong>Versão:</strong> v{}</p>
                    <p><strong>Usuário:</strong> {}</p>
                    <p><strong>Conteúdo:</strong></p>
                    <pre style="white-space:pre-wrap; word-break:break-word; background:#0b1220; color:#e5e7eb; border:1px solid #1d4ed8; border-radius:12px; padding:16px; max-height:320px; overflow:auto;">{}</pre>
                </div>
            </div>
            ''',
            previous.titulo_snapshot,
            previous.get_status_snapshot_display(),
            previous.versao_snapshot,
            previous_user,
            previous_content,
            obj.titulo_snapshot,
            obj.get_status_snapshot_display(),
            obj.versao_snapshot,
            current_user,
            current_content,
        )

    @admin.display(description='Diff visual')
    def raw_content_diff(self, obj):
        previous = self._get_previous_log(obj)
        if not previous:
            return 'Este é o primeiro registro de auditoria do documento.'

        before = (previous.raw_content_snapshot or '').splitlines()
        after = (obj.raw_content_snapshot or '').splitlines()
        if before == after:
            return mark_safe(
                '''
                <div style="max-width: 820px; border:1px solid #374151; border-radius:16px; background:#0f172a; padding:18px 20px; color:#e5e7eb;">
                    <p style="margin:0; font-weight:700; color:#93c5fd;">Nenhuma alteração textual detectada</p>
                    <p style="margin:8px 0 0 0; color:#cbd5e1; line-height:1.7;">
                        Este registro mudou metadados do documento, mas o conteúdo em texto permaneceu igual ao da versão anterior.
                    </p>
                </div>
                '''
            )

        diff_html = difflib.HtmlDiff(wrapcolumn=80).make_table(
            before,
            after,
            fromdesc='Versão anterior',
            todesc='Versão atual',
            context=True,
            numlines=2,
        )
        return format_html(
            '''
            <div style="max-width: 1200px; overflow:auto; border:1px solid #374151; border-radius:16px; background:#0f172a; padding:8px;">
                <style>
                    .diff {{
                        width: 100%;
                        border-collapse: collapse;
                        color: #e5e7eb;
                        background: #0f172a;
                    }}
                    .diff th, .diff td {{
                        border: 1px solid #374151;
                        padding: 8px;
                        vertical-align: top;
                    }}
                    .diff_header {{
                        background: #1f2937;
                        color: #93c5fd;
                    }}
                    .diff_next {{
                        background: #111827;
                    }}
                    .diff_add {{
                        background: rgba(34, 197, 94, 0.18);
                        color: #dcfce7;
                    }}
                    .diff_chg {{
                        background: rgba(234, 179, 8, 0.18);
                        color: #fef3c7;
                    }}
                    .diff_sub {{
                        background: rgba(239, 68, 68, 0.18);
                        color: #fee2e2;
                    }}
                </style>
                {}
            </div>
            ''',
            mark_safe(diff_html),
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(DocumentationViewAudit)
class DocumentationViewAuditAdmin(admin.ModelAdmin):
    list_display = (
        'aberto_em',
        'documento',
        'usuario',
        'tempo_formatado',
        'encerrado_em',
    )
    list_filter = ('aberto_em', 'encerrado_em')
    search_fields = ('documentacao__titulo', 'usuario__username', 'user_agent')
    readonly_fields = (
        'documentacao',
        'usuario',
        'aberto_em',
        'ultima_interacao_em',
        'encerrado_em',
        'tempo_formatado',
        'session_key',
        'user_agent',
    )
    fieldsets = (
        ('Visualização', {'fields': ('documentacao', 'usuario', 'aberto_em', 'encerrado_em', 'tempo_formatado')}),
        ('Sessão', {'fields': ('ultima_interacao_em', 'session_key', 'user_agent')}),
    )

    @admin.display(description='Documento')
    def documento(self, obj):
        return obj.documentacao.titulo

    @admin.display(description='Tempo de permanência')
    def tempo_formatado(self, obj):
        if obj.tempo_permanencia_segundos is None:
            return 'Ainda não calculado'

        total = int(obj.tempo_permanencia_segundos)
        horas, resto = divmod(total, 3600)
        minutos, segundos = divmod(resto, 60)
        if horas:
            return f'{horas}h {minutos}m {segundos}s'
        if minutos:
            return f'{minutos}m {segundos}s'
        return f'{segundos}s'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
