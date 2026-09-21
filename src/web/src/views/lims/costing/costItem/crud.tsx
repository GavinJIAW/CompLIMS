import { h } from 'vue';
import { compute, dict } from '@fast-crud/fast-crud';
import { auth } from '/@/utils/authFunction';
import { api, payload } from './api';
import ObjectEditor from '../../shared/ObjectEditor.vue';
import MasterSelect from '../../shared/MasterSelect.vue';
import { api as cost_typeApi } from '/@/views/lims/costing/costType/api';

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
        cost_type: {
          title: '成本类型',
          column: { show: !!permissions.cost_type?.is_query, minWidth: 150 },
          dict: dict({ url: '/api/lims/cost_type/', value: 'id', label: 'name', params: { limit: 1000 } }),
          search: {
            show: !!permissions.cost_type?.is_query,
            render: (scope: any) =>
              h(MasterSelect, {
                loadList: cost_typeApi.list,
                loadOne: cost_typeApi.retrieve,
                includeDisabled: true,
                modelValue: scope.form.cost_type,
                'onUpdate:modelValue': (value: any) => (scope.form.cost_type = value),
              }),
          },
          form: {
            col: { span: 12 },
            component: { disabled: compute((scope: any) => disabled(scope, 'cost_type')) },
            rules: [{ required: true, message: '请填写成本类型' }],
            render: (scope: any) =>
              h(MasterSelect, {
                loadList: cost_typeApi.list,
                loadOne: cost_typeApi.retrieve,
                modelValue: scope.form.cost_type,
                'onUpdate:modelValue': (value: any) => {
                  scope.form.cost_type = value;
                },
                disabled: disabled(scope, 'cost_type'),
                label: (row: any) => row.name,
              }),
          },
          addForm: { show: !!permissions.cost_type?.is_create },
          editForm: { show: !!permissions.cost_type?.is_update || !!permissions.cost_type?.is_query },
          viewForm: { show: !!permissions.cost_type?.is_query },
          type: 'dict-select',
        },
        unit_cost: {
          title: '单位成本 (RMB)',
          type: 'input',
          column: { show: !!permissions.unit_cost?.is_query, minWidth: 150 },
          search: { show: false },
          form: {
            col: { span: 12 },
            component: {
              disabled: compute((scope: any) => disabled(scope, 'unit_cost')),
              placeholder: '非负，最多 2 位小数',
            },
            rules: [{ required: true, message: '请填写单位成本 (RMB)' }],
          },
          addForm: { show: !!permissions.unit_cost?.is_create },
          editForm: { show: !!permissions.unit_cost?.is_update || !!permissions.unit_cost?.is_query },
          viewForm: { show: !!permissions.unit_cost?.is_query },
        },
        unit: {
          title: '计价单位',
          type: 'input',
          column: { show: !!permissions.unit?.is_query, minWidth: 150 },
          search: { show: false },
          form: {
            col: { span: 12 },
            component: { disabled: compute((scope: any) => disabled(scope, 'unit')) },
            rules: [{ required: true, message: '请填写计价单位' }],
          },
          addForm: { show: !!permissions.unit?.is_create },
          editForm: { show: !!permissions.unit?.is_update || !!permissions.unit?.is_query },
          viewForm: { show: !!permissions.unit?.is_query },
        },
        basis_data: {
          title: '成本依据',
          type: 'input',
          column: { show: false, minWidth: 150 },
          search: { show: false },
          form: {
            col: { span: 24 },
            component: { disabled: compute((scope: any) => disabled(scope, 'basis_data')) },
            value: {},
            render: (scope: any) =>
              h(ObjectEditor, {
                modelValue: scope.form.basis_data,
                'onUpdate:modelValue': (value: any) => (scope.form.basis_data = value),
                disabled: disabled(scope, 'basis_data'),
              }),
          },
          addForm: { show: !!permissions.basis_data?.is_create },
          editForm: { show: !!permissions.basis_data?.is_update || !!permissions.basis_data?.is_query },
          viewForm: { show: !!permissions.basis_data?.is_query },
        },
        enabled: {
          title: '启用',
          column: { show: !!permissions.enabled?.is_query, minWidth: 150 },
          search: { show: false },
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
      actionbar: { buttons: { add: { show: auth('cost_item:Create') && !!permissions.number?.is_create } } },
      rowHandle: {
        width: 210,
        buttons: {
          view: { show: auth('cost_item:Retrieve') },
          edit: { show: auth('cost_item:Update') },
          remove: { show: auth('cost_item:Delete') },
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
