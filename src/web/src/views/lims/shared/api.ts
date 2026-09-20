import { request } from '/@/utils/service';
export const writable: Record<string,string[]> = {
  service: 'number internal_name name name_en service_type requirement_template result_template enabled description'.split(' '),
  cost_item: 'number name type unit_cost unit basis_data enabled description'.split(' '),
  cost_package: 'number name unit items enabled description'.split(' '),
  product: 'number internal_name name name_en service requirement_defaults unit reference_price packages enabled description'.split(' '),
  scheme: 'number internal_name name name_en items enabled description'.split(' '),
};
const rowKeys: Record<string,string[]> = {cost_package:['id','item','quantity','sequence'], product:['id','package','quantity','sequence'], scheme:['id','product','sequence','requirement_override','remark']};
export function payload(resource: string, form: any, update = false, permissions?: any) {
  const mode = update ? 'is_update' : 'is_create';
  const result = Object.fromEntries(writable[resource].filter(key => (!update || key !== 'number') && (!permissions || permissions[key]?.[mode]) && form[key] !== undefined).map(key => [key, form[key]]));
  const name = resource === 'product' ? 'packages' : 'items';
  if (Array.isArray(result[name])) result[name] = result[name].map((row: any) => Object.fromEntries(rowKeys[resource].filter(key => row[key] !== undefined).map(key => [key,row[key]])));
  return result;
}
export function apiFor(resource: string) {
  const prefix = `/api/lims/${resource}/`;
  return {
    list: (params: any) => request({url:prefix, params}),
    get: (id: number) => request({url:`${prefix}${id}/`}),
    permissions: () => request({url:`${prefix}field_permission/`}),
    create: (form: any) => request({url:prefix, method:'post', data:form}),
    update: (id: number, form: any) => request({url:`${prefix}${id}/`, method:'patch', data:form}),
    remove: (id: number) => request({url:`${prefix}${id}/`, method:'delete'}),
  };
}
