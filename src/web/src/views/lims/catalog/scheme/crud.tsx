import { h } from 'vue';
import { compute, dict } from '@fast-crud/fast-crud';
import { auth } from '/@/utils/authFunction';
import { api, payload } from './api';
import SchemeItemsEditor from './components/SchemeItemsEditor.vue';

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
        internal_name: {
          title: '内部简称',
          type: 'input',
          column: { show: !!permissions.internal_name?.is_query, minWidth: 150 },
          search: { show: !!permissions.internal_name?.is_query, component: { clearable: true } },
          form: {
            col: { span: 12 },
            component: { disabled: compute((scope: any) => disabled(scope, 'internal_name')) },
          },
          addForm: { show: !!permissions.internal_name?.is_create },
          editForm: { show: !!permissions.internal_name?.is_update || !!permissions.internal_name?.is_query },
          viewForm: { show: !!permissions.internal_name?.is_query },
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
        name_en: {
          title: '英文名称',
          type: 'input',
          column: { show: !!permissions.name_en?.is_query, minWidth: 150 },
          search: { show: !!permissions.name_en?.is_query, component: { clearable: true } },
          form: { col: { span: 12 }, component: { disabled: compute((scope: any) => disabled(scope, 'name_en')) } },
          addForm: { show: !!permissions.name_en?.is_create },
          editForm: { show: !!permissions.name_en?.is_update || !!permissions.name_en?.is_query },
          viewForm: { show: !!permissions.name_en?.is_query },
        },
        items: {
          title: '组合明细',
          type: 'input',
          column: { show: false, minWidth: 150 },
          search: { show: false },
          form: {
            col: { span: 24 },
            component: { disabled: compute((scope: any) => disabled(scope, 'items')) },
            value: [],
            render: (scope: any) =>
              h(SchemeItemsEditor, {
                modelValue: scope.form.items,
                'onUpdate:modelValue': (value: any) => (scope.form.items = value),
                disabled: disabled(scope, 'items'),
                permissions: permissions._rows,
                showStandardCost: !!permissions.standard_cost?.is_query,
                showReferencePrice: !!permissions.reference_price?.is_query,
              }),
          },
          addForm: { show: !!permissions.items?.is_create },
          editForm: { show: !!permissions.items?.is_update || !!permissions.items?.is_query },
          viewForm: { show: !!permissions.items?.is_query },
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
        standard_cost: {
          title: '当前标准成本 (RMB)',
          type: 'input',
          column: { show: !!permissions.standard_cost?.is_query, minWidth: 150 },
          form: { show: !!permissions.standard_cost?.is_query, component: { disabled: true } },
          addForm: { show: false },
          search: { show: false },
        },
        reference_price: {
          title: '参考售价 (RMB)',
          type: 'input',
          column: { show: !!permissions.reference_price?.is_query, minWidth: 150 },
          form: { show: !!permissions.reference_price?.is_query, component: { disabled: true } },
          addForm: { show: false },
          search: { show: false },
        },
      },
      request: {
        pageRequest: (query: any) => api.list(query),
        addRequest: ({ form }: any) => api.create(payload(form, permissions)),
        editRequest: ({ form, row }: any) => api.update(row.id, payload({ ...form, id: row.id }, permissions)),
        delRequest: ({ row }: any) => api.destroy(row.id),
      },
      actionbar: { buttons: { add: { show: auth('scheme:Create') && !!permissions.number?.is_create } } },
      rowHandle: {
        width: 300,
        buttons: {
          view: { show: auth('scheme:Retrieve') },
          edit: { show: auth('scheme:Update') },
          remove: { show: auth('scheme:Delete') },
        },
      },
      form: {
        wrapper: {
          is: 'el-drawer',
          size: 'min(1400px, 100vw)',
          style: { maxWidth: '100vw' },
          buttons: { cancel: { show: true, text: '取消' }, ok: { text: '保存' } },
        },
        col: { span: 12 },
        group: {
          groupType: 'tabs',
          groups: {
            tab0: {
              label: '基本信息',
              columns: ['number', 'internal_name', 'name', 'name_en', 'enabled', 'description'],
            },
            tab1: { label: '方案明细', columns: ['items', 'standard_cost', 'reference_price'] },
          },
        },
      },
    },
  };
}
