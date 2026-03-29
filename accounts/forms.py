from django import forms
from django.contrib.auth.forms import AuthenticationForm


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Usuario',
        widget=forms.TextInput(
            attrs={
                'class': 'w-full p-4 bg-gray-50 border border-gray-100 rounded-2xl outline-none focus:ring-2 focus:ring-yellow-400 transition-all',
                'placeholder': 'Digite seu usuario',
                'autofocus': True,
                'autocomplete': 'username',
            }
        ),
    )
    password = forms.CharField(
        label='Senha',
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                'class': 'w-full p-4 bg-gray-50 border border-gray-100 rounded-2xl outline-none focus:ring-2 focus:ring-yellow-400 transition-all',
                'placeholder': '••••••••',
                'autocomplete': 'current-password',
            }
        ),
    )
