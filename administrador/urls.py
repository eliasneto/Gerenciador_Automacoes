from django.urls import path

from .views import AdminHubView, AutomationCreateView, AutomationEditView, ExecutionListView, MonitoringView

app_name = 'administrador'

urlpatterns = [
    path('', AdminHubView.as_view(), name='hub'),
    path('automacoes/nova/', AutomationCreateView.as_view(), name='automation-create'),
    path('automacoes/<slug:setor>/<int:pk>/editar/', AutomationEditView.as_view(), name='automation-edit'),
    path('execucoes/', ExecutionListView.as_view(), name='execution-list'),
    path('monitoramento/', MonitoringView.as_view(), name='monitoring'),
]
