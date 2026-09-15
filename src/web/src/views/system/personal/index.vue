<template>
  <div class="personal-center">
    <h1>{{ $t('message.workbench.personalTitle') }}</h1>
    <section class="personal-panel personal-identity">
      <div class="personal-avatar">
        <avatarSelector v-model="selectImgVisible" @uploadImg="uploadImg" ref="avatarSelectorRef" />
        <p>{{ $t('message.workbench.avatarHint') }}</p>
      </div>
      <div class="personal-identity-content">
        <h2>{{ state.personalForm.name || state.personalForm.username || '—' }}</h2>
        <p class="personal-username">{{ state.personalForm.username }}</p>
        <dl class="personal-context">
          <div><dt>{{ $t('message.workbench.organization') }}</dt><dd>{{ state.personalForm.dept_info.dept_name || '—' }}</dd></div>
          <div><dt>{{ $t('message.workbench.roles') }}</dt><dd class="personal-roles">
            <el-tag v-for="(item, index) in state.personalForm.role_info" :key="index" type="info" effect="plain">{{ item.name }}</el-tag>
          </dd></div>
        </dl>
      </div>
    </section>
    <div class="personal-sections">
      <section class="personal-panel" aria-labelledby="profile-title">
        <h2 id="profile-title">{{ $t('message.workbench.profile') }}</h2>
        <el-form :model="state.personalForm" ref="userInfoFormRef" :rules="rules" size="default" label-position="top" class="profile-form">
						<el-row :gutter="24">
							<el-col :xs="24" :sm="12">
								<el-form-item label="昵称" prop="name">
									<el-input v-model="state.personalForm.name" placeholder="请输入昵称" clearable></el-input>
								</el-form-item>
							</el-col>
							<el-col :xs="24" :sm="12">
								<el-form-item label="邮箱">
									<el-input v-model="state.personalForm.email" placeholder="请输入邮箱" clearable></el-input>
								</el-form-item>
							</el-col>
							<el-col :xs="24" :sm="12">
								<el-form-item label="手机" prop="mobile">
									<el-input v-model="state.personalForm.mobile" placeholder="请输入手机" clearable></el-input>
								</el-form-item>
							</el-col>
							<el-col :xs="24" :sm="12">
								<el-form-item label="性别">
									<el-select v-model="state.personalForm.gender" placeholder="请选择性别" clearable class="w100">
<!--										<el-option label="男" :value="1"></el-option>-->
<!--										<el-option label="女" :value="0"></el-option>-->
<!--										<el-option label="保密" :value="2"></el-option>-->
                    <el-option v-for="(item,index) in genderList" :key="index" :label="item.label" :value="item.value"></el-option>
									</el-select>
								</el-form-item>
							</el-col>
							<el-col :xs="24" :sm="24" :md="24" :lg="24" :xl="24">
								<el-form-item>
									<el-button type="primary" @click="submitForm">
										<el-icon>
											<ele-Position />
										</el-icon>
										更新个人信息
									</el-button>
								</el-form-item>
							</el-col>
						</el-row>
					</el-form>
      </section>
      <section class="personal-panel" aria-labelledby="security-title">
        <h2 id="security-title">{{ $t('message.workbench.security') }}</h2>
        <div class="personal-security-item">
          <h3>{{ $t('message.workbench.password') }}</h3>
          <p>{{ $t('message.workbench.passwordHint') }}</p>
          <el-button @click="passwordFormShow = true">{{ $t('message.workbench.changePassword') }}</el-button>
        </div>
        <dl class="personal-security-details">
          <div><dt>{{ $t('message.workbench.mobile') }}</dt><dd>{{ state.personalForm.mobile || '—' }}</dd></div>
          <div><dt>{{ $t('message.workbench.email') }}</dt><dd>{{ state.personalForm.email || '—' }}</dd></div>
        </dl>
      </section>
    </div>
    <el-dialog v-model="passwordFormShow" title="密码修改" class="personal-password-dialog">
			<el-form
				ref="userPasswordFormRef"
				:model="userPasswordInfo"
				required-asterisk
				label-width="100px"
				label-position="top"
				:rules="passwordRules"
				center
			>
				<el-form-item label="原密码" required prop="oldPassword">
					<el-input type="password" v-model="userPasswordInfo.oldPassword" placeholder="请输入原始密码" show-password clearable></el-input>
				</el-form-item>
				<el-form-item required prop="newPassword" label="新密码">
					<el-input type="password" v-model="userPasswordInfo.newPassword" placeholder="请输入新密码" show-password clearable></el-input>
				</el-form-item>
				<el-form-item required prop="newPassword2" label="确认密码">
					<el-input type="password" v-model="userPasswordInfo.newPassword2" placeholder="请再次输入新密码" show-password clearable></el-input>
				</el-form-item>
			</el-form>
			<template #footer>
				<span class="dialog-footer">
					<el-button type="primary" @click="settingPassword"> <i class="fa fa-check"></i>提交 </el-button>
				</span>
			</template>
		</el-dialog>
  </div>
</template>

<script setup lang="ts" name="personal">
import { reactive, computed, onMounted, ref, defineAsyncComponent } from 'vue';
import { formatAxis } from '/@/utils/formatTime';
import * as api from './api';
import { ElMessage } from 'element-plus';
import { getBaseURL } from '/@/utils/baseUrl';
import { Session } from '/@/utils/storage';
import { useRouter } from 'vue-router';
import { useUserInfo } from '/@/stores/userInfo';
import { successMessage } from '/@/utils/message';
import {dictionary} from "/@/utils/dictionary";
import {Md5} from "ts-md5";
const router = useRouter();

// 头像裁剪组件
const avatarSelector = defineAsyncComponent(() => import('/@/components/avatarSelector/index.vue'));
const avatarSelectorRef = ref(null);
// 当前时间提示语
const currentTime = computed(() => {
	return formatAxis(new Date());
});
const userInfoFormRef = ref();
const rules = reactive({
	name: [{ required: true, message: '请输入昵称', trigger: 'blur' }],
	mobile: [{ pattern: /^1[3-9]\d{9}$/, message: '请输入正确手机号' }],
});

let selectImgVisible = ref(false);

const state = reactive<PersonalState>({
	newsInfoList: [],
	personalForm: {
		avatar: '',
		username: '',
		name: '',
		email: '',
		mobile: '',
		gender: '',
		dept_info: {
			dept_id: 0,
			dept_name: '',
		},
		role_info: [
			{
				id: 0,
				name: '',
			},
		],
	},
});

/**
 * 跳转消息中心
 */
const route = useRouter();
const msgMore = () => {
	route.push({ path: '/messageCenter' });
};

const genderList = ref();
/**
 * 获取用户个人信息
 */
const getUserInfo = function () {
	api.GetUserInfo({}).then((res: any) => {
		const { data } = res;
    genderList.value = dictionary('gender')
		state.personalForm.avatar = data.avatar || '';
		state.personalForm.username = data.username || '';
		state.personalForm.name = data.name || '';
		state.personalForm.email = data.email || '';
		state.personalForm.mobile = data.mobile || '';
		state.personalForm.gender = data.gender;
		state.personalForm.dept_info.dept_name = data.dept_info.dept_name || '';
		state.personalForm.role_info = data.role_info || [];
	});
};

/**
 * 更新用户信息
 * @param formEl
 */
const submitForm = async () => {
	if (!userInfoFormRef.value) return;
	await userInfoFormRef.value.validate((valid, fields) => {
		if (valid) {
			api.updateUserInfo(state.personalForm).then((res: any) => {
				ElMessage.success('更新成功');
				getUserInfo();
			});
		} else {
			ElMessage.error('表单验证失败,请检查~');
		}
	});
};

/**
 * 获取消息通知
 */
const getMsg = () => {
	api.GetSelfReceive({}).then((res: any) => {
		const { data } = res;
		state.newsInfoList = data || [];
	});
};
onMounted(() => {
	getUserInfo();
	getMsg();
});

/**************************密码修改部分************************/
const passwordFormShow = ref(false);
const userPasswordFormRef = ref();
const userPasswordInfo = reactive({
	oldPassword: '',
	newPassword: '',
	newPassword2: '',
});

const validatePass = (rule, value, callback) => {
	const pwdRegex = new RegExp('(?=.*[0-9])(?=.*[a-zA-Z]).{8,30}');
	if (value === '') {
		callback(new Error('请输入密码'));
	} else if (value === userPasswordInfo.oldPassword) {
		callback(new Error('原密码与新密码一致'));
	} else if (!pwdRegex.test(value)) {
		callback(new Error('您的密码复杂度太低(密码中必须包含字母、数字)'));
	} else {
		if (userPasswordInfo.newPassword2 !== '') {
			userPasswordFormRef.value.validateField('newPassword2');
		}
		callback();
	}
};
const validatePass2 = (rule, value, callback) => {
	if (value === '') {
		callback(new Error('请再次输入密码'));
	} else if (value !== userPasswordInfo.newPassword) {
		callback(new Error('两次输入密码不一致!'));
	} else {
		callback();
	}
};

const passwordRules = reactive({
	oldPassword: [
		{
			required: true,
			message: '请输入原密码',
			trigger: 'blur',
		},
	],
	newPassword: [{ validator: validatePass, trigger: 'blur' }],
	newPassword2: [{ validator: validatePass2, trigger: 'blur' }],
});

/**
 * 重新设置密码
 */
const settingPassword = () => {
	userPasswordFormRef.value.validate((valid) => {
		if (valid) {
			api.UpdatePassword(userPasswordInfo).then((res: any) => {
				ElMessage.success('密码修改成功');
        setTimeout(() => {
          Session.remove('token');
          router.push('/login');
			}, 1000);
			});
		} else {
			// 校验失败
			// 登录表单校验失败
			ElMessage.error('表单校验失败，请检查');
		}
	});
};

const uploadImg = (data: any) => {
	let formdata = new FormData();
	formdata.append('file', data);
	api.uploadAvatar(formdata).then((res: any) => {
		if (res.code === 2000) {
			selectImgVisible.value = false;
			// state.personalForm.avatar = getBaseURL() + res.data.url;
			state.personalForm.avatar = res.data.url;
			api.updateUserInfo(state.personalForm).then((res: any) => {
				successMessage('更新成功');
				getUserInfo();
				useUserInfo().updateUserInfos();
				// @ts-ignore
				avatarSelectorRef.value.updateAvatar(state.personalForm.avatar);
			});
		}
	});
};
</script>

<style scoped lang="scss">
.personal-center {
  min-width: 0;
  padding: var(--lims-space-6);
  display: grid;
  gap: var(--lims-space-6);
  color: var(--lims-text-regular);
  overflow-wrap: anywhere;
  h1 { font-size: var(--lims-type-page-title-size); line-height: var(--lims-type-page-title-line-height); font-weight: var(--lims-type-page-title-weight); color: var(--lims-text-primary); }
  h2 { font-size: var(--lims-type-section-title-size); line-height: var(--lims-type-section-title-line-height); font-weight: var(--lims-type-section-title-weight); color: var(--lims-text-primary); }
  h3 { font-size: var(--lims-type-card-title-size); line-height: var(--lims-type-card-title-line-height); font-weight: var(--lims-type-card-title-weight); color: var(--lims-text-primary); }
}
.personal-panel {
  min-width: 0;
  padding: var(--lims-space-6);
  background: var(--lims-background-card);
  border: var(--lims-border-width) solid var(--lims-border-default);
  border-radius: var(--lims-radius-card);
}
.personal-identity { display: flex; align-items: center; gap: var(--lims-space-6); }
.personal-avatar {
  flex-shrink: 0;
  text-align: center;
  :deep(.el-avatar) { border: var(--lims-border-width) solid var(--lims-border-default); }
  :deep(.user-info-head:hover::after) { color: var(--lims-text-primary); background: var(--lims-background-hover); border-radius: 50%; font-size: var(--lims-type-form-value-size); }
  p { margin-top: var(--lims-space-2); color: var(--lims-text-secondary); font-size: var(--lims-type-helper-size); }
}
.personal-identity-content { min-width: 0; flex: 1; }
.personal-username { margin-top: var(--lims-space-1); color: var(--lims-text-secondary); }
.personal-context {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 2fr);
  gap: var(--lims-space-4);
  margin-top: var(--lims-space-4);
}
.personal-context, .personal-security-details {
  dt { color: var(--lims-text-secondary); margin-bottom: var(--lims-space-2); }
  dd { margin: 0; }
}
.personal-roles { display: flex; flex-wrap: wrap; gap: var(--lims-space-2); }
.personal-sections { display: grid; grid-template-columns: minmax(0, 2fr) minmax(280px, 1fr); gap: var(--lims-space-6); align-items: start; }
.profile-form {
  margin-top: var(--lims-space-6);
  max-width: 800px;
  :deep(.el-form-item) { margin-bottom: var(--lims-space-8); }
  :deep(.el-form-item__label) { color: var(--lims-text-regular); }
  :deep(.el-select) { width: 100%; }
}
.personal-security-item {
  padding-block: var(--lims-space-6);
  border-bottom: var(--lims-border-width) solid var(--lims-border-light);
  p { color: var(--lims-text-secondary); line-height: var(--lims-type-form-value-line-height); margin-block: var(--lims-space-2) var(--lims-space-4); }
}
.personal-security-details { display: grid; gap: var(--lims-space-4); margin-top: var(--lims-space-6); }
:deep(.personal-password-dialog) {
  max-width: calc(100vw - 32px);
  .el-form-item { margin-bottom: calc(var(--lims-type-helper-line-height) * 2 + var(--lims-space-3)); }
  .el-form-item__error { line-height: var(--lims-type-helper-line-height); overflow-wrap: anywhere; }
}
@media (max-width: 1200px) {
  .personal-sections { grid-template-columns: minmax(0, 1fr); }
}
@media (max-width: 1100px) {
  .personal-center { padding: var(--lims-space-4); gap: var(--lims-space-4); }
  .personal-sections { gap: var(--lims-space-4); }
  .personal-context { grid-template-columns: minmax(0, 1fr); }
}
@media (max-width: 600px) {
  .personal-identity { flex-direction: column; align-items: flex-start; }
}
</style>
