"""Atomic current-master writes, including compatibility and aggregate replacement."""
from contextlib import contextmanager
from django.db import connection, transaction
from lims.catalog.models import Service, Product
from lims.catalog.templates import validate_compatibility, validate_values


@contextmanager
def master_command():
    # Low-volume master editing shares one transaction-scoped lock. All API
    # writers participate, including template mutations and dependency changes;
    # this prevents check/write races even when a composition is initially empty.
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_xact_lock(%s, %s)', [19761, 1])
        yield


def validate_dependencies(instance, data):
    if isinstance(instance, Service) and 'requirement_template' in data:
        validate_compatibility(instance, data['requirement_template'])
    if isinstance(instance, Product) and 'service' in data:
        template = data['service'].requirement_template
        for row in instance.scheme_items.all():
            validate_values(template, row.requirement_override, f'items.{row.pk}.requirement_override')


def save_aggregate(serializer, **audit):
    """Invoked inside master_command after serializer/authority validation."""
    data = dict(serializer.validated_data)
    row_name = getattr(serializer, 'row_name', None)
    rows = data.pop(row_name, None) if row_name else None
    if serializer.instance:
        validate_dependencies(serializer.instance, data)
        for name, value in {**data, **audit}.items():
            setattr(serializer.instance, name, value)
        serializer.instance.save()
        obj = serializer.instance
    else:
        obj = serializer.Meta.model.objects.create(**data, **audit)
    if rows is not None:
        manager = getattr(obj, row_name)
        # Full replacement preserves row identity for existing references. Delete
        # first also makes sequence swaps legal under the immediate unique index.
        manager.all().delete()
        for row in rows:
            manager.create(**row)
    serializer.instance = obj
    obj._prefetched_objects_cache = {}
    return obj
