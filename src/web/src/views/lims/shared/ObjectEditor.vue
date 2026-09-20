<template><div><el-input v-model="text" type="textarea" :rows="4" :disabled="disabled" @change="parse" /><el-text v-if="error" type="danger">{{ error }}</el-text></div></template>
<script setup lang="ts">
import { ref, watch } from 'vue';
const props = defineProps<{modelValue?: any; disabled?: boolean}>();
const emit = defineEmits(['update:modelValue']);
const text = ref(''), error = ref('');
watch(() => props.modelValue, value => {text.value = JSON.stringify(value || {}, null, 2);}, {immediate:true});
function parse() {try {const value = JSON.parse(text.value); if (!value || Array.isArray(value) || typeof value !== 'object') throw new Error(); error.value = ''; emit('update:modelValue',value);} catch {error.value = '请输入有效 JSON 对象（仅存储说明，不执行公式）'; emit('update:modelValue', text.value);}}
</script>
