from django.db import models
from lims.shared.base import Master


class Customer(Master):
    short_name = models.CharField(max_length=255, blank=True, default='', verbose_name='客户简称', help_text='供实验室内部搜索和识别客户使用')
    tax_number = models.CharField(max_length=100, blank=True, default='', verbose_name='税号', help_text='客户用于商务文件的纳税识别信息')
    address = models.TextField(blank=True, default='', verbose_name='客户地址', help_text='初始化商务单据客户地址快照的来源')

    class Meta(Master.Meta):
        abstract = False
        verbose_name = '客户'
        verbose_name_plural = verbose_name


class CustomerContact(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='contacts', verbose_name='客户', help_text='联系人所属客户，随未被引用的客户一起删除')
    name = models.CharField(max_length=255, verbose_name='联系人姓名', help_text='供选择联系人和初始化商务联系信息使用')
    department = models.CharField(max_length=255, blank=True, default='', verbose_name='联系人部门', help_text='联系人在客户组织中所属的部门')
    title = models.CharField(max_length=255, blank=True, default='', verbose_name='职务', help_text='联系人在客户组织中承担的职务')
    phone = models.CharField(max_length=64, blank=True, default='', verbose_name='电话', help_text='商务沟通使用的固定联系电话')
    mobile = models.CharField(max_length=64, blank=True, default='', verbose_name='手机', help_text='商务沟通使用的移动电话号码')
    email = models.EmailField(blank=True, default='', verbose_name='电子邮箱', help_text='商务联系使用的电子邮件地址')
    address = models.TextField(blank=True, default='', verbose_name='联系地址', help_text='联系人使用的通讯或收件地址')
    is_default = models.BooleanField(default=False, verbose_name='默认联系人', help_text='每个客户最多有一个启用的默认联系人')
    enabled = models.BooleanField(default=True, verbose_name='启用', help_text='停用联系人不占用启用默认联系人的唯一名额')
    remark = models.TextField(blank=True, default='', verbose_name='备注', help_text='补充与此联系人有关的商务沟通说明')

    class Meta:
        ordering = ('id',)
        verbose_name = '客户联系人'
        verbose_name_plural = verbose_name
        constraints = [models.UniqueConstraint(fields=['customer'], condition=models.Q(enabled=True, is_default=True), name='customer_enabled_default_unique')]
