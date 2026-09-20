from decimal import Decimal, localcontext
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from coreadmin.utils.serializers import CustomModelSerializer
from lims.shared.contract import READ, ROW_FIELDS
from lims.catalog.templates import validate_template, validate_values
from lims.shared.authority import reference, readable, row_fields
from lims.costing.services import package_cost


class StrictRow(serializers.Serializer):
    id = serializers.IntegerField(required=False, min_value=1)
    sequence = serializers.IntegerField(min_value=0, max_value=2147483647)

    def to_internal_value(self, data):
        if not isinstance(data, dict) or set(data) - set(self.fields):
            raise ValidationError('Unknown composition fields.')
        return super().to_internal_value(data)


def package_visible(actor, package):
    return (readable(actor, 'cost_package', package, ['current_cost']) and
            all(readable(actor, 'cost_item', row.item, ['unit_cost']) for row in package.items.all()))


class MasterSerializer(CustomModelSerializer):
    resource = None
    row_name = None
    row_serializer = None
    row_model = None
    target = None
    target_resource = None

    def validate(self, attrs):
        if self.instance and 'number' in attrs and attrs['number'] != self.instance.number:
            raise ValidationError({'number': 'Number cannot change after creation.'})
        if 'basis_data' in attrs and not isinstance(attrs['basis_data'], dict):
            raise ValidationError({'basis_data': 'Expected an object.'})
        for name in ('requirement_template', 'result_template'):
            if name in attrs:
                validate_template(attrs[name], name)
        if self.resource == 'product':
            service = attrs.get('service', getattr(self.instance, 'service', None))
            if 'service' in attrs:
                reference(self.request.user, 'service', service,
                          bool(self.instance and self.instance.service_id == service.pk))
            validate_values(service.requirement_template,
                attrs.get('requirement_defaults', getattr(self.instance, 'requirement_defaults', {})), 'requirement_defaults')
        return attrs

    def to_internal_value(self, data):
        attrs = super().to_internal_value(data)
        if self.row_name and self.row_name in data:
            raw = data[self.row_name]
            if not isinstance(raw, list) or len(raw) > 500:
                raise ValidationError({self.row_name: 'Expected at most 500 rows.'})
            child = self.row_serializer(data=raw, many=True)
            if not child.is_valid():
                raise ValidationError({self.row_name: child.errors})
            rows = child.validated_data
            existing = {row.pk: row for row in getattr(self.instance, self.row_name).all()} if self.instance else {}
            context = self.request._canonical_access_view.access_context
            seen, seen_ids = set(), set()
            for row in rows:
                pk = row.get('id')
                old = existing.get(pk)
                if pk is not None and (old is None or pk in seen_ids):
                    raise ValidationError({self.row_name: 'Invalid or repeated row ID for this master.'})
                seen_ids.add(pk)
                mode = 'update' if old else 'create'
                allowed = row_fields(context, self.row_model, mode) - {'id'}
                # Existing rows may echo unchanged non-writable values. Changed
                # values require the corresponding child field permission.
                for key, value in row.items():
                    previous = getattr(old, key, None) if old else None
                    if key != 'id' and key not in allowed and (old is None or value != previous):
                        raise ValidationError({self.row_name: f'Child field {key} is not writable.'})
                obj = row[self.target]
                reference(self.request.user, self.target_resource, obj,
                    bool(old and getattr(old, self.target + '_id') == obj.pk))
                unique = row['sequence'] if self.resource == 'scheme' else obj.pk
                if unique in seen:
                    raise ValidationError({self.row_name: 'Duplicate sequence or composition target.'})
                seen.add(unique)
                if self.resource == 'scheme':
                    validate_values(obj.service.requirement_template, row['requirement_override'], 'requirement_override')
            attrs[self.row_name] = rows
        return attrs

    def to_representation(self, instance):
        result = super().to_representation(instance)
        actor = self.request.user
        if self.resource == 'product' and 'service' in result:
            if not readable(actor, 'service', instance.service, ['id']):
                result['service'] = None
        if self.row_name in result:
            context = self.request._canonical_access_view.access_context
            allowed = row_fields(context, self.row_model, 'read')
            output = []
            for row in getattr(instance, self.row_name).all():
                obj = getattr(row, self.target)
                values = {name: getattr(row, name) for name in ROW_FIELDS[self.row_model.__name__].split() if name in allowed}
                if self.target in values:
                    values[self.target] = obj.pk if readable(actor, self.target_resource, obj, ['id']) else None
                    if readable(actor, self.target_resource, obj, ['name']):
                        values['target_name'] = obj.name
                    if hasattr(obj, 'unit') and readable(actor, self.target_resource, obj, ['unit']):
                        values['unit'] = obj.unit
                    cost = None
                    if self.resource == 'cost_package' and readable(actor, 'cost_item', obj, ['unit_cost']):
                        cost = obj.unit_cost
                    if self.resource == 'product' and package_visible(actor, obj):
                        cost = package_cost(obj)
                    if cost is not None and 'quantity' in allowed:
                        with localcontext() as decimal_context:
                            decimal_context.prec = 80
                            values.update(unit_cost=str(cost), line_cost=str(cost * row.quantity))
                if 'quantity' in values:
                    values['quantity'] = str(values['quantity'])
                output.append(values)
            result[self.row_name] = output
        return result
