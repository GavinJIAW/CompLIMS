import { defineStore } from 'pinia';
import { ElMessage } from 'element-plus';

/**
 * 权限抽屉：角色-用户
 */

export const RoleUserStores = defineStore('RoleUserStores', {
	state: (): any => ({
		drawerVisible: false,
		role_id: undefined,
		role_name: undefined,
	}),
	actions: {
		getCurrentRoleId(): number {
			const id = this.role_id;
			if (!this.drawerVisible || !Number.isSafeInteger(id) || id <= 0) {
				const message = '当前角色上下文缺失，请重新打开授权用户。';
				ElMessage.error(message);
				throw new Error(message);
			}
			return id;
		},
		/**
		 * 打开权限修改抽屉
		 */
		handleDrawerOpen(row: any) {
			this.role_name = row.name;
			this.role_id = row.id;
			this.drawerVisible = true;
		},
		/**
		 * 关闭权限修改抽屉
		 */
		handleDrawerClose() {
			this.drawerVisible = false;
			this.role_id = undefined;
			this.role_name = undefined;
		},
	},
});
