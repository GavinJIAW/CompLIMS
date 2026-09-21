import { h } from 'vue';
import { compute, dict } from '@fast-crud/fast-crud';
import { auth } from '/@/utils/authFunction';
import { api, payload } from './api';
import TemplateEditor from '../shared/TemplateEditor.vue';

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
        service_type: {
          title: '服务分类',
          type: 'input',
          column: { show: !!permissions.service_type?.is_query, minWidth: 150 },
          search: { show: !!permissions.service_type?.is_query, component: { clearable: true } },
          form: {
            col: { span: 12 },
            component: { disabled: compute((scope: any) => disabled(scope, 'service_type')) },
          },
          addForm: { show: !!permissions.service_type?.is_create },
          editForm: { show: !!permissions.service_type?.is_update || !!permissions.service_type?.is_query },
          viewForm: { show: !!permissions.service_type?.is_query },
        },
        requirement_template: {
          title: '需求模板',
          type: 'input',
          column: { show: false, minWidth: 150 },
          search: { show: false },
          form: {
            col: { span: 24 },
            component: { disabled: compute((scope: any) => disabled(scope, 'requirement_template')) },
            value: [],
            render: (scope: any) =>
              h(TemplateEditor, {
                modelValue: scope.form.requirement_template,
                'onUpdate:modelValue': (value: any) => (scope.form.requirement_template = value),
                disabled: disabled(scope, 'requirement_template'),
              }),
          },
          addForm: { show: !!permissions.requirement_template?.is_create },
          editForm: {
            show: !!permissions.requirement_template?.is_update || !!permissions.requirement_template?.is_query,
          },
          viewForm: { show: !!permissions.requirement_template?.is_query },
        },
        result_template: {
          title: '结果模板',
          type: 'input',
          column: { show: false, minWidth: 150 },
          search: { show: false },
          form: {
            col: { span: 24 },
            component: { disabled: compute((scope: any) => disabled(scope, 'result_template')) },
            value: [],
            render: (scope: any) =>
              h(TemplateEditor, {
                modelValue: scope.form.result_template,
                'onUpdate:modelValue': (value: any) => (scope.form.result_template = value),
                disabled: disabled(scope, 'result_template'),
              }),
          },
          addForm: { show: !!permissions.result_template?.is_create },
          editForm: { show: !!permissions.result_template?.is_update || !!permissions.result_template?.is_query },
          viewForm: { show: !!permissions.result_template?.is_query },
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
      actionbar: { buttons: { add: { show: auth('service:Create') && !!permissions.number?.is_create } } },
      rowHandle: {
        width: 210,
        buttons: {
          view: { show: auth('service:Retrieve') },
          edit: { show: auth('service:Update') },
          remove: { show: auth('service:Delete') },
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
              columns: ['number', 'internal_name', 'name', 'name_en', 'service_type', 'enabled', 'description'],
            },
            tab1: { label: '需求模板', columns: ['requirement_template'] },
            tab2: { label: '结果模板', columns: ['result_template'] },
          },
        },
      },
    },
  };
}
