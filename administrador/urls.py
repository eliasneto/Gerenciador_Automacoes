from django.urls import path

from .views import AdminHubView, AutomationCreateView, ExecutionListView, MonitoringView

app_name = 'administrador'

urlpatterns = [
    path('', AdminHubView.as_view(), name='hub'),
    path('automacoes/nova/', AutomationCreateView.as_view(), name='automation-create'),
    path('execucoes/', ExecutionListView.as_view(), name='execution-list'),
    path('monitoramento/', MonitoringView.as_view(), name='monitoring'),
]
