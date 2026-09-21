"""App-owned resource identities and explicit field ceilings."""
READ = {'quotation': 'id creator creator_name modifier modifier_name dept_belong_id create_datetime update_datetime '
              'number customer customer_name_snapshot customer_tax_number_snapshot customer_address_snapshot '
              'contact_name_snapshot contact_mobile_snapshot contact_email_snapshot adjustment_amount '
              'commercial_terms remark schemes status quotation_date valid_until subtotal total_amount '
              'sent_at sent_by accepted_at accepted_by rejected_at rejected_by voided_at voided_by',
 'contract': 'id creator creator_name modifier modifier_name dept_belong_id create_datetime update_datetime '
             'number customer customer_name_snapshot customer_tax_number_snapshot customer_address_snapshot '
             'contact_name_snapshot contact_mobile_snapshot contact_email_snapshot adjustment_amount '
             'commercial_terms remark schemes status contract_date source_quotation subtotal total_amount '
             'signed_at signed_by voided_at voided_by'}
WRITE = {'quotation': 'number customer customer_name_snapshot customer_tax_number_snapshot customer_address_snapshot '
              'contact_name_snapshot contact_mobile_snapshot contact_email_snapshot adjustment_amount '
              'commercial_terms remark schemes quotation_date valid_until',
 'contract': 'number customer customer_name_snapshot customer_tax_number_snapshot customer_address_snapshot '
             'contact_name_snapshot contact_mobile_snapshot contact_email_snapshot adjustment_amount '
             'commercial_terms remark schemes contract_date'}
CLASSES = {'quotation': 'QuotationViewSet', 'contract': 'ContractViewSet'}
MODULES = {'quotation': 'lims.commercial.views', 'contract': 'lims.commercial.views'}
SCOPES = {'quotation': 'attribution', 'contract': 'attribution'}
ACTIONS = {'quotation': {'Send': 'send', 'Accept': 'accept', 'Reject': 'reject', 'Void': 'void', 'CreateContract': 'create_contract'}, 'contract': {'Sign': 'sign', 'Void': 'void'}}
SNAPSHOT = 'customer_name_snapshot customer_tax_number_snapshot customer_address_snapshot contact_name_snapshot contact_mobile_snapshot contact_email_snapshot'
CHILD_READ = {'ContractScheme': 'id source_scheme sequence name_snapshot name_en_snapshot description_snapshot remark '
                   'items',
 'ContractSchemeItem': 'id source_product sequence product_number_snapshot name_snapshot name_en_snapshot '
                       'unit_snapshot requirement_schema requirement_data quantity unit_price line_amount '
                       'remark',
 'QuotationScheme': 'id source_scheme sequence name_snapshot name_en_snapshot description_snapshot remark '
                    'items',
 'QuotationSchemeItem': 'id source_product sequence product_number_snapshot name_snapshot name_en_snapshot '
                        'unit_snapshot requirement_schema requirement_data quantity unit_price line_amount '
                        'remark'}
CHILD_CREATE = {'ContractScheme': 'source_scheme sequence name_snapshot name_en_snapshot description_snapshot remark items',
 'ContractSchemeItem': 'source_product sequence name_snapshot name_en_snapshot unit_snapshot '
                       'requirement_data quantity unit_price remark',
 'QuotationScheme': 'source_scheme sequence name_snapshot name_en_snapshot description_snapshot remark items',
 'QuotationSchemeItem': 'source_product sequence name_snapshot name_en_snapshot unit_snapshot '
                        'requirement_data quantity unit_price remark'}
CHILD_UPDATE = {'ContractScheme': 'sequence name_snapshot name_en_snapshot description_snapshot remark items',
 'ContractSchemeItem': 'sequence name_snapshot name_en_snapshot unit_snapshot requirement_data quantity '
                       'unit_price remark',
 'QuotationScheme': 'sequence name_snapshot name_en_snapshot description_snapshot remark items',
 'QuotationSchemeItem': 'sequence name_snapshot name_en_snapshot unit_snapshot requirement_data quantity '
                        'unit_price remark'}
CHILDREN = {'quotation': ['QuotationScheme', 'QuotationSchemeItem'], 'contract': ['ContractScheme', 'ContractSchemeItem']}
