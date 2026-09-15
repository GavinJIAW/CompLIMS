<template>
  <div class="workbench">
    <header class="workbench-header">
      <h1>{{ $t('message.workbench.title') }}</h1>
      <p>{{ $t('message.workbench.context') }}</p>
    </header>
    <section class="workbench-section" aria-labelledby="workbench-user">
      <h2 id="workbench-user">{{ userInfos.name || '—' }}</h2>
      <dl class="workbench-context">
        <div><dt>{{ $t('message.workbench.organization') }}</dt><dd>{{ userInfos.dept_info?.dept_name || '—' }}</dd></div>
        <div>
          <dt>{{ $t('message.workbench.roles') }}</dt>
          <dd class="workbench-roles">
            <el-tag v-for="role in roles" :key="role.id" type="info" effect="plain">{{ role.name }}</el-tag>
            <span v-if="!roles.length">—</span>
          </dd>
        </div>
      </dl>
    </section>
    <section class="workbench-section" aria-labelledby="workbench-overview">
      <h2 id="workbench-overview">{{ $t('message.workbench.overview') }}</h2>
      <div class="workbench-unconnected">
        <el-icon aria-hidden="true"><ele-Connection /></el-icon>
        <div>
          <h3>{{ $t('message.workbench.notConnected') }}</h3>
          <p>{{ $t('message.workbench.explanation') }}</p>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts" name="home">
import { computed } from 'vue';
import { storeToRefs } from 'pinia';
import { useUserInfo } from '/@/stores/userInfo';
// Consume existing identity context; no business metrics or permission inference.
const { userInfos } = storeToRefs(useUserInfo());
const roles = computed(() => (userInfos.value.role_info || []).filter((role) => role.name));
</script>

<style scoped lang="scss">
.workbench {
  min-width: 0;
  padding: var(--lims-space-6);
  display: grid;
  gap: var(--lims-space-6);
  color: var(--lims-text-regular);
  overflow-wrap: anywhere;
  h1 { font-size: var(--lims-type-page-title-size); line-height: var(--lims-type-page-title-line-height); font-weight: var(--lims-type-page-title-weight); color: var(--lims-text-primary); }
  h2 { font-size: var(--lims-type-section-title-size); line-height: var(--lims-type-section-title-line-height); font-weight: var(--lims-type-section-title-weight); color: var(--lims-text-primary); }
  p { line-height: var(--lims-type-form-value-line-height); color: var(--lims-text-secondary); }
}
.workbench-header p { margin-top: var(--lims-space-2); }
.workbench-section {
  min-width: 0;
  padding: var(--lims-space-6);
  border: var(--lims-border-width) solid var(--lims-border-default);
  border-radius: var(--lims-radius-card);
  background: var(--lims-background-card);
}
.workbench-context {
  margin-top: var(--lims-space-4);
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 2fr);
  gap: var(--lims-space-4);
  dt { color: var(--lims-text-secondary); margin-bottom: var(--lims-space-2); }
  dd { margin: 0; }
}
.workbench-roles { display: flex; flex-wrap: wrap; gap: var(--lims-space-2); }
.workbench-unconnected {
  display: flex;
  gap: var(--lims-space-4);
  align-items: flex-start;
  padding-block: var(--lims-space-8);
  .el-icon { flex-shrink: 0; font-size: 32px; color: var(--lims-text-secondary); }
  h3 { margin-bottom: var(--lims-space-2); font-size: var(--lims-type-card-title-size); font-weight: var(--lims-type-card-title-weight); color: var(--lims-text-primary); }
}
@media (max-width: 1100px) {
  .workbench { padding: var(--lims-space-4); gap: var(--lims-space-4); }
  .workbench-context { grid-template-columns: minmax(0, 1fr); }
}
</style>
