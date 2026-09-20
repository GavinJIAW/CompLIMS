from decimal import Decimal, localcontext


def package_cost(package):
    with localcontext() as context:
        context.prec = 80
        return sum((row.item.unit_cost * row.quantity for row in package.items.all()), Decimal(0))
