<template>
  <div class="template-editor">
    <el-empty v-if="!rows.length" description="尚未定义字段" :image-size="48" />
    <el-card v-for="(field, index) in rows" :key="index" shadow="never" class="field-card">
      <div class="field-header">
        <strong>{{ index + 1 }}. {{ field.label || '新字段' }}</strong>
        <div>
          <el-button :disabled="disabled || index === 0" @click="move(index, -1)">上移</el-button>
          <el-button :disabled="disabled || index === rows.length - 1" @click="move(index, 1)">下移</el-button>
          <el-button
            :disabled="disabled"
            type="danger"
            plain
            @click="
              rows.splice(index, 1);
              publish();
            "
            >删除字段</el-button
          >
        </div>
      </div>
      <div class="field-grid">
        <label
          >字段 key<el-input v-model="field.key" :disabled="disabled" placeholder="如 temperature" @change="publish"
        /></label>
        <label>显示名称<el-input v-model="field.label" :disabled="disabled" @change="publish" /></label>
        <label
          >类型<el-select v-model="field.type" :disabled="disabled" @change="changeType(field)"
            ><el-option v-for="type in types" :key="type" :value="type" :label="type" /></el-select
        ></label>
        <label>单位<el-input v-model="field.unit" :disabled="disabled" @change="publish" /></label>
        <label
          >必填<el-switch
            v-model="field.required"
            :disabled="disabled"
            @change="
              field.nullable = false;
              publish();
            "
        /></label>
        <label
          >允许空值<el-switch v-model="field.nullable" :disabled="disabled || field.required" @change="publish"
        /></label>
        <label class="wide"
          >帮助说明<el-input v-model="field.help_text" :disabled="disabled" @change="publish"
        /></label>
      </div>
      <div v-if="['select', 'multiple_select'].includes(field.type)" class="options">
        <div v-for="(option, optionIndex) in field.options" :key="optionIndex" class="option-row">
          <el-input v-model="option.value" placeholder="稳定选项值" :disabled="disabled" @change="publish" />
          <el-input v-model="option.label" placeholder="选项名称" :disabled="disabled" @change="publish" />
          <el-button
            :disabled="disabled"
            @click="
              field.options.splice(optionIndex, 1);
              publish();
            "
            >移除</el-button
          >
        </div>
        <el-button
          :disabled="disabled"
          @click="
            field.options.push({ value: '', label: '' });
            publish();
          "
          >添加选项</el-button
        >
      </div>
      <TemplateEditor
        v-if="field.type === 'table'"
        :model-value="field.columns"
        columns
        :disabled="disabled"
        @update:model-value="
          field.columns = $event;
          publish();
        "
      />
      <div v-if="!['file', 'image', 'csv', 'table'].includes(field.type)" class="default-row">
        <el-checkbox
          :model-value="Object.hasOwn(field, 'default')"
          :disabled="disabled"
          @change="toggleDefault(field, $event)"
          >设置默认值</el-checkbox
        >
        <el-checkbox
          v-if="Object.hasOwn(field, 'default') && field.nullable"
          :model-value="field.default === null"
          :disabled="disabled"
          @change="
            field.default = $event ? null : initial(field.type);
            publish();
          "
          >默认空值</el-checkbox
        >
        <ValueInput
          v-if="Object.hasOwn(field, 'default') && field.default !== null"
          :field="field"
          :model-value="field.default"
          :disabled="disabled"
          @update:model-value="
            field.default = $event;
            publish();
          "
        />
      </div>
    </el-card>
    <el-button
      :disabled="disabled || rows.length >= 100"
      type="primary"
      plain
      @click="
        rows.push({ key: '', label: '', type: 'string', required: false });
        publish();
      "
      >{{ columns ? '添加表格列' : '添加字段' }}</el-button
    >
    <p class="hint">仅定义模板。文件字段不上传实体文件；表格列不支持嵌套表格。</p>
  </div>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import ValueInput from '../../shared/ValueInput.vue';
const props = defineProps<{ modelValue?: any[]; columns?: boolean; disabled?: boolean }>();
const emit = defineEmits(['update:modelValue']);
const rows = ref<any[]>([]);
watch(
  () => props.modelValue,
  (value) => {
    rows.value = JSON.parse(JSON.stringify(value || []));
  },
  { immediate: true, deep: true }
);
const types = computed(() =>
  props.columns
    ? ['string', 'integer', 'float', 'date', 'boolean', 'select']
    : ['string', 'integer', 'float', 'date', 'boolean', 'select', 'multiple_select', 'file', 'image', 'csv', 'table']
);
const publish = () => emit('update:modelValue', JSON.parse(JSON.stringify(rows.value)));
const initial = (type: string): any =>
  type === 'boolean' ? false : ['integer', 'float'].includes(type) ? 0 : type === 'multiple_select' ? [] : '';
function toggleDefault(field: any, enabled: any) {
  if (enabled) field.default = initial(field.type);
  else delete field.default;
  publish();
}
function changeType(field: any) {
  delete field.default;
  delete field.options;
  delete field.columns;
  if (['select', 'multiple_select'].includes(field.type)) field.options = [];
  if (field.type === 'table') field.columns = [];
  publish();
}
function move(index: number, direction: number) {
  const [row] = rows.value.splice(index, 1);
  rows.value.splice(index + direction, 0, row);
  publish();
}
</script>
<style scoped>
.template-editor {
  width: 100%;
  min-width: 0;
}
.field-card {
  margin-bottom: 12px;
}
.field-header,
.option-row,
.default-row {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.field-header {
  justify-content: space-between;
}
.field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}
.field-grid label {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.wide {
  grid-column: 1/-1;
}
.option-row .el-input {
  flex: 1;
  min-width: 100px;
}
.hint {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
@media (max-width: 700px) {
  .field-grid {
    grid-template-columns: 1fr;
  }
}
</style>
