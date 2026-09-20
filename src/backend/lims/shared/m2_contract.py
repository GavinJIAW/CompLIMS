"""Explicit M2 resource and aggregate field contracts; no database access."""
AUDIT = 'id creator creator_name modifier modifier_name dept_belong_id create_datetime update_datetime'
CUSTOMER = 'number name short_name tax_number address enabled description contacts'
SNAPSHOT = 'customer_name_snapshot customer_tax_number_snapshot customer_address_snapshot contact_name_snapshot contact_phone_snapshot contact_email_snapshot'
BODY = 'number customer ' + SNAPSHOT + ' adjustment_amount commercial_terms remark schemes'
READ = {
    'customer': AUDIT + ' ' + CUSTOMER,
    'quotation': AUDIT + ' ' + BODY + ' status quotation_date valid_until subtotal total_amount sent_at sent_by accepted_at accepted_by rejected_at rejected_by voided_at voided_by',
    'contract': AUDIT + ' ' + BODY + ' status contract_date source_quotation subtotal total_amount signed_at signed_by voided_at voided_by',
}
WRITE = {'customer': CUSTOMER, 'quotation': BODY + ' quotation_date valid_until', 'contract': BODY + ' contract_date'}
MODULES = {'customer': 'lims.customer.views', 'quotation': 'lims.commercial.views', 'contract': 'lims.commercial.views'}
CLASSES = {'customer': 'CustomerViewSet', 'quotation': 'QuotationViewSet', 'contract': 'ContractViewSet'}
SCOPES = {'customer': 'shared_all', 'quotation': 'attribution', 'contract': 'attribution'}
ACTIONS = {'customer': {}, 'quotation': {'Send': 'send', 'Accept': 'accept', 'Reject': 'reject', 'Void': 'void', 'CreateContract': 'create_contract'}, 'contract': {'Sign': 'sign', 'Void': 'void'}}
CONTACT = 'name department title phone mobile email address is_default enabled remark'
GROUP = 'source_scheme sequence name_snapshot name_en_snapshot description_snapshot remark items'
ITEM = 'source_product sequence product_number_snapshot name_snapshot name_en_snapshot unit_snapshot requirement_schema requirement_data quantity unit_price line_amount remark'
CHILD_READ = {'CustomerContact': 'id ' + CONTACT}
CHILD_CREATE = {'CustomerContact': CONTACT}
CHILD_UPDATE = {'CustomerContact': CONTACT}
for prefix in ('Quotation', 'Contract'):
    CHILD_READ[prefix + 'Scheme'] = 'id ' + GROUP
    CHILD_CREATE[prefix + 'Scheme'] = GROUP
    CHILD_UPDATE[prefix + 'Scheme'] = GROUP.replace('source_scheme ', '')
    CHILD_READ[prefix + 'SchemeItem'] = 'id ' + ITEM
    CHILD_CREATE[prefix + 'SchemeItem'] = 'source_product sequence name_snapshot name_en_snapshot unit_snapshot requirement_data quantity unit_price remark'
    CHILD_UPDATE[prefix + 'SchemeItem'] = CHILD_CREATE[prefix + 'SchemeItem'].replace('source_product ', '')
CHILDREN = {'customer': ['CustomerContact'], 'quotation': ['QuotationScheme', 'QuotationSchemeItem'], 'contract': ['ContractScheme', 'ContractSchemeItem']}
