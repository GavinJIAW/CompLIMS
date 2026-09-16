# CompLIMS Handover

Project: **CompLIMS**。当前阶段：**UI Redesign 已完成，下一阶段准备进入 P0 Security Remediation**。P0 启动前最后一个已验收功能代码基线（UI Redesign final code baseline）为 `6410514b6298998adc0adfa74c3c271acf055ba4`，也是生成 Handover.md 时的 main HEAD（2026-09-16 核验）。本文是供全新 ChatGPT / Codex 对话快速恢复上下文的交接入口，不是开发报告或新的实施授权。**当前源码、Schema / Migration、API Contract、Config、Tests、已验证运行状态及 Git 优先于本文的历史描述**；已批准目标与现状分开判断。

证据标记：

- **Confirmed current fact**：本次通过 Git / 文件 / 源码静态核验；不自动等于运行测试通过。
- **Historical finding**：2026-09-14 审计发现或前序实施记录；需要按当前基线重新核对。
- **Frozen decision**：用户已确认的长期约束；不能因旧代码或旧设计示例而推翻。
- **NOT EXECUTED**：没有实际执行，不得补记 PASS。
- **Next action**：后续任务，不表示已经实现或已获写入授权。

本次完整读取：`AGENTS.md`、`docs/CURRENT_PROJECT_REVIEW.md`、`docs/P0_REMEDIATION_PLAN.md`、`docs/UI_REDESIGN_PLAN.md`、`docs/FAST_CRUD_CONFIGURATION_GUIDE.md`。**审查文档实际在 docs 下，根目录没有 CURRENT_PROJECT_REVIEW.md**；旧文档中的短路径按此定位。

## 1. Current Project State

**Confirmed current fact**：现有项目是 Django + DRF backend、Vue 3 + Element Plus + FastCrud frontend 的系统管理底座，已有用户、部门、角色、菜单、配置、字典、文件、消息和日志等管理功能。前端继续使用 TypeScript、Vite、Pinia、Vue Router、Axios、VXE 及既有 Request Wrapper；后端沿用现有 Django / DRF / PostgreSQL 方向。

**Frozen decision**：目标是面向第三方复合材料力学性能测试实验室的 **Composite Materials Mechanical Testing LIMS**。正式 LIMS 业务开发尚未开始，必须先通过 P0 门槛。Customer / Project / Specimen / TestRun / Result / Report 等未来领域对象不能描述成已实现；受控审计、资格、版本和文件基础也不能仅凭规划认定存在。

当前 Git 中 `src/backend/apps/` 只有 `__init__.py`，业务模型仍集中在 `coreadmin/system/models.py`，另有 `coreadmin/utils/models.py`。从初始 Git baseline `58ce66f` 到 UI Redesign final code baseline `6410514`，`src/backend/` 无跟踪文件差异；这不证明部署、数据库或被忽略的本地配置未变化，也不代替 P0 重审。

## 2. Current Git Baseline

**Confirmed current fact — 生成 Handover.md 时的 Git 快照（2026-09-16）：**

| 项目 | 实际值 |
| --- | --- |
| Repository | https://github.com/GavinJIAW/CompLIMS |
| origin URL | https://github.com/GavinJIAW/CompLIMS.git |
| Default branch | main（本地 origin/HEAD 指向 origin/main） |
| 生成时 branch | main |
| 生成时 HEAD / local main | `6410514b6298998adc0adfa74c3c271acf055ba4` |
| 生成时 fetch 后 origin/main | `6410514b6298998adc0adfa74c3c271acf055ba4` |
| 生成时 main 与 origin/main | 同步 |
| 生成前 working tree | clean |
| 后续核验规则 | 新对话开始时重新执行 git status / branch / rev-parse / fetch，以实际仓库状态为准 |

以下完整 SHA 已由当前 Git log 核对。阶段终点包含该批后续 UAT 修正，不一定是该批首次实施 commit：

| 阶段 | Commit |
| --- | --- |
| Baseline | `58ce66f3095e2a0aed88b571fae69b04ad21994a` |
| Docs baseline | `aa9450ce627578a999aaeca4b451e84277cce6f5` |
| UI B1A | `781440b75d1ede7edadb7be3007728bc6d0599a4` |
| UI B2 | `6fd58896ca9c51102f7f8c693a68d3caf1ca838e` |
| UI B3 | `2a2f70e67d217115a29992fc68afc70f65333aab` |
| UI B4A | `dfbf0964a93e0c22d00bb77ff377c5aba3912ddb` |
| UI B4B | `44c3537031032c69754784b898073d463e26bb3d` |
| UI B5 | `619cd494d5c15318b8e9afdfb9e0a63c4ef4d59f` |
| Motion Fix | `b55419474945e2c270d91a97578ca27d93e2d020` |
| UI B6 audit | `54e3396525cbe7a1aa98db70b34acacdc4f12d99` |
| Frontend media tracking fix / B6 final | `6410514b6298998adc0adfa74c3c271acf055ba4` |

已验收阶段采用 fast-forward 集成，生成时日志无额外 merge commit。后续若有 documentation-only commit，当前 Git 状态应以重新 fetch 后的 git rev-parse HEAD / origin/main 为准；`6410514` 仍作为进入 P0 前最后一个已验收功能代码基线，不是永久的当前 main HEAD。若出现功能代码变更，应重新核对基线与验收范围。保留既有阶段分支，不自动删除、rebase、reset 或 force push。

## 3. UI Redesign Final Status

**用户最终人工 UAT 验收记录：UI Redesign phase = COMPLETE；Repository completeness = PASS；Build = PASS。**

| 阶段 | 已交付范围 | 最终验收记录 |
| --- | --- | --- |
| B1A | Design Tokens / Light-Dark Theme Foundation / Element Plus 与 FastCrud 基础皮肤 | PASS |
| B2 | Shell / Sidebar / Header / Brand / Breadcrumb / Tabs 呈现 | PASS |
| B3 | FastCrud Visual Standardization，保持原生 Layout | PASS |
| B4A | Login + 现有 401/404；Logo 安全区、稳定校验提示空间、删除独立 CompLIMS 行 | PASS |
| B4B | Dashboard / Workbench + Personal Center，桌面双 Panel 等高 | PASS |
| B5 | System Management Visual Convergence | PASS |
| Motion Fix | Normal / Reduced Motion 独立修复 | PASS |
| B6 | Cleanup + Responsive + Dark Audit；Dept chart；media source tracking | PASS |

最终 B6 人工验收包括 Dept dark chart、Dark、1366/1440/1920 与 1000 视口、125% zoom、Teleport overlays、Keyboard/focus、Reduced / Normal Motion、FastCrud Layout Freeze。它是**用户确认的最终验收结果**，不是本次文档任务重新执行的浏览器测试。

Build PASS 来自前序 B6 修复与 main 集成验证记录；本次未重新 build、启动服务或运行安全测试。UI 视觉验收不代表所有写操作、安全边界或生产配置已验证（见第 9 节）。

**文档时序差异：**当前 UI 计划仍保留 B6 初次审计 PARTIAL、media 未跟踪及“未来实施尚未执行”的历史段落；B6 后续 `6410514` 已解决 tracking，用户最终验收为 PASS。早期 Review / P0 文档的“未发现 Git 元数据”也不再是当前事实。保留这些历史文件，不照抄为现状；FastCrud Guide 中各 Current 同样受其标注日期/批次限制。

**Confirmed current fact**：活动 `views/system/home/index.vue` 仅只读消费 userInfo Store 的真实姓名、部门、角色，显示“业务数据尚未接入”；没有用 demo KPI、图表或 0 冒充业务数据，未实现授权快捷入口。backup 不等同活动 Home。

## 4. UI Decisions That Are Frozen

**Frozen decision；关键值已与 tokens.scss、layout.scss、BrandLogo 和 Login 源码核对。**

| 项目 | 冻结值 / 行为 |
| --- | --- |
| Direction B | Industrial / Engineering Precision |
| Brand | Applus+ Laboratories |
| 原始 Brand orange / 暖灰 | `#FF6900` / `#746661` |
| Light action primary | `#B74700` |
| Dark action primary | `#FF9A52` |
| Sidebar expanded / collapsed | 240px / 64px |
| Header / Tabs | 56px / 36px |
| 完整 Logo | 源 `docs/logo.png`；运行时 `src/web/src/assets/logo.png` |
| 紧凑 Logo | 源 `docs/compact-logo.png`；运行时 `src/web/src/assets/compact-logo.png` |
| Expanded Sidebar | 仅显示完整 Applus+ Laboratories Logo，无第二行产品名 |
| Collapsed Sidebar | approved compact logo；不恢复 CL badge；Tooltip 可为 CompLIMS |
| Login Brand Area | 不单独显示 CompLIMS 行；完整 Logo 后为配置驱动标题/描述 |

两对 Logo 本次 SHA-256 核对均内容一致。不得修改 Logo 像素、字形、比例或颜色；只允许经授权的 presentation 调整。Dark 完整 Logo 使用 light brand plate，不 invert/filter/recolor；docs 不作为运行时资产入口。

品牌色、Action、Status Semantic 分离；不把所有控件机械染橙。沿用 `--lims-*` 语义 token、根部 Light/Dark contract 与 Teleport 继承。保留系统字体栈、4/8/12/16/24/32 spacing、克制 radius/shadow，不另建页面 Dark palette。

Login 保留 `login.site_logo`、`login.site_title`、`login.site_name`、`login.login_background` 与回退能力；删除可见产品行不删除仍被 aria 使用的 i18n key。Sidebar 与 Login 共享资源但 Login 具有独立 Logo 安全区，不以全局裁切变化破坏 Sidebar。

## 5. FastCrud Layout Freeze

**Frozen decision — 保留 Fast CRUD Layout，修改 Visual Skin。Configuration first，CSS second。**

保留 `index.vue + crud.tsx + api.ts`、已有 `fs-page / fs-crud` 及原生组合；嵌套 Drawer 中直接 fs-crud 等既有用法无需补壳。FastCrud 继续拥有 **Search / Actionbar / Toolbar / Table / Pagination / Form / Dialog**。

禁止为了视觉统一：

- 自建 FilterBar 替代 Search，或搬移/复制 Add / Import / Export 到另一操作栏、PageHeader。
- 重建 Toolbar、Pagination、CRUD Dialog / Form；用 replacement DataTable 或包装层替代 fs-crud。
- 为样式改写 useFs / useCrud / useExpose、request lifecycle；在框架外重复维护 request / query / loading / pagination state。
- 用 CSS order / absolute positioning 变相重排原生区域、改变 ownership。
- 强制现有 System CRUD 增加 PageHeader / PageContainer / Section Layout。

视觉链路：**Design Tokens → Element Plus Theme → FastCrud Theme → crud.tsx Visual Configuration**。

允许的视觉范围：typography、colors、spacing、density、header/row/button/dialog/form appearance、列宽与对齐、form col/span、原位置 status/empty/loading renderer。不得借此改变 CRUD request、API contract、query/pagination mapping、permission、show/disabled、dict、valueBuilder/valueResolve、refresh/submit lifecycle 或 validation 业务规则。

Global config 只放真正稳定的共享规则；crud.tsx 表达页面配置与按钮 props；Element Plus 承担组件语义；Global SCSS 仅 spacing/density/typography/surface/有限响应式。CSS 不强制抹平 type / link / plain / danger / primary / success。

Backend Is Authoritative：前端 auth / show / disabled、按钮/列隐藏只负责 UX，不能代替服务端 Permission、Serializer / Service Validation、Database Constraint、Transaction。

这些规则约束 UI 与结构。未来 P0 明确批准的安全契约整改可能需要窄 payload、受控上传/下载或 HTTP 错误适配，必须在独立 SPEC/批次范围内联调，不能以本交接文档自动获得修改授权，也不能为兼容恢复漏洞。

## 6. Frontend Environment

**Frozen decision：**

```text
cd src/web
nvm use 20.19.5
```

使用 **Yarn**。不要 npm install，不要 pnpm，不随意删除/重生成 package-lock.json 或 yarn.lock，不生成 pnpm-lock.yaml；依赖与锁文件治理单独授权。

**Confirmed current fact — package.json 与 yarn.lock：**

| Package | declaration | yarn.lock resolved |
| --- | --- | --- |
| @fast-crud/fast-crud | ^1.21.2 | 1.28.7 |
| @fast-crud/fast-extends | ^1.21.2 | 1.28.7 |
| @fast-crud/ui-element | ^1.21.2 | 1.28.7 |
| @fast-crud/ui-interface | ^1.21.2 | 1.28.7 |
| Element Plus | ^2.8.0 | 2.14.5 |

这是声明/锁定证据，不声称所有部署运行版本已核对。package 的 `django-vue3-admin / 3.2.0` 是既有 manifest 信息，不是新的 CompLIMS release 编号；宽泛 engines 不覆盖 Node 20.19.5 约定。

当前真实 scripts：

| Yarn command | script |
| --- | --- |
| yarn run dev | vite |
| yarn run build | vite build |
| yarn run build:dev | vite build --mode development |
| yarn run build:local | vite build --mode local_prod |
| yarn run lint-fix | eslint --fix --ext .js --ext .jsx --ext .vue src/ |

没有独立只读 lint / typecheck / test script。不要虚构命令，不在只读审计运行 lint-fix；Vite build 不等于完整 TypeScript / Vue 类型检查。P0 文档里的条件式 npm 示例不覆盖当前 Yarn 决策。

## 7. Backend Environment

**Frozen decision：**

```text
cd src/backend
conda activate dvadmin3_env
```

所有 Django / Python 命令从 backend 执行。不要未经授权新建 .venv、换 Poetry / Pipenv、换框架或数据库。

**Confirmed current fact**：两份 requirements 声明 Django 4.2.14、DRF 3.15.2、SimpleJWT 5.4.0；不是本次已安装版本证明。当前可见 `application/settings.py`、`coreadmin/system/tests.py`；文件存在不代表隔离回归套件就绪。

**Next action — P0 开始时重新确认：**真实解释器/依赖、Django test 发现入口、test settings、独立 PostgreSQL test DB、最小 fixture、migration 跟踪与应用状态、URL import 是否查询业务表、日志/初始化副作用。优先现有 Django TestCase / TransactionTestCase / DRF APIClient，不先强装新测试框架。

历史审计记录 `system/tests.py` 为手工查询脚本、`application/urls.py` 导入执行 dispatch 初始化；这些是需要复核的阻碍，不直接运行默认 manage.py 命令试探现有数据库。确认隔离前不得 migrate、初始化或执行写入测试。本任务没有运行后端测试、迁移或连接数据库。

## 8. UI Known Remaining Debt

**Historical finding / 保留决策，不是 B6 introduced failures：**

- Historical i18n debt：存量硬编码中文及旧组件国际化不全，不在收尾全站重写。
- `home/backup`：KEPT；动态组件解析可命中，未证明所有后端 component mapping 均无引用，不能仅凭无静态 import 删除。
- `views/system/demo`、`views/template`：保留模板/动态兼容内容，不因名称删除。
- Legacy icon compatibility：Element Plus / SvgIcon / iconfont / Font Awesome 等旧值兼容保留；未证明无消费者不强删。
- Existing Sass deprecation warnings 与 chunk-size warnings：前序构建已有，Build PASS 不等于 warning-free。
- 旧 Theme Store / cache / 自由配色协调、重复权限入口等历史技术债不因 UI COMPLETE 自动被认定已重构。

Dept statistics chart dark legend contrast 已在 B6 修复并通过最终人工 UAT，不再列为待修项。media tracking 已解决，见第 10 节。缺少正常入口的插件全路径不能从代表页面验收推导为已运行。

## 9. NOT EXECUTED Write Operations

以下沿用 B4B / B5 / B6 只读 UI 审计的保守记录；不能在新对话中自动视为已通过：

| 操作 | 状态 |
| --- | --- |
| Avatar upload | NOT EXECUTED |
| Profile update / save | NOT EXECUTED |
| Password change | NOT EXECUTED |
| Role authorization save | NOT EXECUTED |
| Config save | NOT EXECUTED |
| File upload | NOT EXECUTED |
| First-login password-change flow | NOT EXECUTED（无实际触发通过证据） |

表单/弹层可打开、视觉正常、原脚本未改，不等于服务端写入成功或授权正确。后续只在隔离环境、获准测试数据与明确范围下补测；不得为 UI 或安全审计修改真实关键数据。

## 10. Frontend Media Tracking Incident

**Historical finding，已由 `6410514b6298998adc0adfa74c3c271acf055ba4` 修复。**

根 `.gitignore` 的 `media/` 匹配任意层级同名目录，曾把 `src/web/src/theme/media/` 前端源码忽略；但 `theme/index.scss` 持续 import `./media/media.scss`。旧本地 Build PASS 因而不能证明干净 checkout 完整。

修复保留 runtime `media/` 忽略规则，新增精确例外：

```gitignore
!/src/web/src/theme/media/
!/src/web/src/theme/media/**
```

正常跟踪 15 个 SCSS（未靠 git add -f）：`chart`、`cityLinkage`、`date`、`dialog`、`error`、`form`、`home`、`index`、`layout`、`login`、`media`、`pagination`、`personal`、`scrollbar`、`tagsView`。均位于该目录；`media.scss` 引入 13 个分项，分项使用 `index.scss` 公共断点。

**Confirmed current fact**：本次 `git ls-files`、`git ls-tree HEAD` 和 `git archive HEAD` 列表均包含全部 15 个 source；check-ignore 的匹配为否定例外。runtime 路径探针仍匹配 `media/` 忽略规则。源 import 保留，没有删除样式来掩盖缺失。

**前序验证记录**：clean detached worktree 源码/完整 theme import 编译验证 PASS，archive 含 media source，正式工作区 Yarn build PASS，Repository completeness 最终用户验收 PASS。干净 worktree 验证复用了已有 Sass 工具，不应扩写为“已在全新机器重新安装全部依赖并完成全应用 build”。本次只重验 Git/归档，不重复创建 worktree 或 build。

## 11. Motion Fix

**Frozen decision + Confirmed current fact**：`b55419474945e2c270d91a97578ca27d93e2d020` 已集成。

| 模式 / 对象 | 规范 |
| --- | --- |
| Normal Page | slide-right / slide-left / opacitys，300ms |
| Normal Drawer / Overlay | 240ms |
| overlay fast token | 180ms |
| 原 micro-motion fast / normal | 120ms / 160ms，未全局变慢 |
| Reduced Motion | 尊重 prefers-reduced-motion: reduce，相关 token 为 0ms，直接最终状态 |

`theme/common/transition.scss` 中页面 enter-from / leave-to 在 reduce 下 `opacity: 1; transform: none`；`theme/element.scss` 对 `.el-overlay.is-drawer` 局部映射 overlay token，并中和 Drawer/Overlay 的透明/位移瞬态。避免“duration=0 但先透明/偏移再跳入”的 flash。

Router `parent.vue` 的 out-in、keep-alive、刷新 key、缓存与 route watcher 不因此重设计。不用 JS 定时器、强制 reflow 或恢复全局动画绕过用户减少运动偏好。Normal/Reduced 的最终人工 UAT 均 PASS；本次仅复核实现。

## 12. P0 Background

**Historical finding — 2026-09-14：**`docs/CURRENT_PROJECT_REVIEW.md` 结论为 **C. 可以使用，但需要较大范围重构**。保留技术路线和管理 UI，但不能直接承载可信实验室记录。`docs/P0_REMEDIATION_PLAN.md` 定义 **5 个 BLOCKER Gate、6 个整改批次**；它是设计方案，不是已落地的安全实现。

正式 LIMS 开发前必须通过以下最小闭环及可重复验证：

| Gate | 门槛 | 原计划核心范围 |
| --- | --- | --- |
| G1 | 权限执行边界可信 | action/scope/object/field；授权越权、匿名、lookup、路径导入、XSS 受控或关闭 |
| G2 | 认证与生产秘密可信 | Secret rotation、安全配置拒启、会话/改密失效、统一密码与首登边界 |
| G3 | 数据写入完整性可重现 | 隔离测试、迁移可重建、关键 FK/唯一、服务事务、并发/回滚 |
| G4 | 可信变更历史与冻结契约 | 授权/配置同事务 append-only AuditEvent；版本/revision/资格接口测试 |
| G5 | 受控不可变文件入口 | 私有存储、随机最终 key、服务器 hash、授权下载、file_id 导入、封闭旧公开入口 |

这些不是要求先建完整 LIMS。OperationLog 不等于 AuditTrail，FileList 不等于不可变 RawDataFile；新 app、ManagedFile、AuditEvent 等出现在计划中不代表当前存在。关闭危险旧入口可作为阶段措施，但“全部请求拒绝”不能代替安全且可用的正反例验收。

当前 Git 基础已不同于原审计：初始迁移 `coreadmin/system/migrations/0001_initial.py` 与 `__init__.py` 已跟踪，backend .gitignore 不再含历史迁移排除规则，新 migration 路径探针未被忽略。**只证明 tracking 层已变化**；实际 schema、已应用历史、空库重建/旧库升级均需 P0 重新验证，不能直接把 G3 标 PASS。

## 13. Original Critical / High P0 Findings

**全部是 2026-09-14 Historical findings，不是本次对当前 main 的漏洞复现结果。**S 是摘要，T 是明细，不能重复计数为独立问题。

| 原编号 | 摘要 | 原审计定位（均相对 src/backend/，前端另注明） |
| --- | --- | --- |
| S01 | Authorization management privilege escalation | system/views/role.py::set_role_users；role_menu_button_permission.py::set_role_menu*；仅登录后可进入授权 mutation |
| S02 | Anonymous file access | system/views/file_list.py::FileViewSet 空权限、get_all 与继承 multiple_delete |
| S03 | SECRET/JWT signing | application/settings.py 的历史固定 Secret、JWT 无独立签名配置；部署沿用情况未确认 |
| S04 | User sensitive fields writable | system/views/user.py 创建/更新 fields='__all__'；PATCH serializer 分派需同时核对 |
| S05 | Scope / field permission bypass | utils/viewset.py bulk/field；User list；SystemConfig lookup |

Restart Audit 至少覆盖以下相邻风险，保留触发条件，不夸大影响：

- Role / Menu / Button / Field / Data Range 的直接 CRUD、自定义 set_role_*、save_auth、角色成员 mutation；旧 AdminPermission 读取不存在字段的风险；禁用角色一致性。
- FileViewSet / DownloadCenter 的身份、枚举、下载、删除、上传边界，以及旧 media/CDN 直链；失败或 500 不是权限控制。
- multiple_delete 是否走完整 scope/object 核验，是否整批原子；User list 的 show_all/dept 分支；DataLevelPermissionsFilter 的跨 action CUSTOM 范围、多角色提前 return、PATCH/HEAD。
- User fields='__all__'、CoreModel creator/modifier/dept_belong_id 等受控字段、后端 field read/create/update enforcement；前端列权限不足以证明安全。
- SystemConfig 动态 model lookup / 全字段 values / 分页、公开配置 allowlist。原风险依赖可访问或可控制相关配置，不是“任意匿名必然读任意表”。
- OperationLog/LoginLog mutation、客户端 log_id 与敏感日志。原审计仅确认响应摘要 code/msg，不应声称已记录完整 JWT 响应；重点是请求体递归脱敏、改密字段、配置凭据与日志篡改。
- Import 路径信任：用户 url→join→load_workbook，需真实路径/file_id 授权；原风险是可达且可解析 Excel 路径，不是已经证实任意文件外泄或 RCE。
- MessageCenter 到前端 `src/web/src/layout/navBars/breadcrumb/userNews.vue` 的 v-html 链路；历史未做浏览器攻击载荷复现。
- db_constraint=False、关键联合唯一、孤儿/重复数据与 migration tracking；源码声明不等于已连接确认的数据库约束。
- transaction boundaries：get_serializer 内 atomic 不覆盖后续 save；role/menu 授权替换、Config 批量、Message 多模型写入及 on_commit。原 ImportSerializerMixin.import_data 已有 atomic，不能声称所有导入都无事务。
- DEBUG / CORS / ALLOWED_HOSTS、Secret 来源/轮换、JWT/注销/改密撤销、MD5 多路兼容、首次改密的服务端边界；当前部署、真实桶 ACL/覆盖策略仍需运行核验。

不写入任何 Secret 实际值、密码、Token、Cookie、连接串或存储密钥。历史“hardcoded secret existed”必须推动来源与轮换核验，不能以移出 Git 代替轮换，也不能伪称生产已安全。

## 14. P0 Security Boundary

**Frozen decision / 后续实施原则（未由本交接任务实施）：先封入口，再替换抽象。**

B1 临时对 Role / Menu / Button / Field / Data Range 授权 mutation、角色成员变更及直接授权 CRUD 使用明确条件：

```text
is_authenticated and is_active and is_superuser
```

不要用历史 AdminPermission 替代，除非新审计证明它已修复且满足同一边界。最终受控授权服务仍要处理目标、受保护管理员、自提权和委派范围；临时 superuser 守卫不是完整新权限平台。

普通 User CRUD 不得直接写 `is_superuser`、`is_staff`、`groups`、`user_permissions`、`role`、`creator`、`modifier`、`dept_belong_id`，以及未经专用动作授权的 dept、密码状态/安全计数等。Create / PUT / PATCH 都要显式硬上限；角色、部门、安全属性不能借普通资料更新获得写权。

危险路径优先通过服务端 **403 / 405** 封闭，再逐批恢复安全功能：路径导入、任意 model lookup、未受控文件入口；同时核对菜单排序/部门统计等旁路。公共配置采用允许清单；日志 API 只读、内部 ID 不信客户端；消息先安全文本展示。不得只隐藏前端按钮。

保留 API envelope 的兼容价值，但认证/拒绝/不可见/冲突/无效字段/禁用动作应有明确 HTTP 语义：401（既有 DRF 挑战机制的过渡情形可 403）、403、404、409、400、405；不能全部吞成 HTTP 200。具体例外、前端兼容与最小修改范围由 Restart Audit 后的 B1 scope 冻结。

## 15. P0 Batch Strategy

**以下按 P0 计划第 22 / 27 节提炼，是 P0 B1–B6，不是已完成的 UI B1–B6。**

| 批次 | 原计划范围与出口 |
| --- | --- |
| P0 B1 — 测试入口与安全封堵 | 隔离测试 settings/入口；授权 mutation 临时守卫；User 敏感字段；匿名文件/危险 lookup/import 封闭；日志/消息/公共配置、安全配置和密钥轮换；基础正反例。不先换整个权限抽象。 |
| P0 B2 — 统一 Action / Scope / Object / Field | 稳定 action code/default deny、授权 queryset/object、字段硬上限与有效 grant、bulk 全集核验、受控 lookup；兼容旧 MenuButton 映射但无双路放行。 |
| P0 B3 — 事务、约束与认证生命周期 | 授权/用户/配置/消息服务 atomic、on_commit；关键 FK/联合唯一与受控迁移；密码入口、会话撤销/改密/禁用失效；PostgreSQL 并发/回滚测试。 |
| P0 B4 — Audit / Versioning 最小基础 | 授权/配置同事务 AuditEvent、append only、受限 DB 账号；revision/冻结版本与资格接口契约测试；不建 Result/Report 业务表。 |
| P0 B5 — Managed File / 安全导入下载 | 私有存储、随机不可变 key、服务器 SHA-256、受控确认/下载、file_id 导入、旧附件映射与旧 URL 封闭；可从私有本地存储开始。 |
| P0 B6 — 集成验收与 CI 门槛 | 前五批联动；后端安全/事务/约束测试、迁移检查、前端获准建立的只读 lint/typecheck/build、部署检查；五 Gate 证据与合法流程通过。 |

顺序不变：B1→B2→B3→B4→B5→B6。测试从 B1 开始，先建立失败回归，再最小修复；每批独立验收。不恢复已确认漏洞、旧泄露密钥或公开原始文件作为回滚方案。

原计划路径和测试名是拟议，须按当前代码复核后才创建。audit / managed files 本身属于 P0 最小闭环，不能延到“P0 全部完成”之后才做；资格/版本具体 LIMS 模型仍待未来 SPEC。每批授权、数据操作和部署动作单独明确。

## 16. What Must NOT Happen at P0 Start

**Frozen decision：**

- 不开始正式 LIMS 模型，不建立 Customer / Specimen / TestRun 等业务表，不提前搭万能工作流。
- 不顺手重写 Django、DRF、FastCrud 或整个 coreadmin，不一次性实现完整新权限平台。
- 不用前端隐藏/禁用按钮、Route Guard 或表单校验代替服务端安全。
- 不把 Historical finding、旧计划、用户 UAT 或 Codex 报告混成当前源码/生产事实。
- 不在没有隔离测试环境时声称漏洞已修复；不连接生产数据库进行测试、迁移或破坏性探测。
- 不伪造 test / write-operation PASS，不伪造生产配置、实际密钥轮换、桶策略或 DB 约束状态。
- 不输出、复制或提交 Secret；不恢复旧秘密作为 fallback。
- 不删除/重写已应用迁移，不 reset/rebase/force，不覆盖用户修改；仅在当前明确授权条件下切分支、提交、推送。
- 不把历史 UI-only 行为冻结当成禁止一切获准安全修复，也不把 P0 计划当成任意扩面的授权；必要前端适配须保持 FastCrud Layout 并有独立契约回归。

## 17. Next Task For New Conversation

**Next action：第一项任务是 P0 Restart Audit，不是直接开始 P0 implementation。**

P0 functional code baseline：`6410514b6298998adc0adfa74c3c271acf055ba4`。新对话开始时必须重新执行 git status、git branch --show-current、git rev-parse HEAD、git fetch origin、git rev-parse origin/main，以实际仓库状态为准。区分后续仅文档提交与功能代码变更；若功能基线变化，记录实际差异并重新界定范围。

在当前 main 上重新检查：

1. Authorization mutation：直接 CRUD + 全部自定义 action、角色成员与委派目标。
2. File access：匿名、枚举、删除、下载、上传和公开 URL。
3. SECRET / JWT / config：只报告来源和策略，不输出实际值；部署事实单列。
4. User sensitive fields：POST / PUT / PATCH / 嵌套或导入写入上限。
5. Bulk / scope / field bypass：列表、对象、全部 ID、show_all/dept、跨 action / 多角色、字段输出与输入。
6. Logging：日志 mutation、log_id、递归脱敏、异常与 request ID。
7. Import：路径信任、真实文件边界、授权流、事务。
8. MessageCenter XSS：生产者→存储→v-html 消费路径，运行复现条件。
9. Constraints：模型/迁移声明与实际数据库 FK/唯一分开核对。
10. Transactions：atomic 实际覆盖、M2M/多模型写入、异常回滚、on_commit。
11. Migration tracking：Git/ignore、链完整性、已应用状态、空库重建与升级条件。
12. Isolated test baseline：Django runner/settings、PostgreSQL 测试库、URL import side effects、无生产连接保障。

每项必须分类 **CONFIRMED / PARTIALLY CONFIRMED / RESOLVED / NEED RUNTIME VERIFICATION**，注明当前文件/符号/commit、触发条件、静态或运行证据、未执行原因及拟覆盖测试。未运行不写“未复现”；tracking 解决不能扩大成整个 migration/database 问题 RESOLVED。

交付应是当前风险清单、历史差异、隔离测试可行性及 **B1 最小 implementation scope 提案**。随后再根据真实事实冻结允许文件、临时关闭入口、兼容影响、测试正反例和验收条件。没有新的实施任务前，不修改代码、数据库、权限或部署；本文不授权预建基础 app。

## 18. Recommended New-Conversation Opening

> 请先阅读根目录 Handover.md、AGENTS.md、docs/CURRENT_PROJECT_REVIEW.md 和 docs/P0_REMEDIATION_PLAN.md；前端适配同时遵守 UI / FastCrud Guide。UI Redesign 已完成，P0 functional code baseline 为 6410514b6298998adc0adfa74c3c271acf055ba4。不要开始 LIMS 业务或 P0 代码修改。先执行 P0 Restart Audit，核对当前 Git 和隔离测试条件，基于当前源码重新分类历史 P0 Findings，再制定 B1 最小整改范围。
