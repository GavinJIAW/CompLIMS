<template>
  <div class="defaults-editor" v-loading="loading">
    <el-alert v-if="error" :title="error" type="warning" :closable="false" />
    <el-empty v-else-if="!fields.length" description="请选择有参数模板的技术服务 / 产品" :image-size="48" />
    <div v-for="field in fields" :key="field.key" class="default-field">
      <el-checkbox :model-value="has(field.key)" :disabled="disabled" @change="toggle(field, $event)">{{ field.label }}（{{ field.key }}）</el-checkbox>
      <template v-if="has(field.key)">
        <el-checkbox v-if="field.nullable && !field.required" :model-value="modelValue?.[field.key] === null" :disabled="disabled" @change="set(field.key, $event ? null : initial(field.type))">空值</el-checkbox>
        <ValueInput v-if="modelValue?.[field.key] !== null" :field="field" :model-value="modelValue?.[field.key]" :disabled="disabled" @update:model-value="set(field.key, $event)" />
      </template>
    </div>
    <el-alert v-if="unknown.length" title="模板外的旧字段需要移除后保存" type="warning" :closable="false" />
    <el-button v-for="key in unknown" :key="key" :disabled="disabled" @click="remove(key)">移除 {{ key }}</el-button>
    <p>未勾选表示不设置该层默认值。覆盖按字段浅合并；M1 不保存文件或表格实体数据。</p>
  </div>
</template>
<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { request } from '/@/utils/service';
import ValueInput from './ValueInput.vue';
const props = defineProps<{ modelValue?: Record<string, any>; serviceId?: number; productId?: number; disabled?: boolean }>();
const emit = defineEmits(['update:modelValue']);
const fields = ref<any[]>([]), loading = ref(false), error = ref('');
const has = (key: string) => Object.prototype.hasOwnProperty.call(props.modelValue || {}, key);
const unknown = computed(() => Object.keys(props.modelValue || {}).filter(key => !fields.value.some(field => field.key === key)));
const set = (key: string, value: any) => emit('update:modelValue', { ...props.modelValue, [key]: value });
const remove = (key: string) => { const value = { ...props.modelValue }; delete value[key]; emit('update:modelValue', value); };
const initial = (type: string): any => type === 'boolean' ? false : ['integer','float'].includes(type) ? 0 : type === 'multiple_select' ? [] : '';
function toggle(field: any, enabled: any) { if (enabled) set(field.key, Object.hasOwn(field, 'default') ? field.default : initial(field.type)); else remove(field.key); }
let serial = 0;
watch(() => [props.serviceId, props.productId], async () => {
  const current = ++serial; fields.value = []; error.value = ''; if (!props.serviceId && !props.productId) return;
  loading.value = true;
  try { let id = props.serviceId;
    if (props.productId) id = (await request({ url: `/api/lims/product/${props.productId}/` })).data.service;
    if (!id) throw new Error('技术服务不可读');
    const res = await request({ url: `/api/lims/service/${id}/` });
    if (!Array.isArray(res.data.requirement_template)) throw new Error('没有参数模板读取权限');
    if (current === serial) fields.value = res.data.requirement_template.filter((field: any) => !['file','image','csv','table'].includes(field.type));
  } catch { if (current === serial) error.value = '无法读取参数模板，请检查技术服务与产品读取权限。'; }
  finally { if (current === serial) loading.value = false; }
}, { immediate: true });
</script>
<style scoped>.default-field { display:flex; align-items:center; gap:12px; flex-wrap:wrap; margin-bottom:12px; }p { color:var(--el-text-color-secondary); font-size:12px; }</style>
