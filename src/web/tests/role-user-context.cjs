// Deterministic checks using the existing TypeScript dependency; no browser or DB writes.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const ts = require('typescript');
const root = path.resolve(__dirname, '../src/views/system/role');
function load(file, deps) {
 const ctx = {exports: {}, require: id => { assert.ok(id in deps, id); return deps[id]; }};
 vm.createContext(ctx);
 vm.runInContext(ts.transpileModule(fs.readFileSync(path.join(root,file),'utf8'), {compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,ctx);
 return ctx.exports;
}
let errors = [], requests = [];
const {RoleUserStores} = load('stores/RoleUserStores.ts', {
 'pinia': {defineStore: (_, options) => {const store = options.state(); for(const [key,action] of Object.entries(options.actions)) store[key] = action.bind(store); return () => store;}},
 'element-plus': {ElMessage:{error: message => errors.push(message)}}
});
const deps = {'/@/utils/service':{request:config=>{requests.push(config); return config;}}, '../../stores/RoleUserStores':{RoleUserStores}};
const main = load('components/searchUsers/api.ts',deps);
const candidate = load('components/addUsers/api.ts',deps);
const store = RoleUserStores();
const last = () => requests.at(-1);
let count=0;
function check(name,fn){fn();count++;console.log('PASS '+name);}
check('initial authorized list',()=>{store.handleDrawerOpen({id:1,name:'A'});main.getRoleUsersAuthorized({page:1,limit:20});assert.equal(last().params.role_id,1);assert.equal(last().params.authorized,1);});
check('main query and reset preserve business context',()=>{main.getRoleUsersAuthorized({name:'test',dept:3});assert.equal(last().params.dept,3);main.getRoleUsersAuthorized({page:1,limit:20});assert.equal(last().params.role_id,1);assert.equal(last().params.authorized,1);assert.ok(!('name' in last().params));assert.ok(!('dept' in last().params));});
check('add after main reset',()=>{candidate.getRoleUsersUnauthorized({page:1,limit:20});assert.equal(last().params.role_id,1);assert.equal(last().params.authorized,0);});
check('candidate query and reset preserve business context',()=>{candidate.getRoleUsersUnauthorized({name:'test',dept:3});assert.equal(last().params.dept,3);candidate.getRoleUsersUnauthorized({page:1,limit:20});assert.equal(last().params.role_id,1);assert.equal(last().params.authorized,0);assert.ok(!('name' in last().params));assert.ok(!('dept' in last().params));});
check('pagination preserves role for both lists',()=>{for(const query of [main.getRoleUsersAuthorized,candidate.getRoleUsersUnauthorized]){query({page:2,limit:10});assert.equal(last().params.role_id,1);assert.equal(last().params.page,2);assert.equal(last().params.limit,10);}});
check('role switch overrides stale search identity',()=>{store.handleDrawerClose();assert.equal(store.role_id,undefined);store.handleDrawerOpen({id:2,name:'B'});for(const query of [main.getRoleUsersAuthorized,candidate.getRoleUsersUnauthorized]){query({role_id:1});assert.equal(last().params.role_id,2);}});
check('add and single/bulk delete use stable role context',()=>{candidate.addRoleUsers([3]);assert.equal(last().url,'/api/system/role/2/add_role_users/');main.addRoleUsers([3]);assert.equal(last().url,'/api/system/role/2/add_role_users/');for(const ids of [[3],[3,4]]){main.removeRoleUser(ids);assert.equal(last().url,'/api/system/role/2/remove_role_user/');assert.deepEqual(last().data.user_id,ids);}});
check('closed/missing/invalid role fails before every HTTP request',()=>{const calls=[()=>main.getRoleUsersAuthorized({}),()=>candidate.getRoleUsersUnauthorized({}),()=>main.removeRoleUser([3]),()=>candidate.addRoleUsers([3]),()=>main.addRoleUsers([3])];store.handleDrawerClose();for(const invalid of [undefined,null,0,-1,'',NaN]){store.role_id=invalid;store.drawerVisible=true;for(const call of calls){const before=requests.length;assert.throws(call,/当前角色上下文缺失/);assert.equal(requests.length,before);}}store.role_id=1;store.drawerVisible=false;assert.throws(calls[0]);assert.ok(errors.length>0);});
check('return to role A uses fresh identity',()=>{store.handleDrawerOpen({id:1,name:'A'});candidate.getRoleUsersUnauthorized({});assert.equal(last().params.role_id,1);});
console.log(`${count} checks PASS`);
