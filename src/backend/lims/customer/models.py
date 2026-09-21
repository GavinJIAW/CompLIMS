from django.db import models
from lims.shared.base import Master
from coreadmin.utils.models import CoreModel
from django.conf import settings


class Customer(Master):
    short_name = models.CharField(max_length=255, blank=True, default='', verbose_name='客户简称', help_text='供实验室内部搜索和识别客户使用')
    tax_number = models.CharField(max_length=100, blank=True, default='', verbose_name='税号', help_text='客户用于商务文件的纳税识别信息')
    address = models.TextField(blank=True, default='', verbose_name='客户地址', help_text='初始化商务单据客户地址快照的来源')

    class Meta(Master.Meta):
        abstract = False
        verbose_name = '客户'
        verbose_name_plural = verbose_name


class CustomerContact(CoreModel):
    description = None
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')
    gender = models.IntegerField(choices=((0, '未知'), (1, '男'), (2, '女')), default=0, verbose_name='性别', help_text='联系人性别：未知、男或女')
    direct_supervisor = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='direct_reports', verbose_name='直接上级', help_text='同客户中的直接上级联系人，不得指向自身或构成循环')
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='contacts', verbose_name='客户', help_text='联系人所属客户，存在联系人时禁止删除客户')
    name = models.CharField(max_length=255, verbose_name='联系人姓名', help_text='供选择联系人和初始化商务联系信息使用')
    title = models.CharField(max_length=255, blank=True, default='', verbose_name='职务', help_text='联系人在客户组织中承担的职务')
    mobile = models.CharField(max_length=64, blank=True, default='', verbose_name='手机', help_text='商务沟通使用的移动电话号码')
    email = models.EmailField(blank=True, default='', verbose_name='电子邮箱', help_text='商务联系使用的电子邮件地址')
    address = models.TextField(blank=True, default='', verbose_name='联系地址', help_text='联系人使用的通讯或收件地址')
    is_default = models.BooleanField(default=False, verbose_name='默认联系人', help_text='每个客户最多有一个启用的默认联系人')
    enabled = models.BooleanField(default=True, verbose_name='启用', help_text='停用联系人不占用启用默认联系人的唯一名额')

    class Meta:
        ordering = ('id',)
        verbose_name = '客户联系人'
        verbose_name_plural = verbose_name
        constraints = [models.CheckConstraint(check=models.Q(gender__in=[0, 1, 2]), name='contact_gender_valid'), models.CheckConstraint(check=~models.Q(direct_supervisor=models.F('id')), name='contact_supervisor_not_self'), models.UniqueConstraint(fields=['customer'], condition=models.Q(enabled=True, is_default=True), name='customer_enabled_default_unique')]
