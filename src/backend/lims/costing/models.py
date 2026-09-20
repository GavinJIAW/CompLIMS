from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from lims.shared.base import Master, NamedMaster


class CostItem(Master):
    TYPES = tuple((value, value) for value in (
        'LABOR', 'EQUIPMENT', 'CONSUMABLE', 'CERTIFICATION',
        'MAINTENANCE', 'REPAIR', 'OPERATION'))
    type = models.CharField(max_length=20, choices=TYPES, verbose_name='成本类型', help_text='区分人工、设备、耗材、认证、保养、维修和运营标准成本')
    unit_cost = models.DecimalField(max_digits=20, decimal_places=6, validators=[MinValueValidator(0)], verbose_name='单位成本', help_text='以人民币计价的最小标准单位成本，最多保留六位小数')
    unit = models.CharField(max_length=64, verbose_name='计价单位', help_text='定义单位成本或产品报价对应的标准计量单位')
    basis_data = models.JSONField(default=dict, blank=True, verbose_name='成本依据', help_text='记录成本换算依据、来源参数与说明，不执行公式或表达式')

    class Meta(Master.Meta):
        abstract = False
        constraints = [
            models.CheckConstraint(check=models.Q(unit_cost__gte=0), name='lims_item_cost_nonnegative'),
            models.CheckConstraint(check=models.Q(type__in=[
                'LABOR', 'EQUIPMENT', 'CONSUMABLE', 'CERTIFICATION',
                'MAINTENANCE', 'REPAIR', 'OPERATION']), name='lims_item_type_valid'),
        ]
        verbose_name = '成本项'
        verbose_name_plural = verbose_name


class CostPackage(Master):
    unit = models.CharField(max_length=64, verbose_name='计价单位', help_text='定义单位成本或产品报价对应的标准计量单位')

    class Meta(Master.Meta):
        abstract = False
        verbose_name = '成本包'
        verbose_name_plural = verbose_name


class CostPackageItem(models.Model):
    package = models.ForeignKey(CostPackage, on_delete=models.CASCADE, related_name='items', verbose_name='成本包', help_text='被组合或引用的标准成本包，具体删除策略由所属明细关系决定')
    item = models.ForeignKey(CostItem, on_delete=models.PROTECT, related_name='package_items', verbose_name='成本项', help_text='成本包引用的最小标准成本项，被引用后禁止删除')
    quantity = models.DecimalField(max_digits=20, decimal_places=6, validators=[MinValueValidator(Decimal('0.000001'))], verbose_name='标准用量', help_text='成本组合的正数用量或换算系数，最多六位小数，不决定任务数量')
    sequence = models.PositiveIntegerField(default=10, verbose_name='显示顺序', help_text='用于明细展示与排序，不表示强制前置依赖或任务数量')

    class Meta:
        ordering = ('sequence', 'id')
        constraints = [
            models.UniqueConstraint(fields=('package', 'item'), name='lims_package_item_unique'),
            models.CheckConstraint(check=models.Q(quantity__gt=0), name='lims_package_qty_positive'),
        ]
        verbose_name = '成本包明细'
        verbose_name_plural = verbose_name
