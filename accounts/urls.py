from django.urls import path

from .views import SessionTimeoutLogoutView, UserLoginView, UserLogoutView

app_name = 'accounts'

urlpatterns = [
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('logout/inatividade/', SessionTimeoutLogoutView.as_view(), name='timeout-logout'),
]
