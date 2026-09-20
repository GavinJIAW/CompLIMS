"""Strict collection validation and identity-preserving persistence primitives."""
from rest_framework import serializers
from rest_framework.exceptions import ValidationError


def collection(raw, existing):
    if not isinstance(raw, list) or len(raw) > 500:
        raise ValidationError('Expected a collection of at most 500 rows.')
    seen = set()
    result = []
    for data in raw:
        if not isinstance(data, dict):
            raise ValidationError('Each child must be an object.')
        pk = data.get('id')
        if 'id' in data and (type(pk) is not int or pk not in existing or pk in seen):
            raise ValidationError('Invalid, duplicate, or foreign-parent child ID.')
        seen.add(pk)
        result.append((data.copy(), existing.get(pk)))
    return result


def validate_row(model, data, instance, fields):
    meta = type('Meta', (), {'model': model, 'fields': fields, 'validators': []})
    cls = type('AggregateRowSerializer', (serializers.ModelSerializer,), {'Meta': meta})
    serializer = cls(instance, data=data, partial=instance is not None)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


def unique_sequences(rows):
    values = [data.get('sequence', getattr(old, 'sequence', None)) for data, old in rows]
    if None in values or len(values) != len(set(values)):
        raise ValidationError({'sequence': 'Sequences are required and unique within the parent.'})
