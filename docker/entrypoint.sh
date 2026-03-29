#!/bin/sh
set -e

export DJANGO_SETTINGS_MODULE=config.settings

python - <<'PY'
import os
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
from django.db import connections
from django.db.utils import OperationalError

django.setup()

for attempt in range(60):
    try:
        connections['default'].cursor()
        print('Banco de dados disponivel.')
        break
    except OperationalError:
        if attempt == 59:
            raise
        print(f'Aguardando banco de dados... tentativa {attempt + 1}/60')
        time.sleep(2)
PY

if [ "$APP_ROLE" = "web" ]; then
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput

    python - <<'PY'
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
from django.contrib.auth import get_user_model

django.setup()

User = get_user_model()
username = os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin')
email = os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@local.test')
password = os.getenv('DJANGO_SUPERUSER_PASSWORD', 'admin123')

user, created = User.objects.get_or_create(
    username=username,
    defaults={
        'email': email,
        'is_superuser': True,
        'is_staff': True,
    },
)

user.email = email
user.is_superuser = True
user.is_staff = True
user.set_password(password)
user.save()

if created:
    print(f'Superusuario inicial criado: {username}')
else:
    print(f'Superusuario inicial atualizado: {username}')
PY
fi

exec "$@"
