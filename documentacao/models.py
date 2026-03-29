from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


User = get_user_model()


class DocumentationPage(models.Model):
    class PublicationSection(models.TextChoices):
        SYSTEM = 'system', 'Sistema'
        ADMINISTRATION = 'administracao', 'Administração'
        COMMERCIAL = 'comercial', 'Comercial'
        FINANCIAL = 'financeiro', 'Financeiro'
        IT = 'ti', 'TI'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Rascunho'
        PUBLISHED = 'published', 'Publicado'
        ARCHIVED = 'archived', 'Arquivado'

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, blank=True, null=True)
    object_id = models.PositiveBigIntegerField(blank=True, null=True)
    automacao = GenericForeignKey('content_type', 'object_id')

    titulo = models.CharField(max_length=160)
    raw_content = models.TextField(blank=True)
    rendered_html = models.TextField(blank=True)
    publication_section = models.CharField(
        max_length=20,
        choices=PublicationSection.choices,
        default=PublicationSection.SYSTEM,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    versao = models.PositiveIntegerField(default=1)
    criado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='documentation_creations',
        blank=True,
        null=True,
    )
    atualizado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='documentation_updates',
        blank=True,
        null=True,
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-atualizado_em']
        verbose_name = 'Documento'
        verbose_name_plural = 'Documentos'
        constraints = [
            models.UniqueConstraint(
                fields=['content_type', 'object_id'],
                name='unique_documentation_page_per_automation',
            )
        ]

    def __str__(self):
        return self.titulo

    @property
    def possui_vinculo(self):
        return self.content_type_id is not None and self.object_id is not None


class DocumentationAuditLog(models.Model):
    class Action(models.TextChoices):
        CREATED = 'created', 'Criação'
        UPDATED = 'updated', 'Alteração'
        STATUS_CHANGED = 'status_changed', 'Mudança de status'

    documentacao = models.ForeignKey(
        DocumentationPage,
        on_delete=models.CASCADE,
        related_name='auditorias',
    )
    acao = models.CharField(max_length=20, choices=Action.choices)
    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='documentation_audit_logs',
    )
    titulo_snapshot = models.CharField(max_length=160)
    raw_content_snapshot = models.TextField(blank=True)
    rendered_html_snapshot = models.TextField(blank=True)
    status_snapshot = models.CharField(max_length=20, choices=DocumentationPage.Status.choices)
    versao_snapshot = models.PositiveIntegerField(default=1)
    content_type_snapshot = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='+',
    )
    object_id_snapshot = models.PositiveBigIntegerField(blank=True, null=True)
    automacao_nome_snapshot = models.CharField(max_length=160, blank=True)
    campos_alterados = models.JSONField(default=list, blank=True)
    observacao = models.CharField(max_length=255, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Auditoria de documentação'
        verbose_name_plural = 'Auditorias de documentação'

    def __str__(self):
        return f'{self.get_acao_display()} - {self.titulo_snapshot} - {self.criado_em:%d/%m/%Y %H:%M}'


class DocumentationViewAudit(models.Model):
    documentacao = models.ForeignKey(
        DocumentationPage,
        on_delete=models.CASCADE,
        related_name='visualizacoes',
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='documentation_view_audits',
    )
    aberto_em = models.DateTimeField(auto_now_add=True)
    ultima_interacao_em = models.DateTimeField(blank=True, null=True)
    encerrado_em = models.DateTimeField(blank=True, null=True)
    tempo_permanencia_segundos = models.PositiveIntegerField(blank=True, null=True)
    session_key = models.CharField(max_length=40, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        ordering = ['-aberto_em']
        verbose_name = 'Auditoria de visualização'
        verbose_name_plural = 'Auditorias de visualização'

    def __str__(self):
        usuario = self.usuario.username if self.usuario else 'Usuário não informado'
        return f'{self.documentacao.titulo} - {usuario} - {self.aberto_em:%d/%m/%Y %H:%M}'
