from django.db.models.signals import post_migrate

from .security import sync_module_groups


def ensure_module_groups(sender, **kwargs):
    sync_module_groups()


post_migrate.connect(ensure_module_groups)
