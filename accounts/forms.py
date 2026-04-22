from django import forms
from django.contrib.auth.forms import AuthenticationForm


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Usuario",
        widget=forms.TextInput(
            attrs={
                "class": "h-[52px] w-full rounded-[1.25rem] border border-[#d8deea] bg-[#f5f7fb] py-3 pl-14 pr-4 text-[14px] font-semibold text-[#23304f] outline-none transition-all placeholder:text-[#c3cada] focus:border-[#ffc107] focus:bg-white focus:ring-4 focus:ring-[#ffc107]/20",
                "placeholder": "ex: elias.neto",
                "autofocus": True,
                "autocomplete": "username",
            }
        ),
    )

    password = forms.CharField(
        label="Senha",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "h-[52px] w-full rounded-[1.25rem] border border-[#d8deea] bg-[#f5f7fb] py-3 pl-14 pr-14 text-[14px] font-semibold tracking-[0.16em] text-[#23304f] outline-none transition-all placeholder:text-[#c3cada] focus:border-[#ffc107] focus:bg-white focus:ring-4 focus:ring-[#ffc107]/20",
                "placeholder": "********",
                "autocomplete": "current-password",
            }
        ),
    )
