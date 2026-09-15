<template>
  <el-tooltip v-if="compact" content="CompLIMS" placement="right">
    <span class="brand-logo-compact" aria-label="CompLIMS">CL</span>
  </el-tooltip>
  <span v-else class="brand-logo-plate">
    <span class="brand-logo-viewport" :class="{ 'brand-logo-custom': customSource }">
      <img :src="customSource || officialLogo" @error="failedSource = src" :alt="customSource ? 'CompLIMS' : 'Applus+ Laboratories'" />
    </span>
  </span>
</template>

<script setup lang="ts" name="BrandLogo">
import { computed, ref } from 'vue';
import officialLogo from '/@/assets/logo.png';
// CL identifies the product; it is not an official Applus+ symbol.
const props = defineProps<{ compact?: boolean; src?: string }>();
const failedSource = ref<string>();
const customSource = computed(() => props.src && props.src !== failedSource.value ? props.src : undefined);
</script>

<style scoped lang="scss">
.brand-logo-plate {
  display: inline-flex;
  padding: var(--lims-space-2);
  background: var(--lims-brand-plate);
  border-radius: var(--lims-radius-input);
}
.brand-logo-viewport {
  display: block;
  width: var(--lims-logo-width, 172px);
  aspect-ratio: 1281 / 413;
  overflow: hidden;
  position: relative;
  // Original 1421x1005 PNG; viewport removes transparent margins only.
  img {
    position: absolute;
    width: 110.93%;
    max-width: none;
    height: auto;
    left: -5.62%;
    top: -61.5%;
  }
  &.brand-logo-custom img {
    position: static;
    width: 100%;
    height: 100%;
    object-fit: contain;
  }
}
.brand-logo-compact {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: var(--lims-space-8);
  height: var(--lims-space-8);
  border: 1px solid var(--lims-brand-primary);
  border-radius: var(--lims-radius-input);
  color: var(--lims-text-primary);
  font-weight: 600;
  font-size: var(--lims-type-table-size);
}
</style>
