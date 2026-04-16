from django import forms
from django.contrib.auth.forms import AuthenticationForm


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Usuario",
        widget=forms.TextInput(
            attrs={
                "class": "w-full rounded-[1.15rem] border border-slate-200 bg-[#f7f8fb] py-3.5 pl-12 pr-4 text-[14px] font-medium text-slate-800 outline-none transition-all placeholder:text-slate-300 focus:border-[#ffc107] focus:bg-white focus:ring-4 focus:ring-[#ffc107]/20",
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
                "class": "w-full rounded-[1.15rem] border border-slate-200 bg-[#f7f8fb] py-3.5 pl-12 pr-12 text-[14px] font-medium tracking-[0.18em] text-slate-800 outline-none transition-all placeholder:text-slate-300 focus:border-[#ffc107] focus:bg-white focus:ring-4 focus:ring-[#ffc107]/20",
                "placeholder": "••••••••",
                "autocomplete": "current-password",
            }
        ),
    )
