<template>
  <div class="customer-snapshot">
    <MasterSelect
      :model-value="form.customer"
      :load-list="customerApi.list"
      :load-one="customerApi.retrieve"
      :disabled="disabled || !writable('customer')"
      @update:model-value="selectCustomer"
    />
    <el-select
      v-model="selectedContact"
      placeholder="选择启用联系人填入快照"
      clearable
      :disabled="disabled || !contacts.length"
      @change="selectContact"
    >
      <el-option
        v-for="contact in contacts"
        :key="contact.id"
        :value="contact.id"
        :label="`${contact.name}${contact.is_default ? '（默认）' : ''}`"
      />
    </el-select>
    <el-alert v-if="error" :title="error" type="warning" :closable="false" />
    <p>选择客户时优先填入默认联系人；已有单据快照不会随主数据更新。</p>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue';
import MasterSelect from '../../shared/MasterSelect.vue';
import { api as customerApi } from '../../customer/customer/api';
import { api as contactApi } from '../../customer/contact/api';
const props = defineProps<{ form: any; permissions: any; disabled?: boolean }>();
const contacts = ref<any[]>([]),
  selectedContact = ref<number>(),
  error = ref('');
const writable = (key: string) => !!props.permissions[key]?.[props.form.id ? 'is_update' : 'is_create'];
let serial = 0;
async function loadContacts(id: number) {
  const current = ++serial;
  contacts.value = [];
  selectedContact.value = undefined;
  error.value = '';
  if (!id) return;
  try {
    const { data } = await contactApi.list({ customer: id, enabled: true, limit: 1000 });
    if (current === serial) contacts.value = data;
  } catch {
    if (current === serial) error.value = '无法读取联系人，请检查联系人查询及字段权限。';
  }
}
onMounted(() => {
  if (props.form.customer && !props.disabled) loadContacts(props.form.customer);
});
async function selectCustomer(id: number) {
  props.form.customer = id;
  for (const key of ['contact_name_snapshot', 'contact_mobile_snapshot', 'contact_email_snapshot'])
    if (writable(key)) props.form[key] = '';
  const expected = id;
  await loadContacts(id);
  if (!id || props.form.customer !== expected) return;
  const { data } = await customerApi.retrieve(id);
  if (props.form.customer !== expected) return;
  for (const [target, key] of Object.entries({
    customer_name_snapshot: 'name',
    customer_tax_number_snapshot: 'tax_number',
    customer_address_snapshot: 'address',
  }))
    if (writable(target) && data[key] !== undefined) props.form[target] = data[key];
  const preferred = contacts.value.find((row) => row.is_default);
  if (preferred) {
    selectedContact.value = preferred.id;
    selectContact(preferred.id);
  }
}
function selectContact(id: number) {
  const row = contacts.value.find((c) => c.id === id);
  if (!row) return;
  for (const [target, value] of Object.entries({
    contact_name_snapshot: row.name,
    contact_mobile_snapshot: row.mobile,
    contact_email_snapshot: row.email,
  }))
    if (writable(target) && value !== undefined) props.form[target] = value;
}
</script>
<style scoped>
.customer-snapshot {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px;
}
.customer-snapshot p,
.customer-snapshot .el-alert {
  grid-column: 1/-1;
}
</style>
