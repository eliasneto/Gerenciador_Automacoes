# Generated manually for DocumentationPage
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DocumentationPage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('object_id', models.PositiveBigIntegerField()),
                ('titulo', models.CharField(max_length=160)),
                ('raw_content', models.TextField(blank=True)),
                ('rendered_html', models.TextField(blank=True)),
                ('versao', models.PositiveIntegerField(default=1)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('atualizado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='documentation_updates', to=settings.AUTH_USER_MODEL)),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
            ],
            options={
                'ordering': ['-atualizado_em'],
            },
        ),
        migrations.AddConstraint(
            model_name='documentationpage',
            constraint=models.UniqueConstraint(fields=('content_type', 'object_id'), name='unique_documentation_page_per_automation'),
        ),
    ]
