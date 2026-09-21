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
      <el-table-column label="备注" min-width="160"
        ><template #default="{ row }"
          ><el-input
            v-if="visible('remark')"
            v-model="row.remark"
            :disabled="!writable('remark', row)"
            @change="publish" /></template
      ></el-table-column>
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
      <el-table-column v-if="visible('requirement_override')" type="expand"
        ><template #default="{ row }">
          <div class="override">
            <DefaultsEditor
              v-model="row.requirement_override"
              :product-id="row.product"
              :disabled="!writable('requirement_override', row)"
              @update:model-value="publish"
            />
          </div> </template
      ></el-table-column>
    </el-table>
    <div class="footer">
      <el-button type="primary" plain :disabled="disabled || rows.length >= 500" @click="add"
        >添加{{ targetLabel }}</el-button
      >
      <strong v-if="showStandardCost">当前标准成本：{{ schemeCost ?? '无成本读取权限或尚未加载' }} RMB</strong>
      <strong v-if="showReferencePrice">当前参考售价：{{ schemePrice ?? '无售价读取权限或尚未加载' }} RMB</strong>
    </div>
    <p>允许同一产品重复添加；顺序必须唯一。展开行可编辑参数覆盖。</p>
  </div>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { api as targetApi } from '/@/views/lims/catalog/product/api';
import MasterSelect from '../../../shared/MasterSelect.vue';
import DefaultsEditor from '../../shared/DefaultsEditor.vue';
import { sum } from '../../../shared/decimal';
const props = defineProps<{
  modelValue?: any[];
  permissions?: any;
  disabled?: boolean;
  showStandardCost?: boolean;
  showReferencePrice?: boolean;
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
const target = 'product';
const targetLabel = '产品';
const visible = (field: string) =>
  ['is_query', 'is_create', 'is_update'].some((mode) => props.permissions?.[field]?.[mode]);
const writable = (field: string, row: any) =>
  !props.disabled && !!props.permissions?.[field]?.[row.id ? 'is_update' : 'is_create'];
const products = ref<Record<number, any>>({});
const schemeCost = computed(() =>
  sum(
    rows.value.map((row) => products.value[row.product]?.standard_cost ?? null),
    2
  )
);
const schemePrice = computed(() =>
  sum(
    rows.value.map((row) => products.value[row.product]?.reference_price ?? null),
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
    requirement_override: {},
    remark: '',
  });
  publish();
}
function selected(row: any, obj: any) {
  if (obj) products.value[obj.id] = obj;
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
