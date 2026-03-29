from django.conf import settings

from .sector_registry import SECTOR_REGISTRY
from .security import (
    EXTRA_ACCESS_GROUPS,
    user_has_area_access,
    user_has_dashboard_access,
    user_has_module_access,
    visible_dashboard_keys_for_user,
    visible_module_keys_for_user,
)


def module_access_context(request):
    user = getattr(request, 'user', None)
    module_access = {key: user_has_module_access(user, key) for key in SECTOR_REGISTRY}
    dashboard_access = {key: user_has_dashboard_access(user, key) for key in SECTOR_REGISTRY}
    area_access = {key: user_has_area_access(user, key) for key in EXTRA_ACCESS_GROUPS}
    visible_modules = [
        {
            'key': key,
            'label': SECTOR_REGISTRY[key]['label'],
            'icon': SECTOR_REGISTRY[key]['icon'],
        }
        for key in visible_module_keys_for_user(user)
    ]
    visible_dashboard_modules = [
        {
            'key': key,
            'label': SECTOR_REGISTRY[key]['label'],
            'icon': SECTOR_REGISTRY[key]['icon'],
        }
        for key in visible_dashboard_keys_for_user(user)
    ]
    return {
        'module_access': module_access,
        'dashboard_access': dashboard_access,
        'area_access': area_access,
        'app_version': getattr(settings, 'APP_VERSION', ''),
        'visible_modules': visible_modules,
        'has_any_module_access': bool(visible_modules),
        'visible_dashboard_modules': visible_dashboard_modules,
        'has_any_dashboard_access': bool(visible_dashboard_modules),
    }
