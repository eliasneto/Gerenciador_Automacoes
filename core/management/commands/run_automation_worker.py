import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import OperationalError, ProgrammingError

from core.services import schedule_pending_executions


class Command(BaseCommand):
    help = 'Worker simples para consumir a fila de automacoes pendentes.'

    def handle(self, *args, **options):
        poll_interval = max(1, settings.AUTOMATION_WORKER_POLL_INTERVAL)
        self.stdout.write(self.style.SUCCESS(f'Worker de automacoes iniciado. Intervalo: {poll_interval}s'))

        while True:
            try:
                started = schedule_pending_executions()
                if started:
                    self.stdout.write(
                        self.style.SUCCESS(f'Execucoes iniciadas a partir da fila: {", ".join(map(str, started))}')
                    )
            except (OperationalError, ProgrammingError) as exc:
                self.stdout.write(
                    self.style.WARNING(f'Fila ainda indisponivel ({exc}). Nova tentativa em {poll_interval}s.')
                )
            time.sleep(poll_interval)
