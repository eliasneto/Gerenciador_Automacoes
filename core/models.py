from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models


User = get_user_model()


class AutomationBaseModel(models.Model):
    nome = models.CharField(max_length=120)
    identificador = models.SlugField(max_length=120)
    descricao = models.TextField(blank=True)
    executor_path = models.CharField(max_length=255)
    aceita_arquivo_entrada = models.BooleanField(default=True)
    aceita_anexos = models.BooleanField(default=True)
    ativa = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    execucoes = GenericRelation(
        'core.AutomationExecution',
        content_type_field='content_type',
        object_id_field='object_id',
        related_query_name='automacao',
    )
    arquivos_salvos = GenericRelation(
        'core.AutomationAsset',
        content_type_field='content_type',
        object_id_field='object_id',
        related_query_name='automacao',
    )

    class Meta:
        abstract = True
        ordering = ['nome']

    def __str__(self):
        return self.nome

    @property
    def em_execucao(self):
        return self.execucoes.filter(status=AutomationExecution.Status.RUNNING).exists()


class AutomationQueueSettings(models.Model):
    max_concurrent_executions = models.PositiveIntegerField(default=1)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Configuração da fila de automações'
        verbose_name_plural = 'Configurações da fila de automações'

    def __str__(self):
        return f'Fila de automações (máx. {self.max_concurrent_executions} simultâneas)'


class AutomationExecution(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendente'
        RUNNING = 'running', 'Executando'
        SUCCESS = 'success', 'Sucesso'
        ERROR = 'error', 'Erro'
        STOPPED = 'stopped', 'Interrompida'

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    automacao = GenericForeignKey('content_type', 'object_id')

    usuario = models.ForeignKey(User, on_delete=models.PROTECT, related_name='automation_executions')
    modulo = models.CharField(max_length=40)
    automacao_nome = models.CharField(max_length=120)
    executor_path = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    parametros_texto = models.TextField(blank=True)
    mensagem_resumo = models.TextField(blank=True)
    log_saida = models.TextField(blank=True)
    arquivo_entrada = models.FileField(upload_to='entradas/%Y/%m/%d/', blank=True, null=True)
    pid = models.IntegerField(blank=True, null=True)
    interromper_solicitado = models.BooleanField(default=False)
    current_rss_mb = models.FloatField(blank=True, null=True)
    peak_rss_mb = models.FloatField(blank=True, null=True)
    cpu_user_seconds = models.FloatField(blank=True, null=True)
    cpu_system_seconds = models.FloatField(blank=True, null=True)
    metrics_updated_em = models.DateTimeField(blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    iniciado_em = models.DateTimeField(blank=True, null=True)
    finalizado_em = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Execução de automação'
        verbose_name_plural = 'Execuções de automação'

    def __str__(self):
        return f'{self.automacao_nome} - {self.get_status_display()}'

    @property
    def output_dir(self):
        return Path('saidas') / self.modulo / str(self.id)


class AutomationExecutionFile(models.Model):
    class Tipo(models.TextChoices):
        PRIMARY_INPUT = 'primary_input', 'Principal'
        ATTACHMENT = 'attachment', 'Anexo'
        OUTPUT = 'output', 'Saida'

    execution = models.ForeignKey(AutomationExecution, on_delete=models.CASCADE, related_name='arquivos')
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    arquivo = models.FileField(upload_to='automacoes/')
    nome_original = models.CharField(max_length=255)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Arquivo da execução'
        verbose_name_plural = 'Arquivos da execução'

    def __str__(self):
        return f'{self.get_tipo_display()} - {self.nome_original}'


class AutomationAsset(models.Model):
    class Tipo(models.TextChoices):
        PRIMARY = 'primary', 'Principal'
        AUXILIARY = 'auxiliary', 'Auxiliar'

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    automacao = GenericForeignKey('content_type', 'object_id')

    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    arquivo = models.FileField(upload_to='automacoes/salvos/%Y/%m/%d/')
    nome_original = models.CharField(max_length=255)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Arquivo salvo da automação'
        verbose_name_plural = 'Arquivos salvos da automação'

    def __str__(self):
        return f'{self.get_tipo_display()} - {self.nome_original}'
