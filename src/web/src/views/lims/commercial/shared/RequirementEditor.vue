<template>
  <div class="requirements">
    <p>依据本行保存的需求结构编辑；商务阶段可暂不填写必填项。</p>
    <div v-for="field in schema || []" :key="field.key" class="requirement">
      <el-checkbox
        :model-value="has(field.key)"
        :disabled="disabled || files.includes(field.type)"
        @change="toggle(field, $event)"
        >{{ field.label }} {{ field.unit ? `(${field.unit})` : '' }}</el-checkbox
      >
      <span v-if="files.includes(field.type)">文件要求仅保留定义，本阶段不上传文件。</span>
      <template v-else-if="has(field.key)">
        <el-checkbox
          v-if="field.nullable && !field.required"
          :model-value="modelValue?.[field.key] === null"
          :disabled="disabled"
          @change="set(field.key, $event ? null : initial(field))"
          >空值</el-checkbox
        >
        <template v-if="modelValue?.[field.key] !== null">
          <div v-if="field.type === 'table'" class="table-input">
            <el-table :data="modelValue?.[field.key] || []" border>
              <el-table-column v-for="col in field.columns" :key="col.key" :label="col.label" min-width="150"
                ><template #default="{ row }">
                  <ValueInput
                    :field="col"
                    :model-value="row[col.key]"
                    :disabled="disabled"
                    @update:model-value="
                      row[col.key] = $event;
                      set(field.key, [...modelValue[field.key]]);
                    "
                  /> </template
              ></el-table-column>
              <el-table-column label="操作" width="80"
                ><template #default="{ $index }"
                  ><el-button
                    link
                    type="danger"
                    :disabled="disabled"
                    @click="
                      set(
                        field.key,
                        modelValue[field.key].filter((_: any, i: number) => i !== $index)
                      )
                    "
                    >删除</el-button
                  ></template
                ></el-table-column
              >
            </el-table>
            <el-button :disabled="disabled" @click="set(field.key, [...modelValue[field.key], {}])"
              >添加数据行</el-button
            >
          </div>
          <ValueInput
            v-else
            :field="field"
            :model-value="modelValue?.[field.key]"
            :disabled="disabled"
            @update:model-value="set(field.key, $event)"
          />
        </template>
      </template>
    </div>
  </div>
</template>
<script setup lang="ts">
import ValueInput from '../../shared/ValueInput.vue';
const props = defineProps<{ schema: any[]; modelValue: Record<string, any>; disabled?: boolean }>();
const emit = defineEmits(['update:modelValue']);
const files = ['file', 'image', 'csv'];
const has = (key: string) => Object.hasOwn(props.modelValue || {}, key);
const initial = (field: any): any =>
  field.type === 'boolean'
    ? false
    : ['integer', 'float'].includes(field.type)
    ? 0
    : ['table', 'multiple_select'].includes(field.type)
    ? []
    : '';
const set = (key: string, value: any) => emit('update:modelValue', { ...props.modelValue, [key]: value });
function toggle(field: any, on: any) {
  const values = { ...props.modelValue };
  if (on) values[field.key] = initial(field);
  else delete values[field.key];
  emit('update:modelValue', values);
}
</script>
<style scoped>
.requirement {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
  margin: 12px 0;
}
.table-input {
  width: 100%;
}
</style>
