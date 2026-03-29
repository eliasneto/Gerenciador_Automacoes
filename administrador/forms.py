from django import forms
from django.utils.text import slugify

from .catalog import SECTOR_REGISTRY, sector_choices


class AutomationCreateForm(forms.Form):
    nome = forms.CharField(max_length=120)
    identificador = forms.SlugField(max_length=120, required=False)
    descricao = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 4}))
    executor_path = forms.CharField(max_length=255)
    setores = forms.MultipleChoiceField(
        choices=sector_choices(),
        widget=forms.CheckboxSelectMultiple,
    )
    aceita_arquivo_entrada = forms.BooleanField(required=False, initial=True)
    aceita_anexos = forms.BooleanField(required=False, initial=True)
    ativa = forms.BooleanField(required=False, initial=True)

    def clean_identificador(self):
        identificador = (self.cleaned_data.get('identificador') or '').strip()
        nome = (self.cleaned_data.get('nome') or '').strip()
        generated = slugify(identificador or nome)
        if not generated:
            raise forms.ValidationError('Informe um nome valido para gerar o identificador da automacao.')
        return generated

    def clean_executor_path(self):
        executor_path = (self.cleaned_data.get('executor_path') or '').strip()
        if executor_path.count('.') < 2:
            raise forms.ValidationError('Use um caminho completo, por exemplo: comercial.automacoes.minha_rotina.executar')
        return executor_path

    def clean_setores(self):
        setores = self.cleaned_data.get('setores') or []
        if not setores:
            raise forms.ValidationError('Selecione pelo menos um setor para publicar a automacao.')
        return setores

    def clean(self):
        cleaned_data = super().clean()
        identificador = cleaned_data.get('identificador')
        setores = cleaned_data.get('setores') or []

        if not identificador or not setores:
            return cleaned_data

        duplicates = []
        for setor in setores:
            model = SECTOR_REGISTRY[setor]['model']
            if model.objects.filter(identificador=identificador).exists():
                duplicates.append(SECTOR_REGISTRY[setor]['label'])

        if duplicates:
            raise forms.ValidationError(
                f'Ja existe uma automacao com esse identificador em: {", ".join(duplicates)}.'
            )

        return cleaned_data
