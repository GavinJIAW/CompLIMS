import { h } from 'vue';
import { compute, dict } from '@fast-crud/fast-crud';
import { auth } from '/@/utils/authFunction';
import { api, payload } from './api';

export function createCrudOptions({ context }: any) {
  const permissions = context.permissions || {};
  const disabled = (scope: any, key: string) =>
    scope.mode === 'view' || !permissions[key]?.[scope.form.id ? 'is_update' : 'is_create'];
  return {
    crudOptions: {
      columns: {
        id: { title: 'ID', type: 'number', column: { show: false }, form: { show: false } },
        number: {
          title: '编号',
          type: 'input',
          column: { show: !!permissions.number?.is_query, minWidth: 150 },
          search: { show: !!permissions.number?.is_query, component: { clearable: true } },
          form: {
            col: { span: 12 },
            component: { disabled: compute((scope: any) => disabled(scope, 'number')) },
            rules: [{ required: true, message: '请填写编号' }],
          },
          addForm: { show: !!permissions.number?.is_create },
          editForm: {
            show: !!permissions.number?.is_update || !!permissions.number?.is_query,
            component: { disabled: true },
          },
          viewForm: { show: !!permissions.number?.is_query },
        },
        name: {
          title: '名称',
          type: 'input',
          column: { show: !!permissions.name?.is_query, minWidth: 150 },
          search: { show: !!permissions.name?.is_query, component: { clearable: true } },
          form: {
            col: { span: 12 },
            component: { disabled: compute((scope: any) => disabled(scope, 'name')) },
            rules: [{ required: true, message: '请填写名称' }],
          },
          addForm: { show: !!permissions.name?.is_create },
          editForm: { show: !!permissions.name?.is_update || !!permissions.name?.is_query },
          viewForm: { show: !!permissions.name?.is_query },
        },
        short_name: {
          title: '客户简称',
          type: 'input',
          column: { show: !!permissions.short_name?.is_query, minWidth: 150 },
          search: { show: !!permissions.short_name?.is_query, component: { clearable: true } },
          form: { col: { span: 12 }, component: { disabled: compute((scope: any) => disabled(scope, 'short_name')) } },
          addForm: { show: !!permissions.short_name?.is_create },
          editForm: { show: !!permissions.short_name?.is_update || !!permissions.short_name?.is_query },
          viewForm: { show: !!permissions.short_name?.is_query },
        },
        tax_number: {
          title: '税号',
          type: 'input',
          column: { show: !!permissions.tax_number?.is_query, minWidth: 150 },
          search: { show: false },
          form: { col: { span: 12 }, component: { disabled: compute((scope: any) => disabled(scope, 'tax_number')) } },
          addForm: { show: !!permissions.tax_number?.is_create },
          editForm: { show: !!permissions.tax_number?.is_update || !!permissions.tax_number?.is_query },
          viewForm: { show: !!permissions.tax_number?.is_query },
        },
        address: {
          title: '联系地址',
          type: 'input',
          column: { show: !!permissions.address?.is_query, minWidth: 150 },
          search: { show: false },
          form: {
            col: { span: 12 },
            component: { disabled: compute((scope: any) => disabled(scope, 'address')), type: 'textarea', rows: 3 },
          },
          addForm: { show: !!permissions.address?.is_create },
          editForm: { show: !!permissions.address?.is_update || !!permissions.address?.is_query },
          viewForm: { show: !!permissions.address?.is_query },
        },
        enabled: {
          title: '启用',
          column: { show: !!permissions.enabled?.is_query, minWidth: 150 },
          search: { show: !!permissions.enabled?.is_query, component: { clearable: true } },
          form: {
            col: { span: 12 },
            component: { disabled: compute((scope: any) => disabled(scope, 'enabled')) },
            value: true,
          },
          addForm: { show: !!permissions.enabled?.is_create },
          editForm: { show: !!permissions.enabled?.is_update || !!permissions.enabled?.is_query },
          viewForm: { show: !!permissions.enabled?.is_query },
          type: 'dict-switch',
          dict: dict({
            data: [
              { value: true, label: '是' },
              { value: false, label: '否' },
            ],
          }),
        },
        description: {
          title: '说明',
          type: 'input',
          column: { show: false, minWidth: 150 },
          search: { show: false },
          form: {
            col: { span: 12 },
            component: { disabled: compute((scope: any) => disabled(scope, 'description')), type: 'textarea', rows: 3 },
          },
          addForm: { show: !!permissions.description?.is_create },
          editForm: { show: !!permissions.description?.is_update || !!permissions.description?.is_query },
          viewForm: { show: !!permissions.description?.is_query },
        },
      },
      request: {
        pageRequest: (query: any) => api.list(query),
        addRequest: ({ form }: any) => api.create(payload(form, permissions)),
        editRequest: ({ form, row }: any) => api.update(row.id, payload({ ...form, id: row.id }, permissions)),
        delRequest: ({ row }: any) => api.destroy(row.id),
      },
      actionbar: { buttons: { add: { show: auth('customer:Create') && !!permissions.number?.is_create } } },
      rowHandle: {
        width: 300,
        buttons: {
          view: { show: auth('customer:Retrieve') },
          edit: { show: auth('customer:Update') },
          remove: { show: auth('customer:Delete') },
        },
      },
      form: {
        wrapper: {
          is: 'el-drawer',
          size: 'min(800px, 100vw)',
          style: { maxWidth: '100vw' },
          buttons: { cancel: { show: true, text: '取消' }, ok: { text: '保存' } },
        },
        col: { span: 12 },
      },
    },
  };
}
