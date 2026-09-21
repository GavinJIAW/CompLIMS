"""App-owned resource identities and explicit field ceilings."""
READ = {'cost_type': 'id number name enabled description creator creator_name modifier modifier_name dept_belong_id '
              'create_datetime update_datetime',
 'cost_item': 'id number name enabled description creator creator_name modifier modifier_name dept_belong_id '
              'create_datetime update_datetime cost_type unit_cost unit basis_data',
 'cost_package': 'id number name enabled description creator creator_name modifier modifier_name '
                 'dept_belong_id create_datetime update_datetime unit items current_cost'}
WRITE = {'cost_type': 'number name enabled description ',
 'cost_item': 'number name enabled description cost_type unit_cost unit basis_data',
 'cost_package': 'number name enabled description unit items'}
CLASSES = {'cost_type': 'CostTypeViewSet', 'cost_item': 'CostItemViewSet', 'cost_package': 'CostPackageViewSet'}
MODULES = {'cost_type': 'lims.costing.views', 'cost_item': 'lims.costing.views', 'cost_package': 'lims.costing.views'}
SCOPES = {'cost_type': 'shared_all', 'cost_item': 'shared_all', 'cost_package': 'shared_all'}
ACTIONS = {'cost_type': {}, 'cost_item': {}, 'cost_package': {}}
ROW_FIELDS = {'CostPackageItem': 'id item quantity sequence'}
