from django.urls import path

from .views import (
    APIAutomationExecuteView,
    APIAutomationListView,
    APIDocumentationListView,
    APIExecutionDetailView,
    APIExecutionListView,
    APIExecutionStopView,
    APIHealthView,
    APIMeView,
    APIModuleListView,
    APITokenLoginView,
    APITokenRevokeView,
)

app_name = 'api'

urlpatterns = [
    path('health/', APIHealthView.as_view(), name='health'),
    path('auth/token/', APITokenLoginView.as_view(), name='token'),
    path('auth/token/revoke/', APITokenRevokeView.as_view(), name='token-revoke'),
    path('me/', APIMeView.as_view(), name='me'),
    path('modules/', APIModuleListView.as_view(), name='modules'),
    path('automacoes/', APIAutomationListView.as_view(), name='automacoes'),
    path('automacoes/<slug:module_key>/<slug:identificador>/executar/', APIAutomationExecuteView.as_view(), name='execute'),
    path('execucoes/', APIExecutionListView.as_view(), name='execucoes'),
    path('execucoes/<int:execution_id>/', APIExecutionDetailView.as_view(), name='execution-detail'),
    path('execucoes/<int:execution_id>/parar/', APIExecutionStopView.as_view(), name='execution-stop'),
    path('documentacoes/', APIDocumentationListView.as_view(), name='documentacoes'),
]
