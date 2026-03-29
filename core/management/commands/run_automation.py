import json
import os
import resource
import signal
import threading
import time
import traceback
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.models import AutomationExecution
from core.services import (
    attachment_paths,
    clear_automation_assets,
    clear_execution_inputs,
    collect_output_files,
    execution_output_dir,
    get_execution_automation,
    import_executor,
    primary_input_paths,
    schedule_pending_executions,
)


class StopRequested(Exception):
    pass


class OutputMirror:
    def __init__(self, append_log, original_stream=None):
        self.append_log = append_log
        self.original_stream = original_stream
        self.buffer = ''

    def write(self, value):
        if not value:
            return 0

        if self.original_stream:
            self.original_stream.write(value)
            self.original_stream.flush()

        self.buffer += value
        while '\n' in self.buffer:
            line, self.buffer = self.buffer.split('\n', 1)
            line = line.rstrip('\r')
            if line:
                self.append_log(line)
        return len(value)

    def flush(self):
        if self.original_stream:
            self.original_stream.flush()
        if self.buffer.strip():
            self.append_log(self.buffer.rstrip('\r'))
        self.buffer = ''


class Command(BaseCommand):
    help = 'Executa uma automacao cadastrada a partir de uma execucao registrada.'

    def add_arguments(self, parser):
        parser.add_argument('execution_id', type=int)

    def handle(self, *args, **options):
        execution = AutomationExecution.objects.select_related('usuario').get(pk=options['execution_id'])
        if execution.status not in [AutomationExecution.Status.PENDING, AutomationExecution.Status.RUNNING]:
            raise CommandError('A execucao informada nao esta pendente ou em andamento.')

        stop_state = {'requested': False}
        metrics_stop_event = threading.Event()

        def read_current_rss_mb():
            try:
                with open('/proc/self/status', 'r', encoding='utf-8') as status_file:
                    for line in status_file:
                        if line.startswith('VmRSS:'):
                            parts = line.split()
                            if len(parts) >= 2:
                                return round(int(parts[1]) / 1024, 2)
            except (FileNotFoundError, ValueError, OSError):
                return None
            return None

        def snapshot_execution_metrics():
            usage = resource.getrusage(resource.RUSAGE_SELF)
            current_rss_mb = read_current_rss_mb()
            peak_rss_mb = None
            if usage.ru_maxrss is not None:
                peak_rss_mb = round(usage.ru_maxrss / 1024, 2)
            return {
                'current_rss_mb': current_rss_mb,
                'peak_rss_mb': peak_rss_mb,
                'cpu_user_seconds': round(usage.ru_utime, 2),
                'cpu_system_seconds': round(usage.ru_stime, 2),
                'metrics_updated_em': timezone.now(),
            }

        def metrics_worker():
            while not metrics_stop_event.is_set():
                AutomationExecution.objects.filter(pk=execution.pk).update(**snapshot_execution_metrics())
                metrics_stop_event.wait(2)

        def handle_term(signum, frame):
            stop_state['requested'] = True
            AutomationExecution.objects.filter(pk=execution.pk).update(interromper_solicitado=True)

        signal.signal(signal.SIGTERM, handle_term)
        signal.signal(signal.SIGINT, handle_term)

        metrics_thread = threading.Thread(target=metrics_worker, daemon=True)
        metrics_thread.start()

        output_dir = execution_output_dir(execution)
        input_path = Path(execution.arquivo_entrada.path) if execution.arquivo_entrada else None
        input_paths = primary_input_paths(execution)
        attachments = attachment_paths(execution)

        def should_stop():
            refreshed = AutomationExecution.objects.get(pk=execution.pk)
            requested = stop_state['requested'] or refreshed.interromper_solicitado
            if requested:
                raise StopRequested('Execucao interrompida pelo usuario.')
            return False

        def append_log(message):
            refreshed = AutomationExecution.objects.get(pk=execution.pk)
            refreshed.log_saida = (refreshed.log_saida + '\n' + message).strip()
            refreshed.save(update_fields=['log_saida'])

        try:
            executor = import_executor(execution.executor_path)
            parametros = execution.parametros_texto
            parametros_json = None
            stdout_mirror = OutputMirror(append_log, self.stdout)
            stderr_mirror = OutputMirror(append_log, self.stderr)
            if parametros:
                try:
                    parametros_json = json.loads(parametros)
                except json.JSONDecodeError:
                    parametros_json = None

            try:
                with redirect_stdout(stdout_mirror), redirect_stderr(stderr_mirror):
                    result = executor(
                        input_path=input_path,
                        input_paths=input_paths,
                        attachments=attachments,
                        output_dir=output_dir,
                        should_stop=should_stop,
                        log=append_log,
                        parametros=parametros,
                        parametros_json=parametros_json,
                    ) or {}
            finally:
                stdout_mirror.flush()
                stderr_mirror.flush()

            collect_output_files(execution, output_dir)
            execution.status = AutomationExecution.Status.SUCCESS
            execution.mensagem_resumo = result.get('message', 'Automacao concluida com sucesso.')
        except StopRequested as exc:
            execution.status = AutomationExecution.Status.STOPPED
            execution.mensagem_resumo = str(exc)
        except Exception as exc:
            collect_output_files(execution, output_dir)
            execution.status = AutomationExecution.Status.ERROR
            execution.mensagem_resumo = f'Falha na execucao: {exc}'
            execution.log_saida = (execution.log_saida + '\n' + traceback.format_exc()).strip()
        finally:
            metrics_stop_event.set()
            metrics_thread.join(timeout=2)
            metric_snapshot = snapshot_execution_metrics()
            final_status = execution.status
            final_message = execution.mensagem_resumo
            final_log = execution.log_saida
            execution.refresh_from_db(fields=['log_saida', 'iniciado_em'])
            execution.status = final_status
            execution.mensagem_resumo = final_message
            execution.log_saida = (execution.log_saida + '\n' + final_log).strip() if final_log else execution.log_saida
            execution.pid = None
            execution.finalizado_em = timezone.now()
            if not execution.iniciado_em:
                execution.iniciado_em = timezone.now()
            execution.current_rss_mb = metric_snapshot['current_rss_mb']
            execution.peak_rss_mb = metric_snapshot['peak_rss_mb']
            execution.cpu_user_seconds = metric_snapshot['cpu_user_seconds']
            execution.cpu_system_seconds = metric_snapshot['cpu_system_seconds']
            execution.metrics_updated_em = metric_snapshot['metrics_updated_em']
            execution.save(
                update_fields=[
                    'status',
                    'mensagem_resumo',
                    'log_saida',
                    'pid',
                    'finalizado_em',
                    'iniciado_em',
                    'current_rss_mb',
                    'peak_rss_mb',
                    'cpu_user_seconds',
                    'cpu_system_seconds',
                    'metrics_updated_em',
                ]
            )

            if execution.status == AutomationExecution.Status.SUCCESS and not execution.interromper_solicitado:
                automation = get_execution_automation(execution)
                if automation is not None:
                    clear_automation_assets(automation)
                clear_execution_inputs(execution)

            schedule_pending_executions()
