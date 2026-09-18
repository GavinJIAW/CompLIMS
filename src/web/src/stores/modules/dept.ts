import {defineStore} from "pinia";
import {request} from "/@/utils/service";
import XEUtils from "xe-utils";
import {toRaw} from 'vue'
import { useUserInfo } from '/@/stores/userInfo';
import { BtnPermissionStore } from '/@/stores/btnPermission';

export const useDeptInfoStore = defineStore('deptInfo', {
    state:()=>(
        {
            loaded: false,
            owner: '',
            pending: undefined as Promise<void> | undefined,
            list:[],
            tree:[],
        }
    ),
    actions:{
      async ensureLoaded() {
            const owner = String(useUserInfo().userInfos.id);
            if (this.owner !== owner) {
                this.list = []; this.tree = []; this.loaded = false; this.pending = undefined; this.owner = owner;
            }
            if (!BtnPermissionStore().data.includes('dept:SearchAll')) {
                this.list = []; this.tree = []; this.loaded = false;
                return;
            }
            if (this.loaded) return;
            if (!this.pending) this.pending = this.requestDeptInfo().finally(() => { this.pending = undefined; });
            await this.pending;
        },
      async requestDeptInfo() {
            const owner = this.owner;
            // 请求部门信息
            const ret = await request({
                url: '/api/system/dept/all_dept/'
            })
            if (this.owner !== owner) return;
            this.list = ret.data
            this.tree = XEUtils.toArrayTree(ret.data,{parentKey:'parent',strict:true})
            this.loaded = true;
        },
        async getDeptById(id:any){

        },
        async getParentDeptById(id: any){
            await this.ensureLoaded();
            const tree = toRaw(this.tree)
            const obj =  XEUtils.findTree(tree, item => item.id == id)
            return  obj
        }
    }
})
