from django.urls import path

from .views import (
    ComercialExecutionLogView,
    ComercialHomeView,
    ComercialStartAutomationView,
    ComercialStopAutomationView,
)

app_name = 'comercial'

urlpatterns = [
    path('', ComercialHomeView.as_view(), name='home'),
    path('automacoes/<int:pk>/executar/', ComercialStartAutomationView.as_view(), name='execute'),
    path('execucoes/<int:execution_id>/parar/', ComercialStopAutomationView.as_view(), name='stop'),
    path('execucoes/<int:execution_id>/logs/', ComercialExecutionLogView.as_view(), name='logs'),
]
