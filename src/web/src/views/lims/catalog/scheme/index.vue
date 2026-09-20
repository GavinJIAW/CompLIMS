<template>
  <fs-page><fs-crud ref="crudRef" v-bind="crudBinding" /></fs-page>
</template>
<script setup lang="ts" name="lims_scheme">
import { onMounted } from 'vue';
import { useFs } from '@fast-crud/fast-crud';
import { createCrudOptions } from './crud';
import { api } from './api';
const context: any = { permissions: {} };
const { crudBinding, crudRef, crudExpose, resetCrudOptions } = useFs({ createCrudOptions, context });
onMounted(async () => {
  const result = await api.permissions();
  context.permissions = result.data;
  resetCrudOptions(createCrudOptions({context}).crudOptions);
  await crudExpose.doRefresh();
});
</script>
