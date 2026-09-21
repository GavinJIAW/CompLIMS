import { request } from '/@/utils/service';

const prefix = '/api/lims/contact/';
export const api = {
  list: (params: any = {}) => request({ url: prefix, params }),
  retrieve: (id: number) => request({ url: `${prefix}${id}/` }),
  field_permission: () => request({ url: `${prefix}field_permission/` }),
  create: (data: any) => request({ url: prefix, method: 'post', data }),
  update: (id: number, data: any) => request({ url: `${prefix}${id}/`, method: 'patch', data }),
  destroy: (id: number) => request({ url: `${prefix}${id}/`, method: 'delete' }),
};

export function payload(form: any, permissions: any) {
  const keys = [
    'name',
    'gender',
    'customer',
    'direct_supervisor',
    'title',
    'email',
    'mobile',
    'address',
    'enabled',
    'is_default',
  ];
  const mode = form.id ? 'is_update' : 'is_create';
  const result: any = Object.fromEntries(
    keys
      .filter((key) => !(form.id && key === 'number') && permissions[key]?.[mode] && form[key] !== undefined)
      .map((key) => [key, form[key]])
  );
  return result;
}
