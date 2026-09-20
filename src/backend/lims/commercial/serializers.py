from decimal import Decimal
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from coreadmin.utils.serializers import CustomModelSerializer
from lims.shared.m2_contract import READ, WRITE
from lims.shared.aggregate_authority import child_fields
from .models import Quotation, Contract
from .services import save_document


class DocumentSerializer(CustomModelSerializer):
    schemes = serializers.JSONField(required=False, write_only=True)

    def validate(self, attrs):
        if 'schemes' in attrs and not isinstance(attrs['schemes'], list):
            raise ValidationError({'schemes': 'Expected a target collection.'})
        if self.instance and attrs.get('number', self.instance.number) != self.instance.number:
            raise ValidationError({'number': 'Number cannot change after creation.'})
        return attrs

    def create(self, validated_data):
        return save_document(self, validated_data)

    def update(self, instance, validated_data):
        return save_document(self, validated_data)

    def to_representation(self, instance):
        result = super().to_representation(instance)
        view = self.request._canonical_access_view
        if 'schemes' in view.field_policy.allowed(instance):
            groups = []
            for group in instance.schemes.all():
                allowed = child_fields(view.access_context, instance, type(group), 'read')
                data = {}
                for key in allowed - {'items'}:
                    data[key] = getattr(group, key + '_id' if key == 'source_scheme' else key)
                if 'items' in allowed:
                    data['items'] = []
                    for row in group.items.all():
                        fields = child_fields(view.access_context, instance, type(row), 'read')
                        item = {}
                        for key in fields:
                            value = getattr(row, key + '_id' if key == 'source_product' else key)
                            item[key] = str(value) if isinstance(value, Decimal) else value
                        if not {'quantity', 'unit_price'} <= fields:
                            item.pop('line_amount', None)
                        data['items'].append(item)
                groups.append(data)
            result['schemes'] = groups
        # Derived totals must not expose prices hidden in nested field policy.
        from .models import QuotationScheme, QuotationSchemeItem, ContractScheme, ContractSchemeItem
        group_model, item_model = (QuotationScheme, QuotationSchemeItem) if isinstance(instance, Quotation) else (ContractScheme, ContractSchemeItem)
        if ('schemes' not in view.field_policy.allowed(instance)
                or 'items' not in child_fields(view.access_context, instance, group_model, 'read')
                or not {'quantity', 'unit_price', 'line_amount'} <= child_fields(view.access_context, instance, item_model, 'read')):
            result.pop('subtotal', None)
            result.pop('total_amount', None)
        return result


class QuotationSerializer(DocumentSerializer):
    class Meta:
        model = Quotation
        fields = READ['quotation'].split()
        read_only_fields = list(set(fields) - set(WRITE['quotation'].split()))
        extra_kwargs = {'customer_name_snapshot': {'required': False}}


class ContractSerializer(DocumentSerializer):
    class Meta:
        model = Contract
        fields = READ['contract'].split()
        read_only_fields = list(set(fields) - set(WRITE['contract'].split()))
        extra_kwargs = {'customer_name_snapshot': {'required': False}}
