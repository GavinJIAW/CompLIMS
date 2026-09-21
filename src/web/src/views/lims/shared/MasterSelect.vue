<template>
  <el-select
    :model-value="modelValue"
    clearable
    :disabled="disabled"
    filterable
    remote
    :remote-method="search"
    :loading="loading"
    placeholder="搜索编号或名称"
    @visible-change="(visible) => visible && search('')"
    @update:model-value="select"
  >
    <el-option
      v-for="row in options"
      :key="row.id"
      :value="row.id"
      :label="`${label(row)}${row.enabled === false ? '（已停用）' : ''}`"
      :disabled="!includeDisabled && row.enabled === false && row.id !== modelValue"
    />
  </el-select>
</template>
<script setup lang="ts">
import { ref, watch } from 'vue';
const props = defineProps<{
  modelValue?: number;
  loadList: (params: any) => Promise<any>;
  loadOne: (id: number) => Promise<any>;
  label?: (row: any) => string;
  params?: Record<string, any>;
  excludeId?: number;
  disabled?: boolean;
  includeDisabled?: boolean;
}>();
const label = (row: any) => (props.label ? props.label(row) : `${row.number || row.id} · ${row.name || ''}`);
const emit = defineEmits(['update:modelValue', 'selected']);
const options = ref<any[]>([]),
  loading = ref(false);
let serial = 0;
async function search(term: string) {
  const current = ++serial;
  loading.value = true;
  try {
    const res = await props.loadList({
      search: term,
      ...(props.includeDisabled ? {} : { enabled: true }),
      limit: 50,
      ...props.params,
    });
    if (current === serial) {
      const selected = options.value.find((row) => row.id === props.modelValue);
      options.value = res.data.filter((row: any) => row.id !== props.excludeId);
      if (selected && !options.value.some((row) => row.id === selected.id)) options.value.unshift(selected);
    }
  } finally {
    if (current === serial) loading.value = false;
  }
}
function select(id: number) {
  emit('update:modelValue', id);
  emit(
    'selected',
    options.value.find((row) => row.id === id)
  );
}
let detailSerial = 0;
watch(
  () => [props.loadList, JSON.stringify(props.params || {}), props.excludeId],
  () => {
    ++serial;
    options.value = [];
  }
);
watch(
  () => [props.modelValue, props.loadOne, JSON.stringify(props.params || {})],
  async () => {
    const current = ++detailSerial;
    if (!props.modelValue) return;
    try {
      const res = await props.loadOne(props.modelValue);
      if (current !== detailSerial || res.data.id !== props.modelValue || res.data.id === props.excludeId) return;
      if (!options.value.some((row) => row.id === res.data.id)) options.value.unshift(res.data);
      emit('selected', res.data);
    } catch {
      /* Keep the ID visible; authority stays on the server. */
    }
  },
  { immediate: true }
);
</script>
