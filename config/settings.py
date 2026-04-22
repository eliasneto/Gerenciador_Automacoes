"""
Django settings for config project.
"""

import os
from pathlib import Path

import dj_database_url


BASE_DIR = Path(__file__).resolve().parent.parent
APP_VERSION = 'v1.0.0'


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 't', 'yes', 'y', 'on'}


def env_int(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-dev-key')
DEBUG = env_bool('DJANGO_DEBUG', True)

allowed_hosts = os.getenv('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost,testserver')
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts.split(',') if host.strip()]

CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if origin.strip()
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'api.apps.ApiConfig',
    'core.apps.CoreConfig',
    'administrador',
    'documentacao',
    'accounts',
    'comercial',
    'financeiro',
    'ti',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.module_access_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=env_bool('DATABASE_SSL_REQUIRE', False),
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
MEDIA_SERVE_WITH_DJANGO = env_bool('DJANGO_SERVE_MEDIA', DEBUG)

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'core:dashboard'
LOGOUT_REDIRECT_URL = 'accounts:login'
AUTHENTICATION_BACKENDS = [
    'accounts.auth_backends.ActiveDirectoryBackend',
    'django.contrib.auth.backends.ModelBackend',
]
SESSION_COOKIE_AGE = 20 * 60
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_SECURE = env_bool('DJANGO_SESSION_COOKIE_SECURE', not DEBUG)
CSRF_COOKIE_SECURE = env_bool('DJANGO_CSRF_COOKIE_SECURE', not DEBUG)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

AUTOMATION_SCHEDULER_ENABLED = env_bool('AUTOMATION_SCHEDULER_ENABLED', True)
AUTOMATION_WORKER_POLL_INTERVAL = env_int('AUTOMATION_WORKER_POLL_INTERVAL', 5)

USE_AD_AUTH = env_bool('USE_AD_AUTH', False)
AD_SERVER_URI = os.getenv('AD_SERVER_URI', '').strip()
AD_BIND_DN = os.getenv('AD_BIND_DN', '').strip()
AD_BIND_PASSWORD = os.getenv('AD_BIND_PASSWORD', '')
AD_USER_SEARCH_BASE = os.getenv('AD_USER_SEARCH_BASE', '').strip()
AD_DEFAULT_DOMAIN = os.getenv('AD_DEFAULT_DOMAIN', '').strip()
AD_DEFAULT_DOMAIN_FQDN = os.getenv('AD_DEFAULT_DOMAIN_FQDN', '').strip()

if not AD_DEFAULT_DOMAIN_FQDN and AD_BIND_DN and '@' in AD_BIND_DN:
    AD_DEFAULT_DOMAIN_FQDN = AD_BIND_DN.split('@', 1)[1].strip().lower()

if not AD_DEFAULT_DOMAIN_FQDN and AD_USER_SEARCH_BASE:
    ad_parts = []
    for item in AD_USER_SEARCH_BASE.split(','):
        item = item.strip()
        if item.upper().startswith('DC='):
            ad_parts.append(item.split('=', 1)[1].strip())
    AD_DEFAULT_DOMAIN_FQDN = '.'.join(ad_parts).lower()

DJANGO_SUPERUSER_USERNAME = os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin').strip()

if not DEBUG:
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
