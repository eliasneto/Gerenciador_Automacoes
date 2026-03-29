from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

admin.site.site_header = 'Administração do AutoControllers'
admin.site.site_title = 'Administração do AutoControllers'
admin.site.index_title = 'Painel administrativo'

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='core:dashboard', permanent=False)),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('contas/', include('accounts.urls')),
    path('dashboard/', include('core.urls')),
    path('administrador/', include('administrador.urls')),
    path('documentacao/', include('documentacao.urls')),
    path('comercial/', include('comercial.urls')),
    path('financeiro/', include('financeiro.urls')),
    path('ti/', include('ti.urls')),
]

if settings.DEBUG or settings.MEDIA_SERVE_WITH_DJANGO:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
