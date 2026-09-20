<template>
  <el-select v-if="field.type === 'select' || field.type === 'multiple_select'" :model-value="modelValue" :multiple="field.type === 'multiple_select'" :disabled="disabled" @update:model-value="emit('update:modelValue', $event)">
    <el-option v-for="option in field.options || []" :key="option.value" :label="option.label" :value="option.value" />
  </el-select>
  <el-switch v-else-if="field.type === 'boolean'" :model-value="modelValue" :disabled="disabled" @update:model-value="emit('update:modelValue', $event)" />
  <el-date-picker v-else-if="field.type === 'date'" :model-value="modelValue" value-format="YYYY-MM-DD" :disabled="disabled" @update:model-value="emit('update:modelValue', $event)" />
  <el-input-number v-else-if="['integer', 'float'].includes(field.type)" :model-value="modelValue" :precision="field.type === 'integer' ? 0 : undefined" :disabled="disabled" @update:model-value="emit('update:modelValue', $event)" />
  <el-input v-else :model-value="modelValue" :disabled="disabled" @update:model-value="emit('update:modelValue', $event)" />
</template>
<script setup lang="ts">
defineProps<{ field: any; modelValue: any; disabled?: boolean }>();
const emit = defineEmits(['update:modelValue']);
</script>
