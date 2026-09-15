# CompLIMS Fast CRUD Configuration Guide

> 长期工程 Guide · 源码复核日期：2026-09-14
> 范围：当前 Fast CRUD 接入方式、可复用配置约定与维护边界。
> 本文不实施 UI、不定义 LIMS 业务规则，不替代 AGENTS.md、UI 设计方案或未来 Feature / Phase SPEC。

## 1. Purpose and Evidence Labels

为以后普通 CRUD 页面提供统一配置依据，优先复用现有框架能力。本文使用以下标记，不能把建议理解为已完成改造：

- **Current**：本次从 CompLIMS 当前文件重新核验的静态事实；不代表服务已启动或接口已通过运行回归。
- **Recommended**：未来获准任务的配置约定；对既有页面仍须遵守冻结边界。
- **Caution**：已发现的差异、兼容风险或需要另行验证的事项，不构成修改授权。
- **Required**：用户及仓库已经确认的长期约束。

本次完整阅读三份规则文档，检查 package.json、yarn.lock、main.ts、settings.ts、utils、theme、system 与 template，搜索所有 crud.tsx、useFs/useCrud/useExpose、auth、compute、dict/dictionary、commonCrud 和样式接入。代表性模式按第 17 节核对。只进行静态读取；未安装依赖、运行页面、发送业务请求或验证后端安全实施情况。

## 2. Authority and Sources

**Required — 配置决策依据：**

1. 当前任务 / 已确认 Feature / Phase SPEC。
2. `AGENTS.md`。
3. 当前真实源码和 API Contract。
4. `docs/UI_REDESIGN_PLAN.md`。
5. `docs/FAST_CRUD_CONFIGURATION_GUIDE.md`。
6. `docs/FastCrud-doc/` 本地参考快照。

上列是任务与配置决策的约束顺序；判断“是否已经实现”仍遵循 AGENTS 的 Source of Truth，不能用任何计划覆盖源码事实。P0 安全相关行为参考 `docs/P0_REMEDIATION_PLAN.md`，本文不复制其整改内容，也不宣称整改已落地。

## 3. Version and Environment Baseline

**Current — 下表重新读取当前 package.json 声明及 yarn.lock 对应条目所得。版本与迁移前文档相同，但结论来自本次核验。**

| Package | package.json declaration | yarn.lock resolved version |
| --- | --- | --- |
| @fast-crud/fast-crud | ^1.21.2 | 1.28.7 |
| @fast-crud/fast-extends | ^1.21.2 | 1.28.7 |
| @fast-crud/ui-element | ^1.21.2 | 1.28.7 |
| @fast-crud/ui-interface | ^1.21.2 | 1.28.7 |
| element-plus | ^2.8.0 | 2.14.5 |

Current：本地 Fast CRUD changelog 在 `docs/FastCrud-doc/guide/other/changelogs/packages/fast-crud/CHANGELOG.md`，包含 1.28.7；这不保证快照内每一篇内容均与锁定版本完全同步。本文配置合并说明另检查了本机已存在的 Fast CRUD 发行代码，按钮弃用说明另检查了 Element Plus 的 use-button 实现；这些安装产物不是仓库正式参考入口。

Required：Node **20.19.5**，包管理器 **Yarn**。开发前执行 `cd src/web`、`nvm use 20.19.5`。已有 package-lock.json 属历史遗留，不删除、不更新，不运行 npm install，不生成 pnpm-lock.yaml。本迁移任务不安装或升级依赖。

Current：package.json 的脚本是 dev、build:dev、build、build:local、lint-fix；没有独立 test/typecheck 脚本。lint-fix 会写文件。manifest 的 engines 范围较宽，不替代 AGENTS 的环境约定。后端环境若涉及后续任务，统一 `cd src/backend`、`conda activate dvadmin3_env`。

Caution：声明范围不等于锁定版本或部署运行版本。依赖变更须单独审查四个 Fast CRUD 包与 Element Plus 的兼容性；不因本文核验顺手固定版本或清理锁文件。

## 4. Fast CRUD Layout Freeze

**Required — 保留 Fast CRUD Layout，修改 Visual Skin。Configuration first，CSS second。**

现有页面原则上保留 `index.vue + crud.tsx + api.ts` 分层及已有 `fs-page / fs-crud` 结构。嵌套 Drawer 内直接使用 fs-crud 等既有组合也保持，不为形式统一补壳。

Search、Actionbar、Toolbar、Table、Pagination、Form、Dialog 继续由 Fast CRUD 管理。除非明确任务要求结构调整，不得为了视觉统一：

- 自建 FilterBar 替换 Fast CRUD Search。
- 把 Add / Import / Export 搬出 Actionbar，或在 PageHeader 复制入口。
- 重建 Toolbar、Pagination、CRUD Dialog / Form。
- 使用另一套 DataTable 替代或包装 fs-crud。
- 为样式目的重写 useFs / useCrud / useExpose。
- 在 Fast CRUD 外重复维护 CRUD request/query/loading/pagination state。
- 通过 CSS order、absolute 定位等方式变相搬移原生区域。

UI 接入顺序：**Design Tokens → Element Plus Theme → Fast CRUD Theme → crud.tsx Visual Configuration**。这与 Configuration first / CSS second 不冲突：组件语义和页面布局意图先用配置表达，CSS 仅提供主题皮肤；顺序不授权修改被冻结的行为。

允许 typography、colors、spacing、density、header/row/button/dialog/form appearance、列宽/对齐、form col/span、原位置 status/empty/loading renderer。禁止借视觉任务改变 request、API contract、query/pagination mapping、permission、show/disabled、valueBuilder/valueResolve、dict behavior、refresh/submit lifecycle。

**现有 System CRUD 不强制增加 PageHeader**，不改造为新操作栏或 Section Layout。UI Batch 3 为 FastCrud Visual Standardization。未来复杂独立页面是否采用 PageHeader / workspace 由相应 SPEC 决定。

## 5. Current Configuration Architecture

| 文件 / 层 | Current 职责与证据 |
| --- | --- |
| `src/web/src/main.ts` | 创建 Vue app，安装 Pinia、Router、Element Plus、i18n 和 settings 导出的 fastCrud 插件；注册指令。导入 RegisterPermission，但未调用该函数。 |
| `src/web/src/settings.ts` | 先 app.use(ui-element)，后安装 FastCrud；配置 dictRequest、commonOptions、上传/编辑器扩展、logger，并修改部分字段类型默认值。 |
| `src/web/src/utils/commonCrud.ts` | 页面主动展开的列配置片段，不是 FastCrud 安装全局选项；活动输出为 create_datetime/update_datetime，其他元数据列仍在注释中。 |
| `src/web/src/utils/dictionary.ts` | 从 DictionaryStore 的 toRaw(data) 取数组；给定 key 时按 value 严格匹配返回 label 或空字符串。它本身不创建 FastCrud Dict 实例。 |
| `src/web/src/stores/dictionary.ts` | 请求初始化字典，按 type 将部分值转换成 Number/boolean，持久化字典数据。 |
| `src/web/src/utils/authFunction.ts` | auth/auths/authAll 读取按钮权限 store，返回前端展示判断。 |
| `src/web/src/utils/columnPermission.ts` | 提供列权限查询及 handleColumnPermission 配置处理；不是自动挂到所有 CRUD 的全局钩子。 |
| `src/web/src/utils/service.ts` | 当前 system/template api.ts 引用的 request/downloadFile 封装，负责 Axios、序列化、认证头和响应处理。 |
| `src/web/src/utils/request.ts` | 另一 Axios 实现，其认证头与成功码判断不同；不能因名称相近替换 service。 |
| 各页 index.vue | refs/context、既有周边树/抽屉/插槽、初始化及刷新。 |
| 各页 crud.tsx | request 适配回调、columns/search/form/actions、字典、权限和页面 hooks。 |
| 各页 api.ts | URL、method、参数及对 service 的调用。 |

Recommended：只在真正稳定、跨页面共用时提升配置层级。页面专用权限、父子 ID、业务校验、状态转换、删除文案均不应提升到全局。

## 6. Configuration Merge and Precedence

**Current — 已用本地 `guide/advance/cover.md`、`options.md` 及安装包合并代码交叉核验。** 原先“commonOptions → 字段类型 → useFs/useCrud 生成配置”不能解释为真实覆盖顺序；生成的事件配置在公共/页面配置之前合并。

通常从低到高理解为：

```text
Fast CRUD built-in defaults
→ useFs/useCrud generated event configuration
→ global commonOptions
→ field type configuration（按字段合并插件）
→ page CrudOptions
```

上述保留了五种配置来源，但不是单次平铺对象合并：当前实现先组合 default/common/page，执行配置插件，再把默认项、生成事件、公共项和处理后的页面项合并，最后 buildColumns 分发。插件的 before 选项和动态对象可能影响具体结果。不要重写此管线。

字段通常优先级（高→低）：

| 位置 | 优先级 |
| --- | --- |
| column | page column > type column |
| search | page search > type search > page form > type form |
| mode form | page add/edit/viewForm > type add/edit/viewForm > page form > type form |

Recommended：只覆盖必要叶子属性；需要清除继承值时，可依 API 使用 null，先确认该属性允许置空。不要为了一个按钮复制整套 commonOptions。动态 compute 对象不具有普通静态配置的同等合并特性，优先计算叶子值。

Caution：CrudOptions 是生成输入，crudBinding 是组件实际绑定。不要假设修改普通原始配置对象会自动更新生成绑定。现有 resetCrudOptions/刷新调用顺序应保持，视觉任务不另建同步机制。

## 7. Current Global Installation Defaults

**Current — settings.ts 当前显式提供：**

- dictRequest 使用 service.request，传入 url、dict.params；普通结果取 res.data，isTree 时用 XEUtils.toArrayTree，parentKey 为 parent。
- commonOptions.request 提供第 8 节的 transformQuery / transformRes。
- form.wrapper.buttons：ok 为空配置；cancel、reset、copy、paste 的 show 均为 false。
- form.afterSubmit 仅在 res?.code == 2000 时发送 successNotification；这不是后端验证，也不是完整提交生命周期的替代实现。
- 全局 search 配置块被注释；没有启用该块中的 multi-line/collapse。
- 编辑器注册 FsExtendsEditor，wangEditor.width 为 300；上传配置见第 15 节。
- setLogger 的 level 为 error；FastCrud 安装选项另含 logger.off.tableColumns=false。
- dict-cascader/checkbox/radio/select/switch/tree 类型的 column.component.color 为 auto，column.align 为 center。
- text/textarea/input/password 类型通过条件分支设置中文 placeholder 和列居中。
- FastCrud 安装参数中的 i18n 仅为注释；不能把 app 安装 vue-i18n 等同于 FastCrud 已显式接入。

**Caution：当前 commonOptions 未显式设置全局 stripe/border/highlight-current-row、pagination layout、Toolbar type/link/plain、rowHandle 对齐、form labelWidth/col/span 或统一 640px Dialog。未设置项由框架和页面配置决定。** 不保留“全局取消可见”“全局单列表单”“已实施搜索布局”等错误事实。

Recommended：以后获准设置共享视觉默认值时，必须覆盖普通 CRUD、树表、嵌套页、日志、弹层的回归；取消按钮 show、字典 auto 染色等当前行为仍冻结。

## 8. Request / Response Contract

**Current — settings.ts：**

| 输入 | 转换 |
| --- | --- |
| page.currentPage / page.pageSize | page / limit |
| sort.asc !== undefined | 在 form.ordering 写入升序 prop 或降序 -prop |
| form | 展开到查询顶层；代码顺序为 `{page, limit, ...form}` |
| res.data / res.page / res.limit / res.total | records / currentPage / pageSize / total |

Current：service.request 默认配置含 getBaseURL()、50 秒 timeout，并可由调用参数覆盖；从 Session 获取 token 后附加 JWT 前缀。查询序列化过滤空字符串，将 boolean 转成 True/False。普通响应保留项目 envelope，code 2000 分支返回 dataAxios；blob 返回 Axios response，另有 swagger/无 code 分支。不能在 API 层重复解包成数组再交给 transformRes。

Current：Role 的 pageRequest 调用 GetList(query)，editRequest 将 row.id 写入 form.id 后调用 UpdateObj，delRequest 用 row.id，addRequest 用 form；role/api.ts 保留具体 URL 和 method。Template 的 exportData 使用 downloadFile；普通列表与 blob 下载不能共用错误的解包假设。

Recommended：沿用现有 api.ts 命名及各端点契约，不照抄伪代码发明 create/update/remove 方法。新的特殊端点若不符合 envelope，先明确 SPEC/API Contract，再局部适配。视觉任务不得改排序、分页、日期查询字段或提交/刷新时机。

## 9. Page Initialization and Composition

Current：Role、Areas、Dictionary、MessageCenter、Template 使用 useFs；User、FileList、DownloadCenter 存在 useExpose + useCrud。保留已经工作着的初始化方式，不为样式统一迁移 hooks。

Recommended：新获准普通 CRUD 可从 useFs 开始，保留原生结构。例如以下只是初始化形状，不是新增业务实现：

```vue
<template>
  <fs-page>
    <fs-crud ref="crudRef" v-bind="crudBinding" />
  </fs-page>
</template>
<script setup lang="ts">
import { onMounted } from 'vue';
import { useFs } from '@fast-crud/fast-crud';
import { createCrudOptions } from './crud';
const { crudRef, crudBinding, crudExpose } = useFs({ createCrudOptions });
onMounted(() => crudExpose.doRefresh());
</script>
```

实际页面若需列权限或父上下文初始化，必须保留其准备完成后 reset/refresh 的顺序，不能照抄上述最小示例覆盖它。context 用于已有父树、抽屉与页面状态，不用于在框架外重建 CRUD state。

## 10. Columns, Search and Forms

Recommended：columns 的 key 同时承载 column/search/form 配置；使用 type 获得字段基础能力，再设置必要的叶子属性。

- Search：通过 search.show 表达是否加入搜索。不要把 disabled 当作隐藏的同义词。既有 Search 布局与查询/清空/折叠机制保持。
- Table：列宽、minWidth、alignment 在 column 配置；真实数值右对齐，编号保持字符串语义，不能丢前导零。原 rowKey、fixed、selection、列权限、排序事件保持。
- Form：共享 form 放共同行为，addForm/editForm/viewForm 放模式差异；视觉调整只在允许的外观及 col/span 范围内。
- valueBuilder/valueResolve 属于数据转换，不是格式美化。日期范围、dict、ID、上传值的转换不可在 UI 批次修改。
- 校验与提交 hooks 沿用框架；客户端规则不能承诺服务端约束成立。不得新建 CRUD Form/Dialog 或独立 sticky 保存栏。

Current：Role 显式 form.col.span=24、labelWidth=100px、Dialog width=600px，并非全局 640px；没有旧文档描述的响应式两字段搜索布局。commonCrud 的日期搜索将范围写入 *_after/*_before 后删除原字段，默认宽度 160、居中并支持排序；不能作为所有审计字段已标准化的证据。

Caution：commonCrud 中 picker-options / picker.$emit 等历史写法需另行核验当前日期组件兼容性，不能宣称快捷日期已通过运行验证。

## 11. Actions, Toolbar, Dialog and Drawer

Required：Add / Import / Export 保留在既有 Actionbar；Toolbar 继续承载原生表格工具；Pagination 继续使用原分页映射。PageHeader 不接管这些能力。

Recommended：按钮语义由 Fast CRUD / Element Plus props 控制。以后获准视觉调整可使用 `link: true` 搭配 `type: 'primary'`、`type: 'danger'` 或中性类型；保留 show/disabled/order/click/确认/请求。

Current：安装的 Element Plus use-button 实现对 `type: 'text'` 给出以 link 替代的弃用提示，当前 Areas、Template、OperationLog 等配置仍使用旧写法。Role 的 remove 仅显式配置 show:auth('role:Delete')，没有显式 danger/link；其 assignment/permission 为 type:'primary'。**不存在可继承的“Role 删除外观已修正”实施结论。**

Recommended：删除确认沿用 Fast CRUD table.remove 及既有生命周期，未来如需更改文案/策略应有独立明确范围。不要为皮肤修改确认方式、saveRemind、关闭守卫、取消按钮可见性或提交生命周期。

Current：RoleDrawer 使用 80% Drawer、before-close 与 destroy-on-close；SubDict 使用 70% Drawer 包含 fs-crud，并有关闭确认。这些是页面上下文容器，不表示已有 CRUD 编辑器应全部改 Drawer。

未来新交互的容器选择遵循 SPEC：短编辑可用原生 Dialog，较长且需保留上下文时可评估原生 Drawer，复杂执行/复核交互评估独立页面。不能反向据此重写既有 CRUD。

## 12. Dictionaries and Reactive Configuration

Current：页面常以 `dict({ data: dictionary('button_status_bool') })` 接入应用字典，也存在本地数组与带 URL 的 Dict。settings 的 dictRequest 负责远程结果适配；dictionary 工具本身仅查询 store。DictionaryStore 对 type=1 转 Number、type=6 转 boolean；现有值类型、label、颜色规则和加载时机全部保持。

Recommended：稳定共享码表优先现有 store；API 所有或依赖上下文的选项使用合适远程字典；明确 value/label/children 对应字段，区分显示 label 与提交 value。使用默认值前检查数据就绪；对大数据量/权限过滤选项评估现有选择器，不能无界加载所有记录。

Caution：dictionary(name,key) 直接访问对应数组；未加载数据不等于已安全返回空。不要未经验证修改其缓存、就绪或错误行为。未来 StatusTag 只能做允许的原位置显示映射，不重写既有 dict；本文不创建 LIMS 状态枚举。

Current：Role 的操作列宽使用 Vue computed 读取权限；其开关 onChange 使用 Fast CRUD compute 返回调用 API 的回调。MessageCenter 通过 useCompute 获取 compute，并结合 row/form/context 配置选择器与编辑器。compute 不等于 Vue computed，onChange 中的写请求更不能当作纯颜色代码删除。

Recommended：静态值优先；页面级响应数据使用 ref/computed；依赖 row/form 的叶子使用 Fast CRUD compute。动态对象可能失去深合并特性；异步计算的使用限制先查本地 API 并验证当前版本，不引入额外请求状态机。

## 13. Backend Is Authoritative

Required：Frontend auth / show / disabled 仅负责 UX / presentation。正式 Permission 必须由 Backend 强制；Frontend Validation 不替代 Serializer Validation、Service Validation、Database Constraint 或 Transaction。隐藏按钮/列不证明接口授权正确。

Current：authFunction.auth 用按钮权限 store.data.some 判断字符串。Areas 与 LoginLog 在 mounted 中 await handleColumnPermission，再 resetCrudOptions、doRefresh。该工具仅处理接口返回的匹配字段，保留指定排除字段；禁查时设置 column.show=false 和 columnSetDisabled=true，并设置 addForm/editForm.show。不是所有页面都自动接入。

Recommended：新动作权限标识必须来自已确认后台契约，不能根据页面名称自行发明。已有权限初始化、缺失字段处理、show/disabled 和列设置逻辑均不得在视觉任务修改。P0 行为按独立计划核对，不在本 Guide 宣称后端权限已全面验收。

## 14. Slots and Custom Components

Recommended：标准配置优先，已有原生插槽用于必要局部渲染，不替换容器。模板插槽适合 Vue 标记；TSX 配置可按 API 使用 crudOptions.slots；自定义字段必须匹配 v-model/value 契约，组件定义按需要用 shallowRef。

Current：User 使用 cell_avatar；Template 使用 cell_url 与 actionbar-right 的 importExcel；MessageCenter 使用 header-middle 放原有 tabs。Areas 引用现有 tableSelector。保留这些插槽的位置与权限，不能照抄文档示例把导入移到 Toolbar。

Required：外部通用示例中的自定义 default 容器能力不豁免项目 Layout Freeze。只在未来明确 SPEC 要求时评估结构扩展，不能新增 DataTable 包装 fs-crud。

## 15. Uploader Configuration

Current：settings.ts 注册 FsExtendsUploader，defaultType=form，action=/api/system/file/，name=file，withCredentials=false。uploadRequest 使用 FormData，POST 通过 service.request，timeout=60000，multipart header，并把上传进度转换成百分比。

Current：successHandle 返回的对象顺序是 `{url: getBaseURL(ret.data.url), key: ret.data.id, ...ret.data}`；末尾展开可能覆盖同名字段，不能简化描述为“保证返回归一化 URL”。valueBuilder 另调用 getBaseURL(row[key])。这是现有契约记录，不是本次修复。

Recommended：复用传输入口，页面仅配置经确认的文件类型/数量/大小/展示需求；先明确存储 key、URL、预览和删除权限，以及“清空关联”和“删除文件”的区别。视觉改造不改 header、FormData、返回形状、valueBuilder 或上传生命周期。不在配置或文档放入凭据。

## 16. Theme / Global SCSS Boundary

Current：main.ts 引入 Element Plus CSS、theme/index.scss、VXE CSS、assets/style/reset.scss 等；settings.ts 引入 FastCrud 与 fast-extends 的 dist/style.css。实际级联需以构建结果和浏览器 computed styles 验证，不能只凭入口文本顺序断言。

Current：真实专用文件为 `src/web/src/theme/fastCrud.scss`。其现内容只有 fs-page 白底、10px 圆角和 88vh!important；theme/index.scss 及 src 的引用搜索未发现接入。不能称为已生效的统一 FastCrud 主题。活动 reset.scss 则对 fs-crud-container 的表头颜色与 placeholder 做硬编码覆盖。

Recommended：延用 UI 方案的 theme 目录与未来 tokens，改写专用样式后才接入；不要直接导入上述旧高度规则。设计 token 尚属计划，本文不声称已有完整 Light/Dark 视觉标准实施。

| 层级 | 允许职责 |
| --- | --- |
| Global config | 真正全局稳定规则；视觉任务只碰已授权视觉默认项 |
| crud.tsx | 页面 behavior / layout intent / button props；既有行为在 UI 范围内冻结 |
| Element Plus | 组件语义、props 与可用交互 |
| Global SCSS | spacing / density / typography / surface / limited responsive presentation |

**Required：Global SCSS 禁止强制覆盖页面 action semantics：type、link、plain、danger、primary、success。** 不把所有 rowHandle/Toolbar 按钮强制变成链接、透明或同一颜色。先在 Fast CRUD / Element Plus configuration 表达语义，再由 token 提供相应皮肤。

桌面验收至少 1366 / 1440 / 1920；宽表使用原生横向滚动，不能挤小字体或重建分页。Light/Dark 检查弹层、下拉、日期、上传和编辑器。现有 Search 折叠/展开行为不改，CSS 只改善原区域呈现。

## 17. Current Project Patterns

以下为本次重新核查的真实用例，不是预先选定的 LIMS 架构：

| Pattern | 当前路径与行为 | 保留点 |
| --- | --- | --- |
| Standard CRUD | `src/web/src/views/system/role/index.vue`、同目录 crud.tsx/api.ts：useFs、权限动作、请求分层 | 原生 CRUD 与 Role 上下文 |
| Parent / Child CRUD | `src/web/src/views/system/dictionary/crud.tsx` 向 subDict 设置 parent=row.id 后刷新；`subDict/crud.tsx` 新增从搜索上下文取 parent | 父标识与刷新时机，70% Drawer |
| Side Tree + CRUD | `src/web/src/views/system/user/index.vue`：组织树点击 doSearch({form:{dept:id}})，useExpose/useCrud | 组织筛选与原页面结构 |
| Tree / Lazy Table | `src/web/src/views/system/areas/crud.tsx`：lazy、rowKey=id、treeProps、按 pcode=tree.code 加载，pagination.show=false | 不套普通分页行为 |
| Read-only Log presentation | `src/web/src/views/system/log/operationLog/crud.tsx`：隐藏 add/edit/remove，保留 view/搜索 | 只读是展示模式；文件仍定义写请求回调，不代表后端写接口不存在 |
| Contextual Drawer | `src/web/src/views/system/role/components/RoleDrawer.vue` 与角色页传入的 stores/context | 原关闭守卫、权限配置和授权用户入口 |
| Contextual Tabs | `src/web/src/views/system/messageCenter/index.vue` 的 send/receive tabs；crud.tsx 按上下文选择请求及动作、含 editor-wang5 | 原 tabs、请求选择与只读控制 |

Caution：`src/web/src/views/template/` 仍包含 VIEWSETNAME/COLUMNS_CONFIG 占位、user:Import 权限和旧 text 按钮。它是模板材料，不是可不经审查直接复制的正式业务页。System demo 也不能作为已实现 LIMS 的证据。

## 18. Inventory Findings and Cautions

Current：本次通过 `rg --files src/web/src -g crud.tsx` 重新枚举，并搜索 hook、dict/dictionary、compute、auth、commonCrud、按钮与样式。为避免把注释、导入、配置与运行调用混为一谈，本文不继承迁移前的词法计数，也不把出现次数作为长期验收条件。

| 事实 / 差异 | 源码依据 | 建议边界 |
| --- | --- | --- |
| legacy type:'text' | areas、template、operationLog 的 crud.tsx | 以后获准视觉批次局部替换 props，不改动作 |
| Role 未显式设置 danger-link remove | role/crud.tsx | 删除“已修正”叙述；不可继承其他实施状态 |
| mixed initialization | user/fileList/downloadCenter 与 role/areas 等 | 保留现有 hooks，不机械迁移 |
| shared helper 只输出两类时间字段 | utils/commonCrud.ts | 不是完整字段标准；扩展需真实复用需求 |
| search.disabled 与 show 混杂 | areas/crud.tsx、operationLog/crud.tsx | 不猜测等价；问题验证与行为修复单独处理 |
| 广泛 any 与手动 ID/日期转换 | role/crud.tsx、commonCrud.ts 等 | 后续类型工作围绕真实契约，不伴随 UI 改写 |
| 两种 request 封装 | utils/service.ts、utils/request.ts | 不按名称替换；当前 CRUD api.ts 使用 service |
| 表面样式与主题接入未统一 | theme/fastCrud.scss、assets/style/reset.scss | 按 UI 方案渐进接入，不声称既有皮肤已完成 |
| 成功提示依赖 code 2000 | settings.ts、service.ts | 特殊返回契约须明确适配，不全局放宽判断 |

这些发现只定位维护风险，不授权源代码清理。

## 19. Future Usage and Open Questions

Recommended：普通 Master Data CRUD 优先 Fast CRUD；复杂 workflow、test execution、dynamic result entry、result review、report approval 根据未来 SPEC 决定是否采用 dedicated page/workspace。本文不为 Customer、Project、Specimen、TestRun、Result、Report 提前选框架，不创建页面、状态机或业务契约。

仅保留当前尚未决定的长期工程问题：

1. 后续依赖治理是否收窄 caret 范围，以及如何处理历史双锁文件？由单独依赖任务决定，本次不改。
2. commonCrudConfig 是否值得演进为受支持的共享字段片段？先以真实重复用例及日期组件兼容性验证决定。

Layout Freeze、PageHeader 非强制、动作归属、Yarn/Node、Backend authoritative、UI 批次方向均已确定，不再列为 Open Question。其他页面故障按具体任务验证，不将未证实猜测长期登记为产品决策。

## 20. Recommended Workflow and Review Checklist

未来实施前：读任务/SPEC、AGENTS、UI 方案和本 Guide；确认 API/权限/值转换；选择最近的真实用例；从继承配置开始，只添加必要页面项。源代码变化后重验 Current 段落，不能让 Guide 反向制造源码事实。

- [ ] 现有 index.vue / crud.tsx / api.ts 与 fs-page / fs-crud 组合保持。
- [ ] 无 FilterBar、Toolbar、Pagination、CRUD Form/Dialog 或 DataTable 替代，无强制 PageHeader。
- [ ] Add / Import / Export 保持原 Actionbar 归属；无 CSS 变相搬移。
- [ ] request、API、pagination/query mapping、dict、valueBuilder/valueResolve 不变。
- [ ] auth/show/disabled、列权限、refresh/submit lifecycle 不变，前端展示不替代后端校验。
- [ ] Configuration first / CSS second；按钮语义通过 props，CSS 不抹平类型。
- [ ] global defaults 不重复复制；compute 只用于必要上下文值。
- [ ] 新业务由 SPEC 明确，不伪造 LIMS 数据或已实施状态。
- [ ] 1366/1440/1920、Light/Dark、原生弹层和插件呈现验证；测试未执行时明确说明。
- [ ] 按真实 package scripts 验证；禁止为文档任务安装依赖或运行写入式 lint。
- [ ] 无凭据、无无关源代码/锁文件修改；普通任务不默认新增 *_REPORT.md。

## 21. Local Reference Index

以下均在本次 CompLIMS 仓库中检查存在。目录表示真实目录，不是声称未来文件已经创建；第 17 节的同目录文件按实际用例核验。

```text
AGENTS.md
docs/UI_REDESIGN_PLAN.md
docs/FAST_CRUD_CONFIGURATION_GUIDE.md
docs/P0_REMEDIATION_PLAN.md
docs/FastCrud-doc/
docs/FastCrud-doc/guide/advance/cover.md
docs/FastCrud-doc/guide/advance/options.md
docs/FastCrud-doc/guide/advance/compute.md
docs/FastCrud-doc/guide/advance/dict.md
docs/FastCrud-doc/guide/advance/slots.md
docs/FastCrud-doc/api/use.md
docs/FastCrud-doc/api/install-options.md
docs/FastCrud-doc/api/crud-options/form.md
docs/FastCrud-doc/guide/other/changelogs/packages/fast-crud/CHANGELOG.md
src/web/package.json
src/web/yarn.lock
src/web/src/main.ts
src/web/src/settings.ts
src/web/src/utils/commonCrud.ts
src/web/src/utils/dictionary.ts
src/web/src/utils/authFunction.ts
src/web/src/utils/columnPermission.ts
src/web/src/utils/service.ts
src/web/src/utils/request.ts
src/web/src/stores/dictionary.ts
src/web/src/theme/index.scss
src/web/src/theme/element.scss
src/web/src/theme/dark.scss
src/web/src/theme/fastCrud.scss
src/web/src/assets/style/reset.scss
src/web/src/views/system/role/
src/web/src/views/system/role/components/RoleDrawer.vue
src/web/src/views/system/dictionary/
src/web/src/views/system/dictionary/subDict/
src/web/src/views/system/user/
src/web/src/views/system/areas/
src/web/src/views/system/log/loginLog/
src/web/src/views/system/log/operationLog/
src/web/src/views/system/fileList/
src/web/src/views/system/downloadCenter/
src/web/src/views/system/messageCenter/
src/web/src/views/template/
```

本文为 CompLIMS 工程配置基线。发布文档不代表任何 UI Batch、P0 整改、依赖升级或 LIMS 功能已经实施。
