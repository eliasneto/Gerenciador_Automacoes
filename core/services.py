import importlib
import os
import signal
import subprocess
import sys
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.db import connection, transaction
from django.urls import reverse
from django.utils import timezone

from .forms import AutomationRunForm
from .models import (
    AutomationAsset,
    AutomationExecution,
    AutomationExecutionFile,
    AutomationQueueSettings,
)


def build_success_url(namespace):
    return reverse(f'{namespace}:home')


def get_queue_settings():
    settings_obj = AutomationQueueSettings.objects.order_by('pk').first()
    if settings_obj is None:
        settings_obj = AutomationQueueSettings.objects.create(max_concurrent_executions=1)
    return settings_obj


@transaction.atomic
def create_execution(automation, user, cleaned_data, module_name):
    primary_files = cleaned_data.get('arquivo_entrada', [])
    execution = AutomationExecution.objects.create(
        content_type=ContentType.objects.get_for_model(automation),
        object_id=automation.pk,
        usuario=user,
        modulo=module_name,
        automacao_nome=automation.nome,
        executor_path=automation.executor_path,
        parametros_texto=cleaned_data.get('parametros_texto', ''),
        arquivo_entrada=primary_files[0] if primary_files else None,
        status=AutomationExecution.Status.PENDING,
    )

    for primary_file in primary_files[1:]:
        AutomationExecutionFile.objects.create(
            execution=execution,
            tipo=AutomationExecutionFile.Tipo.PRIMARY_INPUT,
            arquivo=primary_file,
            nome_original=primary_file.name,
        )

    for attachment in cleaned_data.get('anexos', []):
        AutomationExecutionFile.objects.create(
            execution=execution,
            tipo=AutomationExecutionFile.Tipo.ATTACHMENT,
            arquivo=attachment,
            nome_original=attachment.name,
        )

    return execution


def save_automation_assets(automation, cleaned_data):
    primary_files = cleaned_data.get('arquivo_entrada', [])
    auxiliary_files = cleaned_data.get('anexos', [])

    if primary_files:
        existing_primary = automation.arquivos_salvos.filter(tipo=AutomationAsset.Tipo.PRIMARY)
        for asset in existing_primary:
            asset.arquivo.delete(save=False)
            asset.delete()

        for primary_file in primary_files:
            AutomationAsset.objects.create(
                content_type=ContentType.objects.get_for_model(automation),
                object_id=automation.pk,
                tipo=AutomationAsset.Tipo.PRIMARY,
                arquivo=primary_file,
                nome_original=primary_file.name,
            )

    for auxiliary in auxiliary_files:
        AutomationAsset.objects.create(
            content_type=ContentType.objects.get_for_model(automation),
            object_id=automation.pk,
            tipo=AutomationAsset.Tipo.AUXILIARY,
            arquivo=auxiliary,
            nome_original=auxiliary.name,
        )


def spawn_execution_process(execution):
    command = [sys.executable, 'manage.py', 'run_automation', str(execution.pk)]
    process = subprocess.Popen(command, cwd=settings.BASE_DIR)
    execution.pid = process.pid
    execution.status = AutomationExecution.Status.RUNNING
    execution.iniciado_em = timezone.now()
    execution.save(update_fields=['pid', 'status', 'iniciado_em'])
    return process.pid


def queue_position(execution):
    if execution.status != AutomationExecution.Status.PENDING:
        return None
    return (
        AutomationExecution.objects.filter(
            status=AutomationExecution.Status.PENDING,
            criado_em__lte=execution.criado_em,
        ).count()
    )


@transaction.atomic
def schedule_pending_executions():
    if not settings.AUTOMATION_SCHEDULER_ENABLED:
        return []

    queue_settings = get_queue_settings()
    max_concurrent = max(1, queue_settings.max_concurrent_executions)
    running_count = AutomationExecution.objects.filter(status=AutomationExecution.Status.RUNNING).count()
    available_slots = max_concurrent - running_count

    if available_slots <= 0:
        return []

    pending_queryset = AutomationExecution.objects.filter(
        status=AutomationExecution.Status.PENDING,
        pid__isnull=True,
    ).order_by('criado_em')

    if connection.vendor == 'postgresql':
        pending_queryset = pending_queryset.select_for_update(skip_locked=True)
    else:
        pending_queryset = pending_queryset.select_for_update()

    pendings = list(pending_queryset[:available_slots])

    started_ids = []
    for execution in pendings:
        spawn_execution_process(execution)
        started_ids.append(execution.pk)

    return started_ids


def start_automation_request(request, automation, module_name, namespace):
    if not automation.ativa:
        messages.error(request, 'Esta automacao esta desativada no momento.')
        return None

    form = AutomationRunForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, 'Revise os arquivos enviados antes de iniciar a automacao.')
        return None

    arquivo_entrada = form.cleaned_data.get('arquivo_entrada', [])
    anexos = form.cleaned_data.get('anexos', [])

    if automation.aceita_arquivo_entrada is False and arquivo_entrada:
        messages.error(request, 'Esta automacao nao aceita arquivo de entrada.')
        return None

    if automation.aceita_anexos is False and anexos:
        messages.error(request, 'Esta automacao nao aceita anexos.')
        return None

    save_automation_assets(automation, form.cleaned_data)
    execution = create_execution(automation, request.user, form.cleaned_data, module_name)
    schedule_pending_executions()
    execution.refresh_from_db(fields=['status', 'pid', 'iniciado_em'])

    if execution.status == AutomationExecution.Status.RUNNING:
        messages.success(request, 'Automacao iniciada com sucesso.')
    else:
        position = queue_position(execution)
        queue_message = 'Automacao adicionada na fila com sucesso.'
        if position:
            queue_message = f'Automacao adicionada na fila com sucesso. Posicao atual: {position}.'
        messages.success(request, queue_message)
    return build_success_url(namespace)


def stop_automation_request(request, execution, namespace):
    if execution.status == AutomationExecution.Status.PENDING:
        execution.status = AutomationExecution.Status.STOPPED
        execution.mensagem_resumo = 'Execucao removida da fila pelo usuario.'
        execution.finalizado_em = timezone.now()
        execution.save(update_fields=['status', 'mensagem_resumo', 'finalizado_em'])
        schedule_pending_executions()
        messages.success(request, 'Execucao removida da fila com sucesso.')
        return build_success_url(namespace)

    if execution.status != AutomationExecution.Status.RUNNING:
        messages.error(request, 'Esta execucao nao esta em andamento.')
        return build_success_url(namespace)

    execution.interromper_solicitado = True
    execution.mensagem_resumo = 'Interrupcao solicitada pelo usuario.'
    execution.save(update_fields=['interromper_solicitado', 'mensagem_resumo'])

    if execution.pid:
        try:
            os.kill(execution.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    messages.success(request, 'Solicitacao de parada enviada para a automacao.')
    return build_success_url(namespace)


def import_executor(executor_path):
    module_path, function_name = executor_path.rsplit('.', 1)
    module = importlib.import_module(module_path)
    return getattr(module, function_name)


def execution_output_dir(execution):
    output_dir = Path(settings.MEDIA_ROOT) / 'saidas' / execution.modulo / str(execution.pk)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def attachment_paths(execution):
    return [Path(file.arquivo.path) for file in execution.arquivos.filter(tipo=AutomationExecutionFile.Tipo.ATTACHMENT)]


def primary_input_paths(execution):
    paths = []
    if execution.arquivo_entrada:
        paths.append(Path(execution.arquivo_entrada.path))
    paths.extend(
        Path(file.arquivo.path)
        for file in execution.arquivos.filter(tipo=AutomationExecutionFile.Tipo.PRIMARY_INPUT)
    )
    return paths


def collect_output_files(execution, output_dir):
    media_root = Path(settings.MEDIA_ROOT)
    existing_names = set(
        execution.arquivos.filter(tipo=AutomationExecutionFile.Tipo.OUTPUT).values_list('arquivo', flat=True)
    )

    for path in output_dir.rglob('*'):
        if not path.is_file():
            continue
        relative_name = path.relative_to(media_root).as_posix()
        if relative_name in existing_names:
            continue

        db_file = AutomationExecutionFile(
            execution=execution,
            tipo=AutomationExecutionFile.Tipo.OUTPUT,
            nome_original=path.name,
        )
        db_file.arquivo.name = relative_name
        db_file.save()
        existing_names.add(relative_name)


def clear_execution_inputs(execution):
    if execution.arquivo_entrada:
        execution.arquivo_entrada.delete(save=False)
        execution.arquivo_entrada = None
        execution.save(update_fields=['arquivo_entrada'])

    for file in execution.arquivos.filter(tipo__in=[AutomationExecutionFile.Tipo.ATTACHMENT, AutomationExecutionFile.Tipo.PRIMARY_INPUT]):
        file.arquivo.delete(save=False)
        file.delete()


def clear_automation_assets(automation):
    for asset in automation.arquivos_salvos.all():
        asset.arquivo.delete(save=False)
        asset.delete()


def get_execution_automation(execution):
    model_class = execution.content_type.model_class()
    if model_class is None:
        return None
    try:
        return model_class.objects.get(pk=execution.object_id)
    except model_class.DoesNotExist:
        return None
