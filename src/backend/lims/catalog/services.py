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
