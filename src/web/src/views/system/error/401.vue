<template>
  <section class="error-state" aria-labelledby="error-title">
    <div class="error-state-content">
      <p class="error-state-code">401</p>
      <h1 id="error-title">{{ $t('message.noAccess.accessTitle') }}</h1>
      <p class="error-state-description">{{ $t('message.noAccess.accessMsg') }}</p>
      <el-button type="primary" @click="onSetAuth">{{ $t('message.noAccess.accessBtn') }}</el-button>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent, computed } from 'vue';
import { storeToRefs } from 'pinia';
import { useThemeConfig } from '/@/stores/themeConfig';
import { useTagsViewRoutes } from '/@/stores/tagsViewRoutes';
import { Session } from '/@/utils/storage';

export default defineComponent({
	name: '401',
	setup() {
		const storesThemeConfig = useThemeConfig();
		const storesTagsViewRoutes = useTagsViewRoutes();
		const { themeConfig } = storeToRefs(storesThemeConfig);
		const { isTagsViewCurrenFull } = storeToRefs(storesTagsViewRoutes);
		const onSetAuth = () => {
			// https://gitee.com/lyt-top/vue-next-admin/issues/I5C3JS
			// 清除缓存/token等
			Session.clear();
			// 使用 reload 时，不需要调用 resetRoute() 重置路由
			window.location.reload();
		};
		// 设置主内容的高度
		const initTagViewHeight = computed(() => {
			let { isTagsview } = themeConfig.value;
			if (isTagsViewCurrenFull.value) {
				return `30px`;
			} else {
				if (isTagsview) return `114px`;
				else return `80px`;
			}
		});
		return {
			onSetAuth,
			initTagViewHeight,
		};
	},
});
</script>

<style scoped lang="scss">
@import './error.scss';
</style>
