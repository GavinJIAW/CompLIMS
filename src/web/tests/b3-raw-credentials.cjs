// Deterministic credential-boundary checks using the existing TypeScript toolchain.
// Run from src/web: node tests/b3-raw-credentials.cjs
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const ts = require('typescript');
const raw = '  Raw-input-password-2026!  ';
const read = p => fs.readFileSync('src/' + p, 'utf8');
function execute(source, deps = {}) {
  const ctx = {exports: {}, ...deps};
  vm.createContext(ctx);
  vm.runInContext(ts.transpileModule(source, {compilerOptions: {module: ts.ModuleKind.CommonJS}}).outputText, ctx);
  return ctx;
}
function script(p) {
  const source = read(p);
  return p.endsWith('.vue') ? source.match(/<script[^>]*>([\s\S]*?)<\/script>/)[1] : source;
}
function binding(p, name, deps) {
  const ast = ts.createSourceFile(p, script(p), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  let found;
  function visit(n) {
    if (ts.isVariableDeclaration(n) && n.name.getText(ast) === name) found = n.getText(ast);
    ts.forEachChild(n, visit);
  }
  visit(ast);
  assert.ok(found, name + ' exists in current source');
  return execute('const ' + found + '; exports.run = ' + name + ';', deps).exports.run;
}
let sent;
const request = config => {sent = config; return Promise.resolve({code: 4000});};
function api(p) {return execute(read(p).replace(/^import .*$/gm, ''), {request}).exports;}
const loginApi = api('views/system/login/api.ts');
const userApi = api('views/system/user/api.ts');
const personalApi = api('views/system/personal/api.ts');
const formRef = {value: {validate: async cb => {if (cb) cb(true); return true;}}};
const noop = () => {};
let count = 0;
async function check(name, action, url, fields) {
  sent = undefined;
  await action();
  await Promise.resolve();
  assert.equal(sent.url, url);
  for (const field of fields) assert.equal(sent.data[field], raw);
  count++;
  console.log('PASS ' + name);
}
(async () => {
  await check('login component to API preserves raw input', binding('views/system/login/component/account.vue', 'loginClick', {
    formRef, state: {ruleForm: {username: 'probe', password: raw}}, loginApi,
    refreshCaptcha: () => {throw new Error('unexpected login rejection');}, errorMessage: noop
  }), '/api/login/', ['password']);
  const crudSource = script('views/system/user/crud.tsx');
  assert.ok(!/valueResolve|\bMd5\b|\$md5/.test(crudSource), 'no pre-submit credential transformation');
  await check('create user request preserves raw input', () => binding('views/system/user/crud.tsx', 'addRequest', {api: userApi})({form: {username: 'probe', password: raw}}),
    '/api/system/user/', ['password']);
  await check('personal password change preserves raw input', binding('views/system/personal/index.vue', 'settingPassword', {
    userPasswordFormRef: formRef, userPasswordInfo: {oldPassword: raw, newPassword: raw, newPassword2: raw},
    api: personalApi, ElMessage: {success: noop}, setTimeout: noop
  }), '/api/system/user/change_password/', ['oldPassword', 'newPassword', 'newPassword2']);
  await check('admin reset prompt to API preserves raw input', () => binding('views/system/user/crud.tsx', 'resetPasswordRequest', {
    ElMessageBox: {prompt: async () => ({value: raw})}, api: userApi, successMessage: noop
  })({id: 7}), '/api/system/user/7/reset_password/', ['newPassword', 'newPassword2']);
  await check('must-change form to API preserves raw input', binding('views/system/login/component/changePwd.vue', 'loginClick', {
    formRef, state: {loading: {signIn: false}, ruleForm: {oldPassword: raw, password: raw, password_regain: raw}},
    loginApi, ElMessage: {success: noop}, Session: {clear: noop},
    window: {location: {assign: noop, reload: noop}}, NextLoading: {done: noop}
  }), '/api/system/user/change_password/', ['oldPassword', 'newPassword', 'newPassword2']);
  console.log(count + ' credential payload checks PASS');
})().catch(error => {console.error(error); process.exitCode = 1;});
