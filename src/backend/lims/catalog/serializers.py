from decimal import Decimal, localcontext
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from coreadmin.utils.serializers import CustomModelSerializer
from .access_contract import READ, ROW_FIELDS
from lims.catalog.templates import validate_template, validate_values
from lims.shared.authority import reference, readable, row_fields
from lims.costing.services import package_cost
from lims.costing.models import CostPackage
from lims.catalog.models import Service, Product, ProductCostPackage, Scheme, SchemeItem
from lims.shared.serializers import StrictRow, MasterSerializer
from lims.shared.composition import CompositionSerializer
from lims.costing.authority import package_visible
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
    def validate(self, attrs):
        attrs = super().validate(attrs)
        for name in ('requirement_template', 'result_template'):
            if name in attrs:
                validate_template(attrs[name], name)
        return attrs

    class Meta:
        model = Service
        fields = READ['service'].split()
        read_only_fields = ['id', 'creator', 'modifier', 'dept_belong_id']


class ProductSerializer(CompositionSerializer):
    row_fields = ROW_FIELDS['ProductCostPackage']
    resource, row_name, row_serializer, row_model = 'product', 'packages', ProductRow, ProductCostPackage
    target, target_resource = 'package', 'cost_package'
    def validate(self, attrs):
        attrs = super().validate(attrs)
        service = attrs.get('service', getattr(self.instance, 'service', None))
        if 'service' in attrs:
            reference(self.request.user, 'service', service, bool(self.instance and self.instance.service_id == service.pk))
        validate_values(service.requirement_template, attrs.get('requirement_defaults', getattr(self.instance, 'requirement_defaults', {})), 'requirement_defaults')
        return attrs

    def to_representation(self, instance):
        result = super().to_representation(instance)
        if 'service' in result and not readable(self.request.user, 'service', instance.service, ['id']):
            result['service'] = None
        return result

    def project_cost(self, actor, row, values, allowed):
        from lims.costing.services import money, line_cost
        if 'quantity' in allowed and package_visible(actor, row.package):
            cost = package_cost(row.package)
            values.update(unit_cost=str(money(cost)), line_cost=str(line_cost(cost, row.quantity)))

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


class SchemeSerializer(CompositionSerializer):
    row_fields = ROW_FIELDS['SchemeItem']
    resource, row_name, row_serializer, row_model = 'scheme', 'items', SchemeRow, SchemeItem
    target, target_resource = 'product', 'product'
    def row_identity(self, row):
        return row['sequence']

    def validate_row(self, row):
        validate_values(row['product'].service.requirement_template, row['requirement_override'], 'requirement_override')

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
