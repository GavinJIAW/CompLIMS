from lims.shared.authority import readable

def package_visible(actor, package):
    return (readable(actor, 'cost_package', package, ['current_cost']) and
            all(readable(actor, 'cost_item', row.item, ['unit_cost']) for row in package.items.all()))
