from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from lims.shared.base import Master, NamedMaster
from lims.costing.models import CostPackage


class Service(NamedMaster):
    service_type = models.CharField(max_length=64, blank=True, default='', verbose_name='服务分类', help_text='用于服务检索与分组，不决定动态模板内容')
    requirement_template = models.JSONField(default=list, blank=True, verbose_name='需求模板', help_text='定义后续任务需求字段，修改不得使现有产品默认值或方案覆盖值失效')
    result_template = models.JSONField(default=list, blank=True, verbose_name='结果模板', help_text='定义后续任务结果字段和表格列，当前仅维护模板定义')

    class Meta(Master.Meta):
        abstract = False
        verbose_name = '技术服务'
        verbose_name_plural = verbose_name


class Product(NamedMaster):
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name='products', verbose_name='技术服务', help_text='产品使用的技术服务定义及需求模板来源')
    requirement_defaults = models.JSONField(default=dict, blank=True, verbose_name='需求默认值', help_text='按技术服务需求模板设置产品层默认参数，与方案覆盖值采用浅合并')
    unit = models.CharField(max_length=64, verbose_name='计价单位', help_text='定义单位成本或产品报价对应的标准计量单位')
    reference_price = models.DecimalField(max_digits=20, decimal_places=2, validators=[MinValueValidator(0)], verbose_name='参考售价', help_text='产品当前人民币标准参考售价，保留两位小数，不代表客户成交价')

    class Meta(Master.Meta):
        abstract = False
        constraints = [models.CheckConstraint(check=models.Q(reference_price__gte=0), name='lims_price_nonnegative')]
        verbose_name = '产品'
        verbose_name_plural = verbose_name


class Scheme(NamedMaster):
    class Meta(Master.Meta):
        abstract = False
        verbose_name = '技术方案'
        verbose_name_plural = verbose_name


class ProductCostPackage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='packages', verbose_name='产品', help_text='引用服务的稳定成本与商务变体，被引用时受关系授权约束')
    package = models.ForeignKey(CostPackage, on_delete=models.PROTECT, related_name='product_packages', verbose_name='成本包', help_text='被组合或引用的标准成本包，具体删除策略由所属明细关系决定')
    quantity = models.DecimalField(max_digits=20, decimal_places=6, validators=[MinValueValidator(Decimal('0.000001'))], verbose_name='标准用量', help_text='成本组合的正数用量或换算系数，最多六位小数，不决定任务数量')
    sequence = models.PositiveIntegerField(default=10, verbose_name='显示顺序', help_text='用于明细展示与排序，不表示强制前置依赖或任务数量')

    class Meta:
        ordering = ('sequence', 'id')
        constraints = [
            models.UniqueConstraint(fields=('product', 'package'), name='lims_product_package_unique'),
            models.CheckConstraint(check=models.Q(quantity__gt=0), name='lims_product_qty_positive'),
        ]
        verbose_name = '产品成本包'
        verbose_name_plural = verbose_name


class SchemeItem(models.Model):
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE, related_name='items', verbose_name='技术方案', help_text='明细所属的标准技术方案，明细随所属方案删除')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='scheme_items', verbose_name='产品', help_text='引用服务的稳定成本与商务变体，被引用时受关系授权约束')
    sequence = models.PositiveIntegerField(verbose_name='显示顺序', help_text='方案内唯一的明细显示顺序，不表示强制前置依赖或任务数量')
    requirement_override = models.JSONField(default=dict, blank=True, verbose_name='需求覆盖值', help_text='覆盖产品默认参数的方案行配置，必须符合关联服务当前需求模板')
    remark = models.TextField(blank=True, default='', verbose_name='明细备注', help_text='记录本配置行的技术要求补充说明，不表示报价或合同条款')

    class Meta:
        ordering = ('sequence', 'id')
        constraints = [models.UniqueConstraint(fields=('scheme', 'sequence'), name='lims_scheme_sequence_unique')]
        verbose_name = '方案明细'
        verbose_name_plural = verbose_name
