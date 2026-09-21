import { request } from '/@/utils/service';

const prefix = '/api/lims/quotation/';
export const api = {
  list: (params: any = {}) => request({ url: prefix, params }),
  retrieve: (id: number) => request({ url: `${prefix}${id}/` }),
  field_permission: () => request({ url: `${prefix}field_permission/` }),
  create: (data: any) => request({ url: prefix, method: 'post', data }),
  update: (id: number, data: any) => request({ url: `${prefix}${id}/`, method: 'patch', data }),
  destroy: (id: number) => request({ url: `${prefix}${id}/`, method: 'delete' }),
  send: (id: number, data: any = {}) => request({ url: `${prefix}${id}/send/`, method: 'post', data }),
  accept: (id: number, data: any = {}) => request({ url: `${prefix}${id}/accept/`, method: 'post', data }),
  reject: (id: number, data: any = {}) => request({ url: `${prefix}${id}/reject/`, method: 'post', data }),
  void: (id: number, data: any = {}) => request({ url: `${prefix}${id}/void/`, method: 'post', data }),
  createContract: (id: number, data: any = {}) =>
    request({ url: `${prefix}${id}/create_contract/`, method: 'post', data }),
};

export function payload(form: any, permissions: any) {
  const keys = [
    'number',
    'quotation_date',
    'valid_until',
    'customer',
    'customer_name_snapshot',
    'customer_tax_number_snapshot',
    'customer_address_snapshot',
    'contact_name_snapshot',
    'contact_mobile_snapshot',
    'contact_email_snapshot',
    'schemes',
    'adjustment_amount',
    'commercial_terms',
    'remark',
  ];
  const mode = form.id ? 'is_update' : 'is_create';
  const result: any = Object.fromEntries(
    keys
      .filter((key) => !(form.id && key === 'number') && permissions[key]?.[mode] && form[key] !== undefined)
      .map((key) => [key, form[key]])
  );
  if (result.schemes)
    result.schemes = result.schemes.map((row: any) => {
      const value = childPayload(
        row,
        'source_scheme sequence name_snapshot name_en_snapshot description_snapshot remark items'.split(' '),
        permissions._children?.QuotationScheme,
        ['source_scheme']
      );
      if (!row.id && row.source_scheme) delete value.items;
      else if (value.items)
        value.items = value.items.map((item: any) =>
          childPayload(
            item,
            'source_product sequence name_snapshot name_en_snapshot unit_snapshot requirement_data quantity unit_price remark'.split(
              ' '
            ),
            permissions._children?.QuotationSchemeItem,
            ['source_product']
          )
        );
      return value;
    });
  return result;
}

function childPayload(row: any, keys: string[], permissions: any, immutable: string[]) {
  const result: any = row.id ? { id: row.id } : {};
  for (const key of keys)
    if (
      !(row.id && immutable.includes(key)) &&
      row[key] !== undefined &&
      permissions?.[key]?.[row.id ? 'is_update' : 'is_create']
    )
      result[key] = row[key];
  return result;
}
