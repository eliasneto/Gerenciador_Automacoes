from django.urls import path

from .views import (
    FinanceiroExecutionLogView,
    FinanceiroHomeView,
    FinanceiroStartAutomationView,
    FinanceiroStopAutomationView,
)

app_name = 'financeiro'

urlpatterns = [
    path('', FinanceiroHomeView.as_view(), name='home'),
    path('automacoes/<int:pk>/executar/', FinanceiroStartAutomationView.as_view(), name='execute'),
    path('execucoes/<int:execution_id>/parar/', FinanceiroStopAutomationView.as_view(), name='stop'),
    path('execucoes/<int:execution_id>/logs/', FinanceiroExecutionLogView.as_view(), name='logs'),
]
