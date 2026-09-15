# AGENTS.md

本文件规定 CompLIMS 仓库的长期开发规则。优先遵守用户当前任务的明确范围与已确认决策；不得把设计计划当作已实现功能。UI 开发必须遵守下述 Fast CRUD Layout Freeze。

## 1. Repository Structure

- 源码：`src/`
- 后端：`src/backend/`
- 前端：`src/web/`
- 长期文档：`docs/`
- Feature / Phase SPEC 如需独立保存：`specs/`；不因目录规划而提前创建空目录或占位文档。

## 2. Backend / Frontend Environment

### Backend Environment

```bash
cd src/backend
conda activate dvadmin3_env
```

所有 Django / Python 命令从 `src/backend/` 执行，统一使用 `dvadmin3_env`。测试命令依据仓库真实配置。禁止未经批准新建 `.venv`、切换 Poetry / Pipenv 或改变 Python 环境管理方式。环境未就绪时如实说明，不自动替换环境。

### Frontend Environment / Package Manager

统一使用 Node **20.19.5** 和 **Yarn**。开发前：

```bash
cd src/web
nvm use 20.19.5
```

需要启动现有开发服务时使用 `yarn run dev`；确需安装依赖时使用 Yarn，并先检查当前配置及任务授权。运行 lint / type-check / test / build 前先查看 `src/web/package.json`，只运行真实存在的 Yarn Scripts，不能虚构脚本。

已有 `package-lock.json` 视为历史遗留，不作为后续包管理器选择。本次文档基线任务不删除、不更新锁文件、不运行 `npm install`，不生成 `pnpm-lock.yaml`，也不安装依赖。后续锁文件与依赖管理清理单独处理；普通任务不得顺手重生成或删除历史锁文件。未经明确批准不得切换 npm / pnpm。第三方文档中的安装示例不覆盖本仓库 Yarn 规则。

## 3. Source of Truth

项目事实优先依据，顺序如下：

1. 当前源码。
2. Database Schema / Migration。
3. API Contract。
4. 当前配置。
5. 自动化测试。
6. 日志和已验证运行状态。
7. 已批准设计文档。

重要设计文档：

- `docs/CURRENT_PROJECT_REVIEW.md`
- `docs/P0_REMEDIATION_PLAN.md`
- `docs/UI_REDESIGN_PLAN.md`

这是事实核验顺序，不意味着当前代码可以覆盖用户已批准的目标约束。发现实现与设计不一致时分别说明现状、目标与差异；不得把文档中的计划描述成已经实现，不把静态分析描述成运行验证，也不能仅凭依赖声明推断实际运行版本。

引用文件前检查真实存在与适用性，不虚构路径、规格或既有能力。当前任务的明确授权范围优先于旧计划；缺失且会改变业务行为的规格应记录 Open Question，不能猜测补齐。

## 4. Existing Architecture First

这是已有项目，不是 Greenfield。新增基础设施前先检查是否已有等价能力；已有实现能满足时优先复用，不创建第二套方案。

后端优先复用：Base Model、Serializer Base、ViewSet Base、Permission、Response Wrapper、Router、Filter、Pagination、Authentication、File Storage、Audit Fields、Services、Tests。

前端优先复用：Fast CRUD、Element Plus、Form / Table、Dialog / Drawer、Selector、Upload、Router、Store、Request Wrapper、Permission、Utility、Existing Page Patterns。

禁止仅因为 Agent 更熟悉其他技术就替换当前正常工作的基础设施。

## 5. Scope 与编码纪律

只实现当前任务明确要求的范围。禁止因为“以后可能会用”“顺便做完整”而提前增加未要求的 Model / Field / API / Service、Placeholder Component、Fake Data / Fake Algorithm 或 Unused Abstraction。

修改应 Small、Focused、Reviewable、Intentional。禁止重构无关模块、格式化整个仓库、升级无关依赖、批量重命名无关文件、顺手修复大量无关代码，或为方便实现修改高优先级规格。

规格缺失且会改变业务行为时不要猜；真正阻塞时提出 Open Question。保留任务之外的用户修改，不以恢复基线为由覆盖、删除或移动它们。

## 6. Backend Rules

继续使用 Python、Django、Django REST Framework、PostgreSQL，以及当前认证、权限、响应结构和文件存储。禁止未经批准引入第二套 API Framework、ORM、Authentication、Permission 或 Response Framework。

复杂功能按需要使用 models、serializers、services、selectors / query helpers、permissions、views / api、tests，不为空架构提前建层。

- Model：关系、Database Constraint、局部不变量、字段定义。
- Serializer：输入输出、白名单、基础 Validation、API DTO。
- Service：跨模型写用例、Transaction、State Transition、副作用编排。
- Selector：复杂只读查询和查询优化。
- Permission：后端强制正式权限。
- View / ViewSet：保持 HTTP 层薄。

复杂跨模型业务规则不要堆入 ViewSet 或 Serializer 的 create/update。

## 7. Frontend Rules

继续使用 Vue 3、TypeScript、Vite、Element Plus、Fast CRUD、Pinia、Vue Router、Axios、vxe-table 和当前 Request Wrapper。普通 CRUD 优先复用 Fast CRUD。复杂业务工作台可用专用页面，但继续复用已有组件、Request、Permission 和 Store Pattern。Backend 是业务规则最终权威。

### Fast CRUD 文档引用

优先核对当前源码与以下真实存在的文档：

- `docs/UI_REDESIGN_PLAN.md`：已确认视觉方向与冻结边界。
- `docs/FastCrud-doc/`：本地 FastCrud 文档快照，具体 API 以当前项目版本为准。

- `docs/FAST_CRUD_CONFIGURATION_GUIDE.md`：经当前 CompLIMS 源码核对的长期配置 Guide，区分 Current / Recommended / Caution；不替代本文件、当前源码与 API Contract、UI 冻结决策或未来 Feature / Phase SPEC。文档中的建议不代表已实施。

### Fast CRUD Layout Freeze

现有 Fast CRUD 页面原则上保留：

```text
index.vue
crud.tsx
api.ts
```

保持 `fs-page / fs-crud` 原结构，以及由 Fast CRUD 管理的 Search、Actionbar、Toolbar、Table、Pagination、Form、Dialog。

除非任务明确要求，不得为了视觉统一：

- 自建 FilterBar 替代 Fast CRUD Search。
- 把 Add / Import / Export 搬出 Actionbar。
- 重建 Toolbar 或 Pagination。
- 重建 CRUD Dialog / Form。
- 使用另一套 DataTable 替代或包装 fs-crud。
- 为样式目的重写 useFs / useCrud / useExpose。
- 在 Fast CRUD 外重复维护 CRUD Request State。
- 使用 CSS order、绝对定位等手段变相搬移原生区域。

冻结原则：**保留 Fast CRUD Layout，修改 Visual Skin。**

UI 修改优先顺序：

```text
Design Tokens
→ Element Plus Theme
→ Fast CRUD Theme
→ crud.tsx Visual Configuration
```

允许修改 typography、colors、spacing、table density、header/row/button/dialog/form appearance、column width/alignment、form col/span、status renderer、empty/loading appearance。

不允许以 UI 任务改变 CRUD request、API contract、pagination/query mapping、permission logic、show/disabled logic、valueBuilder/valueResolve、dict behavior、refresh/submit lifecycle 或 Fast CRUD request lifecycle。

现有 Fast CRUD 页面不强制增加 PageHeader，不强制用新 PageContainer 重包。未来 Test Execution、Result Review、Report Approval、Specimen Detail 等复杂 LIMS 页面可以按明确业务任务使用独立 PageHeader / Section Layout，不能反向要求现有 System CRUD 迁移。

### Configuration 与样式职责

Fast CRUD / 页面 crud.tsx 保留行为、布局意图与按钮 props；Element Plus 负责具体组件语义；Global SCSS 负责 spacing、density、typography、surface 和有限响应式呈现。

可配置的组件语义遵循 Configuration first、CSS second：全局样式不应覆盖页面级 type、link、plain、danger、primary、success 的意图，不通过粗暴覆盖把所有按钮变成一种语义。该原则不授权改变冻结行为；统一视觉仍按上述 Token → Theme → Visual Configuration 链路完成。

## 8. Backend Is Authoritative

Frontend Validation 只负责 UX。关键规则必须由 Backend 强制，按需要使用 Database Constraint、Model Constraint、Serializer Validation、Permission、Service Validation、transaction.atomic()、select_for_update()。

禁止仅依赖 Hidden Button、Disabled Input、Frontend Route Guard 或 Frontend Validation 保护正式业务数据。UI 重设计不能顺便更改后端 RBAC、审批规则或 LIMS 业务逻辑。

## 9. Transaction / Database / Migration

多对象写操作若部分成功会产生非法状态，必须定义 Transaction Boundary，优先 transaction.atomic()；有并发竞争时按需要使用 select_for_update()。

正式关系优先 ForeignKey / OneToOne / ManyToMany / Through Model，不用 JSON 数组代替正式关系。

修改 Django Model 后按当前 Migration 流程与任务授权执行适用命令：

```bash
cd src/backend
conda activate dvadmin3_env
python manage.py makemigrations
python manage.py migrate
python manage.py check
python manage.py makemigrations --check
```

这些命令不是每项任务都要执行的清单；文档/UI 任务不执行迁移。迁移执行前明确目标数据库与变更范围。Migration须小步、可审查、与任务一致。禁止删除或修改已应用历史 Migration、重写 Migration History、未经要求 fake migration，或提前加入未来 Phase 模型。

## 10. Dependency / Security

新增依赖前确认现有框架/包是否满足。普通 Feature / Fix 不顺手升级 Django、DRF、Vue、Vite、Fast CRUD 或批量更新依赖；遵守第2节包管理规则。

禁止在代码、日志、测试、文档和 Git 中泄露 Password、Secret、Token、Private Key、Certificate、Database Credential、Connection String。配置检查避免输出敏感值。

禁止对不可信输入使用 eval()/exec()，不得执行业务输入提供的任意 Python、JavaScript、Shell 或 Dynamic Import。既有功能的兼容问题单独处理，不借安全名义扩大当前任务。

## 11. Git Rules

开发或仓库修改任务开始时，正常情况下检查：

```bash
git status
git branch --show-current
git log --oneline -5
```

保护已有用户修改，包括未跟踪文件。不要假设远程 main 存在某个文件或可覆盖本地草案。

若 sandbox / 目录明确无可用 Git metadata，记录一次，不重复重试、不初始化新 Git 仓库，改用目标文件范围检查。

未经用户明确授权，禁止破坏性 Git 操作、创建/切换 Branch、Commit、Rebase、Push、修改 Remote 或创建 PR。已有明确授权时按其条件执行，不重复索要同一授权；若条件不满足，保留工作并明确说明，不自行扩大提交范围。

有Git时完成前检查当前任务相关 git diff 与 git status。提交只显式暂存授权文件，不使用 git add . 掺入用户修改；禁止 force push。本次文档基线仅在 main 且工作区只有 AGENTS.md、docs/UI_REDESIGN_PLAN.md 两个预期变化时按用户指令提交/推送；其他已有修改保持原样，条件不满足不提交/推送。

## 12. Documentation / Completion

长期文档放 docs/，Feature / Phase SPEC 按需放 specs/。普通 Feature implementation、UI 调整、Bug Fix、技术验证默认不新增 *_REPORT.md。

仅以下内容可建立长期 Markdown：

- SPEC。
- ADR。
- 重大 Incident / Root Cause。
- Milestone Summary。
- 正式 Guide / Baseline。
- 用户明确要求。

已有正式文档只做与任务直接相关的最小事实更新。事实、已批准设计、未来计划、已验证结果分开说明；不能将计划描述为已实现。

完成时核查授权范围、diff、实际验证结果与未完成事项；未经运行的测试不报告通过。按用户要求报告分支、提交和推送状态；没有提交不得编造新Commit SHA。

本次仅建立文档基线，不开始 UI 代码、UI B1A、P0，不创建 UI branch。后续阶段必须有对应任务授权，完成当前范围后停止。
