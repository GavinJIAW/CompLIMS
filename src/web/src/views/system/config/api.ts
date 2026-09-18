import { request } from '/@/utils/service';
import { UserPageQuery, AddReq, DelReq, EditReq, InfoReq } from '@fast-crud/fast-crud';
import XEUtils from 'xe-utils';

export const apiPrefix = '/api/system/system_config/';
export function GetList(query: UserPageQuery) {
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
		data: obj,
	});
}

export function UpdateObj(obj: EditReq) {
	return request({
		url: apiPrefix + obj.id + '/',
		method: 'put',
		data: obj,
	});
}

export function DelObj(id: DelReq) {
	return request({
		url: apiPrefix + id + '/',
		method: 'delete',
		data: { id },
	});
}

/*
获取所有的model及字段信息
 */
export function GetAssociationTable() {
	return request({
		url: apiPrefix + 'get_association_table/',
		method: 'get',
		params: {},
	});
}

// Custom mutation contract: id is a target identity, not a writable model field.
const saveContentFields = [
    'id', 'title', 'key', 'value', 'parent', 'sort', 'status', 'description',
    'data_options', 'form_item_type', 'rule', 'placeholder', 'setting',
] as const;

export function projectSystemConfigSaveContent(items: Record<string, unknown>[]) {
    return items.map(item => Object.fromEntries(
        saveContentFields.filter(field => Object.prototype.hasOwnProperty.call(item, field))
            .map(field => [field, item[field]])
    ));
}

export function saveContent(data: Record<string, unknown>[]) {
	return request({
		url: apiPrefix + 'save_content/',
		method: 'put',
		data: projectSystemConfigSaveContent(data),
	});
}
