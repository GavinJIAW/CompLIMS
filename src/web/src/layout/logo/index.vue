<template>
  <div class="layout-logo">
    <BrandLogo :compact="!setShowLogo" :src="siteLogo" />
  </div>
</template>

<script setup lang="ts" name="layoutLogo">
import { computed } from 'vue';
import { storeToRefs } from 'pinia';
import { useThemeConfig } from '/@/stores/themeConfig';
import { SystemConfigStore } from '/@/stores/systemConfig';
import BrandLogo from './BrandLogo.vue';
const { themeConfig } = storeToRefs(useThemeConfig());
const { systemConfig } = storeToRefs(SystemConfigStore());
const setShowLogo = computed(() => {
  const { isCollapse, layout } = themeConfig.value;
  return !isCollapse || layout === 'classic' || layout === 'transverse' || document.body.clientWidth < 1000;
});
const siteLogo = computed(() => systemConfig.value['login.site_logo'] || undefined);
</script>

<style scoped lang="scss">
.layout-logo {
  width: 100%;
  height: var(--lims-shell-brand-height);
  flex: none;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--lims-text-primary);
  font-family: inherit;

}
</style>
