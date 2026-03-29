from django import forms


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(item, initial) for item in data]
        if not data:
            return []
        return [single_file_clean(data, initial)]


class AutomationRunForm(forms.Form):
    arquivo_entrada = MultipleFileField(required=False)
    anexos = MultipleFileField(required=False)
    parametros_texto = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 4}),
        help_text='Opcional: informe parametros livres, JSON ou observacoes para a automacao.',
    )

    def clean_arquivo_entrada(self):
        files = self.cleaned_data.get('arquivo_entrada', [])
        if len(files) > 2:
            raise forms.ValidationError('O campo principal aceita no maximo 2 arquivos.')
        return files
