import { request,downloadFile } from '/@/utils/service';
import { PageQuery, AddReq, DelReq, EditReq, InfoReq } from '@fast-crud/fast-crud';

export const apiPrefix = '/api/system/user/';

// Keep full rows out of write requests, including hidden FastCrud form values.
export function userWritePayload(source: object, create: boolean) {
    const values = source as Record<string, unknown>;
    const fields = ['username', 'name', 'email', 'mobile', 'avatar', 'gender', 'user_type', 'is_active'];
    if (create) fields.push('password');
    return Object.fromEntries(fields
        .filter((key) => Object.prototype.hasOwnProperty.call(values, key))
        .map((key) => [key, values[key]]));
}

export function GetDept(query: PageQuery) {
    return request({
        url: "/api/system/dept/all_dept/",
        method: 'get',
        params: query,
    });
}

export function GetList(query: PageQuery) {
    return request({
        url: apiPrefix,
        method: 'get',
        params: query,
    });
}
export function GetObj(id: InfoReq) {
    return request({
        url: apiPrefix + id,
        method: 'get',
    });
}

export function AddObj(obj: AddReq) {
    return request({
        url: apiPrefix,
        method: 'post',
        data: userWritePayload(obj, true),
    });
}

export function UpdateObj(obj: EditReq) {
    return request({
        url: apiPrefix + obj.id + '/',
        method: 'put',
        data: userWritePayload(obj, false),
    });
}

export function DelObj(id: DelReq) {
    return request({
        url: apiPrefix + id + '/',
        method: 'delete',
        data: { id },
    });
}

export function exportData(params:any){
    return downloadFile({
        url: apiPrefix + 'export_data/',
        params: params,
        method: 'get'
    })
}


export function resetPassword(id: any, password: string){
    return request({
        url: apiPrefix  + id + '/reset_password/',
        method: 'put',
        data: { newPassword: password, newPassword2: password }
    })
}
