"""Atomic commercial aggregate commands. Master data is read only on new sources."""
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP, localcontext
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied
from coreadmin.access.context import AccessContext
from coreadmin.access.registry import REGISTRY
from coreadmin.access.fields import FieldPolicy
from coreadmin.utils.log_targets import record_targets
from lims.catalog.models import Product, Scheme, Service
from lims.catalog.templates import validate_template, validate_value
from lims.shared.authority import row_fields
from lims.catalog.access_contract import ROW_FIELDS as CATALOG_ROWS
from lims.commercial.aggregate_authority import source, proposed, check_child, child_fields
from lims.commercial.aggregate_rows import collection, unique_sequences, validate_row
from lims.commercial.aggregate_views import Conflict
from lims.commercial.access_contract import SNAPSHOT, CHILD_CREATE, CHILD_READ
from lims.customer.models import Customer
from .models import Quotation, Contract, QuotationScheme, ContractScheme, QuotationSchemeItem, ContractSchemeItem

CENT = Decimal('0.01')
MAX_AMOUNT = Decimal('999999999999999999.99')
COPY_HEADER = SNAPSHOT.split() + ['customer_id', 'adjustment_amount', 'subtotal', 'total_amount', 'commercial_terms', 'remark']


def money(value):
    with localcontext() as ctx:
        ctx.prec = 80
        value = value.quantize(CENT, rounding=ROUND_HALF_UP)
        if not value.is_finite() or abs(value) > MAX_AMOUNT:
            raise ValidationError('Amount exceeds the supported monetary range.')
        return value


def requirements(schema, values, path='requirement_data'):
    validate_template(schema)
    if not isinstance(values, dict):
        raise ValidationError({path: 'Expected an object.'})
    definitions = {f['key']: f for f in schema}
    for key, value in values.items():
        field = definitions.get(key)
        if field is None:
            raise ValidationError({path: f'Unknown key: {key}'})
        if field['type'] in ('file', 'image', 'csv'):
            if value is not None:
                raise ValidationError({path: 'M2 does not accept file entity values.'})
            validate_value(field, value, path + '.' + key)
        elif field['type'] == 'table' and value is not None:
            if not isinstance(value, list) or len(value) > 500:
                raise ValidationError({path: 'Expected at most 500 table rows.'})
            for row in value:
                requirements(field['columns'], row, path + '.' + key)
        else:
            validate_value(field, value, path + '.' + key)


def product_snapshot(ctx, product_id, override=None):
    product = source(ctx, 'product', Product, product_id, ['number', 'name', 'name_en', 'unit', 'service', 'requirement_defaults', 'reference_price'])
    access = AccessContext(ctx.user, REGISTRY['service', 'retrieve', 'GET'])
    if not access.allowed() or not access.scope(Service.objects.all()).filter(pk=product.service_id).exists() or 'requirement_template' not in FieldPolicy(access, Service).allowed(product.service):
        raise PermissionDenied('Service requirement template is not readable.')
    values = deepcopy(product.requirement_defaults)
    values.update(deepcopy(override or {}))
    return dict(source_product=product, product_number_snapshot=product.number,
                name_snapshot=product.name, name_en_snapshot=product.name_en, unit_snapshot=product.unit,
                requirement_schema=deepcopy(product.service.requirement_template), requirement_data=values,
                quantity=Decimal('1.000000'), unit_price=product.reference_price, remark='')


def prepare_items(ctx, parent, model, raw, group=None, imported=None):
    existing = {r.pk: r for r in group.items.all()} if group else {}
    rows = collection(raw, existing)
    unique_sequences(model, rows)
    prepared = []
    fields = CHILD_CREATE[model.__name__].split()
    for data, old in rows:
        check_child(ctx, parent, model, data, old)
        incoming = {k: v for k, v in data.items() if k != 'id'}
        if not old:
            snapshot = product_snapshot(ctx, incoming.get('source_product'), (imported or {}).get(data.get('sequence')))
            incoming.pop('source_product', None)
        else:
            snapshot = {}
        values = validate_row(model, incoming, old or model(**snapshot), [f for f in fields if f != 'source_product'])
        values = {**snapshot, **values}
        schema = values.get('requirement_schema', old.requirement_schema if old else [])
        value = values.get('requirement_data', old.requirement_data if old else {})
        requirements(schema, value)
        quantity = values.get('quantity', old.quantity if old else Decimal(1))
        price = values.get('unit_price', old.unit_price if old else None)
        if price is None:
            raise ValidationError('A unit price is required.')
        with localcontext() as precision:
            precision.prec = 80
            values['line_amount'] = money(quantity * price)
        prepared.append((values, old))
    return prepared


def prepare_groups(ctx, parent, model, item_model, raw, instance=None):
    existing = {r.pk: r for r in instance.schemes.all()} if instance else {}
    rows = collection(raw, existing)
    unique_sequences(model, rows)
    prepared = []
    for data, old in rows:
        check_child(ctx, parent, model, data, old)
        values = {k: v for k, v in data.items() if k not in ('id', 'items')}
        item_raw = data.get('items')
        if 'items' in data and not isinstance(item_raw, list):
            raise ValidationError({'items': 'Expected a target collection.'})
        overrides = {}
        if old is None and values.get('source_scheme') is not None:
            template = source(ctx, 'scheme', Scheme, values['source_scheme'], ['name', 'name_en', 'description', 'items'])
            read = AccessContext(ctx.user, REGISTRY['scheme', 'retrieve', 'GET'])
            from lims.catalog.models import SchemeItem
            if not {'product', 'sequence', 'requirement_override', 'remark'} <= row_fields(read, SchemeItem, 'read', CATALOG_ROWS['SchemeItem']):
                raise PermissionDenied('Scheme item snapshot fields are not readable.')
            if 'items' in data:
                raise ValidationError('A new Scheme import supplies its own items; edit them after saving.')
            values = {'name_snapshot': template.name, 'name_en_snapshot': template.name_en, 'description_snapshot': template.description, **values}
            source_id = values.pop('source_scheme')
            item_raw = []
            for row in template.items.all():
                item_raw.append(dict(source_product=row.product_id, sequence=row.sequence, remark=row.remark))
                overrides[row.sequence] = row.requirement_override
        else:
            source_id = values.pop('source_scheme', None)
        clean = validate_row(model, values, old, ['sequence', 'name_snapshot', 'name_en_snapshot', 'description_snapshot', 'remark'])
        if not old:
            clean['source_scheme_id'] = source_id
        items = prepare_items(ctx, parent, item_model, item_raw, old, overrides) if item_raw is not None else None
        prepared.append((clean, old, items))
    return prepared


def persist_rows(manager, rows):
    retained = [old.pk for _, old in rows if old]
    manager.exclude(pk__in=retained).delete()
    for values, old in rows:
        if old:
            for key, value in values.items():
                setattr(old, key, value)
            old.save()
        else:
            manager.create(**values)


def totals(document, verify=False):
    with localcontext() as ctx:
        ctx.prec = 80
        subtotal = Decimal('0.00')
        for group in document.schemes.all():
            for row in group.items.all():
                expected = money(row.quantity * row.unit_price)
                if expected != row.line_amount:
                    raise Conflict('Persisted line amount is inconsistent.')
                subtotal += row.line_amount
        subtotal = money(subtotal)
        total = money(subtotal + document.adjustment_amount)
    if total < 0:
        raise ValidationError({'adjustment_amount': 'Total amount cannot be negative.'})
    if verify and (subtotal != document.subtotal or total != document.total_amount):
        raise Conflict('Persisted totals are inconsistent.')
    document.subtotal, document.total_amount = subtotal, total


@transaction.atomic
def save_document(serializer, data):
    instance = serializer.instance
    ctx = serializer.request._canonical_access_view.access_context
    parent = instance or proposed(ctx)
    if instance and instance.status != 'DRAFT':
        raise Conflict('Commercial body is locked after DRAFT.')
    raw = data.pop('schemes', None)
    customer = data.get('customer')
    if customer and (not instance or customer.pk != instance.customer_id):
        customer = source(ctx, 'customer', Customer, customer.pk, ['name', 'tax_number', 'address'])
        data.setdefault('customer_name_snapshot', customer.name)
        data.setdefault('customer_tax_number_snapshot', customer.tax_number)
        data.setdefault('customer_address_snapshot', customer.address)
    model = serializer.Meta.model
    group_model, item_model = (QuotationScheme, QuotationSchemeItem) if model is Quotation else (ContractScheme, ContractSchemeItem)
    groups = prepare_groups(ctx, parent, group_model, item_model, raw, instance) if raw is not None else None
    if instance:
        for key, value in data.items():
            setattr(instance, key, value)
        instance.save()
    else:
        instance = model.objects.create(**data)
    if groups is not None:
        instance.schemes.exclude(pk__in=[old.pk for _, old, _ in groups if old]).delete()
        for values, old, items in groups:
            if old:
                for key, value in values.items():
                    setattr(old, key, value)
                old.save()
                group = old
            else:
                group = instance.schemes.create(**values)
            if items is not None:
                persist_rows(group.items, items)
    instance._prefetched_objects_cache = {}
    totals(instance)
    instance.save(update_fields=['subtotal', 'total_amount'])
    return instance


@transaction.atomic
def transition(view, command):
    obj = locked_object(view)
    if view.request.data:
        raise ValidationError('State commands do not accept body fields.')
    rules = {'send': ('DRAFT', 'SENT', 'sent'), 'accept': ('SENT', 'ACCEPTED', 'accepted'), 'reject': ('SENT', 'REJECTED', 'rejected'), 'sign': ('DRAFT', 'SIGNED', 'signed'), 'void': ('SENT' if isinstance(obj, Quotation) else 'SIGNED', 'VOID', 'voided')}
    before, after, stem = rules[command]
    if obj.status != before:
        raise Conflict('Invalid state transition.')
    totals(obj, verify=True)
    obj.status = after
    setattr(obj, stem + '_at', timezone.now())
    setattr(obj, stem + '_by', view.request.user)
    obj.modifier = str(view.request.user.pk)
    obj.save(update_fields=['status', stem + '_at', stem + '_by', 'modifier', 'update_datetime'])
    return obj


def locked_object(view):
    obj = view.get_object()
    view.queryset.model.objects.select_for_update().get(pk=obj.pk)
    view.access_context.__dict__.pop('grants', None)
    view.access_context.__dict__.pop('child_depts', None)
    view.field_policy.__dict__.pop('configured', None)
    return view.get_object()


@transaction.atomic
def convert(view):
    quotation = locked_object(view)
    if quotation.status != 'ACCEPTED':
        raise Conflict('Only ACCEPTED quotations can create a contract.')
    if Contract.objects.filter(source_quotation=quotation).exists():
        raise Conflict('This quotation already has a contract.')
    from rest_framework import serializers
    class Input(serializers.Serializer):
        number = serializers.CharField(max_length=64)
        contract_date = serializers.DateField()
    if not isinstance(view.request.data, dict) or set(view.request.data) != {'number', 'contract_date'}:
        raise ValidationError('Provide only number and contract_date.')
    incoming = Input(data=view.request.data)
    incoming.is_valid(raise_exception=True)
    target = AccessContext(view.request.user, REGISTRY['contract', 'create', 'POST'])
    if not target.allowed():
        raise PermissionDenied('Contract create permission is required.')
    FieldPolicy(target, Contract).validate_write(incoming.validated_data)
    source(target, 'customer', Customer, quotation.customer_id)
    required = set(COPY_HEADER) - {'customer_id'} | {'customer', 'schemes'}
    if not required <= view.field_policy.allowed(quotation):
        raise PermissionDenied('Source quotation snapshot fields are not readable.')
    for model in (QuotationScheme, QuotationSchemeItem):
        if not set(CHILD_READ[model.__name__].split()) <= child_fields(view.access_context, quotation, model, 'read'):
            raise PermissionDenied('Source child snapshot fields are not readable.')
    totals(quotation, verify=True)
    header = {key: deepcopy(getattr(quotation, key)) for key in COPY_HEADER}
    # Server-generated copied fields remain governed by target CREATE permission.
    writable = {key: value for key, value in header.items() if key not in ('subtotal', 'total_amount', 'customer_id')}
    FieldPolicy(target, Contract).validate_write({**incoming.validated_data, **writable, 'customer': quotation.customer_id, 'schemes': []})
    parent = proposed(target)
    for model in (ContractScheme, ContractSchemeItem):
        if not set(CHILD_CREATE[model.__name__].split()) <= child_fields(target, parent, model, 'create'):
            raise PermissionDenied('Contract child create fields are not writable.')
    try:
        with transaction.atomic():
            contract = Contract.objects.create(**incoming.validated_data, **header, source_quotation=quotation, **target.create_attribution())
    except IntegrityError as exc:
        # Inspect only after the insert savepoint has rolled back. PostgreSQL's
        # diagnostic constraint must identify this exact field, not another FK,
        # CHECK or UNIQUE failure that happens to coexist with the same number.
        cause = exc.__cause__
        diag = getattr(cause, 'diag', None)
        if getattr(cause, 'pgcode', None) == '23505' and getattr(diag, 'table_name', None) == Contract._meta.db_table:
            connection = transaction.get_connection()
            with connection.cursor() as cursor:
                constraints = connection.introspection.get_constraints(cursor, Contract._meta.db_table)
            constraint = constraints.get(diag.constraint_name, {})
            if constraint.get('unique') and constraint.get('columns') == ['number'] and Contract.objects.filter(number=incoming.validated_data['number']).exists():
                raise Conflict('Contract number already exists.') from exc
        raise
    for group in quotation.schemes.all():
        values = {key: deepcopy(getattr(group, key)) for key in ('sequence', 'name_snapshot', 'name_en_snapshot', 'description_snapshot', 'remark', 'source_scheme_id')}
        copy = contract.schemes.create(**values)
        for row in group.items.all():
            values = {field.name: deepcopy(getattr(row, field.attname)) for field in row._meta.fields if field.name not in ('id', 'quotation_scheme', 'source_product')}
            copy.items.create(**values, source_product_id=row.source_product_id)
    record_targets(view.request, {'quotation': [quotation.pk], 'contract': [contract.pk]})
    return contract
