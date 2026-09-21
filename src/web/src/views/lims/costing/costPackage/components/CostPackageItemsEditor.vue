<template>
  <div class="composition-editor">
    <el-table :data="rows" border row-key="_key">
      <el-table-column label="顺序" width="105"
        ><template #default="{ row }"
          ><el-input-number
            v-model="row.sequence"
            :min="0"
            :controls="false"
            :disabled="!writable('sequence', row)"
            @change="publish" /></template
      ></el-table-column>
      <el-table-column :label="targetLabel" min-width="240"
        ><template #default="{ row }">
          <MasterSelect
            v-if="visible(target)"
            v-model="row[target]"
            :load-list="targetApi.list"
            :load-one="targetApi.retrieve"
            :disabled="!writable(target, row)"
            @selected="selected(row, $event)"
            @update:model-value="publish"
          />
          <span v-else>无字段权限</span>
        </template></el-table-column
      >
      <el-table-column label="单位" width="90"
        ><template #default="{ row }">{{ row.unit || '—' }}</template></el-table-column
      >
      <el-table-column label="当前单位成本 (RMB)" min-width="150"
        ><template #default="{ row }">{{ row.unit_cost ?? '—' }}</template></el-table-column
      >
      <el-table-column label="数量 / 用量" min-width="150"
        ><template #default="{ row }"
          ><el-input
            v-if="visible('quantity')"
            v-model="row.quantity"
            :disabled="!writable('quantity', row)"
            placeholder="最多 6 位小数"
            @change="publish" /></template
      ></el-table-column>
      <el-table-column label="行成本 (RMB)" min-width="150"
        ><template #default="{ row }">{{ multiply(row.unit_cost, row.quantity, 2) ?? '—' }}</template></el-table-column
      >
      <el-table-column label="操作" width="90"
        ><template #default="{ $index }"
          ><el-button
            type="danger"
            link
            :disabled="disabled"
            @click="
              rows.splice($index, 1);
              publish();
            "
            >移除</el-button
          ></template
        ></el-table-column
      >
    </el-table>
    <div class="footer">
      <el-button type="primary" plain :disabled="disabled || rows.length >= 500" @click="add"
        >添加{{ targetLabel }}</el-button
      >
      <strong>当前成本预览：{{ total ?? '无成本读取权限或数量无效' }}<span v-if="total !== null"> RMB</span></strong>
    </div>
    <p>同一目标只能出现一次。保存后以服务器计算结果为准。</p>
  </div>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { api as targetApi } from '/@/views/lims/costing/costItem/api';
import MasterSelect from '../../../shared/MasterSelect.vue';

import { multiply, sum } from '../../../shared/decimal';
const props = defineProps<{
  modelValue?: any[];
  permissions?: any;
  disabled?: boolean;
}>();
const emit = defineEmits(['update:modelValue']);
const rows = ref<any[]>([]);
watch(
  () => props.modelValue,
  (value) => {
    rows.value = (value || []).map((row, index) => ({ ...row, _key: row.id || `new-${index}` }));
  },
  { immediate: true, deep: true }
);
const target = 'item';
const targetLabel = '成本项';
const visible = (field: string) =>
  ['is_query', 'is_create', 'is_update'].some((mode) => props.permissions?.[field]?.[mode]);
const writable = (field: string, row: any) =>
  !props.disabled && !!props.permissions?.[field]?.[row.id ? 'is_update' : 'is_create'];
const total = computed(() =>
  sum(
    rows.value.map((row) => multiply(row.unit_cost, row.quantity, 2)),
    2
  )
);
function publish() {
  emit(
    'update:modelValue',
    rows.value.map(({ _key, ...row }) => row)
  );
}
function add() {
  rows.value.push({
    _key: `new-${Date.now()}`,
    sequence: Math.max(0, ...rows.value.map((row) => row.sequence || 0)) + 10,
    quantity: '1',
  });
  publish();
}
function selected(row: any, obj: any) {
  if (!obj) return;
  row.unit = obj.unit;
  row.target_name = obj.name;
  row.unit_cost = obj.unit_cost;
}
</script>
<style scoped>
.composition-editor {
  width: 100%;
  min-width: 0;
}
.footer {
  display: flex;
  gap: 16px;
  align-items: center;
  flex-wrap: wrap;
  margin-top: 12px;
}
p {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.override {
  padding: 16px;
}
.el-input-number {
  width: 80px;
}
</style>
