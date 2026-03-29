from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_automationqueuesettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='automationexecution',
            name='cpu_system_seconds',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='automationexecution',
            name='cpu_user_seconds',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='automationexecution',
            name='current_rss_mb',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='automationexecution',
            name='metrics_updated_em',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='automationexecution',
            name='peak_rss_mb',
            field=models.FloatField(blank=True, null=True),
        ),
    ]
