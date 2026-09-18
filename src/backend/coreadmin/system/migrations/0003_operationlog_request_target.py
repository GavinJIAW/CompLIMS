from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('system', '0002_b3_integrity_auth')]

    operations = [
        migrations.AddField(
            model_name='operationlog',
            name='request_target',
            field=models.TextField(blank=True, null=True, verbose_name='请求目标', help_text='服务端目标标识摘要'),
        ),
    ]
