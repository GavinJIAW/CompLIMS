"""Explicit M1 capabilities and DTO ceilings; no model/URL inference."""
MASTER = 'id number name enabled description creator creator_name modifier modifier_name dept_belong_id create_datetime update_datetime'
NAMES = 'internal_name name_en'
READ = {
    'service': MASTER + ' ' + NAMES + ' service_type requirement_template result_template',
    'cost_item': MASTER + ' type unit_cost unit basis_data',
    'cost_package': MASTER + ' unit items current_cost',
    'product': MASTER + ' ' + NAMES + ' service requirement_defaults unit reference_price packages standard_cost',
    'scheme': MASTER + ' ' + NAMES + ' items standard_cost reference_price',
}
WRITE = {key: 'number name enabled description ' + fields for key, fields in {
    'service': NAMES + ' service_type requirement_template result_template',
    'cost_item': 'type unit_cost unit basis_data',
    'cost_package': 'unit items',
    'product': NAMES + ' service requirement_defaults unit reference_price packages',
    'scheme': NAMES + ' items',
}.items()}
CLASSES = {'service': 'ServiceViewSet', 'cost_item': 'CostItemViewSet',
           'cost_package': 'CostPackageViewSet', 'product': 'ProductViewSet', 'scheme': 'SchemeViewSet'}
ROW_FIELDS = {
    'CostPackageItem': 'id item quantity sequence',
    'ProductCostPackage': 'id package quantity sequence',
    'SchemeItem': 'id product sequence requirement_override remark',
}

MODULES = {resource: 'lims.' + ('costing' if resource in ('cost_item', 'cost_package') else 'catalog') + '.views' for resource in CLASSES}
