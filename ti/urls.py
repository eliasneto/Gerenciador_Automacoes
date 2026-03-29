from django.urls import path

from .views import TIExecutionLogView, TIHomeView, TIStartAutomationView, TIStopAutomationView

app_name = 'ti'

urlpatterns = [
    path('', TIHomeView.as_view(), name='home'),
    path('automacoes/<int:pk>/executar/', TIStartAutomationView.as_view(), name='execute'),
    path('execucoes/<int:execution_id>/parar/', TIStopAutomationView.as_view(), name='stop'),
    path('execucoes/<int:execution_id>/logs/', TIExecutionLogView.as_view(), name='logs'),
]
