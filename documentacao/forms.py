from django import forms

from core.sector_registry import SECTOR_REGISTRY
from .models import DocumentationPage


def automation_link_choices():
    choices = [('', 'Sem vínculo com automação')]
    for sector_key, registry in SECTOR_REGISTRY.items():
        for automation in registry['model'].objects.all():
            choices.append(
                (
                    f'{sector_key}:{automation.identificador}',
                    f'{registry["label"]} / {automation.nome}',
                )
            )
    return choices


class DocumentationPageForm(forms.Form):
    titulo = forms.CharField(max_length=160)
    publication_section = forms.ChoiceField(
        choices=DocumentationPage.PublicationSection.choices,
        initial=DocumentationPage.PublicationSection.SYSTEM,
        required=False,
    )
    status = forms.ChoiceField(
        choices=[
            ('draft', 'Rascunho'),
            ('published', 'Publicado'),
            ('archived', 'Arquivado'),
        ]
    )
    raw_content = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 18}),
        required=False,
    )


class DocumentationCreateForm(DocumentationPageForm):
    automation_link = forms.ChoiceField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['automation_link'].choices = automation_link_choices()


class DocumentationEditForm(forms.Form):
    titulo = forms.CharField(max_length=160)
    automation_link = forms.ChoiceField(required=False)
    publication_section = forms.ChoiceField(
        choices=DocumentationPage.PublicationSection.choices,
        initial=DocumentationPage.PublicationSection.SYSTEM,
        required=False,
    )
    raw_content = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 18}),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['automation_link'].choices = automation_link_choices()
