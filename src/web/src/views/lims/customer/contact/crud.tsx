import { h } from 'vue';
import { compute, dict } from '@fast-crud/fast-crud';
import { auth } from '/@/utils/authFunction';
import { api, payload } from './api';
import MasterSelect from '../../shared/MasterSelect.vue';
import { api as customerApi } from '/@/views/lims/customer/customer/api';
import { api as contactApi } from '/@/views/lims/customer/contact/api';

export function createCrudOptions({ context }: any) {
  const permissions = context.permissions || {};
  const disabled = (scope: any, key: string) =>
    scope.mode === 'view' || !permissions[key]?.[scope.form.id ? 'is_update' : 'is_create'];
  return {
    crudOptions: {
      columns: {
        id: { title: 'ID', type: 'number', column: { show: false }, form: { show: false } },
        name: {
          title: '名称',
          type: 'input',
          column: { show: !!permissions.name?.is_query, minWidth: 150 },
          search: { show: false },
          form: {
            col: { span: 12 },
            component: { disabled: compute((scope: any) => disabled(scope, 'name')) },
            rules: [{ required: true, message: '请填写名称' }],
          },
          addForm: { show: !!permissions.name?.is_create },
          editForm: { show: !!permissions.name?.is_update || !!permissions.name?.is_query },
          viewForm: { show: !!permissions.name?.is_query },
        },
        gender: {
          title: '性别',
          column: { show: !!permissions.gender?.is_query, minWidth: 150 },
          search: { show: !!permissions.gender?.is_query, component: { clearable: true } },
          form: {
            col: { span: 12 },
            component: { disabled: compute((scope: any) => disabled(scope, 'gender')) },
            value: 0,
          },
          addForm: { show: !!permissions.gender?.is_create },
          editForm: { show: !!permissions.gender?.is_update || !!permissions.gender?.is_query },
          viewForm: { show: !!permissions.gender?.is_query },
          type: 'dict-select',
          dict: dict({
            data: [
              { value: 0, label: '未知' },
              { value: 1, label: '男' },
              { value: 2, label: '女' },
            ],
          }),
        },
        customer: {
          title: '关联客户',
          type: 'input',
          column: { show: !!permissions.customer?.is_query, minWidth: 150 },
          search: {
            show: !!permissions.customer?.is_query,
            render: (scope: any) =>
              h(MasterSelect, {
                loadList: customerApi.list,
                loadOne: customerApi.retrieve,
                includeDisabled: true,
                modelValue: scope.form.customer,
                'onUpdate:modelValue': (value: any) => (scope.form.customer = value),
              }),
          },
          form: {
            col: { span: 12 },
            component: { disabled: compute((scope: any) => disabled(scope, 'customer')) },
            rules: [{ required: true, message: '请填写关联客户' }],
            render: (scope: any) =>
              h(MasterSelect, {
                loadList: customerApi.list,
                loadOne: customerApi.retrieve,
                modelValue: scope.form.customer,
                'onUpdate:modelValue': (value: any) => {
                  scope.form.customer = value;
                  scope.form.direct_supervisor = null;
                },
                disabled: disabled(scope, 'customer'),
              }),
          },
          addForm: { show: !!permissions.customer?.is_create },
          editForm: { show: !!permissions.customer?.is_update || !!permissions.customer?.is_query },
          viewForm: { show: !!permissions.customer?.is_query },
        },
        direct_supervisor: {
          title: '直接上级',
          type: 'input',
          column: { show: !!permissions.direct_supervisor?.is_query, minWidth: 150 },
          search: { show: false },
          form: {
            col: { span: 24 },
            component: { disabled: compute((scope: any) => disabled(scope, 'direct_supervisor')) },
            render: (scope: any) =>
              h(MasterSelect, {
                loadList: contactApi.list,
                loadOne: contactApi.retrieve,
                modelValue: scope.form.direct_supervisor,
                'onUpdate:modelValue': (value: any) => {
                  scope.form.direct_supervisor = value;
                },
                disabled: disabled(scope, 'direct_supervisor') || !scope.form.customer,
                label: (row: any) => row.name,
                params: { customer: scope.form.customer },
                excludeId: scope.form.id,
                includeDisabled: true,
              }),
          },
          addForm: { show: !!permissions.direct_supervisor?.is_create },
          editForm: { show: !!permissions.direct_supervisor?.is_update || !!permissions.direct_supervisor?.is_query },
          viewForm: { show: !!permissions.direct_supervisor?.is_query },
        },
        title: {
          title: '职务',
          type: 'input',
          column: { show: !!permissions.title?.is_query, minWidth: 150 },
          search: { show: false },
          form: { col: { span: 12 }, component: { disabled: compute((scope: any) => disabled(scope, 'title')) } },
          addForm: { show: !!permissions.title?.is_create },
          editForm: { show: !!permissions.title?.is_update || !!permissions.title?.is_query },
          viewForm: { show: !!permissions.title?.is_query },
        },
        email: {
          title: '邮箱',
          type: 'input',
          column: { show: !!permissions.email?.is_query, minWidth: 150 },
          search: { show: false },
          form: { col: { span: 12 }, component: { disabled: compute((scope: any) => disabled(scope, 'email')) } },
          addForm: { show: !!permissions.email?.is_create },
          editForm: { show: !!permissions.email?.is_update || !!permissions.email?.is_query },
          viewForm: { show: !!permissions.email?.is_query },
        },
        mobile: {
          title: '手机号码',
          type: 'input',
          column: { show: !!permissions.mobile?.is_query, minWidth: 150 },
          search: { show: false },
          form: { col: { span: 12 }, component: { disabled: compute((scope: any) => disabled(scope, 'mobile')) } },
          addForm: { show: !!permissions.mobile?.is_create },
          editForm: { show: !!permissions.mobile?.is_update || !!permissions.mobile?.is_query },
          viewForm: { show: !!permissions.mobile?.is_query },
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
        is_default: {
          title: '默认联系人',
          column: { show: !!permissions.is_default?.is_query, minWidth: 150 },
          search: { show: !!permissions.is_default?.is_query, component: { clearable: true } },
          form: {
            col: { span: 12 },
            component: { disabled: compute((scope: any) => disabled(scope, 'is_default')) },
            value: false,
          },
          addForm: { show: !!permissions.is_default?.is_create },
          editForm: { show: !!permissions.is_default?.is_update || !!permissions.is_default?.is_query },
          viewForm: { show: !!permissions.is_default?.is_query },
          type: 'dict-switch',
          dict: dict({
            data: [
              { value: true, label: '是' },
              { value: false, label: '否' },
            ],
          }),
        },
      },
      request: {
        pageRequest: (query: any) => api.list(query),
        addRequest: ({ form }: any) => api.create(payload(form, permissions)),
        editRequest: ({ form, row }: any) => api.update(row.id, payload({ ...form, id: row.id }, permissions)),
        delRequest: ({ row }: any) => api.destroy(row.id),
      },
      actionbar: { buttons: { add: { show: auth('contact:Create') && !!permissions.name?.is_create } } },
      rowHandle: {
        width: 210,
        buttons: {
          view: { show: auth('contact:Retrieve') },
          edit: { show: auth('contact:Update') },
          remove: { show: auth('contact:Delete') },
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
