from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def clear_development_contacts(apps, schema_editor):
    apps.get_model('customer', 'CustomerContact').objects.using(schema_editor.connection.alias).all().delete()


class Migration(migrations.Migration):
    dependencies = [('customer', '0001_initial'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.RunPython(clear_development_contacts),
        migrations.RemoveField('customercontact', 'department'),
        migrations.RemoveField('customercontact', 'phone'),
        migrations.RemoveField('customercontact', 'remark'),
        migrations.AddField('customercontact', 'creator', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
        migrations.AddField('customercontact', 'modifier', models.CharField(blank=True, help_text='修改人', max_length=255, null=True, verbose_name='修改人')),
        migrations.AddField('customercontact', 'dept_belong_id', models.CharField(blank=True, help_text='数据归属部门', max_length=255, null=True, verbose_name='数据归属部门')),
        migrations.AddField('customercontact', 'update_datetime', models.DateTimeField(auto_now=True, help_text='修改时间', null=True, verbose_name='修改时间')),
        migrations.AddField('customercontact', 'create_datetime', models.DateTimeField(auto_now_add=True, help_text='创建时间', null=True, verbose_name='创建时间')),
        migrations.AddField('customercontact', 'gender', models.IntegerField(choices=[(0, '未知'), (1, '男'), (2, '女')], default=0, help_text='联系人性别：未知、男或女', verbose_name='性别')),
        migrations.AddField('customercontact', 'direct_supervisor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='direct_reports', to='customer.customercontact', help_text='同客户中的直接上级联系人，不得指向自身或构成循环', verbose_name='直接上级')),
        migrations.AlterField('customercontact', 'customer', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='contacts', to='customer.customer', help_text='联系人所属客户，存在联系人时禁止删除客户', verbose_name='客户')),
        migrations.AlterField('customercontact', 'id', models.BigAutoField(help_text='Id', primary_key=True, serialize=False, verbose_name='Id')),
        migrations.AddConstraint('customercontact', models.CheckConstraint(check=models.Q(gender__in=[0, 1, 2]), name='contact_gender_valid')),
        migrations.AddConstraint('customercontact', models.CheckConstraint(check=~models.Q(direct_supervisor=models.F('id')), name='contact_supervisor_not_self')),
    ]
