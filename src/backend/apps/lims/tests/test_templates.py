from django.test import SimpleTestCase, TestCase
from rest_framework.exceptions import ValidationError
from apps.lims.templates import validate_template, validate_values, validate_compatibility, TYPES
from apps.lims.models import Service, Product, Scheme, SchemeItem


def field(kind='string', **kwargs):
    return dict(key='value', label='Value', type=kind, required=False, **kwargs)


class TemplateTests(SimpleTestCase):
    def test_all_types(self):
        for kind in TYPES:
            extra = {'options': [{'label': 'A', 'value': 'a'}]} if kind in ('select', 'multiple_select') else {}
            if kind == 'table':
                extra['columns'] = [field()]
            validate_template([field(kind, **extra)])

    def test_restricted_schema(self):
        for template in ({}, [field('script')], [field(), field()], [field('table', columns=[field('table')])],
                         [field('select')], [field('select', options=[{'label': 'A', 'value': 'a'}] * 2)],
                         [dict(field(), script='anything')], [dict(field(), key='a.b')]):
            with self.subTest(template=template), self.assertRaises(ValidationError):
                validate_template(template)

    def test_defaults_type_and_null(self):
        for kind, value in [('integer', True), ('float', float('nan')), ('date', '2026-02-30'), ('boolean', 1), ('file', 12)]:
            with self.subTest(kind=kind), self.assertRaises(ValidationError):
                validate_template([field(kind, default=value)])
        validate_template([field('integer', default=0), dict(field('boolean', default=False), key='other')])
        validate_template([field(default=None, nullable=True)])
        with self.assertRaises(ValidationError):
            validate_template([field(default=None)])

    def test_select_and_table_defaults(self):
        choices = [{'label': 'A', 'value': 'a'}]
        validate_template([field('multiple_select', options=choices, default=['a'])])
        with self.assertRaises(ValidationError):
            validate_template([field('multiple_select', options=choices, default=['b'])])
        validate_template([field('table', columns=[field('integer')], default=[{'value': 2}])])
        with self.assertRaises(ValidationError):
            validate_template([field('table', columns=[field('integer')], default=[{'value': 'x'}])])

    def test_partial_defaults_and_override(self):
        template = [dict(field('integer'), required=True)]
        validate_values(template, {})
        validate_values(template, {'value': 0})
        for values in ({'unknown': 1}, {'value': '1'}, {'value': None}):
            with self.assertRaises(ValidationError):
                validate_values(template, values)
        with self.assertRaises(ValidationError):
            validate_values([field('table', columns=[field()])], {'value': []})


class CompatibilityTests(TestCase):
    def test_existing_product_and_scheme_are_checked(self):
        service = Service.objects.create(number='S', name='Service', requirement_template=[field('integer')])
        product = Product.objects.create(number='P', name='Product', service=service, requirement_defaults={'value': 1}, unit='test', reference_price=0)
        scheme = Scheme.objects.create(number='SC', name='Scheme')
        row = SchemeItem.objects.create(scheme=scheme, product=product, sequence=10, requirement_override={'value': 2})
        validate_compatibility(service, [field('integer')])
        with self.assertRaises(ValidationError):
            validate_compatibility(service, [field()])
        product.requirement_defaults = {}
        product.save()
        with self.assertRaises(ValidationError):
            validate_compatibility(service, [])
        row.requirement_override = {}
        row.save()
        validate_compatibility(service, [])
