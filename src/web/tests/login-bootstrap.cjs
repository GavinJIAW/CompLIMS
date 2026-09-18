// Deterministic checks using the installed TypeScript/Vue toolchain; no new framework.
// Run: node tests/login-bootstrap.cjs [optional sanitized HTTP menu fixture JSON]
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const cp = require('node:child_process');
const XEUtils = require('xe-utils');
const read = p => fs.readFileSync(`src/${p}`, 'utf8');
const plain = x => JSON.parse(JSON.stringify(x));
let passed = 0;
async function test(name, run) { await run(); passed++; console.log(`PASS ${name}`); }
function execute(source, deps = {}) {
 const ctx = { exports: {}, console: { warn() {} }, ...deps };
 vm.createContext(ctx);
 vm.runInContext(ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText, ctx);
 return ctx;
}
function moduleSource(p) { return read(p).replace(/^import .*$/gm, ''); }
function functions(p, names, source = read(p)) {
 const ast = ts.createSourceFile(p, source, ts.ScriptTarget.Latest, true);
 return ast.statements.filter(n => ts.isFunctionDeclaration(n) && names.includes(n.name?.text)).map(n => n.getText(ast)).join('\n');
}
const navigation = execute(moduleSource('utils/navigation.ts')).exports;
const menu = execute(moduleSource('utils/menu.ts'), { XEUtils, ...navigation }).exports;
const helperNames = ['formatFlatteningRoutes', 'formatTwoStageRoutes'];
const deps = { ...navigation, pinia: {}, useKeepALiveNames: () => ({setCacheKeepAlive() {}}) };
const helpers = execute(functions('router/index.ts', helperNames), deps).exports;
const tree = rows => [{path: '/', meta: {isKeepAlive: true}, children: menu.handleMenu(plain(rows)).frameIn}];
const transform = rows => helpers.formatTwoStageRoutes(helpers.formatFlatteningRoutes(tree(rows)));
const valid = [{id: 1, parent: null, name: 'Valid', web_path: '/valid', component_name: 'valid', component: 'system/home/index'}];
const malformed = {id: 20, parent: null, name: 'UAT', web_path: null, is_catalog: true};
function store(p, extra = {}) {
 return execute(moduleSource(p), { defineStore: (_, config) => () => {const s = config.state(); for (const [k,v] of Object.entries(config.actions)) s[k] = v.bind(s); return s;}, XEUtils, toRaw: x => x, ...extra }).exports;
}
(async () => {
 await test('malformed route skipped, valid sibling and home retained', () => {
  const paths = transform([malformed,...valid])[0].children.map(x=>x.path);
  assert.deepEqual(plain(paths), ['/home','/valid']);
 });
 await test('invalid parent subtree not promoted', () => {
  const child = {...valid[0],id:21,parent:20};
  assert.deepEqual(plain(transform([malformed,child])[0].children.map(x=>x.path)),['/home']);
 });
 await test('valid routes preserve pre-fix contract', () => {
  const base = p => cp.execFileSync('git',['show',`ccc62a3871e739ff5e213eba059c6c7a017302e4:src/web/src/${p}`],{encoding:'utf8'});
  const oldMenu=execute(base('utils/menu.ts').replace(/^import .*$/gm,''),{XEUtils}).exports;
  const oldHelpers=execute(functions('router/index.ts',helperNames,base('router/index.ts')),deps).exports;
  const old=oldHelpers.formatTwoStageRoutes(oldHelpers.formatFlatteningRoutes([{path:'/',meta:{isKeepAlive:true},children:oldMenu.handleMenu(plain(valid)).frameIn}]));
  assert.deepEqual(plain(transform(valid)),plain(old));
 });
 await test('helper direct null/undefined paths are isolated and diagnosed', () => {
  const warnings=[];const n=execute(moduleSource('utils/navigation.ts'),{console:{warn:(...x)=>warnings.push(x)}}).exports;
  assert.equal(n.projectRouteTree([{path:null},{path:undefined},{path:' '},{path:'/ok'}]).length,1);
  assert.equal(warnings.length,3);
  assert.equal(helpers.formatTwoStageRoutes([{path:'/',meta:{}},{path:null},{path:'/ok',meta:{}}])[0].children.length,1);
 });
 await test('component helper filters malformed paths and accepts valid catalog', () => {
  const x=execute(functions('router/backEnd.ts',['backEndComponent','dynamicImport']),{...navigation,dynamicViewsModules:{'../layout/routerView/parent.vue':()=>{}}}).exports;
  assert.equal(x.backEndComponent([{path:null},{path:'/ok',is_catalog:true}]).length,1);
  assert.equal(x.dynamicImport({},null),undefined);
 });
 await test('critical bootstrap rejects and cleans both loading indicators', async () => {
  let loading=0,progress=0;
  const e=new Error('controlled bootstrap failure');
  const x=execute(functions('router/backEnd.ts',['initBackEndControlRoutes']),{Session:{get:()=>true},NextLoading:{start(){},done(){loading++;}},NProgress:{done(){progress++;}},useUserInfo:()=>({getApiUserInfo:()=>Promise.reject(e)})}).exports;
  await assert.rejects(x.initBackEndControlRoutes(),/controlled bootstrap failure/);
  assert.equal(loading,1);assert.equal(progress,1);
 });
 await test('global bootstrap has no dept dependency', async () => {
  const calls=[];
  const x=execute(functions('router/backEnd.ts',['getBackEndControlRoutes']),{
   BtnPermissionStore:()=>({getBtnPermissionStore:async()=>calls.push('permissions')}),
   SystemConfigStore:()=>({getSystemConfigs:async()=>calls.push('settings')}),
   DictionaryStore:()=>({getSystemDictionarys:async()=>calls.push('dictionary')}),
   menuApi:{getSystemMenu:async()=>{calls.push('menu');return {data:[]};}}
  }).exports;
  assert.deepEqual(plain(await x.getBackEndControlRoutes()),{data:[]});assert.deepEqual(calls,['permissions','settings','dictionary','menu']);
 });
 await test('optional settings/dictionary rejection is handled', async () => {
  for(const [p,name,method] of [['stores/systemConfig.ts','SystemConfigStore','getSystemConfigs'],['stores/dictionary.ts','DictionaryStore','getSystemDictionarys']]) {
   const s=store(p,{request:()=>Promise.reject(new Error('unavailable'))})[name]();await s[method]();
  }
 });
 await test('lazy dept: no authority means no request; authorized calls deduplicate', async () => {
  let grants=[],calls=0;
  const s=store('stores/modules/dept.ts',{BtnPermissionStore:()=>({data:grants}),useUserInfo:()=>({userInfos:{id:1}}),request:async()=>{calls++;return {data:[{id:1,parent:null,name:'Dept'}]};}}).useDeptInfoStore();
  await s.ensureLoaded();assert.equal(calls,0);
  grants=['dept:SearchAll'];await Promise.all([s.ensureLoaded(),s.ensureLoaded()]);assert.equal(calls,1);assert.equal(s.tree.length,1);
  grants=[];await s.ensureLoaded();assert.equal(s.tree.length,0);
 });
 await test('overlay start idempotent and cleanup removes DOM element', async () => {
  let el=null;
  const document={querySelector:()=>el,createElement:()=>({setAttribute(){},parentNode:{removeChild(){el=null;}}}),body:{childNodes:[],insertBefore:x=>{el=x;}}};
  const x=execute(moduleSource('utils/loading.ts'),{document,window:{},showUpgrade(){},nextTick:fn=>fn(),setTimeout:fn=>fn()}).exports;
  x.NextLoading.start();const first=el;x.NextLoading.start();assert.equal(el,first);x.NextLoading.done();assert.equal(el,null);
 });
 await test('router guard aborts visibly on critical failure without unhandled rejection', async () => {
  const ast=ts.createSourceFile('index.ts',read('router/index.ts'),ts.ScriptTarget.Latest,true);
  const statement=ast.statements.find(n=>n.getText(ast).startsWith('router.beforeEach(')).getText(ast);
  let guard,stops=0,notices=0,next;
  execute(statement,{router:{beforeEach:fn=>guard=fn},checkVersion:async()=>{},checkToken(){},NProgress:{configure(){},start(){},done(){stops++;}},NextLoading:{done(){stops++;}},ElMessage:{error(){notices++;}},Session:{get:()=>true},frameOutRoutes:[],useRoutesList:()=>({routesList:{value:[]}}),storeToRefs:x=>x,pinia:{},isRequestRoutes:true,initBackEndControlRoutes:async()=>{throw Error('controlled');}});
  await guard({path:'/home',meta:{}},{},value=>{next=value;});assert.equal(next,false);assert.equal(stops,2);assert.equal(notices,1);
 });
 for(const page of ['account','changePwd']) await test(`${page} login awaits navigation and cleans on failure`,async()=>{
  const vue=read(`views/system/login/component/${page}.vue`);
  assert.ok(!vue.includes('initBackEndControlRoutes'));assert.ok(vue.includes('await loginSuccess()'));
  const script=require('@vue/compiler-sfc').parse(vue).descriptor.script.content;
  const ast=ts.createSourceFile('login.ts',script,ts.ScriptTarget.Latest,true);let declaration;
  function walk(n){if(ts.isVariableDeclaration(n)&&n.name.getText(ast)==='loginSuccess')declaration=n.getText(ast);ts.forEachChild(n,walk);}walk(ast);
  let stops=0,errors=0;const state={loading:{signIn:false}};
  const x=execute('export const '+declaration+';',{state,NextLoading:{start(){},done(){stops++;}},route:{query:{}},router:{push:async()=>{throw Error('failure');}},errorMessage(){errors++;},ElMessage:{success(){throw Error('must not report success');}}}).exports;
  await x.loginSuccess();assert.equal(stops,1);assert.equal(errors,1);assert.equal(state.loading.signIn,false);
 });
 if(process.argv[2]) for(const item of JSON.parse(fs.readFileSync(process.argv[2],'utf8'))) await test(`HTTP menu replay actor ${item.actor}`,()=>{
  const out=transform(item.rows);assert.ok(!out[0].children.some(x=>x.id===20));assert.ok(out[0].children.some(x=>x.path==='/home'));
 });
 if(process.argv[2]) for(const item of JSON.parse(fs.readFileSync(process.argv[2],'utf8'))) await test(`complete bootstrap replay actor ${item.actor}`,async()=>{
  const registered=[];let projected;
  const x=execute(functions('router/backEnd.ts',['initBackEndControlRoutes','getBackEndControlRoutes','setAddRoute','setFilterRouteEnd','setFilterMenuAndCacheTagsViewRoutes','setCacheTagsViewRoutes','backEndComponent','dynamicImport']),{
   ...navigation,...helpers,handleMenu:menu.handleMenu,pinia:{},
   dynamicRoutes:[{path:'/',meta:{isKeepAlive:true},children:[]}],notFoundAndNoPower:[],dynamicViewsModules:{},
   Session:{get:()=>true},NextLoading:{start(){},done(){}},NProgress:{done(){}},
   useUserInfo:()=>({getApiUserInfo:async()=>{}}),BtnPermissionStore:()=>({getBtnPermissionStore:async()=>{}}),
   SystemConfigStore:()=>({getSystemConfigs:async()=>{}}),DictionaryStore:()=>({getSystemDictionarys:async()=>{}}),
   menuApi:{getSystemMenu:async()=>({data:plain(item.rows)})},router:{addRoute:r=>registered.push(r)},
   useRoutesList:()=>({setRoutesList:r=>projected=r}),useTagsViewRoutes:()=>({setTagsViewRoutes(){}})
  }).exports;
  await x.initBackEndControlRoutes();assert.equal(registered.length,1);assert.ok(projected.length>0);
  assert.ok(!registered[0].children.some(r=>r.id===20));
 });
 console.log(`${passed} checks PASS`);
})().catch(e=>{console.error(e);process.exitCode=1;});
