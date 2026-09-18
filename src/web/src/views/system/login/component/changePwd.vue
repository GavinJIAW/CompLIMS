<template>
	<el-form ref="formRef" size="large" label-position="top" class="login-content-form" :model="state.ruleForm" :rules="rules"
		@keyup.enter="loginClick">
		<el-form-item class="login-animation1" prop="username" :label="$t('message.loginPresentation.username')">
			<el-input type="text" :placeholder="$t('message.account.accountPlaceholder1')" readonly
				v-model="ruleForm.username" clearable autocomplete="off">
				<template #prefix>
					<el-icon class="el-input__icon"><ele-User /></el-icon>
				</template>
			</el-input>
		</el-form-item>
		<el-form-item prop="oldPassword" label="当前密码">
            <el-input v-model="ruleForm.oldPassword" type="password" show-password autocomplete="current-password" />
        </el-form-item>
        <el-form-item class="login-animation2 login-validation-long" prop="password" :label="$t('message.loginPresentation.newPassword')">
			<el-input :type="isShowPassword ? 'text' : 'password'"
				:placeholder="$t('message.account.accountPlaceholder4')" v-model="ruleForm.password">
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
		<el-form-item class="login-animation3" prop="password_regain" :label="$t('message.loginPresentation.confirmPassword')">
			<el-input :type="isShowPassword ? 'text' : 'password'"
				:placeholder="$t('message.account.accountPlaceholder5')" v-model="ruleForm.password_regain">
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
		<el-form-item class="login-animation4">
			<el-button type="primary" class="login-content-submit" @click="loginClick" :loading="loading.signIn">
				<span>修改密码并重新登录</span>
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
import { getBaseURL } from "/@/utils/baseUrl";
import { loginChangePwd } from "/@/views/system/login/api";

export default defineComponent({
	name: 'changePwd',
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
                oldPassword: '',
				password: '',
				password_regain: ''
			},
			loading: {
				signIn: false,
			},
		});

        const validatePass = (rule, value, callback) => {
            callback(value && value.length >= 12 ? undefined : new Error('密码至少需要12个字符'));
        };
		const validatePass2 = (rule, value, callback) => {
			if (value === '') {
				callback(new Error('请再次输入密码'));
			} else if (value !== state.ruleForm.password) {
				callback(new Error('两次输入密码不一致!'));
			} else {
				callback();
			}
		};

		const rules = reactive<FormRules>({
            oldPassword: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
			username: [
				{ required: true, message: '请填写账号', trigger: 'blur' },
			],
			password: [
				{
					required: true,
					message: '请填写密码',
					trigger: 'blur',
				},
				{
					validator: validatePass,
					trigger: 'blur',
				},
			],
			password_regain: [
				{
					required: true,
					message: '请填写密码',
					trigger: 'blur',
				},
				{
					validator: validatePass2,
					trigger: 'blur',
				},
			],
		})
		const formRef = ref();
		// 时间获取
		const currentTime = computed(() => {
			return formatAxis(new Date());
		});

		const applyBtnClick = async () => {
			window.open(getBaseURL('/api/system/apply_for_trial/'));
		};

        const loginClick = async () => {
            if (!formRef.value || state.loading.signIn) return;
            if (!await formRef.value.validate().catch(() => false)) return;
            state.loading.signIn = true;
            try {
                await loginApi.loginChangePwd({
                    oldPassword: state.ruleForm.oldPassword,
                    newPassword: state.ruleForm.password,
                    newPassword2: state.ruleForm.password_regain,
                });
                ElMessage.success('密码已修改，请重新登录');
                Session.clear();
                window.location.assign('/#/login');
                window.location.reload();
            } catch {
                // The request layer displays the server validation error.
            } finally {
                state.loading.signIn = false;
                NextLoading.done();
            }
        };
		onMounted(() => {
			state.ruleForm.username = Cookies.get('username')
			//获取系统配置
			SystemConfigStore().getSystemConfigs();
		});
		// 是否显示申请试用按钮
		const showApply = () => {
			return window.location.href.indexOf('public') != -1
		}

		return {
			loginClick,
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
