import {request} from '/@/utils/service';
import {apiFor} from './api';
export const snapshot='customer_name_snapshot customer_tax_number_snapshot customer_address_snapshot contact_name_snapshot contact_phone_snapshot contact_email_snapshot'.split(' ');
export const writable:Record<string,string[]>={
  customer:'number name short_name tax_number address enabled description contacts'.split(' '),
  quotation:['number','customer',...snapshot,'quotation_date','valid_until','adjustment_amount','commercial_terms','remark','schemes'],
  contract:['number','customer',...snapshot,'contract_date','adjustment_amount','commercial_terms','remark','schemes'],
};
const contact='name department title phone mobile email address is_default enabled remark'.split(' ');
const group='source_scheme sequence name_snapshot name_en_snapshot description_snapshot remark items'.split(' ');
const item='source_product sequence name_snapshot name_en_snapshot unit_snapshot requirement_data quantity unit_price remark'.split(' ');
function child(row:any,keys:string[],permissions:any,immutable:string[]=[]){
  const result:any=row.id?{id:row.id}:{};
  for(const key of keys)if(!(row.id&&immutable.includes(key))&&row[key]!==undefined&&permissions?.[key]?.[row.id?'is_update':'is_create'])result[key]=row[key];
  return result;
}
export function payload(resource:string,form:any,permissions:any){
  const result:any={};
  for(const key of writable[resource])if(!(form.id&&key==='number')&&form[key]!==undefined&&permissions[key]?.[form.id?'is_update':'is_create'])result[key]=form[key];
  if(resource==='customer' && result.contacts)result.contacts=result.contacts.map((row:any)=>child(row,contact,permissions._children?.CustomerContact));
  if(result.schemes){const prefix=resource==='quotation'?'Quotation':'Contract';result.schemes=result.schemes.map((row:any)=>{
    const value=child(row,group,permissions._children?.[prefix+'Scheme'],['source_scheme']);
    if(!row.id&&row.source_scheme)delete value.items;
    else if(value.items)value.items=value.items.map((entry:any)=>child(entry,item,permissions._children?.[prefix+'SchemeItem'],['source_product']));
    return value;
  });}
  return result;
}
export function m2Api(resource:string){return {...apiFor(resource),command:(id:number,action:string,data:any={})=>request({url:`/api/lims/${resource}/${id}/${action}/`,method:'post',data})};}
