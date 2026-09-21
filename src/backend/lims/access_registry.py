"""Metadata-only aggregation for Foundation; business rules stay in each app."""
from lims.costing import access_contract as costing
from lims.catalog import access_contract as catalog
from lims.customer import access_contract as customer
from lims.commercial import access_contract as commercial

READ = {**costing.READ, **catalog.READ, **customer.READ, **commercial.READ}
WRITE = {**costing.WRITE, **catalog.WRITE, **customer.WRITE, **commercial.WRITE}
CLASSES = {**costing.CLASSES, **catalog.CLASSES, **customer.CLASSES, **commercial.CLASSES}
MODULES = {**costing.MODULES, **catalog.MODULES, **customer.MODULES, **commercial.MODULES}
SCOPES = {**costing.SCOPES, **catalog.SCOPES, **customer.SCOPES, **commercial.SCOPES}
ACTIONS = {**costing.ACTIONS, **catalog.ACTIONS, **customer.ACTIONS, **commercial.ACTIONS}
ROW_FIELDS = {**costing.ROW_FIELDS, **catalog.ROW_FIELDS}

CHILDREN = commercial.CHILDREN
CHILD_READ = commercial.CHILD_READ
CHILD_CREATE = commercial.CHILD_CREATE
CHILD_UPDATE = commercial.CHILD_UPDATE
