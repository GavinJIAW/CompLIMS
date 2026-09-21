from decimal import Decimal, ROUND_HALF_UP, localcontext
from lims.costing.services import package_cost, money, line_cost


def product_cost(product):
    with localcontext() as context:
        context.prec = 80
        exact = sum((line_cost(package_cost(row.package), row.quantity) for row in product.packages.all()), Decimal(0))
        return money(exact)


def scheme_totals(scheme):
    """Each configuration row counts once, including repeated products."""
    with localcontext() as context:
        context.prec = 80
        rows = list(scheme.items.all())
        return (money(sum((product_cost(row.product) for row in rows), Decimal('0.00'))),
                money(sum((row.product.reference_price for row in rows), Decimal('0.00'))))


from .models import Service, Product
from .templates import validate_compatibility, validate_values
from lims.shared.services import save_aggregate

def validate_dependencies(instance, data):
    if isinstance(instance, Service) and 'requirement_template' in data:
        validate_compatibility(instance, data['requirement_template'])
    if isinstance(instance, Product) and 'service' in data:
        template = data['service'].requirement_template
        for row in instance.scheme_items.all():
            validate_values(template, row.requirement_override, f'items.{row.pk}.requirement_override')


def save_master(serializer, **audit):
    return save_aggregate(serializer, validate_dependencies=validate_dependencies, **audit)
