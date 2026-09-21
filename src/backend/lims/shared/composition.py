"""Target-collection validation/projection primitive; app serializers own row semantics."""
from rest_framework.exceptions import ValidationError
from .serializers import MasterSerializer
from .authority import reference, readable, row_fields

class CompositionSerializer(MasterSerializer):
    def row_identity(self, row):
        return row[self.target].pk

    def validate_row(self, row):
        pass

    def project_cost(self, actor, row, values, allowed):
        pass

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
                allowed = row_fields(context, self.row_model, mode, self.row_fields) - {'id'}
                # Existing rows may echo unchanged non-writable values. Changed
                # values require the corresponding child field permission.
                for key, value in row.items():
                    previous = getattr(old, key, None) if old else None
                    if key != 'id' and key not in allowed and (old is None or value != previous):
                        raise ValidationError({self.row_name: f'Child field {key} is not writable.'})
                obj = row[self.target]
                reference(self.request.user, self.target_resource, obj,
                    bool(old and getattr(old, self.target + '_id') == obj.pk))
                unique = self.row_identity(row)
                if unique in seen:
                    raise ValidationError({self.row_name: 'Duplicate sequence or composition target.'})
                seen.add(unique)
                self.validate_row(row)
            attrs[self.row_name] = rows
        return attrs

    def to_representation(self, instance):
        result = super().to_representation(instance)
        actor = self.request.user
        if self.row_name in result:
            context = self.request._canonical_access_view.access_context
            allowed = row_fields(context, self.row_model, 'read', self.row_fields)
            output = []
            for row in getattr(instance, self.row_name).all():
                obj = getattr(row, self.target)
                values = {name: getattr(row, name) for name in self.row_fields.split() if name in allowed}
                if self.target in values:
                    values[self.target] = obj.pk if readable(actor, self.target_resource, obj, ['id']) else None
                    if readable(actor, self.target_resource, obj, ['name']):
                        values['target_name'] = obj.name
                    if hasattr(obj, 'unit') and readable(actor, self.target_resource, obj, ['unit']):
                        values['unit'] = obj.unit
                    self.project_cost(actor, row, values, allowed)
                if 'quantity' in values:
                    values['quantity'] = str(values['quantity'])
                output.append(values)
            result[self.row_name] = output
        return result
