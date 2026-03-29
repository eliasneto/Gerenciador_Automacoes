from django.urls import path

from .views import (
    DocumentationCreateView,
    DocumentationDetailView,
    DocumentationEditView,
    DocumentationEditByPageView,
    DocumentationHomeView,
    DocumentationManageView,
    DocumentationStandaloneDetailView,
    DocumentationStatusUpdateView,
    DocumentationViewAuditCloseView,
)

app_name = 'documentacao'

urlpatterns = [
    path('', DocumentationHomeView.as_view(), name='home'),
    path('criar/', DocumentationManageView.as_view(), name='manage'),
    path('criar/nova/', DocumentationCreateView.as_view(), name='create'),
    path('pagina/<int:page_id>/status/', DocumentationStatusUpdateView.as_view(), name='update-status'),
    path('pagina/<int:page_id>/editar/', DocumentationEditByPageView.as_view(), name='edit-page'),
    path('sistema/<int:page_id>/', DocumentationStandaloneDetailView.as_view(), name='standalone-detail'),
    path('visualizacao/<int:audit_id>/encerrar/', DocumentationViewAuditCloseView.as_view(), name='close-view-audit'),
    path('<slug:sector>/<slug:identificador>/', DocumentationDetailView.as_view(), name='detail'),
    path('<slug:sector>/<slug:identificador>/editar/', DocumentationEditView.as_view(), name='edit'),
]
