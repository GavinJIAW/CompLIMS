<template>
  <section class="error-state" aria-labelledby="error-title">
    <div class="error-state-content">
      <p class="error-state-code">404</p>
      <h1 id="error-title">{{ $t('message.notFound.foundTitle') }}</h1>
      <p class="error-state-description">{{ $t('message.notFound.foundMsg') }}</p>
      <el-button type="primary" @click="onGoHome">{{ $t('message.notFound.foundBtn') }}</el-button>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent, computed } from 'vue';
import { useRouter } from 'vue-router';
import { storeToRefs } from 'pinia';
import { useThemeConfig } from '/@/stores/themeConfig';
import { useTagsViewRoutes } from '/@/stores/tagsViewRoutes';

export default defineComponent({
	name: '404',
	setup() {
		const storesThemeConfig = useThemeConfig();
		const storesTagsViewRoutes = useTagsViewRoutes();
		const { themeConfig } = storeToRefs(storesThemeConfig);
		const { isTagsViewCurrenFull } = storeToRefs(storesTagsViewRoutes);
		const router = useRouter();
		const onGoHome = () => {
			router.push('/');
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
			onGoHome,
			initTagViewHeight,
		};
	},
});
</script>

<style scoped lang="scss">
@import './error.scss';
</style>
