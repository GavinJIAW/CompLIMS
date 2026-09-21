import { h } from 'vue';
import { compute, dict } from '@fast-crud/fast-crud';
import { auth } from '/@/utils/authFunction';
import { api, payload } from './api';
import CustomerSnapshot from '../shared/CustomerSnapshot.vue';
import SchemeEditor from '../shared/SchemeEditor.vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import PriceSummary from '../shared/PriceSummary.vue';

export function createCrudOptions({ context }: any) {
  const permissions = context.permissions || {};
  const disabled = (scope: any, key: string) =>
    scope.mode === 'view' ||
    (scope.form.status && scope.form.status !== 'DRAFT') ||
    !permissions[key]?.[scope.form.id ? 'is_update' : 'is_create'];
  const actions = {
    send: {
      text: '发送报价',
      show: compute(({ form }: any) => !!form?.id && form.status === 'DRAFT' && auth('quotation:Send')),
      click: async (scope: any) => {
        try {
          await ElMessageBox.confirm('确认发送报价？', '发送报价', { type: 'warning' });
          const result = await api.send(scope.form.id);
          scope.setFormData(result.data);
          await context.refresh();
          ElMessage.success('操作成功');
        } catch (error) {
          if (error !== 'cancel' && error !== 'close') throw error;
        }
      },
    },
    accept: {
      text: '接受',
      show: compute(({ form }: any) => !!form?.id && form.status === 'SENT' && auth('quotation:Accept')),
      click: async (scope: any) => {
        try {
          await ElMessageBox.confirm('确认接受？', '接受', { type: 'warning' });
          const result = await api.accept(scope.form.id);
          scope.setFormData(result.data);
          await context.refresh();
          ElMessage.success('操作成功');
        } catch (error) {
          if (error !== 'cancel' && error !== 'close') throw error;
        }
      },
    },
    reject: {
      text: '拒绝',
      show: compute(({ form }: any) => !!form?.id && form.status === 'SENT' && auth('quotation:Reject')),
      click: async (scope: any) => {
        try {
          await ElMessageBox.confirm('确认拒绝？', '拒绝', { type: 'warning' });
          const result = await api.reject(scope.form.id);
          scope.setFormData(result.data);
          await context.refresh();
          ElMessage.success('操作成功');
        } catch (error) {
          if (error !== 'cancel' && error !== 'close') throw error;
        }
      },
    },
    void: {
      text: '作废',
      show: compute(({ form }: any) => !!form?.id && form.status === 'SENT' && auth('quotation:Void')),
      click: async (scope: any) => {
        try {
          await ElMessageBox.confirm('确认作废？', '作废', { type: 'warning' });
          const result = await api.void(scope.form.id);
          scope.setFormData(result.data);
          await context.refresh();
          ElMessage.success('操作成功');
        } catch (error) {
          if (error !== 'cancel' && error !== 'close') throw error;
        }
      },
    },
    createContract: {
      text: '创建合同',
      show: compute(
        ({ form }: any) =>
          !!form?.id && form.status === 'ACCEPTED' && auth('quotation:CreateContract') && auth('contract:Create')
      ),
      click: async (scope: any) => {
        context.openConversion(scope.form);
      },
    },
  };
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
        quotation_date: {
          title: '报价日期',
          type: 'input',
          column: { show: !!permissions.quotation_date?.is_query, minWidth: 150 },
          search: { show: !!permissions.quotation_date?.is_query, component: { clearable: true } },
          form: {
            col: { span: 12 },
            component: {
              disabled: compute((scope: any) => disabled(scope, 'quotation_date')),
              name: 'el-date-picker',
              valueFormat: 'YYYY-MM-DD',
            },
            rules: [{ required: true, message: '请填写报价日期' }],
          },
          addForm: { show: !!permissions.quotation_date?.is_create },
          editForm: { show: !!permissions.quotation_date?.is_update || !!permissions.quotation_date?.is_query },
          viewForm: { show: !!permissions.quotation_date?.is_query },
        },
        valid_until: {
          title: '有效期至',
          type: 'input',
          column: { show: !!permissions.valid_until?.is_query, minWidth: 150 },
          search: { show: false },
          form: {
            col: { span: 12 },
            component: {
              disabled: compute((scope: any) => disabled(scope, 'valid_until')),
              name: 'el-date-picker',
              valueFormat: 'YYYY-MM-DD',
            },
          },
          addForm: { show: !!permissions.valid_until?.is_create },
          editForm: { show: !!permissions.valid_until?.is_update || !!permissions.valid_until?.is_query },
          viewForm: { show: !!permissions.valid_until?.is_query },
        },
        customer: {
          title: '关联客户',
          type: 'input',
          column: { show: false, minWidth: 150 },
          search: { show: false },
          form: {
            col: { span: 24 },
            component: { disabled: compute((scope: any) => disabled(scope, 'customer')) },
            rules: [{ required: true, message: '请填写关联客户' }],
            render: (scope: any) =>
              h(CustomerSnapshot, { form: scope.form, permissions, disabled: disabled(scope, 'customer') }),
          },
          addForm: { show: !!permissions.customer?.is_create },
          editForm: { show: !!permissions.customer?.is_update || !!permissions.customer?.is_query },
          viewForm: { show: !!permissions.customer?.is_query },
        },
        customer_name_snapshot: {
          title: '客户名称快照',
          type: 'input',
          column: { show: !!permissions.customer_name_snapshot?.is_query, minWidth: 150 },
          search: { show: !!permissions.customer_name_snapshot?.is_query, component: { clearable: true } },
          form: {
            col: { span: 12 },
            component: { disabled: compute((scope: any) => disabled(scope, 'customer_name_snapshot')) },
          },
          addForm: { show: !!permissions.customer_name_snapshot?.is_create },
          editForm: {
            show: !!permissions.customer_name_snapshot?.is_update || !!permissions.customer_name_snapshot?.is_query,
          },
          viewForm: { show: !!permissions.customer_name_snapshot?.is_query },
        },
        customer_tax_number_snapshot: {
          title: '客户税号快照',
          type: 'input',
          column: { show: !!permissions.customer_tax_number_snapshot?.is_query, minWidth: 150 },
          search: { show: false },
          form: {
            col: { span: 12 },
            component: { disabled: compute((scope: any) => disabled(scope, 'customer_tax_number_snapshot')) },
          },
          addForm: { show: !!permissions.customer_tax_number_snapshot?.is_create },
          editForm: {
            show:
              !!permissions.customer_tax_number_snapshot?.is_update ||
              !!permissions.customer_tax_number_snapshot?.is_query,
          },
          viewForm: { show: !!permissions.customer_tax_number_snapshot?.is_query },
        },
        customer_address_snapshot: {
          title: '客户地址快照',
          type: 'input',
          column: { show: !!permissions.customer_address_snapshot?.is_query, minWidth: 150 },
          search: { show: false },
          form: {
            col: { span: 12 },
            component: {
              disabled: compute((scope: any) => disabled(scope, 'customer_address_snapshot')),
              type: 'textarea',
              rows: 3,
            },
          },
          addForm: { show: !!permissions.customer_address_snapshot?.is_create },
          editForm: {
            show:
              !!permissions.customer_address_snapshot?.is_update || !!permissions.customer_address_snapshot?.is_query,
          },
          viewForm: { show: !!permissions.customer_address_snapshot?.is_query },
        },
        contact_name_snapshot: {
          title: '联系人快照',
          type: 'input',
          column: { show: !!permissions.contact_name_snapshot?.is_query, minWidth: 150 },
          search: { show: false },
          form: {
            col: { span: 12 },
            component: { disabled: compute((scope: any) => disabled(scope, 'contact_name_snapshot')) },
          },
          addForm: { show: !!permissions.contact_name_snapshot?.is_create },
          editForm: {
            show: !!permissions.contact_name_snapshot?.is_update || !!permissions.contact_name_snapshot?.is_query,
          },
          viewForm: { show: !!permissions.contact_name_snapshot?.is_query },
        },
        contact_mobile_snapshot: {
          title: '手机号码快照',
          type: 'input',
          column: { show: !!permissions.contact_mobile_snapshot?.is_query, minWidth: 150 },
          search: { show: false },
          form: {
            col: { span: 12 },
            component: { disabled: compute((scope: any) => disabled(scope, 'contact_mobile_snapshot')) },
          },
          addForm: { show: !!permissions.contact_mobile_snapshot?.is_create },
          editForm: {
            show: !!permissions.contact_mobile_snapshot?.is_update || !!permissions.contact_mobile_snapshot?.is_query,
          },
          viewForm: { show: !!permissions.contact_mobile_snapshot?.is_query },
        },
        contact_email_snapshot: {
          title: '邮箱快照',
          type: 'input',
          column: { show: !!permissions.contact_email_snapshot?.is_query, minWidth: 150 },
          search: { show: false },
          form: {
            col: { span: 12 },
            component: { disabled: compute((scope: any) => disabled(scope, 'contact_email_snapshot')) },
          },
          addForm: { show: !!permissions.contact_email_snapshot?.is_create },
          editForm: {
            show: !!permissions.contact_email_snapshot?.is_update || !!permissions.contact_email_snapshot?.is_query,
          },
          viewForm: { show: !!permissions.contact_email_snapshot?.is_query },
        },
        schemes: {
          title: '方案与服务',
          type: 'input',
          column: { show: false, minWidth: 150 },
          search: { show: false },
          form: {
            col: { span: 24 },
            component: { disabled: compute((scope: any) => disabled(scope, 'schemes')) },
            value: [],
            render: (scope: any) =>
              h(SchemeEditor, {
                modelValue: scope.form.schemes,
                'onUpdate:modelValue': (value: any) => (scope.form.schemes = value),
                disabled: disabled(scope, 'schemes'),
                groupPermissions: permissions._children?.QuotationScheme || {},
                itemPermissions: permissions._children?.QuotationSchemeItem || {},
              }),
          },
          addForm: { show: !!permissions.schemes?.is_create },
          editForm: { show: !!permissions.schemes?.is_update || !!permissions.schemes?.is_query },
          viewForm: { show: !!permissions.schemes?.is_query },
        },
        adjustment_amount: {
          title: '调整金额 / 人民币含税元',
          type: 'input',
          column: { show: !!permissions.adjustment_amount?.is_query, minWidth: 150 },
          search: { show: false },
          form: {
            col: { span: 12 },
            component: { disabled: compute((scope: any) => disabled(scope, 'adjustment_amount')) },
            value: '0.00',
          },
          addForm: { show: !!permissions.adjustment_amount?.is_create },
          editForm: { show: !!permissions.adjustment_amount?.is_update || !!permissions.adjustment_amount?.is_query },
          viewForm: { show: !!permissions.adjustment_amount?.is_query },
        },
        commercial_terms: {
          title: '商务条款',
          type: 'input',
          column: { show: false, minWidth: 150 },
          search: { show: false },
          form: {
            col: { span: 12 },
            component: {
              disabled: compute((scope: any) => disabled(scope, 'commercial_terms')),
              type: 'textarea',
              rows: 3,
            },
          },
          addForm: { show: !!permissions.commercial_terms?.is_create },
          editForm: { show: !!permissions.commercial_terms?.is_update || !!permissions.commercial_terms?.is_query },
          viewForm: { show: !!permissions.commercial_terms?.is_query },
        },
        remark: {
          title: '备注',
          type: 'input',
          column: { show: false, minWidth: 150 },
          search: { show: false },
          form: {
            col: { span: 12 },
            component: { disabled: compute((scope: any) => disabled(scope, 'remark')), type: 'textarea', rows: 3 },
          },
          addForm: { show: !!permissions.remark?.is_create },
          editForm: { show: !!permissions.remark?.is_update || !!permissions.remark?.is_query },
          viewForm: { show: !!permissions.remark?.is_query },
        },
        status: {
          title: '状态',
          type: 'input',
          column: { show: !!permissions.status?.is_query, minWidth: 150 },
          form: { show: !!permissions.status?.is_query, component: { disabled: true } },
          addForm: { show: false },
          search: { show: !!permissions.status?.is_query },
        },
        subtotal: {
          title: '小计 / 元',
          type: 'input',
          column: { show: !!permissions.subtotal?.is_query, minWidth: 150 },
          form: { show: !!permissions.subtotal?.is_query, component: { disabled: true } },
          addForm: { show: false },
          search: { show: false },
        },
        total_amount: {
          title: '总额 / 元',
          type: 'input',
          column: { show: !!permissions.total_amount?.is_query, minWidth: 150 },
          form: { show: !!permissions.total_amount?.is_query, component: { disabled: true } },
          addForm: { show: false },
          search: { show: false },
        },
        _summary: {
          title: '金额汇总',
          column: { show: false },
          form: {
            show: !!permissions.total_amount?.is_query,
            col: { span: 24 },
            render: (scope: any) => h(PriceSummary, { form: scope.form }),
          },
        },
      },
      request: {
        pageRequest: (query: any) => api.list(query),
        addRequest: ({ form }: any) => api.create(payload(form, permissions)),
        editRequest: ({ form, row }: any) => api.update(row.id, payload({ ...form, id: row.id }, permissions)),
        delRequest: ({ row }: any) => api.destroy(row.id),
      },
      actionbar: { buttons: { add: { show: auth('quotation:Create') && !!permissions.number?.is_create } } },
      rowHandle: {
        width: 210,
        buttons: {
          view: { show: auth('quotation:Retrieve') },
          edit: { show: compute(({ row }: any) => auth('quotation:Update') && row.status === 'DRAFT') },
          remove: { show: compute(({ row }: any) => auth('quotation:Delete') && row.status === 'DRAFT') },
        },
      },
      form: {
        wrapper: {
          is: 'el-drawer',
          size: '100%',
          style: { maxWidth: '100vw' },
          buttons: {
            cancel: { show: true, text: '取消' },
            ok: {
              text: '保存',
              show: compute(({ form, mode }: any) => mode !== 'view' && (!form?.status || form.status === 'DRAFT')),
            },
            ...actions,
          },
        },
        col: { span: 12 },
        group: {
          groupType: 'tabs',
          groups: {
            tab0: { label: '基本信息', columns: ['number', 'quotation_date', 'valid_until', 'status'] },
            tab1: {
              label: '客户与联系人',
              columns: [
                'customer',
                'customer_name_snapshot',
                'customer_tax_number_snapshot',
                'customer_address_snapshot',
                'contact_name_snapshot',
                'contact_mobile_snapshot',
                'contact_email_snapshot',
              ],
            },
            tab2: { label: '方案与服务', columns: ['schemes'] },
            tab3: {
              label: '价格与条款',
              columns: ['subtotal', 'adjustment_amount', 'total_amount', 'commercial_terms', 'remark', '_summary'],
            },
          },
        },
      },
    },
  };
}
