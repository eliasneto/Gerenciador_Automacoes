from django.contrib import admin

from .models import APIToken


@admin.register(APIToken)
class APITokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'is_active', 'created_at', 'last_used_at', 'expires_at')
    list_filter = ('is_active', 'created_at', 'expires_at')
    search_fields = ('user__username', 'user__email', 'name', 'key')
    readonly_fields = ('key', 'created_at', 'updated_at', 'last_used_at')

