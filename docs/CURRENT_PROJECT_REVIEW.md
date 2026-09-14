# Current Project Technical Review

审查日期：2026-09-14  
审查对象：`D:\hex\Desktop\Projects\CompLIMS`  
目标：评估现有 Django + Vue 管理系统作为第三方复合材料力学性能测试实验室 LIMS 基础的可行性。

## 1. Executive Summary

**结论：C. 可以使用，但需要较大范围重构。**

当前项目是系统管理底座，具备用户、部门、角色、菜单、字典、配置、文件、消息和日志功能；不是已经具备样品、试验、结果及报告业务的 LIMS。Vue 管理界面、FastCrud 集成和 Django/DRF 技术路线可以保留，但后端存在可静态确认的严重授权缺陷，通用模型、文件、审计、事务和工程化也不足以直接承载受控实验室记录。

### 必须首先处理的严重风险

| 编号 | 严重程度 | 已确认代码事实与影响 | 证据 |
| --- | --- | --- | --- |
| S01 | Critical | 角色成员及菜单/按钮/字段/数据范围授权写操作仅检查 `IsAuthenticated`，直接使用请求中的角色、用户和按钮 ID；普通登录用户能够走到修改授权关系的代码，没有管理员身份或可授权范围检查。 | `src/backend/coreadmin/system/views/role.py`：`set_role_users`；`views/role_menu_button_permission.py`：`set_role_menu*` 系列 |
| S02 | Critical | `FileViewSet.permission_classes=[]`，并继承未按数据范围过滤的批量删除；匿名请求可以到达文件元数据批量删除路径。`get_all` 直接序列化全部文件；上传没有登录权限门槛。 | `src/backend/coreadmin/system/views/file_list.py`；`src/backend/coreadmin/utils/viewset.py`：`multiple_delete` |
| S03 | Critical（部署沿用当前密钥时） | `settings.py` 硬编码实际 `SECRET_KEY`；`env.py` 中另一个 `DJANGO_SECRET_KEY` 未被赋给它。SimpleJWT 未设置独立签名密钥，按默认约定依赖 Django 密钥。源码泄露与部署沿用组合可危及令牌信任。 | `src/backend/application/settings.py`：`SECRET_KEY`、`SIMPLE_JWT`；`src/backend/conf/env.py` |
| S04 | High | 用户创建/更新序列化器暴露全部模型字段，未将 `is_superuser`、`is_staff`、角色等纳入受限写入策略；有普通用户管理权限的人可能提升账号权限。 | `src/backend/coreadmin/system/views/user.py`：`UserCreateSerializer`、`UserUpdateSerializer` |
| S05 | High | 通用批量删除绕过 `filter_queryset`，部分自定义列表/关联表接口同样绕开数据范围；后端字段权限裁剪代码被注释。 | `src/backend/coreadmin/utils/viewset.py`；`views/user.py`：`list`；`views/system_config.py`：`get_table_data` |

以上是**代码路径审查发现**，不是已在生产环境实施的攻击测试；公网暴露、真实账号权限、数据库内容和生产密钥是否相同均**未确认**。本报告不复制任何密钥或数据库密码。

### 结论分类与审查边界

- **已确认事实**：文件、配置、声明和源码控制流直接支持的结论。
- **基于代码的合理推断**：由源码及框架语义推导的行为；不冒充运行结果。
- **风险判断**：说明触发条件、潜在影响和严重性，不等于已发生事件。
- **后续建议**：未来工作，本次未实施。
- **未确认**：运行环境、数据库实况、外部部署、攻击复现及容量等未获得证据的事项。
- **未发现**：在本次扫描的自有源码和工程配置范围内未发现，不代表第三方依赖或外部系统绝对不存在。

扫描清单包含 **909 个非 node_modules 文件**：后端 359、前端 320、FastCrud 文档 230，包括隐藏配置、已有迁移、静态资源、模板和缓存文件。对关键业务源码进行了逐文件及交叉调用阅读；对模板、资源及文档进行了目录清点、针对性检索和关键文档阅读，并非逐字审计所有第三方资源。现有 `node_modules` 只抽查直接依赖元数据，不审计全部供应链代码。

未连接数据库，未启动 Django、Vite、Celery；未执行迁移、初始化、构建、导入导出或攻击请求；未安装依赖。未发现工作区 `.git`，`git status` 返回非 Git 仓库，因此不能确认历史提交中的 Secret，也不能以 Git diff 证明变更。唯一新增文件为本报告。

## 2. Project Overview

**已确认事实：**前后端分离。后端入口为 `src/backend/manage.py`，Django 项目包为 `application`；自有业务 App 为 `coreadmin.system`。`src/backend/apps/` 只有 `__init__.py`，不是已有 LIMS apps 集合。

前端为 `src/web`，`package.json` 名称为 `django-vue3-admin`、项目版本 `3.2.0`。前端通过 Axios 请求 `/api/system/` 等接口，默认开发地址与后端端口分开。`local_prod` 构建可把前端输出到后端模板目录，这只改变交付方式，不改变 API 分离架构。

**合理推断：**代码具有 django-vue3-admin / vue-next-admin 风格与遗留插件痕迹；确切上游版本、fork 历史、许可证继承关系未确认。数据库名虽为 `lims`，不代表已经实现 LIMS。

## 3. Repository Structure

```text
CompLIMS/
├─ docs/
│  └─ FastCrud-doc/               本地 FastCrud 文档，非项目业务源码
│     ├─ .vitepress/ admin/ api/ demo/ guide/
│     └─ images/ public/ index.md
└─ src/
   ├─ backend/
   │  ├─ application/             settings、urls、dispatch、WSGI、ASGI、Celery
   │  ├─ conf/env.py              数据库、Redis、开发开关等
   │  ├─ apps/__init__.py          当前无业务 App
   │  ├─ coreadmin/
   │  │  ├─ system/               models、views、urls、tasks、signals
   │  │  │  ├─ migrations/0001_initial.py
   │  │  │  ├─ fixtures/          用户/菜单/角色/配置初始化数据
   │  │  │  └─ management/commands/
   │  │  └─ utils/                通用模型、权限、过滤、CRUD、导入导出
   │  ├─ templates/               DRF / drf-yasg 模板
   │  ├─ static/                  DRF、Swagger、验证码资源
   │  ├─ logs/                    server.log、error.log
   │  ├─ manage.py main.py serve.py del_migrations.py
   │  └─ requirements.txt requirements2.txt .gitignore .idea/
   └─ web/
      ├─ src/
      │  ├─ api/                  login、menu
      │  ├─ views/system/         系统管理页面，常见 api.ts + crud.tsx + index.vue
      │  ├─ views/template/       CRUD 开发模板
      │  ├─ views/plugins/        插件扫描入口
      │  ├─ components/           文件、表格、关联选择、富文本等
      │  ├─ layout/ router/ stores/ plugin/ directive/
      │  ├─ utils/ types/ i18n/ theme/ assets/
      │  └─ main.ts settings.ts App.vue
      ├─ public/ node_modules/
      └─ package.json package-lock.json yarn.lock vite.config.ts
         flowH5.config.ts tsconfig.json .env* .eslintrc.js .prettierrc.js
```

根目录原有内容只有 `docs`、`src`；未发现项目 README、AGENTS.md、Dockerfile、compose、Nginx 配置、CI/CD 配置或根目录版本控制元数据。依赖包自带的 `.github`、测试和 README 不视为本项目的工程能力。

## 4. Technology Stack

| 项目 | 当前证据/版本 | 判断与边界 |
| --- | --- | --- |
| Python | 存在 `cpython-311.pyc`；IDE 环境名 `dvadmin3_env` | 合理推断曾用 Python 3.11；当前服务解释器和补丁版本未确认；未发现版本声明文件 |
| Django | 两份 requirements 均 `4.2.14` | 声明锁定版本；settings 注释中的 3.2.3 不是实际依赖版本；已安装后端版本未确认 |
| DRF | `djangorestframework==3.15.2` | 声明锁定版本 |
| JWT | `djangorestframework_simplejwt==5.4.0` | JWT + SessionAuthentication |
| Vue | 声明 `^3.4.38`；package-lock 与现有安装 `3.5.42` | 不能将声明下限误报为实际安装版本 |
| Vue Router | 声明 `^4.4.3`；锁定/安装 `4.6.4` | `createWebHashHistory`，动态路由 |
| 状态管理 | Pinia 声明 `^2.0.28`；锁定/安装 `2.3.1` | `pinia-plugin-persist`；未发现实际 Vuex 集成，注释残留不作证据 |
| UI | Element Plus 声明 `^2.8.0`；锁定/安装 `2.14.5` | 主 UI；VXE 全局注册；Vant 等在依赖中 |
| CRUD | FastCrud 声明 `^1.21.2`；锁定/安装 `1.28.7` | ui-element、fast-extends；本地文档另含更高版本特性说明 |
| 构建 | Vite 声明 `^5.4.20`；锁定/安装 `5.4.21` | Vue/JSX 插件，TS/TSX、Sass、Tailwind |
| TypeScript | 声明 `^4.9.4`，安装 `4.9.5` | strict=true，但大量 any / ts-ignore，无独立类型检查脚本 |
| Node | package engines `>=16` | 安装的 Vite 要求 `^18 || >=20`，ESLint 要求更高；声明不一致，实际 Node 未确认 |
| 数据库 | `django.db.backends.postgresql`，本机 5433 | PostgreSQL 已配置；服务器版本、实际表及数据量未确认；同时声明 MySQL 驱动不代表正在使用 MySQL |
| 缓存 | dispatch 默认 memory，settings 内字典；使用 Django cache API | 未发现 `CACHES` 配置；按默认行为推断为进程本地缓存，非共享 Redis |
| Redis | env 中有 URL、依赖 redis/django-redis/channels-redis | 未发现当前缓存/任务/Channels 完整接线；服务是否运行未确认 |
| Celery | `5.5.3`；`application/celery.py`，Excel 导出 task | 有骨架；未发现 broker 配置，异步导出调用被注释，不能认定已启用 |
| 定时任务 | django-celery-beat 依赖；前端 celery 插件依赖 | beat 未列入 INSTALLED_APPS，未发现现行业务调度定义 |
| WebSocket | Channels 依赖、前端客户端工具 | ASGI 仅 HTTP，Channels 配置注释；未发现 consumer/WS 路由 |
| 文件 | Django FileField，本地 `MEDIA_ROOT='../media'` | 路径依赖进程工作目录；开发通常落到 `src/media`，当前扫描未发现该目录 |
| 对象存储 | Aliyun OSS、Tencent COS 上传函数 | 可配置后端；实际启用引擎及桶权限未确认；未发现业务 MinIO/S3 接入 |
| Docker / Nginx | 未发现 | env 的 Docker 注释不是交付配置 |
| CI/CD | 未发现 | 未发现项目工作流、自动部署或验证流水线 |
| 日志 | Python logging、RotatingFileHandler、OperationLog、LoginLog | 具备运行日志与操作记录，缺少受控审计 |
| 测试 | `system/tests.py` 导入 TestCase | 内容是手动查询计时脚本；未发现实际 TestCase 子类、pytest 或前端测试套件 |
| API 文档 | drf-yasg `1.21.7`，Swagger / ReDoc | Swagger/OpenAPI 2.0 风格；`v1` 是文档版本，非 API 版本机制 |
| 权限 | 自定义 RBAC + 部门过滤 + 字段权限元数据 | 有实现但存在严重旁路；未发现完整对象授权/资格授权框架 |

版本与配置结论来自本地文件；未进行联网 CVE 全量审计，也未将某个依赖版本直接等同于已确认漏洞。

## 5. Django Architecture

主要请求链：

```text
application.urls
→ system.urls / SimpleRouter
→ ViewSet / 自定义 action
→ CustomPermission（可被子类或 action 覆盖）
→ CustomModelViewSet.filter_queryset
→ 默认 Filter + CoreModelFilterBankend + DataLevelPermissionsFilter
→ CustomModelSerializer / 按 action 选择的 Serializer
→ CoreModel / ORM / PostgreSQL
→ DetailResponse / CustomPagination / CustomExceptionHandler
```

**已确认事实：**`CustomModelViewSet` 继承 DRF `ModelViewSet`、导入导出 Mixin 和 django-restql QueryArgumentsMixin；业务序列化器通常直接放在对应 `views/*.py` 内。没有独立 services/domain/repositories 层。`CustomModelSerializer` 自动补充创建/修改人，但不能覆盖直接 ORM 更新、所有自定义 action 或后台任务。

**风险判断：**业务规则散落在 Serializer.save、Model.save、ViewSet action、dispatch 和初始化脚本中，边界不稳定。基础工具反向依赖 `coreadmin.system.models`，新 LIMS App 如果直接复制这套模式，会同时继承其授权、删除、日志与字段写入问题。

**后续建议：**保留 DRF 分层入口，给跨对象写操作建立明确业务服务及事务边界。公共 CRUD 适用于低风险配置；结果提交、作废、复核、签发应是受控动作，不能仅套通用 update/destroy。

## 6. Django Apps Analysis

### 自有 App

| App/目录 | 职责、主要模型 | 主要 API | 依赖与 LIMS 复用判断 |
| --- | --- | --- | --- |
| `coreadmin.system` / label `system` | 用户、岗位、部门、角色、菜单、字段权限、字典、系统参数、地区、文件、消息、下载任务及日志；20 个具体模型 | `/api/system/` 下 17 个 router 注册资源及自定义动作 | 依赖 auth、DRF、captcha、dispatch、utils、Celery 等；职责过重；应分边界改造后复用 |
| `apps/` | 仅 `__init__.py` | 未发现 | 预留空间；不是已安装业务 App |
| `coreadmin.utils` | CoreModel、权限、过滤、CRUD 等工具 | 通过 Mixin 提供动作 | 不是独立 Django App；与 system 双向模块依赖，需治理 |
| `application` | 项目配置、路由、启动、缓存门面、Celery | 登录、初始化、文档等根路由 | 不是业务 App；可保留项目骨架 |

### 已注册框架/第三方 Apps

`django.contrib.auth`（Group/Permission 与认证）、`contenttypes`（模型类型）、`sessions`（会话）、`messages`（Django 消息机制）、`staticfiles`（静态文件）、`django_comment_migrate`（表注释支持）、`rest_framework`、`django_filters`、`corsheaders`、`drf_yasg`、`captcha`（验证码存储）。它们不应被当作 LIMS 业务 App。`django.contrib.admin` 未注册；Channels 和 celery-beat 也未在当前 INSTALLED_APPS 启用。

### 模块依赖与职责

- `Users` 依赖 `Dept`、`Role`、`Post`；角色通过中间模型关联菜单、按钮、字段和部门范围。
- `MessageCenter` 依赖用户/部门/角色；`FileList`、日志等依赖 CoreModel 的创建人字段。
- `CoreModel` 导入 settings，`CustomModelSerializer` 导入 Users，`viewset.py` 导入 FieldPermission/MenuField；所谓通用层不是可独立复用的纯工具。
- `settings.py → conf.env → application.settings.BASE_DIR` 是已确认配置循环导入；当前能利用先定义的 BASE_DIR，但初始化顺序脆弱。
- `system.models → application.dispatch → system.models` 通过函数内延迟导入缓解；view 间也使用局部导入。**未确认存在必然触发的 ImportError**，但新增模块时有循环依赖风险。
- 未发现独立 Organization、审批、流程或 AuditTrail App。tenant 信号、`connection.tenant` 检查和前端插件判断只是兼容痕迹。

## 7. Database Model Analysis

### 7.1 继承与公共字段

证据：`src/backend/coreadmin/utils/models.py:100` 的 `CoreModel`。

| 要求 | 当前实现 | 评估 |
| --- | --- | --- |
| 主键 | `BigAutoField` | 自增 64 位 ID，非 UUID；可用于内部主键，仍需独立实验室业务编号 |
| created_at / updated_at | `create_datetime(auto_now_add)` / `update_datetime(auto_now)` | 最后状态时间，不是修改历史；bulk update 等不保证执行 save |
| created_by | creator FK → AUTH_USER_MODEL，SET_NULL，db_constraint=False | 人被删除后可能失去引用，不适合作为唯一审计身份 |
| updated_by | modifier CharField | 不是 FK；manager/serializer 写 ID，`common_update_data` 写 username，语义不一致 |
| department | dept_belong_id CharField | 无 FK、无显式索引，客户端在部分通用 serializer 中可提交/修改；不构成可信隔离边界 |
| status | 无统一字段；各模型自定义 bool/int | 不是可执行状态机 |
| soft delete | 单独 SoftDeleteModel 存在，但 20 个具体 system 模型均未继承 | 当前 system 删除通常是物理删除 |
| version / UUID | 未发现通用版本字段、乐观锁或 UUID 主键 | 缺少历史版本和并发冲突保护 |
| tenant / organization | 未发现实体字段及隔离模型 | 不能声称支持多租户或多组织 |

`CoreModel.update()` 使用 `common_insert_data()`，会同时写入创建人和创建时间（`utils/models.py:215`）。**已确认潜在语义错误**；现有常规 DRF update 未调用此帮助方法，不能将其说成所有更新都已破坏创建时间。

### 7.2 全部自有具体模型

以下类均位于 `src/backend/coreadmin/system/models.py`，行号用于定位。

| 模型（行） | 关键字段/关系 | 完整性与未来影响 |
| --- | --- | --- |
| Role (12) | name、唯一 key、sort、status | 可保留角色概念；不是方法或设备资格 |
| Users (39) | CoreModel + AbstractUser；唯一 username；role/post M2M；dept PROTECT | 自定义用户已配置；保留模型身份比未来再次替换用户模型风险低；敏感字段写入必须修复 |
| Post (94) | name、code、sort、status | code 无 DB 唯一约束；未发现独立岗位 router/page |
| Dept (111) | parent 自关联 CASCADE，唯一可空 key | 用户 dept 使用 PROTECT，但部门树自身无防环数据库约束 |
| Menu (177) | parent CASCADE、路由/组件/外链、可见性与状态 | 树与页面能力可复用；不是业务对象权限 |
| MenuField (235) | model 字符串、menu FK、field_name、title | 缺 `(menu,model,field_name)` DB 唯一；模型重名/重命名风险 |
| FieldPermission (247) | role/field FK；query/create/update flags | 缺 `(role,field)` 唯一，后端未完整执行 |
| MenuButton (261) | 唯一 value；menu FK；api/method/sort | 权限与 URL/前端组件耦合；method 未绑定已定义 choices 参数 |
| RoleMenuPermission (290) | role/menu FK CASCADE | 缺角色+菜单唯一，重复授权风险 |
| RoleMenuButtonPermission (315) | role/button FK；data_range；dept M2M | 缺角色+按钮唯一；范围是按钮级，不是单独 Role.data_scope |
| Dictionary (353) | parent PROTECT；label/value/type/status/color | value 无 DB 唯一；save/delete 刷新缓存；不可充当方法版本 |
| OperationLog (400) | 请求体、路径、IP、方法、响应摘要 | 无 old/new/reason/object version；可普通 CRUD |
| FileList (440) | FileField、file_url、engine、MIME、size、md5sum | size 是字符串；hash 无索引/唯一；无业务引用和不可变状态 |
| Area (480) | 唯一 code；pcode 自关联至 code，CASCADE | 可作为地址字典；有逐条子节点查询 |
| ApiWhiteList (509) | url/method、enable_datasource | 高敏策略表；缺 URL+method 唯一，regex 规则需严格校验 |
| SystemConfig (529) | parent CASCADE；value/data_options/rule/setting JSONField | 唯一 `(key,parent_id)`；parent NULL 根项不能仅靠此保证唯一，应用查重有竞态 |
| LoginLog (590) | username/IP/UA/浏览器/系统/地理信息 | 当前保存成功登录；无可靠失败登录记录及不可变性 |
| MessageCenter (619) | title/content；target_user through；dept/role M2M | 文本通知可改造；不是审批任务 |
| MessageCenterTargetUser (638) | user/message FK CASCADE；is_read | 缺 `(users,messagecenter)` 唯一；重复通知/已读行风险 |
| DownloadCenter (657) | 任务状态 0/1/2/3、文件、大小、MD5 | 导出状态而非工作流；可复用任务展示外壳 |

### 7.3 约束与删除

**已确认事实：**大量 ForeignKey / ManyToMany 显式 `db_constraint=False`，初始迁移也保持该设置。ORM 的 PROTECT/CASCADE 仍有作用，但不能代替数据库外键对直接 SQL、后台任务与并发导入的一致性保护。未发现自有业务 `GenericForeignKey`、显式 `CheckConstraint` / `UniqueConstraint` / `Meta.indexes`；这不等于数据库没有任何索引，主键、unique 和 Django 默认 FK 索引仍应区分。

`SoftDeleteQuerySet` 只有 pass，批量 `.delete()` 未覆盖；SoftDeleteManager 还在 filter 中改变共享实例标志。SoftDeleteModel.delete 递归处理关联对象，未统一遵守各模型删除策略，普通关联对象也未必接受 `soft_delete` 参数。**不建议原样用于 LIMS。**

**后续建议：**未来关键引用开启真实 FK，使用 PROTECT/RESTRICT 思路保留追溯链；合法范围、序号、唯一关系和版本号建立数据库约束。已执行试验、原始文件、结果版本、审批及已签发报告不允许普通物理删除。不要把缺少约束的 CoreModel 原封不动推广至所有新 App。

## 8. API Architecture

### 路由结构

根路由见 `src/backend/application/urls.py`：

- `/api/system/`：系统 API；未发现 `/api/project/`、独立 `/api/user/` 或 LIMS 前缀。
- `/api/login/`、`/api/logout/`、`/api/token/refresh/`。
- `/api/captcha/`、`/api/init/dictionary/`、`/api/init/settings/`。
- `/api/swagger/`、`/api/swagger.json` / `.yaml`、`/api/redoc/`、`/api/api-auth/`、`/apiLogin/`。
- `/healthz`、`/readiness` 由中间件处理。
- `/media/` 通过 Django static helper 在 DEBUG 条件下提供；非生产受控下载。

`system/urls.py` 注册 17 个资源：`menu`、`menu_button`、`role`、`dept`、`user`、`operation_log`、`dictionary`、`area`、`file`、`api_white_list`、`system_config`、`message_center`、`role_menu_button_permission`、`role_menu_permission`、`column`、`login_log`、`download_center`。

资源继承 list/create/retrieve/update/partial_update/destroy，常有 `multiple_delete`、`import_data`、`export_data`、`update_template` 等继承动作；即使未配置导入导出字段，也可能暴露动作并在调用时 assertion 失败。额外显式路径包括 `user/export/` POST、`user/import/` GET/POST、`system_config/save_content/` PUT、`get_table_data/<int:pk>/` GET。

### 统一规范及偏差

| 项目 | 当前规则 | 偏差/风险 |
| --- | --- | --- |
| View | CustomModelViewSet → ModelViewSet（含 GenericViewSet 能力） | 未发现另一个独立 GenericViewSet 业务体系；登录/初始化用 APIView/TokenObtainPairView |
| Serializer | ModelSerializer + DynamicFieldsMixin；按 action 指定 serializer | 多处 fields='__all__'；restql 动态字段选择不等于安全授权 |
| 返回 | 成功 `{code:2000,msg,data}`；列表增加 page/limit/total/is_next/is_previous | 多数 ErrorResponse 业务码 4000，HTTP 默认仍 200；刷新 token 等第三方接口不是同一封装 |
| 分页 | PageNumberPagination，page/limit；默认 10，最大 999 | 深分页/COUNT 成本；非法页可能返回空而隐藏错误 |
| 查询 | CustomDjangoFilterBackend、SearchFilter、OrderingFilter | 默认 filter_fields/order_fields 全开放；CharField 常变 icontains；JSON/File 排除自动过滤 |
| 时间过滤 | create_datetime_after/before、update_datetime_after/before | 来自 CoreModelFilterBankend |
| 排序 | `ordering=字段` 或 `-字段` | 未按业务建立字段白名单和稳定复合排序 |
| 权限 | 默认 IsAuthenticated；通用 ViewSet 覆盖为 CustomPermission | action 可进一步覆盖，导致 S01/S02 |
| 异常 | CustomExceptionHandler 转统一 ErrorResponse | 通用 Exception 的 str(ex) 返回客户端；500/403 语义被削弱 |
| 版本 | 未发现 DRF versioning 配置或 URL v1 | 文档 default_version='v1' 不构成 API 版本管理 |
| 文档 | Swagger、ReDoc；DEBUG 下 AllowAny | 描述仍是 Snippets/Test，认证定义写 basic，与 JWT 实际协议不一致 |

**RESTful 判断：**基础资源 CRUD 接近 REST；大量动作接口、GET 更新消息已读、状态码约定和批量逻辑使其不是严格一致的资源 API。对 LIMS 应明确命令接口、幂等性、冲突响应和审计关联 ID。

## 9. Authentication and Authorization

`AUTH_USER_MODEL='system.Users'`，Users 继承 AbstractUser；已保留 Django 的 groups/user_permissions/is_superuser 等字段，但主要 API 权限使用自有 Role/MenuButton，而非 DjangoModelPermissions。

用户所属部门是单 FK，可空；角色和岗位是多对多。**Organization 实体未发现**；部门树不能等同于客户、法人或多租户组织隔离。

认证支持 JWT 与 Session。JWT 请求头为 `Authorization: JWT <token>`；access 1440 分钟，refresh 1 天，ROTATE_REFRESH_TOKENS=True。未启用 token_blacklist App；`LogoutView.post` 只返回“注销成功”，未吊销 token，也未执行 session logout。旧 token 在有效期内是否继续可用应作为后续测试重点，不能把前端清 Cookie 当作后端失效。

密码存在多条不一致路径：Users.set_password 对原文先 MD5 再调用 Django hasher；创建 serializer 自行 MD5 + make_password；导入又预先 MD5 再 set_password，可能双重 MD5；登录 backend 尝试原输入和一次 MD5；首次改密/重置与普通改密编码不同。**不是“数据库明文 MD5 存储”**，外层仍使用 Django 密码哈希，但混合约定提高兼容和安全维护风险。`validate_complex_password` 直接 return password，未执行其声称的复杂度校验；settings 声明的 AUTH_PASSWORD_VALIDATORS 未在这些 API 路径显式调用。

登录失败 5 次禁用账号；未发现 DRF throttle。`ApiLogin` 使用另一认证入口，不经过 LoginSerializer 的验证码与错误计数。成功登录日志在 token 路径保存，失败与其他入口覆盖不完整。`pwd_change_count` 主要参与前端首次改密流程，未发现后端禁止未改密账号访问所有业务 API 的统一检查。

浏览器 `Session.set('token')` 实际使用 js-cookie，未显式设置 Secure/SameSite，且 JS 可读；前端 sessionStorage 和 Cookie 不是同一个安全边界。

## 10. RBAC and Data Permission

### 关系与执行

```text
Users ──M2M── Role ──RoleMenuPermission── Menu
  │              ├──RoleMenuButtonPermission── MenuButton(api,method,value)
  │              │            └──M2M── Dept（自定义数据范围）
  │              └──FieldPermission── MenuField(menu,model,field_name)
  ├──FK── Dept ──parent── Dept
  └──M2M── Post
```

**已确认：**五类数据范围都有枚举和过滤实现，范围存储在 RoleMenuButtonPermission：0 本人、1 本部门及下级、2 本部门、3 全部、4 指定部门。非超级管理员无部门时返回空；模型无 dept_belong_id 时放行；超级管理员放行；白名单可关闭数据过滤。

**正确性风险（`src/backend/coreadmin/utils/filters.py:73`）：**

1. 多角色包含本人范围 0 时提前返回本人数据，未形成除全数据之外的完整权限并集。
2. 指定部门查询只按角色与 data_range=4，未限制当前 menu_button，可能把另一 API 的指定部门范围带入当前接口。
3. 权限类支持 PATCH，但数据过滤器 methodList 缺 PATCH/HEAD；可产生 ValueError，行为不一致。
4. CustomPermission 未筛选 role.status，而数据范围查询筛选 role.status=1；禁用角色在 API/菜单/按钮层不一定失效。
5. 白名单 regex 缺乏统一转义/完整匹配策略；不应将任意数据库字符串视为可靠路由权限模式。
6. 不经过 `filter_queryset/get_object` 的自定义动作不会自动获得对象范围保护。`has_object_permission` 业务实现未发现。

前端动态菜单来自 `MenuViewSet.web_router`；按钮 permission value 由 `menu_button_all_permission` 返回；前端 `auth()/auths()/authAll()` 和指令控制显示。列权限通过 FieldPermissionMixin 返回元数据，Vue 的 handleColumnPermission 控制 query/form/edit 显示；通用后端字段裁剪注释意味着隐藏列仍可能通过 API 读取或修改。

### 对 LIMS 角色和资格的适配

实验员、技术负责人、审核人、批准人、样品管理员、设备管理员、质量负责人、项目管理员、系统管理员可以用 Role 表表达“角色名称及功能入口”，但当前系统**只部分具备角色容器**，还不能可靠执行这些职责边界。

检测方法资格、设备操作资格、审核资格和报告批准资格均**未发现**对应授权记录、版本范围、有效期、授权人、撤销、培训依据及执行时核验。后续应把“有按钮”与“对这个任务/方法版本/设备且在这个时间具有资格”分开。还需项目成员/客户数据范围、本人不得复核本人结果、审核与批准职责分离，以及超级管理员不能悄悄改写已签发记录的规则。不能把部门数据权限直接当作项目保密或技术资格授权。

## 11. Audit Trail

### 当前日志能力

| 日志类型 | 当前状态 | 证据和限制 |
| --- | --- | --- |
| 运行日志 | 已有 | settings.LOGGING，控制台 + server.log/error.log；每份 100 MB，分别保留 5/3 个备份 |
| 登录日志 | 部分具备 | LoginSerializer 成功后调用 save_login_log；保存用户名、IP、浏览器、系统等；失败登录、ApiLogin 不统一覆盖 |
| 操作/API 日志 | 部分具备 | ApiLoggingMiddleware 对具有 queryset 的视图、配置方法建立 OperationLog；不是所有 API 请求日志 |
| Model 修改历史 | 未发现 | CoreModel 只有最近一次 modifier/update_datetime |
| 不可变 AuditTrail | 未发现 | 没有 old/new/reason/object_version，也没有数据库禁止更新删除或独立保全机制 |

| 审计要素 | 能力 | 具体说明 |
| --- | --- | --- |
| WHO | 部分具备 | creator/modifier、登录用户名；引用可被删除/修改，不是不可变身份快照 |
| WHEN | 部分具备 | create/update_datetime；USE_TZ=False，API 格式秒级；未发现统一事件时间/时区策略 |
| WHAT | 部分具备 | 请求路径、方法、请求体和模块名；不足以表达业务语义 |
| OLD VALUE | 完全缺失 | 没有更新前快照或字段差异 |
| NEW VALUE | 部分具备 | 请求体可能包含输入，但不是最终持久化结果；json_result 仅 code/msg |
| WHY | 完全缺失 | request_msg 读 session，不是必填、经校验的修改原因 |
| OBJECT | 部分具备 | 路径可能含 ID；无稳定模型/对象/版本外键与事务关联 |
| IP | 部分具备 | 读取 X-Forwarded-For，未声明可信代理边界，可能伪造 |
| REQUEST | 部分具备 | 无统一 request_id/correlation_id，后台任务不走该中间件 |

settings 的 `API_LOG_METHODS=[POST,UPDATE,DELETE,PUT]` 含非标准 HTTP 方法 UPDATE，却遗漏 PATCH；GET 读取副作用也不会被记录。Model signals 只处理消息变化时间，没有全局修改历史机制。

**严重缺陷：**OperationLog/LoginLog 暴露通用 ModelViewSet 的新增、更新、删除及批量删除，不是只读审计 API。中间件还从 request_data 取 `log_id` 用于 `update_or_create(id=log_id)`；在没有 queryset、未由 process_view 覆盖 log_id 的接口（如 LogoutView）上，客户端可提供此字段，存在覆盖已有日志的代码路径。未进行请求复现，但代码未隔离客户端字段与内部日志标识。

脱敏只处理顶层 `password`；`oldPassword`、`newPassword`、`newPassword2`、`password_regain`、嵌套配置中的密钥未覆盖。不能声称日志直接保存全部 JWT 响应：当前 json_result 只存 code/msg；真正的问题是请求体敏感字段与日志可篡改。

**LIMS 结论：**不能满足“修改结果仍保留原结果、原因、操作者、时间、修改前后值”。运行日志和操作日志页面可改造复用；**AuditTrail 应重新设计**。应与业务变更在同一数据库事务内追加事件，保存受控对象版本、身份快照、原因、前后差异和请求/任务关联；关闭普通修改删除入口，并设计独立备份、保留与管理员操作审计。结果版本存储与审计事件各司其职，不能互相替代。

## 12. Workflow / Approval

已搜索 Workflow/Approval/Process/Flow/Task/Node/State Machine 等概念与路由、模型注册。**未发现可运行工作流/审批业务模块。**

发现的痕迹不构成完整能力：

- `CoreModelManager` 在模型存在 flow_work_status 时可按值 1 过滤；当前 system 具体模型无该流程字段，且一个状态过滤不是审批引擎。
- `DownloadCenter.task_status` 的创建/进行/完成/失败是导出任务生命周期，没有审批人员或审批历史。
- `src/web/flowH5.config.ts` 指向 `src/views/plugins/dvadmin3-flow-web/src/flowH5/index.ts`，当前源码未发现该插件目录；Vite alias 还出现 `viwes` 拼写。
- jsplumb / Vant / tenant-schemas-celery 等依赖不能证明有工作流或多租户。

节点、条件分支、驳回、撤回、重新提交、审批历史、资格核验、状态转换事务、并发审批防重均未发现。因此结果“提交→技术复核→审核→批准”和报告“草稿→审核→批准→签发”均需新开发。建议 MVP 先实现有限且可测试的显式状态机与版本绑定审批，不先搭通用可视化流程引擎。审批应绑定具体结果/报告版本；已批准版本更改后必须产生新版本和新的审批链。

## 13. File Management

### 上传与存储路径

`src/web/src/settings.ts` 注册 FsExtendsUploader，form 模式 multipart POST 到 `/api/system/file/`，字段名 file；统一 request 可携带 JWT，**但后端 FileViewSet 自身没有权限要求**。

`FileSerializer.create` 读取上传文件、size、客户端 content_type，遍历 chunks 算 MD5，按系统配置选择 local/oss/cos，可选本地备份。FileList 字段是名称、文件 URL、引擎、MIME、size 字符串、MD5、上传方式和大类，没有 TestRun/Specimen 关联。

本地默认路径由 `media_file_name` 生成 `files/<hash第1位>/<hash第2位>/<md5>.<ext>`；file_url 非空时参与自定义目录。MEDIA_ROOT 是相对路径，不是固定基于 BASE_DIR 的绝对路径。OSS/COS 使用配置前缀+原文件名做对象 key，**同目录同名文件有覆盖风险**，没有应用级不可覆盖保护；桶是否启用版本控制未确认。

### 文件控制评估

| 项目 | 当前状态 | 对 LIMS 的影响 |
| --- | --- | --- |
| 类型限制 | 未发现统一后端扩展名/魔数/MIME 白名单；content_type 来源于客户端 | 不可据此确认实际文件类型；前端 accept 即使存在也不是安全边界 |
| 大小限制 | 未发现业务文件大小、用户配额和解析资源限制 | Django 默认内存/请求阈值不是实验室文件总量控制；网关限制未确认 |
| 上传权限 | FileViewSet 空权限 | 可被匿名滥用，占用存储；不能声称所有匿名单条 CRUD 都成功，部分会受数据过滤或参数错误影响 |
| 文件枚举 | get_all 未过滤、未分页 | 可能暴露全部文件 URL、元数据及创建人信息 |
| 下载权限 | 返回本地/对象存储 URL；前端 window.open | 未发现逐对象下载授权；DEBUG media 路由不检查业务用户，桶是否私有未确认 |
| 文件版本 | 未发现 | 同一业务文件更新无法保证历史版本可复现 |
| Hash | MD5 存在 | 可辅助去重；不是防篡改/来源证明；字段非唯一/未显式索引，更新文件时已有 hash 不保证重算 |
| 删除 | 普通/批量 ORM 物理删记录 | 未发现同步删除本地文件/云对象的清理信号；元数据删除不等于字节删除；会留下孤儿文件 |
| 防覆盖 | 未发现应用级不可变策略 | Django 本地文件名冲突处理不能代替业务版本与对象锁；不能推断本地同 hash 一定覆盖 |
| 原始文件关联 | 未发现试验、通道、仪器、校准、采集软件版本字段 | 无法作为 RawDataFile 直接复用 |
| MinIO / S3 | 未发现业务接入 | 文档/依赖内的 S3 上传支持只是可选框架能力 |

**路径穿越证据：**`src/backend/coreadmin/utils/import_export.py` 的 `import_to_data` 将请求 url 与 settings.MEDIA_DIR 用 os.path.join 拼接后直接 load_workbook，无 resolve/允许目录验证。绝对路径可替换前缀、相对路径可越界。影响是服务端尝试读取任意可达 Excel 路径及错误信息暴露；**不是已确认能下载任意类型文件内容**，也未发现直接任意文件下载 API。

**适配结论：**上传交互和存储适配函数可参考，现有 FileList 不适合作为正式试验原始数据档案。建议原始字节使用独立不可变 key，SHA-256/大小/采集来源入库，下载走授权或短期签名，建立版本和保留策略。原始数据、曲线图、计算输出、签发 PDF、SOP/标准附件应分别标记类型和受控状态；任何“重新上传”产生新记录，不覆盖已关联的原始文件。

## 14. Vue Frontend Architecture

### 当前组成与执行路径

- `main.ts` 安装 Pinia 持久化、Vue Router、Element Plus、VXE、i18n、FastCrud；菜单布局、标签页和 keep-alive 已有实现。
- `router/index.ts` 使用 Hash 路由与 token 守卫；`stores/themeConfig.ts` 默认 isRequestRoutes=true。
- `router/backEnd.ts` 从后台获取菜单，通过 import.meta.glob 匹配本地 Vue/TSX 组件，再 addRoute；不是任意后端源码执行。
- `stores/frontendMenu.ts`、`utils/menu.ts`、`router/backEnd.ts` 均有菜单/路由变换；名称与职责有重叠。
- 多数页面以 `views/system/<module>/api.ts + crud.tsx + index.vue` 组织。api 目录不是唯一 API 层，模块内 API 文件是主要方式。
- `utils/service.ts` 承担现行 `{code:2000}` 业务协议、JWT、错误处理和下载；`utils/request.ts` 保留另一套以 code=0 为成功的协议，`src/api/login/index.ts` 仍引用它。

### FastCrud 能力与使用边界

`settings.ts` 全局将 page/currentPage 转成 page/limit，把 ordering 转成 DRF 格式，将响应转成 records/currentPage/pageSize/total。页面 CRUD options 声明列、表单、查询、对话框及 rowHandle；`commonCrud.ts` 提供公共字段配置。

本地 `docs/FastCrud-doc/api/crud-options/request.md`、`form.md` 与实际 transformQuery/transformRes、表单 wrapper 对应；`guide/advance/custom-component.md`、`compute.md` 提供自定义子组件/联动思路。可以支持样品基础信息与主数据 CRUD，但复杂尺寸录入、条件调节时间序列、原始通道映射、结果比对和报告审批不应强塞单张 CRUD 表单。

| 能力 | 当前证据 | 扩展评估 |
| --- | --- | --- |
| Layout / Menu | layout 多布局、面包屑、标签页、动态菜单 | 可保留，统一 route name/component 的规范 |
| Button / Column | auth、directive、Pinia 权限；handleColumnPermission | UI 能力已有；不替代后端授权；需要统一重复 store |
| Table | FastCrud + 自有 components/table；全局 VXE | 已有列表基础；自有页面未发现 VXE 表格实际应用或 tableVersion=v2 配置 |
| 大表格 | 文档 `guide/advance/el-table-v2.md` 说明 1.24.1+ 虚拟表格 | 当前安装 1.28.7，但页面未启用；不能因此保证百万结果交互性能 |
| Form / Dialog | CRUD 配置、Element Plus、foreignKey/manyToMany/tableSelector | 可扩展；跨对象事务、单位/精度与资格校验需后端实现 |
| Upload | FastCrud uploader、fileSelector、头像/裁剪/富文本 | UI 可以改造复用，需新的受控文件 API |
| Chart | home 使用 ECharts；Plotly/echarts-gl 等依赖 | 未发现实际 Plotly 曲线处理业务；曲线抽样/通道单位/数据来源追溯缺失 |
| Dashboard | home/index.vue 固定指标和图表数据 | 展示模板而非真实实验室统计；与 backup 文件内容完全相同 |
| 富文本 | WangEditor + message content | 通知组件 v-html 直接渲染，需要 HTML 清洗和内容策略 |
| 插件 | import.meta.glob 扫描源码和 @great-dream | 部分遗留入口不存在；需按实际功能清理和固定版本 |

**整体判断：**前端适合继续扩展管理界面，但关键实验工作台需要专门页面和清晰状态提示。前端分页不能抵消后端全量查询；表单校验不能成为计量值或审批资格的唯一校验。

## 15. Current Business Modules

当前正式源码模块是：用户/个人中心、部门、角色授权、菜单/按钮、列权限、字典、系统配置、地区、白名单、文件、下载中心、消息、操作日志、登录日志。另有首页、演示页面和 CRUD 模板。

**未发现** Customer、Project、TestOrder、Material、Panel、Specimen、TestTask、TestRun、Equipment、TestResult、Report 等实验室业务实体或对应 API。首页“订单统计/月度计划”标签使用固定数组，不能据此认定已有委托/项目管理。Post 有模型但没有对应独立路由和管理页面。Django messages 与 MessageCenter 是不同机制，均不是工作流。

## 16. Code Quality

### 可取之处

已有统一 Response、分页和 CRUD 适配；各系统 API 按文件拆开；关键类/动作易于定位；前端大多数页面遵循一致三文件模式；已有初始迁移和初始化机制；Python requirements 使用精确版本，前端有 lock 文件。以上能降低基础页面开发成本。

### 规模与集中度

统计为文件总行数（含空行、注释），不等同于单类可执行代码长度：

| 文件 | 行数 | 判断 |
| --- | ---: | --- |
| `src/backend/coreadmin/system/models.py` | 686 | 20 个模型集中，职责过重；并非单个“超大 Model” |
| `src/backend/coreadmin/system/views/user.py` | 453 | 多 serializer、认证相关动作和查询混合，优先拆边界 |
| `src/backend/coreadmin/utils/filters.py` | 425 | 复制/扩展过滤框架内部逻辑较多，升级风险 |
| `src/backend/coreadmin/system/fixtures/initSerializer.py` | 417 | 初始化强耦合与特殊字段处理需建立回归基线 |
| `src/web/src/layout/navBars/breadcrumb/setings.vue` | 824 | 大布局设置组件，低于核心权限问题优先级 |
| `src/web/src/layout/navBars/tagsView/tagsView.vue` | 726 | 导航逻辑集中 |
| `src/web/src/views/system/home/index.vue` 及 backup/index.vue | 各 655 | 哈希完全相同，确定重复文件 |
| `src/web/src/views/system/personal/index.vue` | 533 | 个人信息/交互集中 |
| `src/web/src/components/fileSelector/index.vue` | 521 | 选择、请求、上传与 DOM 操作集中 |
| `src/web/src/views/system/user/crud.tsx` | 425 | 表单配置体量较大，需关注职责而非机械拆行数 |

未发现需要据体积认定的独立“巨型 Serializer”；更突出的是同文件多个 serializer 与绕过验证的 save/action。两份按钮 store 的 SHA-256 相同，且 defineStore 使用相同 `BtnPermission` ID；两份首页也相同。导出任务与同步导出、两套菜单处理和多个密码流程重复且语义逐渐分叉。

## 17. Technical Debt

下表是具体整改清单；“确认”指代码事实，实际数据受损或成功攻击未进行复现。严重性考虑作为 LIMS 基础后的影响。

| ID / 严重程度 | 问题 | 位置（类/函数）与相关逻辑 | 风险原因 / 建议 |
| --- | --- | --- | --- |
| T01 Critical | 授权管理可被普通登录用户修改 | `src/backend/coreadmin/system/views/role.py::set_role_users`；`views/role_menu_button_permission.py::set_role_menu/set_role_menu_btn/set_role_menu_field/set_role_menu_btn_data_range` | IsAuthenticated 后直接取任意 ID；统一管理员/委派范围校验，禁止自提权 |
| T02 Critical | 匿名文件元数据删除及枚举 | `views/file_list.py::FileViewSet/get_all` + `utils/viewset.py::multiple_delete` | 空权限 + 无范围过滤；对上传、枚举、删除、下载分别设策略 |
| T03 Critical（条件） | 实际签名密钥硬编码 | `application/settings.py::SECRET_KEY` | 部署沿用时令牌信任可失守；轮换并使用安全注入，不保留源码兜底 |
| T04 High | 敏感用户字段批量赋值 | `views/user.py::UserCreateSerializer/UserUpdateSerializer.Meta` | fields=all，只保护少数字段；使用白名单，提权/角色变更独立动作 |
| T05 High | 批量删除不走对象数据权限 | `utils/viewset.py::multiple_delete` | get_queryset 而非 filter_queryset；统一授权后按全部目标核验并事务执行 |
| T06 High | 字段权限仅元数据 | `utils/viewset.py::get_serializer` | 裁剪代码被注释、is_create/is_update 无统一强制；按请求实例实施读写白名单 |
| T07 High | 用户列表范围旁路 | `views/user.py::list` | show_all+dept 分支直接 Users.objects 查询，且绕开原 exclude(is_superuser)；所有分支应用同一 scope |
| T08 High | 自定义部门范围串入其他 API | `utils/filters.py::DataLevelPermissionsFilter` | data_range=4 二次查询未限定当前按钮；限定本次动作并测试多角色并集 |
| T09 High | 任意关联表全字段/全量输出 | `views/system_config.py::get_table_data` | 配置指定模型后 objects.values()，不施加模型权限；分页后仍返回 queryset 而非 page；模型/字段白名单和范围过滤 |
| T10 High | 审计可修改删除、客户端 log_id | `utils/middleware.py::__handle_response`；`views/operation_log.py`、`login_log.py` | 用户可写审计数据；内部 ID 不接受请求体，审计追加且无普通 CRUD |
| T11 High | 密码/配置写入日志 | `utils/middleware.py::__handle_response` | 仅顶层 password 脱敏；使用递归敏感字段策略和不记录敏感原文原则 |
| T12 High | 导入路径穿越 | `utils/import_export.py::import_to_data` | 不可信 file_url 直接 join/load_workbook；改用授权文件 ID，校验解析后真实路径 |
| T13 High | 原始对象可覆盖/无版本 | `utils/aliyunoss.py::ali_oss_upload`、`tencentcos.py::tencent_cos_upload` | 前缀+原名 key；不可变随机 key/版本关联/受控保留 |
| T14 High | 文件缺乏类型/大小/配额边界 | `views/file_list.py::FileSerializer.create` | 信任 content_type，未设业务限制；校验内容、限流/配额、隔离预览域 |
| T15 High | 消息存储型 XSS 风险 | `views/message_center.py` 的 content；`src/web/src/layout/navBars/breadcrumb/userNews.vue:13` | 后端无清洗，v-html 消费数据库内容；清洗 HTML，限定链接/图片协议并建立 CSP |
| T16 High | 大量关闭数据库关系约束 | `system/models.py` 与 `migrations/0001_initial.py` | ORM 外写入/并发可形成孤儿；新 LIMS 关键 FK 不沿用 db_constraint=False |
| T17 High | 批量事务范围无效 | `utils/viewset.py::get_serializer` | atomic 只包 serializer 构造，保存发生在退出后；事务覆盖校验与全部业务写入 |
| T18 High | 多表写入缺少整体事务 | `views/role_menu.py::save_auth`、`system_config.py::save_content`、`message_center.py::MessageCenterCreateSerializer.save` | 部分删除/创建后失败可留下半成品；建立服务事务与 on_commit 后续动作 |
| T19 High | 默认开发安全配置 | settings/env：DEBUG=True、ALLOWED_HOSTS=*、CORS 全来源+credentials | 生产沿用会扩大暴露；分离生产配置、明确允许来源和 HTTPS 策略 |
| T20 High | 通用创建/归属字段可变 | `utils/serializers.py::create/update` | 部分 serializer 可写 creator/dept_belong_id；更新只覆盖 modifier；服务端固定审计与归属字段，受控迁移归属 |
| T21 High | 迁移文件被忽略 | `src/backend/.gitignore`：`**/migrations/*.py`（只例外 __init__） | 新迁移易漏入版本控制；后续调整规则并建立迁移可重现验证，本次不修改 |
| T22 Medium | 密码编码分叉与弱验证 | `models.py::Users.set_password`、`views/user.py`、`utils/backends.py` | 兼容分支易出错，复杂度函数为空；统一服务端原文校验和 Django hasher 入口 |
| T23 Medium | logout 不撤销、长期 access | `views/login.py::LogoutView`、settings.SIMPLE_JWT | 被窃 token 持续有效；明确注销/改密失效策略、会话撤销和时长 |
| T24 Medium | 角色禁用规则不一致 | `utils/permission.py`、`filters.py`、`views/menu_button.py` | API 与数据层不同；统一 status 处理及权限缓存失效 |
| T25 Medium | PATCH/HEAD 与权限枚举不一致 | `utils/filters.py`、`permission.py`、`models.py::MenuButton` | methodList.index 抛错；使用统一方法定义和不支持方法响应 |
| T26 Medium | 多角色本人规则提前返回 | `utils/filters.py` | 不正确缩小组合权限；定义并测试合并规则 |
| T27 Medium | 公共更新帮助方法重写创建信息 | `utils/models.py::CoreModel.update` | 使用 common_insert_data；改用 update 字段，确认调用范围 |
| T28 Medium | 软删除实现不可直接复用 | `utils/models.py::SoftDeleteManager/SoftDeleteModel` | 共享状态、QuerySet 未覆盖、递归关系不受控；为业务定义明确归档/作废策略 |
| T29 Medium | N+1 查询普遍存在 | `utils/serializers.py::get_modifier_name`；DeptSerializer；RoleMenuButtonSerializer；UserSerializer | 每条数据查询修改人/部门/角色，部分重复 first；select_related/prefetch/聚合并测量查询数 |
| T30 Medium | 全量导出与全文件内存读取 | `utils/import_export_mixin.py::export_data`、OSS/COS 上传函数 | serializer 全量展开、普通 Workbook、file.read；大数据会放大内存和延迟，使用分块/后台任务 |
| T31 Medium | 多进程配置缓存不一致 | `application/dispatch.py` | settings 字典每进程独立；Redis 分支 refresh/get 不一致；统一共享缓存与提交后失效 |
| T32 Medium | 授权关系缺少联合唯一 | `system/models.py`：RoleMenu*、FieldPermission、MessageCenterTargetUser | create/exists 并发重复；添加业务唯一约束和幂等操作 |
| T33 Medium | 异常响应掩盖故障 | `utils/exception.py::CustomExceptionHandler`；viewset.get_object | 原始异常文本暴露，全部异常变无权限或业务码；保留 HTTP 语义和追踪 ID |
| T34 Medium | 配置缺项引发文件序列化错误 | `views/file_list.py::get_url`、`download_center.py::get_url` | prefix 参数分支访问未定义 settings.ENVIRONMENT；统一环境配置，限制动态主机拼 URL |
| T35 Medium | Celery 链路残缺 | `application/celery.py`、settings、import_export_mixin | 无 broker/beat 注册；task_postrun 导入未声明的 django_celery_results；修复前不依赖其做报告任务 |
| T36 Medium | 未认证菜单排序/部门统计 | `views/menu.py::move_up/move_down`、`dept.py::dept_info` | 空权限且直接 ORM；菜单可被改序，部门统计可泄露；补权限与范围 |
| T37 Medium | 前端请求协议冲突 | `src/web/src/utils/request.ts` 与 `service.ts` | 一个按 code=0，一个按 code=2000；旧 API 入口易失败；统一一套请求协议 |
| T38 Medium | 工具链和声明不一致 | `src/web/package.json`、`.eslintrc.js`、node_modules 元数据 | Node>=16 不满足 Vite；ESLint 9 配旧 eslintrc + ESM 下 module.exports；固定兼容工具链 |
| T39 Low | 重复首页、重复按钮 store | `views/system/home/backup/index.vue`；`stores/btnPermission.ts` / `plugin/permission/store.permission.ts` | 哈希相同，store ID 相同；统一来源，避免后续分叉 |
| T40 Low | 硬编码管理员/状态及旧插件路径 | RoleSerializer.exclude(id=1)、RoleViewSet key='admin'、user.list key='Administrator'；flowH5.config | 身份/角色名语义不一致；采用明确策略与常量，移除无效入口应在后续另立任务 |
| T41 Medium（潜在） | Git 日志 eval | `src/backend/coreadmin/utils/git_utils.py::commits` | eval 解析拼接提交元数据，内容可不可信；未发现业务入口，不能认定现行远程 RCE；使用安全结构化解析 |
| T42 Medium | 运行时与构建代码混用 | `src/web/src/utils/upgrade.ts`、vite.config.ts | 浏览器模块导入 fs/process，加载 Vite 配置写 public/version-build；拆分构建工具与运行代码，验证构建可重现性 |

## 18. Security Risks

### 安全检查覆盖

| 检查项 | 已确认情况 / 未确认边界 |
| --- | --- |
| SECRET_KEY / Secret | settings 含固定签名密钥，env 含明文 DB 密码与另一个未生效命名的密钥；不在报告复写值；Git 历史是否泄露未确认 |
| DEBUG / Host | 当前 DEBUG=True、ALLOWED_HOSTS=*；生产是否覆盖未确认 |
| JWT / Token | 见第 9 节；未发现独立 SIGNING_KEY、统一撤销及 blacklist 配置 |
| Cookie | token 由 JS Cookie 存储；未显式 Secure/SameSite；HttpOnly 无法由 js-cookie 设置 |
| CORS | 全来源与 credentials 同时开启，需按真实前端域收敛 |
| CSRF | CsrfViewMiddleware 与 SessionAuthentication 存在；不能说全局禁用。空权限 DRF API 及匿名登录入口不能只靠该配置假定安全；跨站登录/跨域利用需隔离环境验证 |
| SQL Injection | 主要使用 ORM；搜到健康检查固定 SELECT 1，未发现请求参数直接拼原始 SQL 的已确认入口；动态 ORM 字段查询问题主要是越权/数据暴露，不是 SQL 注入证明 |
| XSS | MessageCenter content 到 userNews v-html 的链路存在；服务端未发现清洗；前端编辑器不应作为唯一安全控制 |
| 上传 | S02、T13/T14；需同时审查直链、类型和配额 |
| 任意下载 / 路径穿越 | 导入路径可越界读取可解析 Excel；未确认任意格式下载或执行，未进行利用 |
| API 越权 / IDOR | 授权 action、批量删除、show_all 分支、动态关联表均有代码证据 |
| 密码策略 | 声明校验器但接口未使用；复杂度函数无实际逻辑，默认密码配置存在，强制首次改密非后端统一策略 |
| 权限绕过 | IsAuthenticated 替换 CustomPermission、permission_classes=[]、直接 ORM、字段权限注释均已确认 |
| 敏感日志 | 仅 password 一种键脱敏；异常 str(ex) 输出；UA/IP 不可信边界未明确 |
| .env | 前端 env 是公开构建配置；生产 API 指向客户端 loopback，发布到其他用户浏览器会指向其本机；后端 env.py 非安全密钥系统 |
| 依赖安全 | 有锁定信息但未做 CVE/许可证全量审计；不能给出“无已知漏洞”结论 |

匿名 `InitSettingsViewSet` 返回配置，仅过滤 status=False 的非根项。fixture 的 default_password 配置为 status=True 且非空。**合理推断：按该 fixture 初始化会公开默认密码配置**；真实数据库是否如此未确认。未来 OSS/COS secret 若误标公开也可能从初始化接口返回，因此必须把公开配置白名单与“启用/禁用”分开，而非一字段兼任两种含义。

高危路径应在隔离测试环境确认：匿名不能枚举/删除文件；普通账号不能修改任何角色成员/授权；用户管理不能写 is_superuser；跨部门单条与批量行为一致；敏感配置不从 init 返回。**本次没有发送这些请求。**

## 19. Performance Risks

**已确认代码问题：**

1. UserSerializer 对每条用户读取角色，RoleSerializer 再读取角色下所有用户，形成高扇出 payload；缺少通用预取策略。
2. CustomModelSerializer.get_modifier_name 每条查 Users；creator_name、dept_name 也会触发关联查询。DeptSerializer 多个子树/count 字段重复查询；RoleMenuButtonSerializer 对同一按钮多次 first。
3. FileViewSet.get_all、MenuButtonViewSet.list 等跳过分页；系统配置关联查询虽然调用 paginate_queryset，仍返回全 queryset。
4. 导出在请求进程内完成全量序列化和普通 openpyxl Workbook；异步分支被注释。OSS/COS 上传一次 file.read，全文件进入内存。
5. 默认所有字符串可 icontains、排序字段全开放；未来在大结果表上极易触发昂贵扫描/排序。
6. 自定义 DataPermission 每请求读取白名单、角色、按钮、授权和部门列表；部门递归无环检测。
7. 字典每次保存刷新全集；系统配置列表按父项查询子项；进程内缓存一致性和过度刷新并存。
8. API 日志写入随业务同步执行，UA 缺失等日志异常可能让已完成写操作返回错误；重试又会放大重复数据风险。

**未确认：**实际 SQL 数量、执行计划、响应时间、并发量、数据库硬件与生产数据量。没有证据给出 TPS 或“可承载百万条”的量化保证。

**后续建议：**先制定查询/payload 上限并修复无分页/N+1；按试验、项目、时间建立索引和稳定排序；大型曲线仅返回窗口/降采样数据；大导出使用后台分块流式任务，但先验证 Celery 配置、幂等与权限快照。不要一开始就以分库分表代替正确查询和约束。

## 20. Testing and Engineering

| 项目 | 当前状态 | 判断 |
| --- | --- | --- |
| pytest | 未发现项目配置、测试及依赖声明 | 不具备 pytest 回归基线 |
| Django TestCase | tests.py 仅导入，实质是 getMenu 计时脚本 | 无权限/事务/文件/认证断言；直接 django.setup 会加载应用并可能访问数据库 |
| 前端测试 | 未发现 Vitest/Jest/Cypress/Playwright 项目测试和 scripts | 页面行为与权限显示缺乏自动验证 |
| Lint | ESLint 配置和 lint-fix 存在 | 唯一脚本带 --fix 且未显式覆盖 ts/tsx 扩展；当前配置与 ESLint 9 格式存在兼容风险，未运行确认 |
| Formatter | 前端 Prettier；后端 Black/Ruff/isort 未发现 | 格式工具不能替代业务一致性 |
| Type check / mypy | TS strict=true；mypy 未发现；无 vue-tsc/check script | build 是 vite build，不等于完整 TS 类型检查 |
| pre-commit / CI | 未发现 | 提交/合并质量门禁缺失 |
| 依赖管理 | 两份精确 requirements；package-lock 与 yarn.lock 并存 | Python 清单差异明显（waitress、报表/数据依赖等），未指定权威安装来源；前端 package-lock 与安装主要包吻合，但两种 lock 全量一致性未确认 |
| 环境隔离 | 前端 development/production/local_prod；后端单 settings+env | 后端测试/生产配置、密钥注入、数据库隔离和调度隔离未发现 |
| 服务启动 | main.py Uvicorn；serve.py Waitress 0.0.0.0:18000 | waitress 仅 requirements2；实际使用入口未确认；ASGI 设置 DJANGO_ALLOW_ASYNC_UNSAFE=true 需复核必要性 |
| 发布 / 回滚 | 未发现 Docker/Nginx/CI/备份恢复脚本 | .env 中部署注释不能证明交付可复现 |
| 数据库演进 | 存在 0001_initial.py，未连接 DB 检查应用状态 | .gitignore 忽略迁移；del_migrations.py 是删除辅助脚本，本次未执行，未来不应作为受控迁移流程 |
| API 文档质量 | Swagger 可生成，默认描述残留 | 无版本兼容政策和业务示例验收 |

本次选择纯静态审查是为了遵守只新增报告的限制：`vite.config.ts` 在配置加载时调用 generateVersionFile，会写 `public/version-build`；Django settings 会配置日志、URL import 会初始化配置并查询数据库；因此没有以“检查”名义启动这些入口。测试执行结果均为**未执行**，不声称通过构建或测试。

## 21. Reusable Components for LIMS

“可直接复用”仅表示该模块自身概念/展示代码可保留，不表示可以跳过系统级安全门槛后直接上线。

| 当前模块 | 当前状态 | LIMS 可复用性 | 风险 | 建议 |
| --- | --- | --- | --- | --- |
| 用户 | 自定义 Users、登录、个人资料齐备 | 需要改造后复用 | 提权字段、密码编码和撤销不足 | 保留 AUTH_USER_MODEL，重写敏感操作策略 |
| 组织 | 未发现 Organization | 需要重新设计 | 无组织边界；客户与实验室部门不能混用 | 先明确单实验室/多场所边界，不贸然启用多租户 |
| 部门 | Dept 树、人员归属、统计 | 需要改造后复用 | 弱 FK、防环缺失、范围旁路 | 保留树，补约束和可信归属策略 |
| 岗位 | Post 模型、用户 M2M | 需要改造后复用 | 无独立管理 API，code 非唯一 | 不将岗位等同于检测资格 |
| 角色 | Role 与授权关系已有 | 需要改造后复用 | Critical 授权漏洞、禁用不一致 | 保留角色容器，收紧授权管理 |
| API/数据权限 | 路径方法匹配与五种范围 | 需要改造后复用 | 旁路、跨按钮范围、字段未执行 | 重构执行边界；新增项目/对象策略与资格核验 |
| 菜单/按钮界面 | 动态路由与按钮展示已有 | 需要改造后复用 | 与组件名/URL 强耦合 | 保留 UI，后端动作权限独立且稳定 |
| 字典 | 层级字典、颜色、类型 | 可直接复用（普通展示字典） | 缺唯一约束、缓存一致性 | 禁止用可编辑字典替代方法版本/已签发语义 |
| 参数配置 | JSON 表单与缓存 | 需要改造后复用 | 公开配置边界与任意关联表读取 | 公开配置白名单，敏感配置专门存储 |
| 文件管理 | local/OSS/COS 上传与选择器 | 需要改造后复用 | 匿名访问、不可变性与版本缺失 | 保留交互；重构文件服务与授权、设计 RawDataFile |
| 运行/登录/操作日志 | 可记录部分请求 | 需要改造后复用 | 可变日志、脱敏不全、覆盖不完整 | 作为运维日志保留，不能充当 AuditTrail |
| 审计 | 无完整 AuditTrail | 需要重新设计 | 无前后值、原因、防篡改 | 与关键业务事务绑定的追加事件 |
| 工作流 | 仅状态字段/插件痕迹 | 需要重新设计 | 无可运行审批模块 | 新建受控状态机、历史和职责分离 |
| 消息通知 | MessageCenter 和已读关系 | 需要改造后复用 | XSS、重复收件人、多表非事务 | 清洗文本、幂等投递、on_commit，按接收人授权 |
| 定时/后台任务 | Celery/beat 依赖与导出骨架 | 需要改造后复用 | 配置断裂、无可靠运行证据 | 完整任务部署、错误重试、幂等和可观察性 |
| 报表/Excel 导出 | 同步通用导出 | 需要改造后复用 | 全量内存、公式注入需防护、无报告审核 | 可用于管理数据导出；正式检测报告另建 |
| 正式检测报告 | 未发现 Report/ReportVersion | 需要重新设计 | 无签发、替代版本及发布快照 | 建立基于已批准结果版本的报告链 |
| Dashboard | 固定演示数据、ECharts 模板 | 需要改造后复用 | 数字不来自业务、不可验证 | 保留图表外壳，重新定义统计口径/API |
| FastCrud/布局组件 | 全局 request/form/uploader 适配 | 可直接复用（基础页面） | 复杂实验工作台不适合纯 CRUD | 受控操作用专门页面和 API |
| 当前 SoftDeleteModel | 未被业务模型使用 | 不建议复用 | 批量和递归删除语义不可靠 | 用生命周期/作废/归档政策替代盲目软删除 |
| 旧 FlowH5/重复请求入口 | 目录缺失或协议分叉 | 不建议复用 | 隐式维护负担 | 后续确认无使用后单独治理，不作为 LIMS 依赖 |

## 22. LIMS Gap Analysis

优先级定义：**P0 = 开始 LIMS 核心开发前必须解决；P1 = LIMS MVP 阶段必须解决；P2 = 第二阶段解决；P3 = 后续优化。**

“完全缺失”指没有对应业务模型/API；已有 Django/CRUD 开发工具不算业务已具备。“部分具备”仅指存在可借用基础，具体对象仍可能缺失。

| LIMS 能力 | 当前是否具备 | 差距 | 优先级 |
| --- | --- | --- | --- |
| 可信用户/角色/数据隔离 | 需要重构 | 已有 RBAC 但存在越权；缺对象和项目范围 | P0 |
| 数据完整性与事务基线 | 需要重构 | 关闭 FK、批量事务位置错误、缺联合唯一和并发策略 | P0 |
| 不可变文件基础 | 需要重构 | 普通 FileList 可删、公开、无版本，云 key 可能覆盖 | P0 |
| Customer | 完全缺失 | 无客户、联系人、客户数据隔离、合同主体 | P1 |
| Project | 完全缺失 | 无项目、负责人、成员、客户关联 | P1 |
| TestOrder | 完全缺失 | 无委托、接收、检测要求与编号 | P1 |
| Material | 完全缺失 | 无材料批次、体系、方向/来源描述 | P1 |
| Panel | 完全缺失 | 无板材批次、来源、铺层/固化信息及裁样关联 | P1 |
| Specimen | 完全缺失 | 无试样编号、取样位置、方向、链路和状态 | P1 |
| SpecimenMeasurement | 完全缺失 | 无逐次尺寸、位置、单位、仪器与测量版本 | P1 |
| Conditioning | 完全缺失 | 无调节环境、起止时间、实测记录及放行条件 | P1 |
| Standard | 完全缺失 | 无标准主档；字典不能代替受控文件 | P1 |
| StandardVersion | 完全缺失 | 无版次、有效期、替代关系及附件快照 | P1 |
| TestMethod | 完全缺失 | 无实验室方法定义 | P1 |
| TestMethodVersion | 完全缺失 | 无方法版次、适用范围和批准/生效状态 | P1 |
| TestProtocol | 完全缺失 | 无针对委托/任务的参数与方法版本冻结 | P1 |
| TestTask | 完全缺失 | 无计划任务、试样分配、方法与资格检查 | P1 |
| TestRun | 完全缺失 | 无一次实际试验、无效/重测及执行事件 | P1 |
| Equipment | 完全缺失 | 无设备台账、状态及量程/能力 | P1 |
| EquipmentCalibration | 完全缺失 | 无校准记录、有效期和证书关联 | P1 |
| Fixture | 完全缺失 | 无夹具型号、适用方法和使用状态 | P1 |
| EquipmentUsage | 完全缺失 | 无 TestRun 对设备/传感器/夹具的实际使用快照 | P1 |
| RawDataFile | 部分具备 | 有文件上传/MD5，缺受控原始数据对象、TestRun 关联、不可覆盖和来源 | P0 |
| RawDataChannel | 完全缺失 | 无通道名、单位、采样率、轴映射、解析版本 | P1 |
| CalculationTemplate | 完全缺失 | 无计算规则、输入输出及单位定义 | P1 |
| CalculationTemplateVersion | 完全缺失 | 无算法版本、批准状态、验证数据集 | P1 |
| TestResult | 完全缺失 | 无数值/单位/有效性、来源与重算记录 | P1 |
| FailureMode | 部分具备 | 字典可承载展示项；无方法相关分类和结果快照 | P1 |
| ResultReview | 完全缺失 | 无复核意见、签署身份、资格、版本绑定 | P1 |
| Report | 完全缺失 | 无正式报告、签发编号、接收方与状态链 | P1 |
| ReportVersion | 完全缺失 | 无报告 PDF/数据快照、替代/作废历史 | P1 |
| AuditTrail | 完全缺失 | 仅有操作日志；无 old/new/reason 与不可变事件 | P0 |
| 方法/设备/审核/批准资格 | 完全缺失 | 角色不能表达版本范围、有效期和授权依据 | P1 |
| 项目级保密与客户隔离 | 完全缺失 | 部门范围无法表达跨部门项目合作与客户保密 | P1 |
| 报告签发职责分离 | 完全缺失 | 无禁止自审、批准与发布控制 | P1 |
| 可靠后台任务 | 部分具备 | Celery 骨架缺部署、幂等、失败恢复 | P1 |
| 设备自动采集连接 | 完全缺失 | 未发现仪器驱动/采集服务；依赖包不是设备集成 | P2 |
| 高级曲线叠加/通道探索 | 部分具备 | 有图表库，缺受控解析/抽样与业务曲线 UI | P2 |
| 实验室 Dashboard | 部分具备 | 演示图表已有，缺真实聚合指标 | P2 |
| 高级可视化工作流编辑器 | 完全缺失 | 只有遗留配置；MVP 应先用明确状态机 | P3 |
| 多租户 SaaS | 完全缺失 | 仅兼容信号/判断，无隔离实现；是否需要未确认 | P3 |

RawDataFile 标 P0 是要求先明确并验证不可变文件基础与接口约定，不要求在开工前完成所有设备导入器。AuditTrail 同理：先确定事件契约和可用基础，再随 MVP 对象逐项接入。

业务链覆盖结果：客户→项目→委托→材料/板材→试样→测量→调节→任务→设备/夹具→执行→原始数据→计算→复核→报告→审核→批准→签发，**没有任何已闭环的现行业务链**。可复用的是身份与管理交互基础，不能用通用状态字段宣布链路已实现。

## 23. Composite Materials Testing LIMS Fit Analysis

### A. Material → Panel → Specimen

**当前：完全缺失业务，技术上可以建立。**Django ORM/PostgreSQL 适合表达这种层级，但现有 Dept/Menu 的可变树模型不能直接作为材料谱系模板复制。

需保持材料批次→板材→试样的明确 FK 和来源，不允许父记录删除导致试样消失。复合材料特征包括铺层/方向、板内位置、加工及取样信息；应先明确术语和编号，避免 Material 同时承担牌号、批次、客户来样三种概念。数据库对唯一编号、父子关系及业务状态建立约束，试样更正使用受控更正/历史，不能任意拖动“树节点”改变来源。现有 CRUD 适合主档编辑和列表，不足以提供谱系追溯。

### B. TestTask 与 TestRun 分离

**当前：完全缺失，现有框架可扩展，但没有现成实现。**任务是待完成的检测意图，一次 Run 是实际执行。应支持一个任务多次 Run，各自保存开始结束、操作者、参数、设备使用、原始文件和有效性。

第一次试验无效时保留 Run #1 及原因，再建立 Run #2，不能更新同一记录使第一次消失。任务完成应指向被采纳的 Run/结果版本；重测不等于覆盖。资格/设备有效期检查、创建执行与状态推进需事务，防止并发开启重复执行。当前 DownloadCenter 状态不含这些语义，不能复用为 TestTask。

### C. Raw Data / Calculated Data / Reported Data 三层分离

**当前：部分技术基础，但需要重构数据/文件基础。**FileList 只保存通用附件，没有“原始”概念；云对象名称可能覆盖、元数据可删除，无法证明结果来源。

方向建议：原始字节保留不动；解析通道记录解析器/通道映射版本；计算结果引用原始文件和方法/计算模板版本；报告引用已批准的具体结果版本并冻结显示精度/单位/取舍。曲线图是派生物，不能代替原始点数据。三层可以关联同一 Run，但不应共用一个可修改 JSON 字段或 URL 来回覆盖。

### D. 结果版本控制

**当前：完全缺失。**CoreModel.update_datetime 只有最后修改时间，OperationLog 不保存旧值，通用 update/destroy 会破坏历史；未发现乐观锁或历史表。

建议 Result V1→V2 采用追加版本与明确当前/采纳关系，每一版记录原因、来源、算法和审核状态。并发更正需要版本匹配或行锁，不能后写覆盖先写。历史结果、已批准引用和 AuditTrail 均保留；重新计算生成新的计算运行/结果版本，不静默更新旧值。

### E. 标准、方法和计算模板版本

**当前：业务完全缺失，ORM 可以实现，但通用可编辑字典/配置不适合。**应区分 Standard 与 StandardVersion、TestMethod 与 TestMethodVersion、CalculationTemplate 与其 Version，并在 TestProtocol/TestRun 上引用所使用版次。

需明确草稿、批准、生效、停用/替代和适用日期。新的标准版次不能自动改变已执行试验；计算模板不仅是公式文本，还包括输入单位、精度、输出、异常处理和已验证数据集。不要用前端表单版本、代码构建号或 Dictionary.value 冒充方法版本。具体 ASTM 版本/标准条文未在本次代码审查中核验，不作合规结论。

### F. 设备、传感器、夹具与校准

**当前：完全缺失业务，框架可扩展。**EquipmentUsage 应关联一次 Run 的实际设备组合：主机 MTS、Load Cell、Extensometer、Fixture、Environmental Chamber 等，而不只保存“试验机名称”字符串。

校准有效性应按实际使用时点、设备状态、量程/能力及适用校准记录判断，保存当时证据；不能只在当前设备主档上读取一个会变化的“有效/无效”布尔值。设备更换、传感器换装、夹具选择和条件箱使用要可追溯。系统时钟、时间精度与历史时点判断需统一；设备校准过期能否例外放行必须由业务明确并受审批，而不是用超级管理员绕过无痕处理。

### 综合适配

Django + PostgreSQL + Vue 足以作为上述关系、数据录入、受控动作和展示的技术载体；**当前应用层实现不具备这些业务保证**。优先治理数据/权限边界，再建设单一试验方法的端到端闭环，比先扩充菜单和 CRUD 表更稳妥。

## 24. Recommended Django App Evolution

以下仅为职责方向，不是要求本次新建 App，也不预设完整新数据库。

| 演进边界 | 建议责任 | 与现有代码关系 |
| --- | --- | --- |
| system（保留并收缩） | 用户、角色、部门、菜单、普通字典和配置 | 保留 Users 表身份；先治理权限，逐步降低 20 模型混合职责 |
| access / qualifications | 对象策略、项目成员权限、方法/设备/审核资格 | 不再把所有业务授权堆进 MenuButton URL |
| customers / orders | Customer、Project、TestOrder | 新开发；MVP 可先合为一个业务 App，避免过早拆碎 |
| samples | Material、Panel、Specimen、Measurement、Conditioning | 第一个正式业务模块；保持来源链与样品生命周期 |
| methods | Standard/Version、TestMethod/Version、Protocol、计算模板版本 | 新开发受控主数据，不用 SystemConfig 代替 |
| equipment | 设备、校准、夹具及使用证据 | 新开发，给执行服务提供可用性检查 |
| testing | TestTask、TestRun、执行与重测动作 | 新开发；编排样品、方法、资格、设备，不把外部模型全部复制进 testing |
| data / results | 原始文件/通道、解析、计算、TestResult/版本、FailureMode | 文件服务提供不可变内容，结果保留来源和计算版本 |
| review / reports | ResultReview、报告版本、审核/批准/签发 | MVP 可集中实现明确状态机，不先抽象万能 Workflow |
| audit | 跨业务追加事件、查询与保留 | 重新设计；不依赖 HTTP 中间件作为唯一来源 |
| files / jobs / notifications | 文件授权与存储、可靠任务、消息投递 | 从 system 拆出时保留兼容入口，逐步改造 |

依赖方向应是业务服务调用明确定义的权限/审计/文件接口；公共基础不要反向导入每个业务 ViewSet。避免为了“通用”让任意模型通过名字字符串被系统配置读取，或依赖 QuerySet manager 隐式隐藏未批准对象。跨对象约束与流程推进集中在服务中，API、后台任务和导入复用同一逻辑。

## 25. Data Architecture Risks

### 长期运行与容量

**风险判断：**PostgreSQL 和 BigAutoField 本身不是百万 TestResult 的阻碍；当前没有 TestResult，无法对实际容量作确认。主要障碍是应用查询模式、无索引的部门字符串、开放式模糊查询、全量输出、历史版本缺失和无法重现的迁移流程。长期运行前还需备份恢复、保留归档、容量告警和慢查询证据，当前未发现相关工程配置。

### 数据库与文件的分工

| 数据类型 | 建议位置与理由 | 当前差距 |
| --- | --- | --- |
| 客户、委托、试样、任务、运行、设备、方法引用 | 关系数据库；需要 FK、筛选和事务 | 全部业务缺失，通用 FK 策略需调整 |
| 结果数值/单位/有效性、版本、审批事件 | 数据库；可查询、追踪并冻结引用 | 无专门精度/版本/审批模型 |
| 原始文件元数据 | 数据库；hash、大小、对象 key、来源、Run、通道说明 | FileList 只具通用附件字段，无不可变关系 |
| 原始试验 CSV/Excel/设备二进制/大批采样点 | 文件或对象存储，保留原始字节；按需求解析为可读派生格式 | 无统一档案策略、版本/保留保证 |
| 照片、断口图片、曲线图、PDF、SOP/标准附件 | 文件/对象存储；数据库存受控元数据与版本关系 | 普通 URL 不足以授权或保全 |
| 曲线窗口/降采样/统计派生数据 | 可重建缓存或派生文件；少量摘要可入数据库 | 未发现曲线处理管道 |
| 系统偏好等低风险配置 | JSONField 可适用 | 不应用 JSONField 取代强约束结果/校准关系 |

**是否把原始曲线直接入库：不建议默认把所有原始采样点塞进通用 PostgreSQL JSONField 或一行一个点的普通业务表。**先保留不可变原始文件，再按采样规模、跨试验查询需求和压测结果选择派生存储；不能一概认定时序入库不可行。百万个结果记录与百万个高频采样点/大文件不是同一容量问题。

### 索引方向（不是本次迁移设计）

- 当前应检查 modifier、dept_belong_id 的类型和索引设计；日志 create_datetime、文件 md5sum/creator/create_datetime、消息收件人+已读状态、角色+按钮等常用查询是否满足需要。
- 未来为业务编号建立唯一约束；常用关系如 specimen→panel、panel→material、run→task、result→run/version、usage→equipment 建立关联索引。
- 按真实查询评估 `(project,status,created_at)`、`(task,run_sequence)`、`(object,version)`、`(equipment,valid_until)` 等联合索引；版本唯一约束兼顾索引。
- RawData 元数据按 run_id、采集时间、hash/对象 key 查找；全表 hash 唯一是否符合业务需另决策，重复字节可能具有不同采集/委托来源。
- 审计按对象类型+ID+事件时间以及操作者+时间查询；是否分区依据保留与容量测试，而非开工就预设。
- 不给所有 JSON 字段和低选择性 bool 无差别建索引；先看执行计划与业务查询。

### 事务、并发与版本边界

| 业务 | 必须考虑的边界 |
| --- | --- |
| 委托接收/批量建样与编号 | 编号唯一、父子关系和创建事件一致；失败不可半成功 |
| 材料/板材/试样关系更正 | 校验可更正状态、保留原因和来源变更事件 |
| 创建 Run / 占用设备 | 校验资格、方法版本、设备状态与任务状态；防重复提交 |
| 提交/复核/批准结果 | 状态与结果版本绑定，检查预期版本/行锁；审计同事务 |
| 生成/签发报告 | 固定结果版本和模板版本，编号/签发动作幂等；先生成文件再可控提交引用 |
| 上传原始数据并关联 | 文件存储与 DB 不是同一事务；需要暂存/校验/正式引用和孤儿修复机制 |
| 消息/后台计算派发 | 业务提交后派发；任务幂等、失败可恢复，避免事务未提交就消费 |
| 授权与范围变更 | DB 关系变更和缓存失效一致；并发/重复请求不能无限添加关系 |

应 Versioning 的对象：标准版本、方法版本、试验协议、计算模板、解析/计算配置、试验结果、正式报告；关键测量更正也需保留历史。原始文件用不可变新对象表达新版本；普通 UI 偏好不必全部版本化。

不允许普通物理删除的对象：已接收后有下游引用的试样/委托来源、已执行 Run、原始数据档案、参与试验的校准证据、历史结果、审批记录、已签发报告版本、AuditTrail。用户/设备/方法停用优于删除历史身份；删除政策需兼顾错误草稿和受控归档，不等于所有表一律软删除。

## 26. Refactoring Priorities

### P0：开始核心业务开发前

1. **封闭权限边界**：修复 S01/S02、敏感用户字段、单条/批量范围一致性、字段写权限；建立匿名、普通用户、跨部门和管理员的回归矩阵。
2. **建立安全环境基线**：正确加载并轮换密钥，移出明文敏感配置，关闭生产 DEBUG，收敛 Host/CORS，明确 token/Cookie/注销策略和公开配置白名单。
3. **修正数据完整性与工程基线**：定义可信审计/归属字段、真实 FK/唯一约束策略与事务模板；统一依赖和环境；让已有及未来迁移可版本化、可重现。不得以删除迁移重建代替演进。
4. **先形成不可变文件基础**：上传/下载对象授权、类型/大小边界、不可覆盖 key、hash/来源元数据和恢复策略，关闭文件匿名删除旁路。
5. **建立版本与 AuditTrail 契约**：明确不可变历史、理由、身份、前后值和事务一致性；验证最小审计事件链，确定结果/报告更正语义。

这五项是启动门槛，不要求一次重写全部 system 或完成所有 LIMS 业务。

### P1：MVP 必须具备

完成一个方法范围内的客户/委托、样品谱系、测量/调节、任务/Run 分离、设备校准、资格核验、原始文件、可验证计算、结果版本、复核批准、报告版本及签发闭环。实现可靠任务与备份恢复验证；对状态转换/重测/更正/拒绝越权做自动测试。先验证正确性和可追溯性，再扩充检测方法数量。

### P2：第二阶段

设备自动采集、复杂曲线探索、多方法/多设备组合、更丰富条件调节、更多统计 Dashboard、大型文件断点/分块与导出优化、长期归档及查询性能优化。

### P3：后续优化

可视化流程设计器、多租户产品化、高级主题和首页定制、非必要插件扩展。优先避免把现有缺失的“插件痕迹”恢复成新的基础依赖。

## 27. LIMS Development Readiness

| 维度 | 就绪判断 | 原因 |
| --- | --- | --- |
| 技术路线 | 可继续 | Django/DRF、PostgreSQL、Vue/FastCrud 足以作为应用载体 |
| 管理界面开发 | 基本具备 | 路由/布局/CRUD/上传/图表组件较完整 |
| 安全与身份边界 | 未就绪 | Critical 授权/文件问题，密钥与敏感字段风险 |
| 实验记录完整性 | 未就绪 | 物理删除、弱关系、无版本/历史 |
| 文件档案 | 未就绪 | 可变 URL/对象、缺授权与不可变保留 |
| 技术复核/批准/签发 | 未就绪 | 工作流与资格体系缺失 |
| 可重复计算 | 未就绪 | 无方法/算法版本、原始通道与结果来源关系 |
| 自动测试与交付 | 未就绪 | 无有效回归套件/CI，环境与迁移管理存在缺口 |
| 百万结果容量 | 未确认 | 无业务模型、真实负载和压测证据 |

**可开展只读业务梳理与领域建模；不宜直接在当前通用 CRUD 上持续堆叠正式检测结果与报告模块。**解决 P0 后，可以有条件进入 MVP。该判断不是对任何实验室法规/认可标准的合规认证；本次仅审查技术代码与所需能力差距。

## 28. Recommended Next Steps

### 建议执行顺序与验收证据

1. 在独立后续任务中建立安全修复清单，优先 T01–T06；验收使用最小权限账号和匿名请求，证明授权管理、文件及跨部门对象不能被旁路访问。当前生产暴露情况另行核查。
2. 固定权威 requirements/lock、Python/Node 环境和启动方式，恢复可重现迁移政策；在隔离测试数据库验证初始化、迁移和恢复，不在生产运行删除迁移工具。
3. 定义并验证不可变文件与 AuditTrail 的最小契约，以及业务服务事务模板；一项业务更正必须能够查出人、时间、原因、旧值、新值和对象版本。
4. 与实验室确认样品编号、材料/板材层级、试样方向/位置、接收与退样、调节与测量规则；选一个明确方法作为 MVP 切片。所选标准与计算规则的技术正确性另行评审。
5. 开发样品谱系模块，再接入任务/Run、设备校准、原始数据与结果计算；最后构建复核/报告链。每层保留版本、来源和拒绝非法状态转换的测试证据。
6. 实现一次完整样例：来样→裁样/编号→测量→调节→首次无效试验→重测→原始文件→计算→更正生成 V2→复核→报告批准/签发；能重新找回无效 Run 与 V1，并证明报告引用的具体版本未被覆盖。

### 最终明确回答

**1. 当前项目是否适合作为 LIMS 的基础框架？**  
**C. 可以使用，但需要较大范围重构。**技术栈与管理界面具有可保留价值，故不必整体推倒；但严重授权缺陷、文件不可变性不足、缺少版本审计/审批/资格，以及数据库约束和工程门禁缺口，使其无法通过少量局部改动就承担可信实验室记录。

**2. 哪些模块应该保留？**  
保留 Django/DRF 项目骨架、现有自定义用户模型身份、部门/角色概念、菜单与布局、普通字典、FastCrud 通用页面模式、前端组件/i18n、图表外壳；保留运行日志作为运维工具。

**3. 哪些模块应该重构？**  
RBAC 授权管理、API/对象/字段权限执行、用户敏感操作与密码流程、CoreModel 公共字段与删除策略、文件服务、系统配置公开边界、操作日志脱敏与权限、导入导出、消息、后台任务链路、前端请求/权限 store，以及依赖/环境/迁移/CI 基线。

**4. 哪些模块应该重新开发？**  
客户/项目/委托、材料/板材/试样及测量调节、标准/方法/协议版本、检测任务和执行、设备/校准/使用、原始数据文件/通道、受控计算/结果版本、技术资格、结果复核、报告版本/审批/签发，以及真正的 AuditTrail。现有通用 FileList 和 OperationLog 不应换个名称就作为 RawDataFile/AuditTrail。

**5. 开始 LIMS 前最优先解决的 5 个问题是什么？**  
①权限旁路和提权；②密钥/生产配置/认证基线；③数据约束、事务及可重现工程基线；④受控不可变文件；⑤结果版本与追加审计契约。具体完成标准见第 26 节 P0。

**6. 推荐第一个正式开发的 LIMS 业务模块是什么？**  
**样品接收与谱系追踪（samples）**：以最小客户/项目/委托引用为上下文，先实现 Material→Panel→Specimen、唯一编号、来源与状态、基础尺寸测量记录；调节可在同一 MVP 切片接入。它是后续 TestTask/TestRun、设备使用、计算与报告共同的追溯起点，也能及早检验权限、事务、文件与审计基础。该建议以 P0 已解决为前提。

**7. 哪些当前设计可能成为重大技术债？**  
把权限绑定前端组件名和 URL、把隐藏按钮/列当安全控制、所有对象默认通用 update/destroy、关系大量关闭 DB 约束、creator/modifier/dept_belong_id 可变且语义不一致、以最后更新时间冒充历史、以普通文件 URL/MD5 冒充原始数据保全、系统参数动态读任意模型、跨对象写入缺事务、进程内全局配置缓存、导出全量驻留内存，以及忽略迁移/缺少回归测试。若这些模式复制到每个新 LIMS App，未来修复会涉及全部业务记录和审批证据，成本远高于开工前修正基础。

---

本次交付仅为本 Markdown 报告；所有整改、建模、迁移、依赖变更和开发建议均未执行。原有代码、配置、迁移、文档和资源未由本次任务修改；未提交 Git commit。

### 交付核验记录与限制

报告结构核验：28 个一级编号章节完整、顺序为 1–28；两张要求的总结表已包含；指定的 29 个 LIMS 实体均有独立差距表行；Markdown 代码围栏成对。

文件核验：新增报告前记录了 909 个非 node_modules 原有文件的聚合 SHA-256，交付核验仍为 909 个原有文件，根目录唯一新增项为本报告。前后聚合值不同（记录值 `D96445F54CBC9F238CA1BB670C319B02182715ABBD55495B10CABDEB28BFE3EF`，核验值 `5B6025AD4EA5EEFD0FB3AAD2A8744362F0D77CDD6BB074CB22F2B68108FD6E31`），因此**不能声称全工作区前后内容完全未变**。只读复查发现 `src/backend/.idea/workspace.xml` 有较新的更新时间（2026-09-14 17:53:30），存在 IDE/其他进程并行写入的可能；由于初始保留的是聚合值而非逐文件基线，具体变化文件全集和来源**未确认**，不作推断性归责。

本次工具调用中，写操作仅为创建/续写 `CURRENT_PROJECT_REVIEW.md`；没有修改原有文件的写命令，也没有运行会生成构建、日志、迁移或数据库内容的项目入口。node_modules 未纳入聚合哈希，Git 历史与逐文件历史差异无法从当前无 .git 的工作区核验。
