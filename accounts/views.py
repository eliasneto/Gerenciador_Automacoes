from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View

from .forms import LoginForm


class UserLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return str(reverse_lazy('core:dashboard'))


class UserLogoutView(LogoutView):
    next_page = reverse_lazy('accounts:login')


class SessionTimeoutLogoutView(View):
    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            logout(request)

        messages.info(request, 'Voce foi desconectado por inatividade de 20 minutos.')
        return redirect('accounts:login')
