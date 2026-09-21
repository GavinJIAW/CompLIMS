import { h } from 'vue';
import { compute, dict } from '@fast-crud/fast-crud';
import { auth } from '/@/utils/authFunction';
import { api, payload } from './api';
import DefaultsEditor from '../shared/DefaultsEditor.vue';
import ProductCostPackagesEditor from './components/ProductCostPackagesEditor.vue';
import MasterSelect from '../../shared/MasterSelect.vue';
import { api as serviceApi } from '/@/views/lims/catalog/service/api';

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
        service: {
          title: '技术服务',
          type: 'input',
          column: { show: !!permissions.service?.is_query, minWidth: 150 },
          search: { show: false },
          form: {
            col: { span: 12 },
            component: { disabled: compute((scope: any) => disabled(scope, 'service')) },
            rules: [{ required: true, message: '请填写技术服务' }],
            render: (scope: any) =>
              h(MasterSelect, {
                loadList: serviceApi.list,
                loadOne: serviceApi.retrieve,
                modelValue: scope.form.service,
                'onUpdate:modelValue': (value: any) => {
                  scope.form.service = value;
                },
                disabled: disabled(scope, 'service'),
              }),
          },
          addForm: { show: !!permissions.service?.is_create },
          editForm: { show: !!permissions.service?.is_update || !!permissions.service?.is_query },
          viewForm: { show: !!permissions.service?.is_query },
        },
        requirement_defaults: {
          title: '需求默认值',
          type: 'input',
          column: { show: false, minWidth: 150 },
          search: { show: false },
          form: {
            col: { span: 24 },
            component: { disabled: compute((scope: any) => disabled(scope, 'requirement_defaults')) },
            value: {},
            render: (scope: any) =>
              h(DefaultsEditor, {
                modelValue: scope.form.requirement_defaults,
                'onUpdate:modelValue': (value: any) => (scope.form.requirement_defaults = value),
                disabled: disabled(scope, 'requirement_defaults'),
                serviceId: scope.form.service,
              }),
          },
          addForm: { show: !!permissions.requirement_defaults?.is_create },
          editForm: {
            show: !!permissions.requirement_defaults?.is_update || !!permissions.requirement_defaults?.is_query,
          },
          viewForm: { show: !!permissions.requirement_defaults?.is_query },
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
        reference_price: {
          title: '参考售价 (RMB)',
          type: 'input',
          column: { show: !!permissions.reference_price?.is_query, minWidth: 150 },
          search: { show: false },
          form: {
            col: { span: 12 },
            component: {
              disabled: compute((scope: any) => disabled(scope, 'reference_price')),
              placeholder: '非负，最多 2 位小数',
            },
            rules: [{ required: true, message: '请填写参考售价 (RMB)' }],
          },
          addForm: { show: !!permissions.reference_price?.is_create },
          editForm: { show: !!permissions.reference_price?.is_update || !!permissions.reference_price?.is_query },
          viewForm: { show: !!permissions.reference_price?.is_query },
        },
        packages: {
          title: '成本包组合',
          type: 'input',
          column: { show: false, minWidth: 150 },
          search: { show: false },
          form: {
            col: { span: 24 },
            component: { disabled: compute((scope: any) => disabled(scope, 'packages')) },
            value: [],
            render: (scope: any) =>
              h(ProductCostPackagesEditor, {
                modelValue: scope.form.packages,
                'onUpdate:modelValue': (value: any) => (scope.form.packages = value),
                disabled: disabled(scope, 'packages'),
                permissions: permissions._rows,
                showStandardCost: !!permissions.standard_cost?.is_query,
                showReferencePrice: !!permissions.reference_price?.is_query,
              }),
          },
          addForm: { show: !!permissions.packages?.is_create },
          editForm: { show: !!permissions.packages?.is_update || !!permissions.packages?.is_query },
          viewForm: { show: !!permissions.packages?.is_query },
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
      },
      request: {
        pageRequest: (query: any) => api.list(query),
        addRequest: ({ form }: any) => api.create(payload(form, permissions)),
        editRequest: ({ form, row }: any) => api.update(row.id, payload({ ...form, id: row.id }, permissions)),
        delRequest: ({ row }: any) => api.destroy(row.id),
      },
      actionbar: { buttons: { add: { show: auth('product:Create') && !!permissions.number?.is_create } } },
      rowHandle: {
        width: 210,
        buttons: {
          view: { show: auth('product:Retrieve') },
          edit: { show: auth('product:Update') },
          remove: { show: auth('product:Delete') },
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
              columns: [
                'number',
                'internal_name',
                'name',
                'name_en',
                'service',
                'unit',
                'reference_price',
                'enabled',
                'description',
              ],
            },
            tab1: { label: '需求默认值', columns: ['requirement_defaults'] },
            tab2: { label: '成本配置', columns: ['packages', 'standard_cost'] },
          },
        },
      },
    },
  };
}
