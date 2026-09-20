"""Restricted data-only template contract; never executes expressions/components."""
import math
import re
from datetime import date
from rest_framework.exceptions import ValidationError

TYPES = ('string', 'integer', 'float', 'date', 'boolean', 'select',
         'multiple_select', 'file', 'image', 'csv', 'table')
SCALARS = ('string', 'integer', 'float', 'date', 'boolean', 'select')
KEY = re.compile(r'^[A-Za-z][A-Za-z0-9_]{0,63}$')


def invalid(path, message):
    raise ValidationError({path: message})


def validate_value(field, value, path):
    kind = field['type']
    if value is None:
        if field['required'] or not field.get('nullable', False):
            invalid(path, 'Null requires an optional, explicitly nullable field.')
        return
    valid = False
    if kind == 'string':
        valid = isinstance(value, str) and (not field['required'] or bool(value.strip()))
    elif kind == 'integer':
        valid = type(value) is int
    elif kind == 'float':
        try:
            valid = type(value) in (int, float) and math.isfinite(value)
        except OverflowError:
            valid = False
    elif kind == 'boolean':
        valid = type(value) is bool
    elif kind == 'date':
        try:
            valid = isinstance(value, str) and date.fromisoformat(value).isoformat() == value
        except ValueError:
            pass
    elif kind in ('select', 'multiple_select'):
        options = [option['value'] for option in field['options']]
        if kind == 'select':
            valid = isinstance(value, str) and value in options
        else:
            valid = (isinstance(value, list) and all(isinstance(v, str) and v in options for v in value)
                     and len(set(value)) == len(value) and (not field['required'] or bool(value)))
    elif kind == 'table':
        if isinstance(value, list) and len(value) <= 500 and (not field['required'] or value):
            for index, row in enumerate(value):
                validate_values(field['columns'], row, f'{path}.{index}', complete=True)
            valid = True
    # M1 defines file types only, with no actual file default/reference data.
    if not valid:
        invalid(path, f'Invalid {kind} value.')


def validate_template(template, path='template', columns=False):
    if not isinstance(template, list) or len(template) > 100:
        invalid(path, 'Expected at most 100 field definitions.')
    seen = set()
    allowed = {'key', 'label', 'type', 'required', 'unit', 'default', 'help_text', 'options', 'columns', 'nullable'}
    for index, field in enumerate(template):
        here = f'{path}.{index}'
        if not isinstance(field, dict) or set(field) - allowed:
            invalid(here, 'Unknown field definition attributes.')
        if not {'key', 'label', 'type', 'required'} <= set(field):
            invalid(here, 'key, label, type and required are required.')
        key = field['key']
        if not isinstance(key, str) or not KEY.fullmatch(key) or key in seen:
            invalid(here, 'Keys must be unique machine identifiers.')
        seen.add(key)
        if not isinstance(field['label'], str) or not field['label'].strip():
            invalid(here, 'A label is required.')
        if field['type'] not in (SCALARS if columns else TYPES):
            invalid(here, 'Unsupported field type.')
        if type(field['required']) is not bool or type(field.get('nullable', False)) is not bool:
            invalid(here, 'required and nullable must be booleans.')
        if field['required'] and field.get('nullable', False):
            invalid(here, 'Required fields cannot be nullable.')
        for name in ('unit', 'help_text'):
            if name in field and not isinstance(field[name], str):
                invalid(here, f'{name} must be text.')
        if field['type'] in ('select', 'multiple_select'):
            options = field.get('options')
            if not isinstance(options, list) or not options or len(options) > 500:
                invalid(here, 'Select fields require options.')
            values = set()
            for option in options:
                if (not isinstance(option, dict) or set(option) != {'label', 'value'}
                        or any(not isinstance(option[k], str) or not option[k].strip() for k in ('label', 'value'))
                        or option['value'] in values):
                    invalid(here, 'Options require labels and unique string values.')
                values.add(option['value'])
        elif 'options' in field:
            invalid(here, 'options only applies to select fields.')
        if field['type'] == 'table':
            if not field.get('columns'):
                invalid(here, 'Table columns are required.')
            validate_template(field['columns'], here + '.columns', columns=True)
        elif 'columns' in field:
            invalid(here, 'columns only applies to tables.')
        if 'default' in field:
            validate_value(field, field['default'], here + '.default')
    return template


def validate_values(template, values, path='values', complete=False):
    if not isinstance(values, dict):
        invalid(path, 'Expected an object.')
    fields = {field['key']: field for field in template}
    for key, value in values.items():
        if key not in fields:
            invalid(path + '.' + key, 'Unknown template key.')
        field = fields[key]
        if not complete and field['type'] in ('file', 'image', 'csv', 'table') and value is not None:
            invalid(path + '.' + key, 'M1 defaults/overrides cannot contain file or table data.')
        validate_value(field, value, path + '.' + key)
    if complete:
        for key, field in fields.items():
            if field['required'] and key not in values and 'default' not in field:
                invalid(path + '.' + key, 'Required value is missing.')
    return values


def validate_compatibility(service, template):
    """Caller holds the master command lock also used by dependent writers."""
    from apps.lims.models import Product, SchemeItem
    for product in Product.objects.filter(service=service):
        validate_values(template, product.requirement_defaults, f'product.{product.pk}.requirement_defaults')
    for row in SchemeItem.objects.filter(product__service=service):
        validate_values(template, row.requirement_override, f'scheme_item.{row.pk}.requirement_override')
