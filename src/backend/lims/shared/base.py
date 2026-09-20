from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from coreadmin.utils.models import CoreModel


class Master(CoreModel):
    number = models.CharField(max_length=64, unique=True, verbose_name='主数据编号', help_text='主数据的唯一稳定编号，创建后不可修改，由人工维护')
    name = models.CharField(max_length=255, verbose_name='正式名称', help_text='用于业务识别与正式文件展示的中文名称')
    enabled = models.BooleanField(default=True, verbose_name='启用状态', help_text='停用后禁止新建下游引用，已有关系仍可读取和计算')
    description = models.TextField(blank=True, default='', verbose_name='业务说明', help_text='记录主数据的用途、适用范围和必要业务说明')
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, null=True,
                                on_delete=models.SET_NULL, related_name='+')

    class Meta:
        abstract = True
        ordering = ('number', 'id')

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exclude(number=self.number).exists():
            raise ValidationError({'number': 'Number cannot change after creation.'})
        return super().save(*args, **kwargs)


class NamedMaster(Master):
    internal_name = models.CharField(max_length=255, blank=True, default='', verbose_name='内部名称', help_text='仅用于实验室内部检索和识别，不直接用于正式对外文件')
    name_en = models.CharField(max_length=255, blank=True, default='', verbose_name='英文正式名称', help_text='用于英文正式商务文件的业务名称')

    class Meta(Master.Meta):
        abstract = True
