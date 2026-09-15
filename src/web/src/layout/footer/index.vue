<template>
  <footer v-if="$slots.default" class="layout-footer"><slot /></footer>
</template>

<script setup lang="ts" name="layoutFooter">
// Keep the existing isFooter gate; no empty footer footprint or fabricated metadata.
</script>

<style scoped lang="scss">
.layout-footer {
  padding: var(--lims-space-2) var(--lims-space-4);
  color: var(--lims-text-secondary);
  text-align: center;
}
</style>
