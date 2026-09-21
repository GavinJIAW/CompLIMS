from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('commercial', '0001_initial')]
    operations = [
        migrations.RenameField('quotation', 'contact_phone_snapshot', 'contact_mobile_snapshot'),
        migrations.RenameField('contract', 'contact_phone_snapshot', 'contact_mobile_snapshot'),
        migrations.AlterField('quotation', 'contact_mobile_snapshot', models.CharField(max_length=64, blank=True, default='', verbose_name='手机号码快照', help_text='本单据确认的联系人手机号码')),
        migrations.AlterField('contract', 'contact_mobile_snapshot', models.CharField(max_length=64, blank=True, default='', verbose_name='手机号码快照', help_text='本单据确认的联系人手机号码')),
    ]
