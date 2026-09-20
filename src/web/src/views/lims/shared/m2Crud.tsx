import {h} from 'vue';
import {compute,dict} from '@fast-crud/fast-crud';
import {ElMessageBox,ElMessage,ElButton} from 'element-plus';
import {auth} from '/@/utils/authFunction';
import {writable,payload} from './m2Api';
import ContactEditor from '../customer/components/ContactEditor.vue';
import CustomerSnapshot from '../commercial/components/CustomerSnapshot.vue';
import SchemeEditor from '../commercial/components/SchemeEditor.vue';
import PriceSummary from '../commercial/components/PriceSummary.vue';

const labels:Record<string,string>={number:'编号',name:'客户名称',short_name:'简称',tax_number:'税号',address:'地址',enabled:'启用',description:'说明',contacts:'联系人',customer:'客户',customer_name_snapshot:'客户名称快照',customer_tax_number_snapshot:'客户税号快照',customer_address_snapshot:'客户地址快照',contact_name_snapshot:'联系人快照',contact_phone_snapshot:'联系电话快照',contact_email_snapshot:'联系邮箱快照',quotation_date:'报价日期',valid_until:'有效期至',contract_date:'合同日期',adjustment_amount:'调整金额 / 人民币含税元',commercial_terms:'商务条款',remark:'备注',schemes:'方案与产品',subtotal:'小计 / 元',total_amount:'总额 / 元',status:'状态'};
const actions:Record<string,any[]>={quotation:[['send','Send','发送报价','DRAFT'],['accept','Accept','接受','SENT'],['reject','Reject','拒绝','SENT'],['void','Void','作废','SENT'],['create_contract','CreateContract','创建合同','ACCEPTED']],contract:[['sign','Sign','签署','DRAFT'],['void','Void','作废','SIGNED']],customer:[]};
export function makeM2Crud(resource:string,api:any,context:any){
  const permissions=context.permissions || {}, commercial=resource!=='customer';
  const prefix=resource==='quotation'?'Quotation':'Contract';
  const locked=(form:any)=>commercial&&form.status&&form.status!=='DRAFT';
  const disabled=(scope:any,key:string)=>scope.mode==='view'||locked(scope.form)||!permissions[key]?.[scope.form.id?'is_update':'is_create'];
  const columns:any={id:{title:'ID',type:'number',column:{show:false},form:{show:false}}};
  const search=resource==='customer'?['number','name','short_name','enabled']:['number','customer_name_snapshot','status',resource+'_date'];
  for(const key of writable[resource]){
    const flag=permissions[key] || {};
    columns[key]={title:labels[key],type:'input',column:{show:!!flag.is_query&&!['contacts','schemes','commercial_terms','description','remark'].includes(key),minWidth:150},search:{show:search.includes(key)&&!!flag.is_query},form:{col:{span:12},component:{disabled:compute((scope:any)=>disabled(scope,key))}},addForm:{show:!!flag.is_create},editForm:{show:!!flag.is_update||!!flag.is_query},viewForm:{show:!!flag.is_query}};
    if(['number','name',resource+'_date','customer'].includes(key))columns[key].form.rules=[{required:true,message:`请填写${labels[key]}`}];
    if(key==='number')columns[key].editForm={show:!!flag.is_query,component:{disabled:true}};
    if(key.endsWith('_date')||key==='valid_until')columns[key].form.component={name:'el-date-picker',valueFormat:'YYYY-MM-DD',disabled:compute((scope:any)=>disabled(scope,key))};
    if(['description','commercial_terms','remark','address','customer_address_snapshot'].includes(key))columns[key].form.component.type='textarea';
    if(key==='enabled')Object.assign(columns[key],{type:'dict-switch',dict:dict({data:[{value:true,label:'启用'},{value:false,label:'停用'}]}),form:{value:true}});
    if(key==='adjustment_amount')columns[key].form.value='0.00';
    if(key==='contacts'){
      columns[key].form.col={span:24};columns[key].form.value=[];
      columns[key].form.render=(scope:any)=>h(ContactEditor,{modelValue:scope.form.contacts,permissions:permissions._children?.CustomerContact,disabled:disabled(scope,key),'onUpdate:modelValue':(value:any)=>scope.form.contacts=value});
    }
    if(key==='customer'){
      columns[key].column.show=false;columns[key].form.col={span:24};
      columns[key].form.render=(scope:any)=>h(CustomerSnapshot,{form:scope.form,permissions,disabled:disabled(scope,key)});
    }
    if(key==='schemes'){
      columns[key].form.col={span:24};columns[key].form.value=[];
      columns[key].form.render=(scope:any)=>h(SchemeEditor,{modelValue:scope.form.schemes,groupPermissions:permissions._children?.[prefix+'Scheme']||{},itemPermissions:permissions._children?.[prefix+'SchemeItem']||{},disabled:disabled(scope,key),'onUpdate:modelValue':(value:any)=>scope.form.schemes=value});
    }
  }
  if(commercial){
    for(const key of ['status','subtotal','total_amount'])columns[key]={title:labels[key],type:'input',column:{show:!!permissions[key]?.is_query,minWidth:140},form:{show:false},search:{show:key==='status'&&!!permissions.status?.is_query,component:{name:'el-input',clearable:true}}};
    columns._summary={title:'金额汇总',column:{show:false},form:{show:!!permissions.total_amount?.is_query,col:{span:24},render:(scope:any)=>h(PriceSummary,{form:scope.form})}};
  }
  const stateButtons:any={};
  for(const [action,suffix,label,state] of actions[resource])stateButtons[action]={text:label,type:'text',show:compute(({row}:any)=>auth(`${resource}:${suffix}`)&&row.status===state),click:async({row}:any)=>{
    try{
      let body:any={};
      if(action==='create_contract'){
        const number=await ElMessageBox.prompt('填写唯一合同编号','创建合同',{inputPattern:/\S+/,inputErrorMessage:'编号不能为空'});
        const date=await ElMessageBox.prompt('合同日期（YYYY-MM-DD）','创建合同',{inputPattern:/^\d{4}-\d{2}-\d{2}$/,inputErrorMessage:'请输入日期'});
        body={number:number.value,contract_date:date.value};
      }else await ElMessageBox.confirm(`确认${label} ${row.number}？`,label,{type:'warning'});
      const result=await api.command(row.id,action,body);
      if(action!=='create_contract')Object.assign(row,result.data);
      ElMessage.success(action==='create_contract'?'合同已创建，请进入合同页面继续编辑。':'操作成功');await context.refresh();
    }catch(error){if(error!=='cancel'&&error!=='close')throw error;}
  }};
  if(commercial)columns._actions={title:'状态操作',column:{show:false},addForm:{show:false},editForm:{show:false},viewForm:{show:true},form:{col:{span:24},render:(scope:any)=>h('div',actions[resource].filter(([action,suffix,label,state])=>scope.form.id&&scope.form.status===state&&auth(`${resource}:${suffix}`)).map(([action,suffix,label])=>h(ElButton,{onClick:()=>stateButtons[action].click({row:scope.form})},()=>label)))}};
  return {crudOptions:{
    request:{pageRequest:(query:any)=>api.list(query),addRequest:({form}:any)=>api.create(payload(resource,form,permissions)),editRequest:({form,row}:any)=>api.update(row.id,payload(resource,form,permissions)),delRequest:({row}:any)=>api.remove(row.id)},
    actionbar:{buttons:{add:{show:auth(`${resource}:Create`)&&!!permissions.number?.is_create}}},
    rowHandle:{width:commercial?330:180,buttons:{view:{show:auth(`${resource}:Retrieve`)},edit:{show:compute(({row}:any)=>auth(`${resource}:Update`)&&(!commercial||row.status==='DRAFT'))},remove:{show:compute(({row}:any)=>auth(`${resource}:Delete`)&&(!commercial||row.status==='DRAFT'))},...stateButtons}},
    form:{wrapper:{is:'el-drawer',size:commercial?'100%':'min(1400px,100vw)',style:{maxWidth:'100vw'}},col:{span:12}},columns,
  }};
}
