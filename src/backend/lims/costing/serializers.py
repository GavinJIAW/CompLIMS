from decimal import Decimal, localcontext
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from coreadmin.utils.serializers import CustomModelSerializer
from lims.shared.contract import READ, ROW_FIELDS
from lims.catalog.templates import validate_template, validate_values
from lims.shared.authority import reference, readable, row_fields
from lims.costing.services import package_cost
from lims.costing.models import CostType, CostItem, CostPackage, CostPackageItem
from lims.shared.serializers import StrictRow, MasterSerializer, package_visible


class PackageRow(StrictRow):
    item = serializers.PrimaryKeyRelatedField(queryset=CostItem.objects.all())
    quantity = serializers.DecimalField(max_digits=20, decimal_places=6, min_value=Decimal('0.000001'))


class CostTypeSerializer(MasterSerializer):
    resource = 'cost_type'
    class Meta:
        model = CostType
        fields = READ['cost_type'].split()
        read_only_fields = ['id', 'creator', 'modifier', 'dept_belong_id']


class CostItemSerializer(MasterSerializer):
    resource = 'cost_item'

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if 'cost_type' in attrs:
            target = attrs['cost_type']
            reference(self.request.user, 'cost_type', target,
                      bool(self.instance and self.instance.cost_type_id == target.pk))
        return attrs

    def to_representation(self, instance):
        result = super().to_representation(instance)
        if 'cost_type' in result and not readable(self.request.user, 'cost_type', instance.cost_type, ['id']):
            result['cost_type'] = None
        return result

    class Meta:
        model = CostItem
        fields = READ['cost_item'].split()
        read_only_fields = ['id', 'creator', 'modifier', 'dept_belong_id']


class CostPackageSerializer(MasterSerializer):
    resource, row_name, row_serializer, row_model = 'cost_package', 'items', PackageRow, CostPackageItem
    target, target_resource = 'item', 'cost_item'
    items = serializers.SerializerMethodField()
    current_cost = serializers.SerializerMethodField()
    def get_items(self, obj):
        return []  # Explicit projection below, never automatic nested fields.
    def get_current_cost(self, obj):
        return str(package_cost(obj)) if package_visible(self.request.user, obj) else None
    class Meta:
        model = CostPackage
        fields = READ['cost_package'].split()
        read_only_fields = ['id', 'creator', 'modifier', 'dept_belong_id']
