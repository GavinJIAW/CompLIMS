<template>
	<el-form ref="formRef" size="large" label-position="top" class="login-content-form" :model="state.ruleForm" :rules="rules" @keyup.enter="loginClick">
		<el-form-item class="login-animation1" prop="username" :label="$t('message.loginPresentation.username')">
			<el-input type="text" :placeholder="$t('message.account.accountPlaceholder1')" v-model="ruleForm.username"
				clearable autocomplete="off">
				<template #prefix>
					<el-icon class="el-input__icon"><ele-User /></el-icon>
				</template>
			</el-input>
		</el-form-item>
		<el-form-item class="login-animation2" prop="password" :label="$t('message.loginPresentation.password')">
			<el-input :type="isShowPassword ? 'text' : 'password'" :placeholder="$t('message.account.accountPlaceholder2')"
				v-model="ruleForm.password">
				<template #prefix>
					<el-icon class="el-input__icon"><ele-Unlock /></el-icon>
				</template>
				<template #suffix>
					<button type="button" class="iconfont el-input__icon login-content-password" :aria-label="$t(isShowPassword ? 'message.loginPresentation.hidePassword' : 'message.loginPresentation.showPassword')" :aria-pressed="isShowPassword" @keyup.enter.stop
						:class="isShowPassword ? 'icon-yincangmima' : 'icon-xianshimima'"
						@click="isShowPassword = !isShowPassword">
					</button>
				</template>
			</el-input>
		</el-form-item>
		<el-form-item class="login-animation3" v-if="isShowCaptcha" prop="captcha" :label="$t('message.loginPresentation.captcha')">
			<el-col :span="15">
				<el-input type="text" maxlength="4" :placeholder="$t('message.account.accountPlaceholder3')"
					v-model="ruleForm.captcha" clearable autocomplete="off">
					<template #prefix>
						<el-icon class="el-input__icon"><ele-Position /></el-icon>
					</template>
				</el-input>
			</el-col>
			<el-col :span="1"></el-col>
			<el-col :span="8">
				<el-button class="login-content-captcha" :aria-label="$t('message.loginPresentation.refreshCaptcha')" @click="refreshCaptcha" @keyup.enter.stop>
					<el-image :src="ruleForm.captchaImgBase" :alt="$t('message.loginPresentation.captcha')" />
				</el-button>
			</el-col>
		</el-form-item>
		<el-form-item class="login-animation4">
			<el-button type="primary" class="login-content-submit" @click="loginClick"
				:loading="loading.signIn">
				<span>{{ $t('message.account.accountBtnText') }}</span>
			</el-button>
		</el-form-item>
	</el-form>
  <!--      申请试用-->
  <div class="login-apply" v-if="showApply()">
    <el-button class="login-content-apply" link type="primary" plain round @click="applyBtnClick">
      <span>{{ $t('message.loginPresentation.apply') }}</span>
    </el-button>
  </div>
</template>

<script lang="ts">
import { toRefs, reactive, defineComponent, computed, onMounted, onUnmounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage, FormInstance, FormRules } from 'element-plus';
import { useI18n } from 'vue-i18n';
import Cookies from 'js-cookie';
import { storeToRefs } from 'pinia';
import { useThemeConfig } from '/@/stores/themeConfig';
import { Session } from '/@/utils/storage';
import { formatAxis } from '/@/utils/formatTime';
import { NextLoading } from '/@/utils/loading';
import * as loginApi from '/@/views/system/login/api';
import { useUserInfo } from '/@/stores/userInfo';
import { DictionaryStore } from '/@/stores/dictionary';
import { SystemConfigStore } from '/@/stores/systemConfig';
import { BtnPermissionStore } from '/@/plugin/permission/store.permission';

import { errorMessage } from '/@/utils/message';
import {getBaseURL} from "/@/utils/baseUrl";

export default defineComponent({
	name: 'loginAccount',
	setup() {
		const { t } = useI18n();
		const storesThemeConfig = useThemeConfig();
		const { themeConfig } = storeToRefs(storesThemeConfig);
		const { userInfos } = storeToRefs(useUserInfo());
		const route = useRoute();
		const router = useRouter();
		const state = reactive({
			isShowPassword: false,
			ruleForm: {
				username: '',
				password: '',
				captcha: '',
				captchaKey: '',
				captchaImgBase: '',
			},
			loading: {
				signIn: false,
			},
		});
		const rules = reactive<FormRules>({
			username: [
				{ required: true, message: '请填写账号', trigger: 'blur' },
			],
			password: [
				{
					required: true,
					message: '请填写密码',
					trigger: 'blur',
				},
			],
			captcha: [
				{
					required: true,
					message: '请填写验证码',
					trigger: 'blur',
				},
			],
		})
		const formRef = ref();
		// 时间获取
		const currentTime = computed(() => {
			return formatAxis(new Date());
		});
		// 是否关闭验证码
		const isShowCaptcha = computed(() => {
			return SystemConfigStore().systemConfig['base.captcha_state'];
		});

		const getCaptcha = async () => {
			loginApi.getCaptcha().then((ret: any) => {
				state.ruleForm.captchaImgBase = ret.data.image_base;
				state.ruleForm.captchaKey = ret.data.key;
			});
		};
		const applyBtnClick = async () => {
			window.open(getBaseURL('/api/system/apply_for_trial/'));
		};
    const refreshCaptcha = async () => {
			state.ruleForm.captcha=''
			loginApi.getCaptcha().then((ret: any) => {
				state.ruleForm.captchaImgBase = ret.data.image_base;
				state.ruleForm.captchaKey = ret.data.key;
			});
		};
		const loginClick = async () => {
			if (!formRef.value) return
			await formRef.value.validate((valid: any) => {
				if (valid) {
					loginApi.login({ ...state.ruleForm, password: state.ruleForm.password }).then(async (res: any) => {
						if (res.code === 2000) {
              const {data} = res
              Cookies.set('username', res.data.username);
              Session.set('token', res.data.access);
              Session.set('refresh', res.data.refresh);
              useUserInfo().setPwdChangeCount(data.pwd_change_count)
              if(data.pwd_change_count==0){
                return router.push('/login');
              }
							await loginSuccess();
						}
					}).catch((err: any) => {
						// 登录错误之后，刷新验证码
						refreshCaptcha();
					});
				} else {
					errorMessage("请填写登录信息")
				}
			})

		};



		// 登录成功后的跳转
		const loginSuccess = async () => {
            state.loading.signIn = true;
            NextLoading.start();
            try {
                const target = route.query?.redirect
                    ? { path: String(route.query.redirect), query: route.query.params ? JSON.parse(String(route.query.params)) : {} }
                    : '/';
                const failure = await router.push(target);
                if (!failure) ElMessage.success(`${currentTime.value}，${t('message.signInText')}`);
            } catch {
                errorMessage('页面初始化失败，请重试或刷新页面');
            } finally {
                state.loading.signIn = false;
                NextLoading.done();
            }
        };
		onMounted(() => {
			getCaptcha();
			//获取系统配置
			SystemConfigStore().getSystemConfigs();
		});
    // 是否显示申请试用按钮
    const showApply = () => {
      return window.location.href.indexOf('public') != -1
    }

		return {
			refreshCaptcha,
			loginClick,
			loginSuccess,
			isShowCaptcha,
			state,
			formRef,
			rules,
      applyBtnClick,
      showApply,
			...toRefs(state),
		};
	},
});
</script>

<style scoped lang="scss">
@import './form.scss';
</style>
