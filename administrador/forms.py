from django import forms
from django.utils.text import slugify

from .catalog import SECTOR_REGISTRY, sector_choices


AUTOMATION_ICON_CHOICES = [
    ('sparkles', 'Destaque / Sparkles'),
    ('briefcase', 'Maleta'),
    ('wallet', 'Carteira'),
    ('cpu', 'CPU'),
    ('settings-2', 'Configurações'),
    ('layout-grid', 'Grade'),
    ('folder-up', 'Pasta Upload'),
    ('file-code-2', 'Código'),
    ('shield-check', 'Segurança'),
    ('activity', 'Atividade'),
]


class AutomationBaseForm(forms.Form):
    nome = forms.CharField(max_length=120)
    identificador = forms.SlugField(max_length=120, required=False)
    icone = forms.ChoiceField(choices=AUTOMATION_ICON_CHOICES, required=False)
    descricao = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 4}))
    executor_path = forms.CharField(max_length=255)
    aceita_arquivo_entrada = forms.BooleanField(required=False, initial=True)
    aceita_anexos = forms.BooleanField(required=False, initial=True)
    ativa = forms.BooleanField(required=False, initial=True)

    def __init__(self, *args, instance=None, allow_setores=False, sector_key=None, **kwargs):
        self.instance = instance
        self.allow_setores = allow_setores
        self.sector_key = sector_key
        super().__init__(*args, **kwargs)

        if self.allow_setores:
            self.fields['setores'] = forms.MultipleChoiceField(
                choices=sector_choices(),
                widget=forms.CheckboxSelectMultiple,
            )

        if not self.allow_setores and 'setores' in self.fields:
            self.fields.pop('setores', None)

        if not self.is_bound and self.instance is not None:
            self.initial.setdefault('nome', self.instance.nome)
            self.initial.setdefault('identificador', self.instance.identificador)
            self.initial.setdefault('icone', getattr(self.instance, 'icone', '') or 'sparkles')
            self.initial.setdefault('descricao', self.instance.descricao)
            self.initial.setdefault('executor_path', self.instance.executor_path)
            self.initial.setdefault('aceita_arquivo_entrada', self.instance.aceita_arquivo_entrada)
            self.initial.setdefault('aceita_anexos', self.instance.aceita_anexos)
            self.initial.setdefault('ativa', self.instance.ativa)
            if self.allow_setores:
                self.initial.setdefault('setores', [self.sector_key] if self.sector_key else [])
        elif not self.is_bound:
            self.initial.setdefault('icone', 'sparkles')

    def clean_identificador(self):
        identificador = (self.cleaned_data.get('identificador') or '').strip()
        nome = (self.cleaned_data.get('nome') or '').strip()

        if identificador:
            generated = slugify(identificador)
        elif self.instance is not None and not self.allow_setores:
            generated = (getattr(self.instance, 'identificador', '') or '').strip()
        else:
            generated = slugify(nome)

        if not generated:
            raise forms.ValidationError('Informe um nome valido para gerar o identificador da automacao.')
        return generated

    def clean_icone(self):
        icone = (self.cleaned_data.get('icone') or '').strip()
        if icone:
            return icone
        if self.instance is not None:
            return getattr(self.instance, 'icone', '') or 'sparkles'
        return 'sparkles'

    def clean_executor_path(self):
        executor_path = (self.cleaned_data.get('executor_path') or '').strip()
        if executor_path.count('.') < 2:
            raise forms.ValidationError('Use um caminho completo, por exemplo: comercial.automacoes.minha_rotina.executar')
        return executor_path

    def clean_setores(self):
        if not self.allow_setores:
            return []

        setores = self.cleaned_data.get('setores') or []
        if not setores:
            raise forms.ValidationError('Selecione pelo menos um setor para publicar a automacao.')
        return setores

    def clean(self):
        cleaned_data = super().clean()
        identificador = cleaned_data.get('identificador')

        if not identificador:
            return cleaned_data

        if self.allow_setores and self.instance is None:
            setores = cleaned_data.get('setores') or []
            if not setores:
                return cleaned_data

            duplicates = []
            for setor in setores:
                model = SECTOR_REGISTRY[setor]['model']
                queryset = model.objects.filter(identificador=identificador)
                if self.instance is not None:
                    queryset = queryset.exclude(pk=self.instance.pk)
                if queryset.exists():
                    duplicates.append(SECTOR_REGISTRY[setor]['label'])

            if duplicates:
                raise forms.ValidationError(
                    f'Ja existe uma automacao com esse identificador em: {", ".join(duplicates)}.'
                )
        elif self.instance is not None and self.sector_key:
            model = SECTOR_REGISTRY[self.sector_key]['model']
            queryset = model.objects.filter(identificador=identificador)
            queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise forms.ValidationError('Ja existe uma automacao com esse identificador neste setor.')

        return cleaned_data


class AutomationCreateForm(AutomationBaseForm):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('allow_setores', True)
        super().__init__(*args, **kwargs)


class AutomationUpdateForm(AutomationBaseForm):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('allow_setores', True)
        super().__init__(*args, **kwargs)
