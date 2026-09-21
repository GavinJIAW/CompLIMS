<template>
  <fs-page><fs-crud ref="crudRef" v-bind="crudBinding" /></fs-page>
</template>
<script setup lang="ts" name="lims_product">
import { onMounted } from 'vue';
import { useFs } from '@fast-crud/fast-crud';
import { createCrudOptions } from './crud';
import { api } from './api';
const context: any = { permissions: {}, refresh: () => crudExpose.doRefresh() };
const { crudBinding, crudRef, crudExpose, resetCrudOptions } = useFs({ createCrudOptions, context });
onMounted(async () => {
  context.permissions = (await api.field_permission()).data;
  resetCrudOptions(createCrudOptions({ context }).crudOptions);
  await crudExpose.doRefresh();
});
</script>
