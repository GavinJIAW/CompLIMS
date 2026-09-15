<template>
  <main class="login-entry">
    <section class="login-brand" :aria-label="$t('message.loginPresentation.productName')">
      <div class="login-brand-content">
        <BrandLogo :src="siteLogo" />
        <p class="login-product">{{ $t('message.loginPresentation.productName') }}</p>
        <h2>{{ getSystemConfig['login.site_title'] || getThemeConfig.globalViceTitle }}</h2>
        <p class="login-description">{{ getSystemConfig['login.site_name'] || getThemeConfig.globalViceTitleMsg || $t('message.loginPresentation.description') }}</p>
        <el-image v-if="siteBg" :src="siteBg" fit="cover" class="login-brand-image" alt="">
          <template #error><span class="login-background-fallback" aria-hidden="true"></span></template>
        </el-image>
      </div>
    </section>
    <section class="login-panel" aria-labelledby="login-title">
      <div class="login-panel-content">
        <h1 id="login-title">{{ userInfos.pwd_change_count === 0 ? $t('message.loginPresentation.firstPasswordTitle') : $t('message.loginPresentation.title') }}</h1>
        <div v-if="!state.isScan">
          <el-tabs v-model="state.tabsActiveName">
            <el-tab-pane :label="$t('message.label.changePwd')" name="changePwd" v-if="userInfos.pwd_change_count===0">
              <ChangePwd />
            </el-tab-pane>
            <el-tab-pane :label="$t('message.label.one1')" name="account" v-else>
              <Account />
            </el-tab-pane>
            <!-- Mobile, QR and OAuth remain unexposed. -->
          </el-tabs>
        </div>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts" name="loginIndex">
import {defineAsyncComponent, onMounted, reactive, computed, watch} from 'vue';
import { storeToRefs } from 'pinia';
import { useThemeConfig } from '/@/stores/themeConfig';
import { NextLoading } from '/@/utils/loading';
import BrandLogo from '/@/layout/logo/BrandLogo.vue';
import { SystemConfigStore } from '/@/stores/systemConfig'
import { getBaseURL } from "/@/utils/baseUrl";
// 引入组件
const Account = defineAsyncComponent(() => import('/@/views/system/login/component/account.vue'));
const Mobile = defineAsyncComponent(() => import('/@/views/system/login/component/mobile.vue'));
const Scan = defineAsyncComponent(() => import('/@/views/system/login/component/scan.vue'));
const ChangePwd = defineAsyncComponent(() => import('/@/views/system/login/component/changePwd.vue'));
// const OAuth2 = defineAsyncComponent(() => import('/@/views/system/login/component/oauth2.vue'));

import _ from "lodash-es";
import {useUserInfo} from "/@/stores/userInfo";
const { userInfos } = storeToRefs(useUserInfo());

// 定义变量内容
const storesThemeConfig = useThemeConfig();
const { themeConfig } = storeToRefs(storesThemeConfig);
const state = reactive({
	tabsActiveName: 'account',
	isScan: false,
});


watch(()=>userInfos.value.pwd_change_count,(val)=>{
  if(val===0){
    state.tabsActiveName ='changePwd'
  }else{
    state.tabsActiveName ='account'
  }
},{deep:true,immediate:true})


// 获取布局配置信息
const getThemeConfig = computed(() => {
	return themeConfig.value;
});

const systemConfigStore = SystemConfigStore()
const { systemConfig } = storeToRefs(systemConfigStore)
const getSystemConfig = computed(() => {
	return systemConfig.value
})

const siteLogo = computed(() => {
	if (!_.isEmpty(getSystemConfig.value['login.site_logo'])) {
		return getSystemConfig.value['login.site_logo']
	}
	return undefined
});

const siteBg = computed(() => {
	if (!_.isEmpty(getSystemConfig.value['login.login_background'])) {
		return getSystemConfig.value['login.login_background']
	}
  return undefined
});

// 页面加载时
onMounted(() => {
	NextLoading.done();
});
</script>

<style scoped lang="scss">
.login-entry {
  height: 100%;
  min-width: 0;
  overflow-y: auto;
  display: grid;
  grid-template-columns: 52% 48%;
  color: var(--lims-text-regular);
  background: var(--lims-background-card);
}
.login-brand, .login-panel {
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: calc(var(--lims-space-6) * 2);
}
.login-brand {
  background: var(--lims-background-page);
  border-right: var(--lims-border-width) solid var(--lims-border-default);
}
.login-brand-content {
  width: 100%;
  max-width: 520px;
  --lims-logo-width: min(300px, calc(100vw - 80px));
  overflow-wrap: anywhere;
  h2 {
    margin: var(--lims-space-2) 0;
    font-size: var(--lims-type-section-title-size);
    line-height: var(--lims-type-section-title-line-height);
    font-weight: var(--lims-type-section-title-weight);
    color: var(--lims-text-primary);
  }
}
.login-product {
  margin-top: var(--lims-space-6);
  font-size: var(--lims-type-metric-size);
  line-height: var(--lims-type-metric-line-height);
  font-weight: var(--lims-type-page-title-weight);
  color: var(--lims-text-primary);
}
.login-description {
  line-height: var(--lims-type-section-title-line-height);
  color: var(--lims-text-secondary);
}
.login-brand-image {
  display: block;
  width: 100%;
  height: 220px;
  margin-top: var(--lims-space-8);
  border-radius: var(--lims-radius-card);
}
.login-background-fallback { width: 100%; height: 100%; background: var(--lims-background-page); }
.login-panel-content {
  width: 100%;
  max-width: 400px;
  margin-block: auto;
  h1 {
    margin-bottom: var(--lims-space-6);
    font-size: var(--lims-type-page-title-size);
    line-height: var(--lims-type-page-title-line-height);
    font-weight: var(--lims-type-page-title-weight);
    color: var(--lims-text-primary);
  }
}
@media (min-width: 1000px) and (max-width: 1399px) {
  .login-entry { grid-template-columns: 48% 52%; }
}
@media (max-width: 999px) {
  .login-entry { grid-template-columns: minmax(0, 1fr); grid-template-rows: auto 1fr; }
  .login-brand, .login-panel { padding: var(--lims-space-6) var(--lims-space-8); }
  .login-brand { border-right: 0; border-bottom: var(--lims-border-width) solid var(--lims-border-default); }
  .login-brand-content { max-width: 400px; --lims-logo-width: min(220px, calc(100vw - 80px)); }
  .login-product { margin-top: var(--lims-space-3); font-size: var(--lims-type-page-title-size); }
  .login-brand-image { height: 120px; margin-top: var(--lims-space-4); }
}
</style>
