<template>
  <div class="customer-snapshot">
    <MasterSelect :model-value="form.customer" resource="customer" :disabled="disabled || !writable('customer')" @update:model-value="selectCustomer" />
    <el-select v-if="contacts.length" placeholder="选择联系人填入快照" :disabled="disabled" @change="selectContact">
      <el-option v-for="contact in contacts" :key="contact.id" :value="contact.id" :label="contact.name" :disabled="!contact.enabled" />
    </el-select>
    <p>选择新客户会填入当前客户资料；已有单据不会自动刷新客户或联系人快照。</p>
  </div>
</template>
<script setup lang="ts">
import {ref,onMounted} from 'vue';
import MasterSelect from '../../shared/MasterSelect.vue';
import {request} from '/@/utils/service';
const props=defineProps<{form:any;permissions:any;disabled?:boolean}>();
const contacts=ref<any[]>([]);
const writable=(key:string)=>!!props.permissions[key]?.[props.form.id?'is_update':'is_create'];
onMounted(async()=>{
  if(!props.form.customer || props.disabled)return;
  try{const {data}=await request({url:`/api/lims/customer/${props.form.customer}/`});contacts.value=data.contacts || [];}
  catch{ /* Existing snapshots remain editable without current customer access. */ }
});
async function selectCustomer(id:number){
  props.form.customer=id;
  const {data}=await request({url:`/api/lims/customer/${id}/`});
  contacts.value=data.contacts || [];
  for(const [target,key] of Object.entries({customer_name_snapshot:'name',customer_tax_number_snapshot:'tax_number',customer_address_snapshot:'address'}))if(writable(target)&&data[key]!==undefined)props.form[target]=data[key];
}
function selectContact(id:number){const row=contacts.value.find(c=>c.id===id);if(!row)return;for(const [target,value] of Object.entries({contact_name_snapshot:row.name,contact_phone_snapshot:row.phone || row.mobile,contact_email_snapshot:row.email}))if(writable(target)&&value!==undefined)props.form[target]=value;}
</script>
