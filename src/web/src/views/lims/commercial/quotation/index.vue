<template>
  <div class="quotation-page">
    <fs-page><fs-crud ref="crudRef" v-bind="crudBinding" /></fs-page>
    <el-drawer v-model="conversionOpen" title="从报价创建合同" size="min(680px,100vw)">
      <el-form label-position="top"
        ><el-form-item label="合同编号" required><el-input v-model="conversion.number" /></el-form-item
        ><el-form-item label="合同日期" required
          ><el-date-picker v-model="conversion.contract_date" value-format="YYYY-MM-DD" /></el-form-item
      ></el-form>
      <template #footer
        ><el-button @click="conversionOpen = false">取消</el-button
        ><el-button type="primary" :loading="converting" @click="createContract">创建合同</el-button></template
      >
    </el-drawer>
  </div>
</template>
<script setup lang="ts" name="lims_quotation">
import { onMounted, ref } from 'vue';
import { useFs } from '@fast-crud/fast-crud';
import { createCrudOptions } from './crud';
import { api } from './api';
import { ElMessage } from 'element-plus';
const conversionOpen = ref(false),
  converting = ref(false),
  conversion = ref({ number: '', contract_date: '' }),
  source = ref<any>();
async function createContract() {
  if (!conversion.value.number || !conversion.value.contract_date) {
    ElMessage.warning('请填写合同编号和日期');
    return;
  }
  converting.value = true;
  try {
    await api.createContract(source.value.id, conversion.value);
    conversionOpen.value = false;
    ElMessage.success('合同已创建，请进入合同页面继续编辑');
    await crudExpose.doRefresh();
  } finally {
    converting.value = false;
  }
}
const context: any = {
  permissions: {},
  refresh: () => crudExpose.doRefresh(),
  openConversion: (row: any) => {
    source.value = row;
    conversion.value = { number: '', contract_date: '' };
    conversionOpen.value = true;
  },
};
const { crudBinding, crudRef, crudExpose, resetCrudOptions } = useFs({ createCrudOptions, context });
onMounted(async () => {
  context.permissions = (await api.field_permission()).data;
  resetCrudOptions(createCrudOptions({ context }).crudOptions);
  await crudExpose.doRefresh();
});
</script>

<style scoped>
/* The route parent allocates height with flex. The absolute fs-page cannot
   provide an intrinsic height for this containing block. */
.quotation-page {
  position: relative;
  flex: 1;
  min-height: 0;
  width: 100%;
}
</style>
