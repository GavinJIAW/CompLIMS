// FastCrud keeps form ownership. Only reviewed CRUD input fields cross the
// request boundary; backend canonical/field policy remains authoritative.
const fields: Record<string, string[]> = Object.fromEntries(Object.entries({
  menu: 'description icon name sort is_link link_url is_catalog web_path component component_name status cache visible is_iframe is_affix parent',
  menu_button: 'name value api method menu sort description',
  role: 'name key sort status description',
  dept: 'name key sort owner phone email status parent description',
  user: 'username name email mobile avatar gender user_type is_active',
  dictionary: 'label value type color is_value status sort remark parent description',
  area: 'name code enable pcode description',
  api_white_list: 'url method enable_datasource description',
  system_config: 'title key value sort status data_options form_item_type rule placeholder setting parent description',
  message_center: 'title content target_type target_user target_dept target_role description',
  role_menu_button_permission: 'role menu_button data_range dept description',
  role_menu_permission: 'role menu description',
  column: 'model field_name title menu description',
}).map(([resource, names]) => [resource, names.split(' ')]));

export function projectCrudPayload(config: any) {
  const method = String(config.method || 'get').toLowerCase();
  const match = /^\/api\/system\/([a-z_]+)\/(?:\d+\/)?$/.exec(config.url || '');
  if (!match || !['post', 'put', 'patch'].includes(method) || !fields[match[1]]) return config;
  const allowed = new Set(fields[match[1]]);
  if (match[1] === 'user' && method === 'post') allowed.add('password');
  const project = (value: any) => value && typeof value === 'object'
    ? Object.fromEntries(Object.entries(value).filter(([key]) => allowed.has(key))) : value;
  return { ...config, data: Array.isArray(config.data) ? config.data.map(project) : project(config.data) };
}

export function changesAuthorization(config: any): boolean {
  return ['post', 'put', 'patch', 'delete'].includes(String(config.method).toLowerCase()) &&
    /^\/api\/system\/(role|role_menu_permission|role_menu_button_permission|menu_button|column|api_white_list)\//.test(config.url || '');
}
