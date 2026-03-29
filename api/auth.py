import json

from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .models import APIToken


def json_error(message, status=400, **extra):
    payload = {'ok': False, 'error': message}
    payload.update(extra)
    return JsonResponse(payload, status=status)


def parse_request_payload(request):
    if request.content_type and 'application/json' in request.content_type:
        try:
            return json.loads(request.body.decode('utf-8') or '{}')
        except json.JSONDecodeError:
            return None
    return request.POST.dict()


def get_bearer_token(request):
    header = request.headers.get('Authorization', '')
    if header.lower().startswith('bearer '):
        return header[7:].strip()
    return request.headers.get('X-API-Token', '').strip()


def resolve_api_token(request):
    key = get_bearer_token(request)
    if not key:
        return None

    token = (
        APIToken.objects.select_related('user')
        .filter(key=key, is_active=True)
        .first()
    )
    if token is None or token.is_expired:
        return None

    token.last_used_at = timezone.now()
    token.save(update_fields=['last_used_at', 'updated_at'])
    return token


@method_decorator(csrf_exempt, name='dispatch')
class APITokenRequiredMixin:
    api_token = None
    api_user = None

    def dispatch(self, request, *args, **kwargs):
        token = resolve_api_token(request)
        if token is None:
            return json_error('Token de API inválido ou ausente.', status=401)

        self.api_token = token
        self.api_user = token.user
        request.api_token = token
        request.api_user = token.user
        return super().dispatch(request, *args, **kwargs)


def get_or_create_default_token(user):
    token = user.api_tokens.filter(name='Token principal').first()
    if token is None:
        token = APIToken.objects.create(user=user, name='Token principal')
    elif not token.is_active:
        token.is_active = True
        token.save(update_fields=['is_active', 'updated_at'])
    return token


def authenticate_api_user(username, password):
    user = authenticate(username=username, password=password)
    if user is None or not user.is_active:
        return None
    return user
