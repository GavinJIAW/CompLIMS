import { h } from 'vue';
import { dict } from '@fast-crud/fast-crud';
import { auth } from '/@/utils/authFunction';
import { payload, writable } from './api';
import TemplateEditor from './TemplateEditor.vue';
import DefaultsEditor from './DefaultsEditor.vue';
import CompositionEditor from './CompositionEditor.vue';
import MasterSelect from './MasterSelect.vue';
import ObjectEditor from './ObjectEditor.vue';

const labels: Record<string,string> = {number:'编号',internal_name:'内部简称',name:'中文名称',name_en:'英文名称',service_type:'服务分类',requirement_template:'需求模板',result_template:'结果模板',enabled:'启用',description:'说明',cost_type:'成本类型',unit_cost:'单位成本 (RMB)',unit:'计价单位',basis_data:'成本依据',items:'组合明细',service:'技术服务',requirement_defaults:'需求默认值',reference_price:'参考售价 (RMB)',packages:'成本包组合',current_cost:'当前成本 (RMB)',standard_cost:'当前标准成本 (RMB)'};
export function makeCrud(resource: string, api: any, context: any) {
  const permissions = context.permissions || {};
  const columns: any = {id:{title:'ID',type:'number',column:{show:false},form:{show:false}}};
  const isNamed = ['service','product','scheme'].includes(resource);
  const searchFields = isNamed ? ['number','internal_name','name','name_en'] : ['number','name'];
  for (const key of writable[resource]) {
    const flags = permissions[key] || {};
    columns[key] = {title:labels[key],type:'input', column:{show:!!flags.is_query,minWidth:130},
      search:{show:(searchFields.includes(key) || key === 'service_type') && !!flags.is_query,component:{name:'el-input',clearable:true}},
      form:{show:true,col:{span:12}}, addForm:{show:!!flags.is_create}, editForm:{show:!!flags.is_update}};
    if (['number','name','unit','service','cost_type','unit_cost','reference_price'].includes(key)) columns[key].form.rules = [{required:true,message:`请填写${labels[key]}`}];
    if (key === 'number') columns[key].editForm = {show:!!flags.is_query,component:{disabled:true}};
    if (key === 'enabled') Object.assign(columns[key],{type:'dict-switch',dict:dict({data:[{value:true,label:'启用'},{value:false,label:'停用'}]}),form:{value:true}});
    if (key === 'cost_type') {
      columns[key].search = {show:!!flags.is_query, render:(scope:any) => h(MasterSelect, {
        resource:'cost_type', includeDisabled:true, modelValue:scope.form[key],
        'onUpdate:modelValue':(value:any) => {scope.form[key]=value;},
      })};
      Object.assign(columns[key], {type:'dict-select', dict:dict({url:'/api/lims/cost_type/', value:'id', label:'name', params:{limit:1000}})});
    }
    if (['unit_cost','reference_price'].includes(key)) columns[key].form.component = {placeholder:'非负，最多 2 位小数'};
    if (key === 'description') columns[key].form.component = {type:'textarea',rows:3};
    const custom: any = {requirement_template:TemplateEditor,result_template:TemplateEditor,basis_data:ObjectEditor,service:MasterSelect,cost_type:MasterSelect,requirement_defaults:DefaultsEditor,items:CompositionEditor,packages:CompositionEditor};
    if (custom[key]) {
      if (!['service','cost_type'].includes(key)) columns[key].column.show = false;
      columns[key].form.col = {span:24};
      columns[key].form.value = ['requirement_template','result_template','items','packages'].includes(key) ? [] : ['basis_data','requirement_defaults'].includes(key) ? {} : undefined;
      columns[key].form.render = (scope: any) => h(custom[key], {
        modelValue:scope.form[key], 'onUpdate:modelValue':(value:any)=>{scope.form[key]=value;},
        ...(['service','cost_type'].includes(key) ? {resource:key} : {}),
        ...(key === 'requirement_defaults' ? {serviceId:scope.form.service} : {}),
        ...(['items','packages'].includes(key) ? {kind:resource,permissions:permissions._rows,
          showStandardCost:!!permissions.standard_cost?.is_query,showReferencePrice:!!permissions.reference_price?.is_query} : {}),
        disabled:!flags[scope.form.id ? 'is_update' : 'is_create'],
      });
    }
  }
  const costs = resource === 'cost_package' ? ['current_cost'] : resource === 'product' ? ['standard_cost'] : resource === 'scheme' ? ['standard_cost','reference_price'] : [];
  for (const cost of costs) columns[cost] = {title:labels[cost],type:'input',column:{show:!!permissions[cost]?.is_query,minWidth:170},form:{show:false}};
  return {crudOptions:{
    request:{pageRequest:(query:any)=>api.list(query), addRequest:({form}:any)=>api.create(payload(resource,form,false,permissions)), editRequest:({form,row}:any)=>api.update(row.id,payload(resource,form,true,permissions)), delRequest:({row}:any)=>api.remove(row.id)},
    actionbar:{buttons:{add:{show:auth(`${resource}:Create`) && !!permissions.number?.is_create}}},
    rowHandle:{width:180,buttons:{view:{show:false},edit:{show:auth(`${resource}:Update`)},remove:{show:auth(`${resource}:Delete`)}}},
    form:{wrapper:{
      ...(['cost_type','cost_item'].includes(resource) ? {is:'el-dialog',width:'min(800px, 95vw)'} : {is:'el-drawer',size:'min(1200px, 100vw)'}),
      buttons:{cancel:{show:true,text:'取消'},ok:{text:'保存'}},
    },col:{span:12}},
    columns,
  }};
}
