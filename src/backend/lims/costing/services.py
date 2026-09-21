from decimal import Decimal, ROUND_HALF_UP, localcontext


def money(value):
    """Round a Decimal monetary boundary; quantities retain their precision."""
    with localcontext() as context:
        context.prec = 80
        return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def line_cost(unit_cost, quantity):
    with localcontext() as context:
        context.prec = 80
        return money(unit_cost * quantity)


def package_cost(package):
    with localcontext() as context:
        context.prec = 80
        return money(sum((line_cost(row.item.unit_cost, row.quantity)
                          for row in package.items.all()), Decimal('0.00')))
