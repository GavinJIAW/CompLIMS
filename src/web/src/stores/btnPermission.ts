import {defineStore} from "pinia";
import {DictionaryStates} from "/@/stores/interface";
import {request} from "/@/utils/service";

export const BtnPermissionStore = defineStore('BtnPermission', {
    state: (): DictionaryStates => ({
        data: []
    }),
    actions: {
        async getBtnPermissionStore() {
            this.data = [];
            const ret = await request({
                url: '/api/system/menu_button/menu_button_all_permission/',
                method: 'get',
            });
            this.data = ret.data;
        },
    },
});
