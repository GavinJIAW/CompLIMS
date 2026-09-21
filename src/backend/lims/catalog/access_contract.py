"""App-owned resource identities and explicit field ceilings."""
READ = {'service': 'id number name enabled description creator creator_name modifier modifier_name dept_belong_id '
            'create_datetime update_datetime internal_name name_en service_type requirement_template '
            'result_template',
 'product': 'id number name enabled description creator creator_name modifier modifier_name dept_belong_id '
            'create_datetime update_datetime internal_name name_en service requirement_defaults unit '
            'reference_price packages standard_cost',
 'scheme': 'id number name enabled description creator creator_name modifier modifier_name dept_belong_id '
           'create_datetime update_datetime internal_name name_en items standard_cost reference_price'}
WRITE = {'service': 'number name enabled description internal_name name_en service_type requirement_template '
            'result_template',
 'product': 'number name enabled description internal_name name_en service requirement_defaults unit '
            'reference_price packages',
 'scheme': 'number name enabled description internal_name name_en items'}
CLASSES = {'service': 'ServiceViewSet', 'product': 'ProductViewSet', 'scheme': 'SchemeViewSet'}
MODULES = {'service': 'lims.catalog.views', 'product': 'lims.catalog.views', 'scheme': 'lims.catalog.views'}
SCOPES = {'service': 'shared_all', 'product': 'shared_all', 'scheme': 'shared_all'}
ACTIONS = {'service': {}, 'product': {}, 'scheme': {}}
ROW_FIELDS = {'ProductCostPackage': 'id package quantity sequence', 'SchemeItem': 'id product sequence requirement_override remark'}
