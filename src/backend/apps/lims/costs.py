"""Exact current-master costs. No persisted totals and no intermediate rounding."""
from decimal import Decimal, ROUND_HALF_UP, localcontext


def package_cost(package):
    with localcontext() as context:
        context.prec = 80
        return sum((row.item.unit_cost * row.quantity for row in package.items.all()), Decimal(0))


def product_cost(product):
    with localcontext() as context:
        context.prec = 80
        exact = sum((package_cost(row.package) * row.quantity for row in product.packages.all()), Decimal(0))
        return exact.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def scheme_totals(scheme):
    """Each configuration row counts once, including repeated products."""
    with localcontext() as context:
        context.prec = 80
        rows = list(scheme.items.all())
        return (sum((product_cost(row.product) for row in rows), Decimal('0.00')),
                sum((row.product.reference_price for row in rows), Decimal('0.00')))
