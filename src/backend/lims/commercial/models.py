from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from coreadmin.utils.models import CoreModel


class Document(CoreModel):
    number = models.CharField(max_length=64, unique=True, verbose_name='单据编号', help_text='人工填写的唯一商务编号，创建后不得修改')
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+', verbose_name='创建人', help_text='创建单据的用户，也是本人数据范围的归属依据')
    customer = models.ForeignKey('customer.Customer', on_delete=models.PROTECT, related_name='%(class)ss', verbose_name='客户', help_text='保留客户业务关联，正式内容使用独立客户快照')
    customer_name_snapshot = models.CharField(max_length=255, verbose_name='客户名称快照', help_text='本单据正式使用的客户名称，不随客户主数据变化')
    customer_tax_number_snapshot = models.CharField(max_length=100, blank=True, default='', verbose_name='客户税号快照', help_text='本单据正式使用的客户纳税识别信息')
    customer_address_snapshot = models.TextField(blank=True, default='', verbose_name='客户地址快照', help_text='本单据保存时确认的客户地址')
    contact_name_snapshot = models.CharField(max_length=255, blank=True, default='', verbose_name='联系人快照', help_text='本单据独立保存的联系人姓名，不建立联系人外键')
    contact_phone_snapshot = models.CharField(max_length=64, blank=True, default='', verbose_name='联系电话快照', help_text='本单据确认的联系电话')
    contact_email_snapshot = models.EmailField(blank=True, default='', verbose_name='联系邮箱快照', help_text='本单据确认的商务联系邮箱')
    adjustment_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0'), verbose_name='调整金额', help_text='人民币含税总额调整，可正可负，但调整后总额不得为负')
    subtotal = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0'), editable=False, verbose_name='小计', help_text='服务端逐行舍入后的人民币含税行金额之和')
    total_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0'), editable=False, verbose_name='总额', help_text='人民币含税小计加调整金额，服务端保留两位小数')
    commercial_terms = models.TextField(blank=True, default='', verbose_name='商务条款', help_text='本单据约定的商务条款，锁定后不得修改')
    remark = models.TextField(blank=True, default='', verbose_name='单据备注', help_text='本单据的补充说明，属于锁定的商务正文')

    class Meta:
        abstract = True
        ordering = ('-id',)
        constraints = [models.CheckConstraint(check=models.Q(total_amount__gte=0), name='%(app_label)s_%(class)s_total_nonnegative')]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exclude(number=self.number).exists():
            raise ValidationError({'number': 'Number cannot change after creation.'})
        return super().save(*args, **kwargs)


class Quotation(Document):
    status = models.CharField(max_length=10, default='DRAFT', editable=False, choices=[(s, s) for s in ('DRAFT', 'SENT', 'ACCEPTED', 'REJECTED', 'VOID')], verbose_name='报价状态', help_text='只能通过发送、接受、拒绝或作废命令改变')
    quotation_date = models.DateField(verbose_name='报价日期', help_text='本报价单对外使用的业务日期')
    valid_until = models.DateField(null=True, blank=True, verbose_name='有效期至', help_text='报价有效期的截止日期，可留空')
    sent_at = models.DateTimeField(null=True, editable=False, verbose_name='发送时间', help_text='发送命令成功时由服务端记录的时间')
    sent_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+', editable=False, verbose_name='发送人', help_text='执行发送报价命令的用户')
    accepted_at = models.DateTimeField(null=True, editable=False, verbose_name='接受时间', help_text='接受命令成功时由服务端记录的时间')
    accepted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+', editable=False, verbose_name='接受操作人', help_text='执行接受报价命令的用户')
    rejected_at = models.DateTimeField(null=True, editable=False, verbose_name='拒绝时间', help_text='拒绝命令成功时由服务端记录的时间')
    rejected_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+', editable=False, verbose_name='拒绝操作人', help_text='执行拒绝报价命令的用户')
    voided_at = models.DateTimeField(null=True, editable=False, verbose_name='作废时间', help_text='作废命令成功时由服务端记录的时间')
    voided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+', editable=False, verbose_name='作废人', help_text='执行报价作废命令的用户')

    class Meta(Document.Meta):
        abstract = False
        verbose_name = '报价'
        verbose_name_plural = verbose_name
        constraints = Document.Meta.constraints + [models.CheckConstraint(check=models.Q(status__in=['DRAFT', 'SENT', 'ACCEPTED', 'REJECTED', 'VOID']), name='quotation_status_valid')]


class Contract(Document):
    source_quotation = models.OneToOneField(Quotation, null=True, blank=True, on_delete=models.PROTECT, related_name='converted_contract', editable=False, verbose_name='来源报价', help_text='每份报价最多转换为一份合同，仅用于追溯，不动态读取其内容')
    status = models.CharField(max_length=10, default='DRAFT', editable=False, choices=[(s, s) for s in ('DRAFT', 'SIGNED', 'VOID')], verbose_name='合同状态', help_text='只能通过签署或作废命令改变')
    contract_date = models.DateField(verbose_name='合同日期', help_text='本合同对外使用的业务日期')
    signed_at = models.DateTimeField(null=True, editable=False, verbose_name='签署时间', help_text='签署命令成功时由服务端记录的时间，不代表电子签名')
    signed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+', editable=False, verbose_name='签署操作人', help_text='执行合同签署命令的用户，不代表法律电子签名')
    voided_at = models.DateTimeField(null=True, editable=False, verbose_name='作废时间', help_text='合同作废命令成功时由服务端记录的时间')
    voided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+', editable=False, verbose_name='作废人', help_text='执行合同作废命令的用户')

    class Meta(Document.Meta):
        abstract = False
        verbose_name = '合同'
        verbose_name_plural = verbose_name
        constraints = Document.Meta.constraints + [models.CheckConstraint(check=models.Q(status__in=['DRAFT', 'SIGNED', 'VOID']), name='contract_status_valid')]


class CommercialScheme(models.Model):
    source_scheme = models.ForeignKey('catalog.Scheme', null=True, blank=True, on_delete=models.SET_NULL, related_name='+', verbose_name='来源方案', help_text='创建时导入的主方案，仅追溯，删除来源不影响快照')
    sequence = models.PositiveIntegerField(verbose_name='分组顺序', help_text='同一单据内唯一的方案分组显示顺序')
    name_snapshot = models.CharField(max_length=255, verbose_name='方案名称快照', help_text='单据正式展示的方案或自定义商业分组名称')
    name_en_snapshot = models.CharField(max_length=255, blank=True, default='', verbose_name='英文方案名称', help_text='本单据独立保存的英文方案名称')
    description_snapshot = models.TextField(blank=True, default='', verbose_name='方案说明快照', help_text='本单据独立保存的方案适用说明')
    remark = models.TextField(blank=True, default='', verbose_name='分组备注', help_text='此商业方案分组的补充说明')

    class Meta:
        abstract = True
        ordering = ('sequence', 'id')


class QuotationScheme(CommercialScheme):
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='schemes', verbose_name='报价', help_text='分组所属报价，只能通过报价聚合接口维护')

    class Meta(CommercialScheme.Meta):
        abstract = False
        verbose_name = '报价方案'
        verbose_name_plural = verbose_name
        constraints = [models.UniqueConstraint(fields=['quotation', 'sequence'], name='quotation_scheme_sequence', deferrable=models.Deferrable.DEFERRED)]


class ContractScheme(CommercialScheme):
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='schemes', verbose_name='合同', help_text='分组所属合同，只能通过合同聚合接口维护')

    class Meta(CommercialScheme.Meta):
        abstract = False
        verbose_name = '合同方案'
        verbose_name_plural = verbose_name
        constraints = [models.UniqueConstraint(fields=['contract', 'sequence'], name='contract_scheme_sequence', deferrable=models.Deferrable.DEFERRED)]


class CommercialItem(models.Model):
    source_product = models.ForeignKey('catalog.Product', null=True, on_delete=models.SET_NULL, related_name='+', verbose_name='来源产品', help_text='新行必须来源于真实产品，来源删除后仍保留独立快照')
    sequence = models.PositiveIntegerField(verbose_name='明细顺序', help_text='同一商业方案分组内唯一的明细显示顺序')
    product_number_snapshot = models.CharField(max_length=64, verbose_name='产品编号快照', help_text='创建时的产品稳定编号，普通更新不可修改')
    name_snapshot = models.CharField(max_length=255, verbose_name='产品名称快照', help_text='本行正式商务名称，可在草稿阶段按权限编辑')
    name_en_snapshot = models.CharField(max_length=255, blank=True, default='', verbose_name='英文产品名称', help_text='本行正式英文商务名称')
    unit_snapshot = models.CharField(max_length=64, verbose_name='单位快照', help_text='本行商务数量与成交单价使用的计量单位')
    requirement_schema = models.JSONField(default=list, editable=False, verbose_name='需求结构快照', help_text='创建时服务需求模板的独立副本，普通更新不可修改')
    requirement_data = models.JSONField(default=dict, blank=True, verbose_name='要求实例', help_text='依据本行结构快照校验的最终要求，商务阶段允许部分填写')
    quantity = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal('1'), validators=[MinValueValidator(Decimal('0.000001'))], verbose_name='商务数量', help_text='大于零的商务计价数量，最多六位小数，不决定任务数量')
    unit_price = models.DecimalField(max_digits=20, decimal_places=2, validators=[MinValueValidator(0)], verbose_name='含税单价', help_text='人民币含税成交单价，允许零价，最多两位小数')
    line_amount = models.DecimalField(max_digits=20, decimal_places=2, editable=False, verbose_name='含税行金额', help_text='数量乘单价后按 HALF_UP 舍入到分的服务端权威金额')
    remark = models.TextField(blank=True, default='', verbose_name='明细备注', help_text='该商业明细的技术或商务补充说明')

    class Meta:
        abstract = True
        ordering = ('sequence', 'id')
        constraints = [models.CheckConstraint(check=models.Q(quantity__gt=0), name='%(class)s_quantity_positive'), models.CheckConstraint(check=models.Q(unit_price__gte=0), name='%(class)s_price_nonnegative')]


class QuotationSchemeItem(CommercialItem):
    quotation_scheme = models.ForeignKey(QuotationScheme, on_delete=models.CASCADE, related_name='items', verbose_name='报价方案', help_text='明细所属报价方案分组，不允许跨父对象移动已有行')

    class Meta(CommercialItem.Meta):
        abstract = False
        verbose_name = '报价方案明细'
        verbose_name_plural = verbose_name
        constraints = CommercialItem.Meta.constraints + [models.UniqueConstraint(fields=['quotation_scheme', 'sequence'], name='quotation_item_sequence', deferrable=models.Deferrable.DEFERRED)]


class ContractSchemeItem(CommercialItem):
    contract_scheme = models.ForeignKey(ContractScheme, on_delete=models.CASCADE, related_name='items', verbose_name='合同方案', help_text='明细所属合同方案分组，不允许跨父对象移动已有行')

    class Meta(CommercialItem.Meta):
        abstract = False
        verbose_name = '合同方案明细'
        verbose_name_plural = verbose_name
        constraints = CommercialItem.Meta.constraints + [models.UniqueConstraint(fields=['contract_scheme', 'sequence'], name='contract_item_sequence', deferrable=models.Deferrable.DEFERRED)]
