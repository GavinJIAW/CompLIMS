<template>
  <el-select :model-value="modelValue" :disabled="disabled" filterable remote :remote-method="search" :loading="loading" placeholder="搜索编号或名称" @visible-change="visible => visible && search('')" @update:model-value="select">
    <el-option v-for="row in options" :key="row.id" :value="row.id" :label="`${row.number || row.id} · ${row.name || ''}${row.enabled === false ? '（已停用）' : ''}`" :disabled="row.enabled === false && row.id !== modelValue" />
  </el-select>
</template>
<script setup lang="ts">
import { ref, watch } from 'vue';
import { request } from '/@/utils/service';
const props = defineProps<{ modelValue?: number; resource: string; disabled?: boolean }>();
const emit = defineEmits(['update:modelValue', 'selected']);
const options = ref<any[]>([]), loading = ref(false);
let serial = 0;
async function search(term: string) {
  const current = ++serial; loading.value = true;
  try { const res = await request({ url: `/api/lims/${props.resource}/`, params: { search: term, enabled: true, limit: 50 } });
    if (current === serial) { const selected = options.value.find(row => row.id === props.modelValue); options.value = res.data; if (selected && !options.value.some(row => row.id === selected.id)) options.value.unshift(selected); }
  } finally { if (current === serial) loading.value = false; }
}
function select(id: number) { emit('update:modelValue', id); emit('selected', options.value.find(row => row.id === id)); }
watch(() => [props.modelValue, props.resource], async () => {
  if (!props.modelValue) return;
  try { const res = await request({ url: `/api/lims/${props.resource}/${props.modelValue}/` });
    if (!options.value.some(row => row.id === res.data.id)) options.value.unshift(res.data);
    emit('selected', res.data);
  } catch { /* Preserve the current ID; the backend remains authoritative. */ }
}, { immediate: true });
</script>
