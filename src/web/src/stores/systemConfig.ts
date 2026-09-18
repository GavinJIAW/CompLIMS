import { defineStore } from 'pinia';
import { ConfigStates } from './interface';
import { request } from '../utils/service';
export const urlPrefix = '/api/init/settings/';

/**
 * 系统配置数据
 * @methods getSystemConfig 获取系统配置数据
 */
export const SystemConfigStore = defineStore('SystemConfig', {
	state: (): ConfigStates => ({
		systemConfig: {},
	}),
	actions: {
		async getSystemConfigs() {
			return request({
				url: urlPrefix,
				method: 'get',
			}).then((ret: { data: [] }) => {
				// 转换数据格式并保存到pinia
				this.systemConfig = JSON.parse(JSON.stringify(ret.data));
			}).catch(() => {
                console.warn('Optional bootstrap data unavailable: getSystemConfigs');
            });
		},
	},
	persist: {
		enabled: true,
	},
});
