"""App-owned resource identities and explicit field ceilings."""
READ = {'customer': 'id creator creator_name modifier modifier_name dept_belong_id create_datetime update_datetime '
             'number name short_name tax_number address enabled description'}
WRITE = {'customer': 'number name short_name tax_number address enabled description'}
CLASSES = {'customer': 'CustomerViewSet'}
MODULES = {'customer': 'lims.customer.views'}
SCOPES = {'customer': 'shared_all'}
ACTIONS = {'customer': {}}

CONTACT = 'name gender customer direct_supervisor title email mobile address enabled is_default'
READ['contact'] = 'id ' + CONTACT + ' customer_name direct_supervisor_name creator creator_name modifier modifier_name dept_belong_id create_datetime update_datetime'
WRITE['contact'] = CONTACT
CLASSES['contact'] = 'ContactViewSet'
MODULES['contact'] = 'lims.customer.views'
SCOPES['contact'] = 'shared_all'
ACTIONS['contact'] = {}
