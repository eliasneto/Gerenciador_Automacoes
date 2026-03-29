from django.contrib.auth.models import Group

from .sector_registry import SECTOR_REGISTRY

EXTRA_ACCESS_GROUPS = {
    'documentacao': 'Modulo Documentacao',
    'administrador': 'Modulo Administracao',
}


def module_group_name(module_key):
    registry = SECTOR_REGISTRY.get(module_key, {})
    return registry.get('group_name')


def dashboard_group_name(module_key):
    registry = SECTOR_REGISTRY.get(module_key, {})
    return registry.get('dashboard_group_name')


def area_group_name(area_key):
    return EXTRA_ACCESS_GROUPS.get(area_key)


def user_has_access(user, area_key):
    if not getattr(user, 'is_authenticated', False):
        return False

    if user.is_superuser:
        return True

    group_name = module_group_name(area_key) or area_group_name(area_key)
    if not group_name:
        return False

    return user.groups.filter(name=group_name).exists()


def user_has_module_access(user, module_key):
    return user_has_access(user, module_key)


def user_has_area_access(user, area_key):
    return user_has_access(user, area_key)


def user_has_dashboard_access(user, module_key):
    if not getattr(user, 'is_authenticated', False):
        return False

    if user.is_superuser:
        return True

    group_name = dashboard_group_name(module_key)
    if not group_name:
        return False

    return user.groups.filter(name=group_name).exists()


def visible_module_keys_for_user(user):
    return [key for key in SECTOR_REGISTRY if user_has_module_access(user, key)]


def visible_dashboard_keys_for_user(user):
    return [key for key in SECTOR_REGISTRY if user_has_dashboard_access(user, key)]


def resolve_module_key_from_instance(instance):
    for key, registry in SECTOR_REGISTRY.items():
        if isinstance(instance, registry['model']):
            return key
    return None


def sync_module_groups():
    created_groups = []

    for module_key in SECTOR_REGISTRY:
        for group_name in {module_group_name(module_key), dashboard_group_name(module_key)}:
            if not group_name:
                continue

            _, created = Group.objects.get_or_create(name=group_name)
            if created:
                created_groups.append(group_name)

    for group_name in EXTRA_ACCESS_GROUPS.values():
        _, created = Group.objects.get_or_create(name=group_name)
        if created:
            created_groups.append(group_name)

    return created_groups
