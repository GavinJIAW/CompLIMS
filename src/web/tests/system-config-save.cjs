// Run with Node and the existing TypeScript dependency. --project accepts test rows on stdin.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const ts = require('typescript');
const path = require('node:path');
const root = path.resolve(__dirname, '../src');
function load(file, deps = {}) {
 const source = fs.readFileSync(path.join(root, file), 'utf8').replace(/^import .*$/gm, '');
 const ctx = { exports: {}, ...deps }; vm.createContext(ctx);
 vm.runInContext(ts.transpileModule(source, {compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText, ctx);
 return ctx.exports;
}
const {projectCrudPayload} = load('utils/accessPayload.ts');
let sent;
const api = load('views/system/config/api.ts', {request: config => {sent = projectCrudPayload(config);return Promise.resolve(sent);}});
const plain = x => JSON.parse(JSON.stringify(x));
if (process.argv.includes('--project')) {
 api.saveContent(JSON.parse(fs.readFileSync(0,'utf8'))).then(() => process.stdout.write(JSON.stringify(sent.data)));
} else {
(async () => {
 const allowed = ['id','title','key','value','parent','sort','status','description','data_options','form_item_type','rule','placeholder','setting'];
 const row = {id:7,title:'Test',key:'test',value:'old',parent:1,sort:0,status:false,description:null,data_options:[],form_item_type:0,rule:[],placeholder:'',setting:{},children:[],create_datetime:'2026-01-01',creator:1,creator_name:'Test actor',dept_belong_id:1,form_item_type_label:'input',modifier:'1',modifier_name:'Test actor',update_datetime:'2026-01-01',unexpected_field:'future'};
 let count=0;
 function check(name,fn){fn();count++;console.log('PASS '+name);}
 const before = plain(row);const projected=plain(api.projectSystemConfigSaveContent([row]))[0];
 check('full read object uses exact write allowlist',()=>assert.deepEqual(Object.keys(projected).sort(),allowed.slice().sort()));
 check('future field absent',()=>assert.ok(!('unexpected_field' in projected)));
 check('children absent',()=>assert.ok(!('children' in projected)));
 check('audit fields absent',()=>['creator','modifier','create_datetime','update_datetime','dept_belong_id'].forEach(k=>assert.ok(!(k in projected))));
 check('display fields absent',()=>['creator_name','modifier_name','form_item_type_label'].forEach(k=>assert.ok(!(k in projected))));
 row.value='edited';await api.saveContent([row,{...row,id:8,value:false}]);
 check('actual saveContent sends edited values and target IDs for every item',()=>{assert.equal(sent.method,'put');assert.equal(sent.url,'/api/system/system_config/save_content/');assert.deepEqual(plain(sent.data).map(x=>[x.id,x.value]),[[7,'edited'],[8,false]]);sent.data.forEach(x=>assert.deepEqual(Object.keys(x).sort(),allowed.slice().sort()));});
 check('projection preserves UI read state',()=>{assert.deepEqual(before,{...row,value:'old'});assert.ok('children' in row);});
 check('null false zero and empty values retained',()=>{assert.equal(projected.status,false);assert.equal(projected.sort,0);assert.equal(projected.description,null);assert.equal(projected.placeholder,'');});
 await api.AddObj(row);
 check('standard create still uses existing CRUD ceiling',()=>{assert.equal(sent.method,'post');assert.equal(sent.url,'/api/system/system_config/');assert.ok(!('id' in sent.data));assert.ok(!('creator' in sent.data));assert.equal(sent.data.value,'edited');});
 await api.UpdateObj(row);
 check('standard detail update still uses existing CRUD ceiling',()=>{assert.equal(sent.method,'put');assert.equal(sent.url,'/api/system/system_config/7/');assert.ok(!('children' in sent.data));assert.ok(!('creator' in sent.data));assert.equal(sent.data.value,'edited');});
 console.log(`${count} checks PASS`);
})().catch(error=>{console.error(error);process.exitCode=1;});
}
