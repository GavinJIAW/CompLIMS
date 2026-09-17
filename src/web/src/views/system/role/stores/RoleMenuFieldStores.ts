import { defineStore } from 'pinia';
import { RoleMenuFieldType, RoleMenuFieldHeaderType } from '../types';
/**
 * 权限配置：角色-菜单-列字段
 */

export const RoleMenuFieldStores = defineStore('RoleMenuFieldStores', {
	state: (): RoleMenuFieldType[] => [],
	actions: {
		/** 重置 */
		setState(data: RoleMenuFieldType[]) {
			this.$state = data;
			this.$state.length = data.length;
		},
	},
});

export const RoleMenuFieldHeaderStores = defineStore('RoleMenuFieldHeaderStores', {
	state: (): RoleMenuFieldHeaderType[] => [
		{ value: 'is_create', label: '允许新增字段', disabled: 'disabled_create', checked: false },
		{ value: 'is_update', label: '允许修改字段', disabled: 'disabled_update', checked: false },
		{ value: 'is_query', label: '允许读取字段（同菜单共享）', disabled: 'disabled_query', checked: false },
	],
});
