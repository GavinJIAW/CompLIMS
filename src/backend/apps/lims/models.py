"""Current shared masters. Historical business snapshots belong to later modules."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from decimal import Decimal

from coreadmin.utils.models import CoreModel


class Master(CoreModel):
    number = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    enabled = models.BooleanField(default=True)
    description = models.TextField(blank=True, default='')
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
    internal_name = models.CharField(max_length=255, blank=True, default='')
    name_en = models.CharField(max_length=255, blank=True, default='')

    class Meta(Master.Meta):
        abstract = True


class Service(NamedMaster):
    service_type = models.CharField(max_length=64, blank=True, default='')
    requirement_template = models.JSONField(default=list, blank=True)
    result_template = models.JSONField(default=list, blank=True)


class CostItem(Master):
    TYPES = tuple((value, value) for value in (
        'LABOR', 'EQUIPMENT', 'CONSUMABLE', 'CERTIFICATION',
        'MAINTENANCE', 'REPAIR', 'OPERATION'))
    type = models.CharField(max_length=20, choices=TYPES)
    unit_cost = models.DecimalField(max_digits=20, decimal_places=6, validators=[MinValueValidator(0)])
    unit = models.CharField(max_length=64)
    basis_data = models.JSONField(default=dict, blank=True)

    class Meta(Master.Meta):
        abstract = False
        constraints = [
            models.CheckConstraint(check=models.Q(unit_cost__gte=0), name='lims_item_cost_nonnegative'),
            models.CheckConstraint(check=models.Q(type__in=[
                'LABOR', 'EQUIPMENT', 'CONSUMABLE', 'CERTIFICATION',
                'MAINTENANCE', 'REPAIR', 'OPERATION']), name='lims_item_type_valid'),
        ]


class CostPackage(Master):
    unit = models.CharField(max_length=64)


class Product(NamedMaster):
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name='products')
    requirement_defaults = models.JSONField(default=dict, blank=True)
    unit = models.CharField(max_length=64)
    reference_price = models.DecimalField(max_digits=20, decimal_places=2, validators=[MinValueValidator(0)])

    class Meta(Master.Meta):
        abstract = False
        constraints = [models.CheckConstraint(check=models.Q(reference_price__gte=0), name='lims_price_nonnegative')]


class Scheme(NamedMaster):
    pass


class CostPackageItem(models.Model):
    package = models.ForeignKey(CostPackage, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(CostItem, on_delete=models.PROTECT, related_name='package_items')
    quantity = models.DecimalField(max_digits=20, decimal_places=6, validators=[MinValueValidator(Decimal('0.000001'))])
    sequence = models.PositiveIntegerField(default=10)

    class Meta:
        ordering = ('sequence', 'id')
        constraints = [
            models.UniqueConstraint(fields=('package', 'item'), name='lims_package_item_unique'),
            models.CheckConstraint(check=models.Q(quantity__gt=0), name='lims_package_qty_positive'),
        ]


class ProductCostPackage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='packages')
    package = models.ForeignKey(CostPackage, on_delete=models.PROTECT, related_name='product_packages')
    quantity = models.DecimalField(max_digits=20, decimal_places=6, validators=[MinValueValidator(Decimal('0.000001'))])
    sequence = models.PositiveIntegerField(default=10)

    class Meta:
        ordering = ('sequence', 'id')
        constraints = [
            models.UniqueConstraint(fields=('product', 'package'), name='lims_product_package_unique'),
            models.CheckConstraint(check=models.Q(quantity__gt=0), name='lims_product_qty_positive'),
        ]


class SchemeItem(models.Model):
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='scheme_items')
    sequence = models.PositiveIntegerField()
    requirement_override = models.JSONField(default=dict, blank=True)
    remark = models.TextField(blank=True, default='')

    class Meta:
        ordering = ('sequence', 'id')
        constraints = [models.UniqueConstraint(fields=('scheme', 'sequence'), name='lims_scheme_sequence_unique')]
