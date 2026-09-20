from decimal import Decimal, localcontext
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from coreadmin.utils.serializers import CustomModelSerializer
from lims.shared.contract import READ, ROW_FIELDS
from lims.catalog.templates import validate_template, validate_values
from lims.shared.authority import reference, readable, row_fields
from lims.costing.services import package_cost
from lims.costing.models import CostPackage
from lims.catalog.models import Service, Product, ProductCostPackage, Scheme, SchemeItem
from lims.shared.serializers import StrictRow, MasterSerializer, package_visible
from lims.catalog.services import product_cost, scheme_totals


class ProductRow(StrictRow):
    package = serializers.PrimaryKeyRelatedField(queryset=CostPackage.objects.all())
    quantity = serializers.DecimalField(max_digits=20, decimal_places=6, min_value=Decimal('0.000001'))


class SchemeRow(StrictRow):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.select_related('service').all())
    requirement_override = serializers.JSONField(default=dict)
    remark = serializers.CharField(required=False, allow_blank=True, default='')


class ServiceSerializer(MasterSerializer):
    resource = 'service'
    class Meta:
        model = Service
        fields = READ['service'].split()
        read_only_fields = ['id', 'creator', 'modifier', 'dept_belong_id']


class ProductSerializer(MasterSerializer):
    resource, row_name, row_serializer, row_model = 'product', 'packages', ProductRow, ProductCostPackage
    target, target_resource = 'package', 'cost_package'
    packages = serializers.SerializerMethodField()
    standard_cost = serializers.SerializerMethodField()
    def get_packages(self, obj):
        return []
    def get_standard_cost(self, obj):
        return str(product_cost(obj)) if all(package_visible(self.request.user, row.package) for row in obj.packages.all()) else None
    class Meta:
        model = Product
        fields = READ['product'].split()
        read_only_fields = ['id', 'creator', 'modifier', 'dept_belong_id']


class SchemeSerializer(MasterSerializer):
    resource, row_name, row_serializer, row_model = 'scheme', 'items', SchemeRow, SchemeItem
    target, target_resource = 'product', 'product'
    items = serializers.SerializerMethodField()
    standard_cost = serializers.SerializerMethodField()
    reference_price = serializers.SerializerMethodField()
    def get_items(self, obj):
        return []
    def get_standard_cost(self, obj):
        actor = self.request.user
        if all(readable(actor, 'product', row.product, ['standard_cost']) and
               all(package_visible(actor, part.package) for part in row.product.packages.all())
               for row in obj.items.all()):
            return str(scheme_totals(obj)[0])
        return None
    def get_reference_price(self, obj):
        if all(readable(self.request.user, 'product', row.product, ['reference_price']) for row in obj.items.all()):
            return str(scheme_totals(obj)[1])
        return None
    class Meta:
        model = Scheme
        fields = READ['scheme'].split()
        read_only_fields = ['id', 'creator', 'modifier', 'dept_belong_id']
