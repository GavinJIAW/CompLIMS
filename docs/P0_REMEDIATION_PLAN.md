# P0 Remediation Plan

## 1. Executive Decision

本方案基于 `CURRENT_PROJECT_REVIEW.md` 和再次读取的当前源码，适用于第三方复合材料力学性能测试实验室 LIMS 的基础整改。审查日期：2026-09-14。结论：**现在不建议开始正式 LIMS 业务开发；先通过 5 个 BLOCKER 验收门槛，按 6 个批次渐进整改。** 保留 Django、DRF、Vue、FastCrud、Users、Dept、Role；不推倒 coreadmin，也不先建立 Customer、Specimen、TestRun 等业务表。

本阶段只编写本文件，没有实施以下设计、生成迁移、安装依赖或运行应用。本文所有“拟新增”“拟修改”“测试命令”均是后续实施要求，不代表已完成。静态确认不等于线上漏洞利用成功；未连接数据库，未验证部署参数、对象存储 ACL、生产网络、实际用户权限和迁移应用状态。当前目录未发现 Git 元数据，因此“源码含 Secret”已确认，“Secret 曾进入 Git 历史”未确认。Secret 不在本文复述；已进入源码的密钥 **must rotate**，不能因清理源码而继续使用。

证据路径以项目根目录为基准；`B/` 表示 `src/backend/`，`W/` 表示 `src/web/`。类/函数名是主要定位依据，行号只作辅助。现有代码与未来设计严格分开：第 2 节为事实与限制，后续为推荐决策。拟新增文件路径仅是实施蓝图，本次不创建。

优先级：P0＝正式 LIMS 核心开发前必须完成或可靠关闭危险入口；P1＝MVP 必须完成；P2＝第二阶段；P3＝后续优化。BLOCKER 是第 25 节的 **5 个聚合验收门槛**，不是把 26 条重复风险编号分别计数。某些旧功能可以先禁用，不必为开始 LIMS 而完整重写。

## 2. Confirmed Findings

复核状态定义：**Confirmed**＝静态代码足以确认缺陷；**Partially Confirmed**＝缺陷或危险机制存在，但原判断含需要配置/运行条件的结果；**Not Reproduced**＝经对应验证未复现，不可把“未运行”写成此项；**Need Runtime Verification**＝仅运行/部署检查能确认。此次没有攻击测试，不使用 Not Reproduced 掩盖未验证项。

以下是整改决策表。测试编号详见第 19 节；B1–B6 详见第 22 节。S 编号是摘要，T 编号是具体问题，二者重叠而非新的漏洞。

| ID | 问题 | 严重度 | 复核状态 | 是否 P0 | 推荐方案 | 涉及代码与确认逻辑 | 测试 | 实施批次 |
| -- | -- | -- | -- | -- | -- | -- | -- | -- |
| S01 | 授权管理越权 | Critical | Confirmed | 是 | 临时仅超级管理员；最终受控授权服务 | B/coreadmin/system/views/role.py::set_role_users；role_menu_button_permission.py::set_role_menu*，仅 IsAuthenticated 后按请求 ID 写入 | SEC-02/03 | B1→B2→B3 |
| S02 | 匿名文件入口 | Critical | Confirmed | 是 | 上传/枚举/批量删除先封闭，后统一文件授权 | views/file_list.py::FileViewSet 空 permission_classes；get_all 直接 get_queryset；继承 multiple_delete | SEC-01/08 | B1→B5 |
| S03 | 源码签名密钥 | Critical（沿用时） | Partially Confirmed | 是 | must rotate；独立 JWT 签名与启动校验 | B/application/settings.py:31 固定 SECRET_KEY；SIMPLE_JWT 无 SIGNING_KEY；实际部署沿用及有效依赖默认值需运行环境核对 | AUTH-01/02 | B1→B3 |
| S04 | 用户敏感字段可写 | High | Confirmed | 是 | 显式读写 serializer；高敏字段独立动作 | views/user.py::UserCreateSerializer/UserUpdateSerializer fields='__all__'；普通授权不应授予超级管理员写权 | SEC-04 | B1→B2 |
| S05 | 数据/字段权限旁路 | High | Confirmed | 是 | scope、object、field 统一执行 | utils/viewset.py::multiple_delete/get_serializer；views/user.py::list；system_config.py::get_table_data | SEC-05～10 | B1→B2 |
| T01 | Role/Menu/Button/Field/Data Range 授权越权 | Critical | Confirmed | 是 | 所有授权关系 CRUD 和自定义 action 一并受控 | role.py::set_role_users；role_menu_button_permission.py::set_role_menu/set_role_menu_field/set_role_menu_btn/set_role_menu_btn_data_range；最后一项直接取 grant ID | SEC-02/03 | B1～B3 |
| T02 | 文件匿名枚举/元数据批量删除 | Critical | Confirmed | 是 | 身份检查在业务执行前；禁止匿名全部文件操作 | file_list.py:97–115；viewset.py::multiple_delete；不能把部分匿名详情可能报错当作安全控制 | SEC-01 | B1/B5 |
| T03 | SECRET_KEY/JWT signing | Critical（条件） | Partially Confirmed | 是 | 独立环境秘密，不设源码回退 | settings.py 固定值覆盖 env 意图；conf/env.py 的 DJANGO_SECRET_KEY 未接到 SECRET_KEY；生产是否使用未确认 | AUTH-01 | B1/B3 |
| T04 | fields='__all__' 与敏感赋值 | High | Confirmed | 是 | 创建/更新/部分更新显式字段上限，拒绝越权键 | user.py::UserCreateSerializer、UserUpdateSerializer；viewset.get_serializer_class 对 partial_update 不使用 update_serializer_class，回退 UserSerializer | SEC-04/10 | B1/B2 |
| T05 | multiple_delete 不按 scope | High | Confirmed | 是 | 授权全集核对，任一不可操作则整体拒绝 | utils/viewset.py::multiple_delete 使用 get_queryset().filter(id__in=keys).delete() | SEC-08 | B1/B2/B3 |
| T06 | 字段权限没有后端执行 | High | Confirmed | 是 | Readable/Creatable/Updatable 后端强制 | viewset.get_serializer 裁剪代码被注释；utils/field_permission.py 只聚合 query/create/update 元数据 | SEC-10 | B2 |
| T07 | User list 分支越范围 | High | Confirmed | 是 | show_all/dept 只能追加业务过滤，不能换数据源 | user.py::list 的 show_all+dept 分支直接 Users.objects.filter，跳过 filter_queryset 和 queryset 的超级用户排除 | SEC-05 | B2 |
| T08 | 自定义部门范围串动作 | High | Confirmed | 是 | 每个有效授权元组内计算 scope，再 OR | filters.py::DataLevelPermissionsFilter 对 data_range=4 二次查角色但未限定当前 menu_button | SEC-06/07 | B2 |
| T09 | SystemConfig 动态模型全字段读取 | High | Partially Confirmed | 是，先关危险入口 | 受控 lookup registry，禁任意模型名和 .values() 全字段 | system_config.py::get_table_data 取配置 setting.table，再 model.objects.values()；客户端需可访问/控制对应配置，不能说任意匿名请求必然读任意表；分页返回了原 queryset | SEC-09 | B1/B2 |
| T10 | OperationLog 可改删/客户端 log_id | High | Confirmed | 是 | 只读日志 API；服务端独立 request 属性；另建 AuditTrail | operation_log.py/login_log.py 继承可写 CRUD；middleware.__handle_response 从 request_data.pop('log_id') 后 update_or_create；无 queryset 的视图可能保留客户端 ID | AUD-01/02 | B1/B4 |
| T11 | 日志敏感信息 | High | Confirmed | 是 | 字段允许清单与递归脱敏，认证请求不记正文 | middleware.py:44–71 只遮盖顶层 password，old/new password、嵌套配置等无统一控制；响应仅 code/msg，并非已确认完整 JWT 响应被记录 | AUD-02 | B1/B4 |
| T12 | Import 路径穿越 | High | Confirmed | 是 | 先禁路径导入，再 file_id→授权文件流 | import_export.py::import_to_data 使用 os.path.join(MEDIA_DIR,file_url)→load_workbook，无真实路径校验；能读取可解析 Excel 的路径风险，不等同任意文件内容必然外泄 | FILE-05 | B1/B5 |
| T13 | 文件同 key 覆盖/缺少不可变性 | High | Partially Confirmed | 是，正式文件入口 | aliyunoss.py::ali_oss_upload、tencentcos.py::tencent_cos_upload 使用前缀+原名 put_object；本地存储可能自动重命名，云桶版本/拒覆盖策略未确认 | FILE-02/03 | B1/B5 |
| T14 | 文件类型/大小未校验 | High | Confirmed | 是，启用上传前 | 策略化配额、流量和内容验证，服务器生成元数据 | file_list.py::FileSerializer.create 信任 file.content_type，无业务大小上限；基础框架内存阈值不等于业务拒收上限 | FILE-01 | B1/B5 |
| T15 | MessageCenter 存储型 XSS 路径 | High | Confirmed | 是，先安全展示 | 先纯文本渲染；恢复富文本须专用净化策略 | message_center.py 的内容写入无清洗；W/src/layout/navBars/breadcrumb/userNews.vue:13 v-html；未运行浏览器载荷 | SEC-11 | B1，富文本 P2 |
| T16 | db_constraint=False | High | Confirmed | 是，新基线；旧表分期 | 新表真实 FK；授权关键关系优先恢复，旧数据先清理 | system/models.py 中 Users/Dept/Menu/授权/消息关系；0001_initial.py 也声明关闭；现行数据库约束状态未连接确认 | DB-01/02 | B3 |
| T17 | atomic 只包 serializer 构造 | High | Confirmed | 是 | 服务事务覆盖验证、写入、M2M 和审计 | utils/viewset.py::get_serializer 的 with atomic 在 serializer.save 前退出 | TX-01 | B3 |
| T18 | 多表操作无整体事务 | High | Confirmed | 是，启用相关写入前 | 角色/配置/消息业务事务与 on_commit | role_menu.py::save_auth 先删后建；system_config.py::save_content 循环保存；MessageCenterCreateSerializer.save 先主对象再收件人 | TX-02/03 | B3/B4 |
| T19 | DEBUG/CORS/ALLOWED_HOSTS | High | Confirmed | 是，生产基线 | dev/test/prod 分离并拒绝不安全生产配置 | settings.py:35–36,165–167；conf/env.py DEBUG=True、hosts 通配；是否部署生效未确认 | CFG-01 | B1 |
| T20 | CoreModel 创建/归属字段受输入影响 | High | Confirmed | 是 | 服务端审计上下文，归属变更独立动作 | utils/serializers.py::create 仅在空值时补 dept_belong_id；update 仅覆盖 modifier；CoreModel.update 使用插入字段构造且外部字典能覆盖 | SEC-04/10 | B1～B3 |
| T21 | migration 被 gitignore | High | Confirmed | 是，迁移可重现基线 | 移除迁移忽略，保留旧链，新增迁移受版本管理 | B/.gitignore:91–92；当前有 0001_initial.py，但 Git 跟踪/生产迁移历史未确认 | ENG-01/DB-03 | B1/B3/B6 |

额外纳入的相邻缺陷：CustomPermission 不检查 role.status；DataLevelPermissionsFilter 检查状态，两者不一致；本人范围提前 return，不能正确实现多角色并集；PATCH/HEAD 方法枚举不一致；AdminPermission 读取 Role 不存在的 coreadmin 字段，不能作为临时管理员守卫；set_role_menu_btn_data_range 对非空部门使用 add 而非 set，旧范围可能残留。登录注销、MD5 分叉、菜单排序/部门统计空权限入口和工程工具链问题也直接影响本方案，纳入同一回归范围，不扩展成全框架重写。

需运行核验清单（均为 **Need Runtime Verification**）：部署实际 SECRET/JWT 算法和密钥来源；生产数据库孤儿/重复/真实约束；现行角色/白名单配置；OSS/COS ACL、版本保留与覆盖行为；代理转发头/上传限制；已应用迁移；刷新令牌实际回收行为；历史文件完整性。不得用这些待确认项否定已经确认的代码边界缺陷。

## 3. Security Boundary

先封入口，再替换抽象。B1 临时将角色成员、菜单、按钮、字段、数据范围授权及其直接 CRUD 限为有效超级管理员；禁止在普通 User API 写入角色、组、权限、部门归属、is_superuser/is_staff。使用明确 `is_authenticated and is_active and is_superuser` 守卫，不使用当前 AdminPermission。最终授权服务仍需防止给自己增加权限、修改受保护管理员及非法委派；CLI 初始化管理员是单独受控运维入口。

FileViewSet、DownloadCenterViewSet、菜单 move_up/move_down、部门 dept_info 均明确身份与动作策略。禁用尚未修复的路径导入、任意模型 lookup 和正式文件上传；不要仅隐藏 Vue 按钮或依赖请求失败。基础只读公共配置替换为代码维护的允许清单，仅品牌名、登录页展示等；不返回全 SystemConfig 再按 status 黑名单扣除。默认密码、存储凭据不属于公共初始化数据。

日志 API 只读；消息通知先使用文本插值，不允许数据库 HTML 直接进入 v-html。日志 ID/request ID 由服务端产生，用户同名参数无效。生产切换安全配置并轮换密钥。这些是可独立提交的最小修补，随后再统一授权服务。

HTTP 规则：无有效凭据 401（受 DRF 认证挑战机制约束的现有端点过渡可 403）；已登录无动作权 403；范围外对象统一 404；可见对象状态/并发冲突 409；禁止字段/参数 400；不存在的写接口 405；真正服务故障 500 和 request_id，不回传堆栈/数据库异常原文。保留现有 code/msg/data 外壳供 FastCrud 兼容，但不能把拒绝和异常都变成 HTTP 200。同步修改 B/coreadmin/utils/exception.py::CustomExceptionHandler 与 W/src/utils/service.ts 的错误处理。

## 4. Permission Architecture

### 4.1 分层职责

| 层级 | 决策 | 明确不能替代的能力 |
| -- | -- | -- |
| Authentication | 当前用户、会话、账号有效性 | 不代表有任意业务权限 |
| API Action Permission | 是否有 user.update / report.issue 等稳定动作权限 | 不代表能操作所有 ID |
| Data Scope Permission | 对此动作可见/可处理的对象集合 | 不代表满足状态、资格或字段限制 |
| Object Permission | 对目标对象当前状态/关系是否允许动作 | 不以“列表曾显示”作为凭证 |
| Field Permission | 可读/可创建/可更新字段的硬上限与动态授权 | 不能开放角色或模型敏感字段突破硬上限 |
| Business Qualification | 方法、设备、复核、批准、签发资格及职责分离 | 按钮存在或超级管理员身份不能代替资格 |

菜单只控制导航；按钮控制 UI 可发现性；API 动作代码才是服务端能力。Role 是授权载体，MenuButton 是现有 UI 映射载体。业务资格是额外且必须满足的条件。

拟在 B/coreadmin/access/ 下新增 registry.py、policy.py、scopes.py、fields.py（先作为 Python 包，不因分层而立刻建立一组新表）。CustomPermission 改为调用 `ActionPolicy.has_permission(context, action_code)`；DataLevelPermissionsFilter 变为 ScopeResolver 适配器；CustomModelViewSet 统一访问管线。禁止各视图自行以 `permission_classes=[IsAuthenticated]` 替换必要的动作策略。

### 4.2 稳定动作映射

| HTTP/DRF action | 动作代码示例 | 额外要求 |
| -- | -- | -- |
| GET list / retrieve | sample.view | scope 和 readable fields 一致 |
| POST create | sample.create | create scope 验证归属、相关对象 |
| PUT update / PATCH partial_update | sample.update | 同一写 serializer 上限、对象验证 |
| DELETE destroy | sample.delete_draft | 仅声明可物理删除的草稿允许 |
| POST receive / assign | sample.receive / test_task.assign | 明确动作输入 DTO |
| POST execute / invalidate / retest | test_run.execute / test_run.invalidate / test_run.retest | 状态机、理由、资格、历史保留 |
| POST submit / review / approve | result.submit / result.review / result.approve | 不同动作不能共用 update 权限 |
| POST reject / cancel | 对应资源.reject / cancel | 允许来源状态及原因 |
| POST issue | report.issue | 固定引用版本、批准资格 |
| HEAD | 对应只读动作 | 与 GET 同身份/范围，不返回数据体 |
| OPTIONS | 显式元数据策略 | 不泄漏不可写字段；跨域预检不获取业务权限 |

不再用请求 URL 正则+HTTP method 搜索数据库 MenuButton 作为最终权限依据。view.action 与服务端注册表确定 code；未注册 action 默认拒绝，并由系统检查/CI 阻止新增裸接口。路由重命名不改变权限；URL 参数不能改变 action。导入 GET 模板与 POST 导入、POST 导出等手工 as_view 映射也必须显式注册，不能仅扫描 Router。

### 4.3 与现有系统兼容迁移

1. 导出并人工核对现有 MenuButton.value/api/method、授权表、前端调用表的映射清单；此项是未来实施准备，不在本阶段导出文件。MenuButton.value 具有 unique，可以保留 UI alias；不能假设其现值已符合新规范。
2. 建立版本控制的 `legacy button ID/value → action code → view/action` 映射。MenuButton.api/method 过渡期用于管理页面展示和一致性检查，不参与无限正则匹配。未映射项冻结写授权；不自动给权限。
3. B2 先通过旧 RoleMenuButtonPermission 读取当前动作的有效授权，保持旧 URL 和请求体；所有写授权改走同一个服务。不能“新授权 OR 旧 URL 授权”双路放行。可做影子比较，但旧安全漏洞不能作为比较基准继续执行。
4. 后续以 RoleActionGrant（Role + stable permission code + scope 配置）承载授权，可在 B3 采用新增表和回填，或者先保留受控适配器；无论选哪种，B2 验收行为相同。授权事实只能有一个权威写源；新旧双写在同一事务并校验一致，读切换后旧表只作 UI 投影。
5. 不能把旧 list/retrieve、导入/创建等不同授权简单合并到一个 code 导致范围扩大：保留临时代码或按原操作保留限制；合并需明确批准的映射决策及测试。
6. W/src/views/system/role/components/api.ts、用户 CRUD、按钮 store/动态菜单保持调用兼容；后端提供 effective actions 和 field 元数据供展示，刷新不能覆盖服务端决策。迁移阶段同步移除提交的只读字段。

禁用 Role 后 API、scope、field、菜单、按钮都在后续请求立即失效。初期每请求查询数据库授权，不把角色权力嵌入长期 JWT，也不依赖进程内缓存 TTL；后续缓存必须有授权修订号和主动失效。关键授权修改和业务写入在事务内重查，按固定锁顺序序列化竞争。

## 5. Data Scope

现行数字语义保留适配：0 本人、1 本部门及下级、2 本部门、3 全部、4 指定部门。不要把范围数字大小当权限高低。现行“本人”额外要求本人部门；推荐新语义以 creator 为本人，仍受组织/客户隔离包络约束。迁移前确认旧数据和跨部门人员调动，不静默扩大权限；必要时旧适配继续 creator+dept，新策略显式切换。

**多角色采用有效授权元组的 union，最后与强制边界取交集。** 元组是 `(active role, action code, scope, allowed fields)`，不是把所有角色字段、部门、按钮分别合并。公式：`Allowed(action,obj,field) = SecurityEnvelope(obj) AND OR(each matching grant permits obj AND field) AND BusinessPolicy(obj)`。组织/客户隔离、记录状态和职责分离属于强制约束，不被“全部数据”覆盖。当前没有组织/客户模型，本阶段只定义 envelope/provider 接口，不伪造现有多租户支持。

范围应绑定 **RolePermission/RoleActionGrant**，不能只绑定 Role（不同动作范围不同），也不能绑定全局 Permission（不同角色范围不同）。MenuButton 在过渡期是 grant 的旧外键，最终不是数据权限语义中心。

拟 `ScopeResolver.resolve(actor, action_code, model, context) -> Q/QuerySet`；每个模型注册 ownership/dept 字段，缺少映射默认拒绝，不能沿用“无 dept_belong_id 则返回全部”。无部门用户：部门 scope 为空；本人 scope 可独立有效；全部 scope 也只在显式有效授权和安全包络内生效。Dept 后代遍历去重/检测环，指定部门只读取当前动作对应 grant.dept；范围修改使用 set 替换，范围类型切换清理不再适用的部门。

| 操作 | 统一策略 |
| -- | -- |
| list | 先安全包络和 scope，再搜索/排序/分页；show_all 只控制分页或 UI 业务过滤 |
| retrieve | 同一 read scope 按 ID 获取；不因知道 ID 而绕过 |
| PATCH/PUT/DELETE | action scope 与 view scope 交集，确保可改对象也能读；再对象策略 |
| custom action | 显式 code、scope provider、目标解析；禁止裸 Model.objects.get(pk) |
| bulk action | 校验完整 ID 集合均在 action∩view scope，禁止只处理授权子集 |
| create/import create | 无现存对象可筛选；验证请求归属、父对象和相关对象均可创建/关联 |
| export/lookup/template | 同模型 scope、readable fields 和安全查询字段；不可借导出拿完整 serializer |

列表分页或用户自选搜索导致某 ID 未出现在当前页，不等于不可读取；安全一致性比较的是同一基础 scope。UserViewSet 排除当前用户等 UI 条件应与安全过滤分离；超级用户对象的访问限制则必须在 list/retrieve/update 共用策略中定义。

未来扩展提供 `ScopeProvider`：ProjectMembershipScope、ProjectOwnerScope、AssignedOperatorScope、SampleCustodianScope、ReviewerScope、CustomerBoundary。只约定输入 actor/action/object context 和输出可组合查询，不建立业务表、不把项目成员硬塞 Dept，也不允许客户端直接提供“可信 customer_id”。

## 6. Object Permission

CustomPermission 实现 has_object_permission 或委派统一 ObjectPolicy；CustomModelViewSet.get_object 先从授权 queryset 取对象，再 check_object_permissions。只将不存在/不在范围转换 404，不吞掉所有异常。

拟统一调用：`get_authorized_object(action, pk, for_update=False)`；custom action 必须使用它。retrieve 做 view check；update/partial_update/destroy 做对应 action check；状态动作在服务中校验状态、相关资格与不可变约束。服务同样接收 ActorContext，避免 Celery、管理命令、导入绕过 API。

写入流程：字段结构验证→atomic→锁定目标和必要父对象→重新校验动作/范围/对象/相关 FK→校验当前修订→变更+审计→提交。锁按稳定顺序获取；不要只在事务外检查后无条件更新。安全授权变更与关键业务提交的竞争需要共同锁定授权主体或检查授权修订，定义清晰提交先后，不承诺中止已经完成提交的请求。

bulk：ID 类型/数量限制、去重；在事务中读取并锁定全部授权目标；实际集合必须等于请求集合（重复输入规范化后比较）；不存在和范围外统一 404，不泄露哪个 ID 不可见；某可见对象状态不允许则 409；整批回滚，审计无成功事件。相关 M2M/FK 输入也必须通过其专用可选范围验证，不能只验证 ID 存在。

## 7. Field Permission

三套策略分开：Readable Fields、Creatable Fields、Updatable Fields。每请求实例计算；禁止修改 Serializer 类全局字段，以免并发用户串权限。

| 层 | 责任 |
| -- | -- |
| Serializer | 显式声明输入/输出上限、类型和嵌套结构；拒绝未知或禁止输入键；只输出可读字段 |
| Permission | 根据有效 action grant、对象范围、字段策略计算动态允许集；不直接写数据库 |
| Service | 固定 creator/modifier/归属来源；再次检查敏感变更和业务状态；不用 initial_data 绕过 validated_data |

UserReadSerializer 只列必要展示字段；UserCreate/Update/PartialUpdate 明确映射（partial_update 不能回退宽泛 UserSerializer）。普通用户管理操作禁止写 is_superuser、is_staff、groups、user_permissions、role、creator、modifier、dept_belong_id、dept、pwd_change_count 和登录安全计数。密码只通过专用创建/设置流程输入且 write_only；任何响应不返回密码或哈希。后续是否允许有资格的管理员分配部门，通过 user.change_department 独立 action，不能默认 user.update 即可。

角色/部门/权限的高敏变更使用窄 DTO、独立 action 和委派校验；管理员也不能通过普通 User PATCH 提升权限。硬上限不能由 FieldPermission.is_update=True 解除。CoreModel 审计字段由 ActorContext 赋值，客户端提交即 400，而非静默忽略；正常 UI 应先移除只读键。更新不可修改 creator/create_datetime；modifier 统一使用用户 ID，不再混用 username；历史格式用明确 backfill，不猜测。

动态字段集 = serializer 硬上限 ∩ 当前对象匹配的 action grant 字段并集。角色 A 对部门 A 的敏感字段读权不能与角色 B 对部门 B 的对象范围拼成对 B 的敏感读权。批量列表可以逐对象裁剪，或使用不扩大权限的统一投影；分页总数不得以隐藏字段过滤造成旁路。

同步收敛 filter_fields='__all__'/ordering_fields='__all__'、DRF 搜索、RESTQL、嵌套 serializer 和导出字段。不可读字段不能被任意排序、条件探测或关联 lookup 暴露。无字段配置不自动允许 all；既有必要字段通过版本控制的显式基础策略回填。

## 8. Business Qualification Extension

拟定义 `BusinessPolicy.check(actor, action, object, context)` 与 `QualificationPolicy.check(actor, requirement, context)`，返回允许或稳定拒绝原因；未知策略/需要资格但未配置时拒绝。无资格要求的系统菜单动作可显式声明 NoQualificationRequired，不能作为全部业务动作默认值。

未来 result.approve 必须同时满足动作授权、对象范围、结果可批准状态、指定方法版本的批准资格、资格有效期、必要的职责分离。report.issue 还需报告批准资格和引用版本完整。superuser 可以管理系统，不能因此批准试验结果。

接口上下文预留 method_version_id、equipment_ids、effective_at、project_id、target_version、performed_by 等受服务端解析的值；相关模型出现后再实现 MethodQualification/EquipmentQualification provider。资质过期、暂停、覆盖方法版本不匹配、自己复核自己等要有拒绝测试。此阶段只建立接口及假对象契约测试，不建立 LIMS 模型和审批引擎。

## 9. Transaction Policy

事务边界放在 application service 的一个业务命令内，View 负责 HTTP 适配，Serializer 负责验证，不能在 get_serializer 内建立“已保护保存”的假象。简单单行保存可以使用数据库原子语句；涉及多个写入、状态、审计或并发条件必须显式 `with transaction.atomic():`。不以全站 ATOMIC_REQUESTS 代替清晰边界，也不把上传/Excel 大文件解析和网络调用长时间放在事务中。

| 命令 | 必须包含的原子范围 | 现有整改点 |
| -- | -- | -- |
| 用户创建/更新及角色、岗位关联 | 用户主记录+M2M+受控归属+审计 | user.py 的 save 与 initial_data.post.set 移入 UsersService |
| 角色授权 | 目标角色锁、菜单/按钮/字段/范围替换、授权修订+审计 | role.py、role_menu.py::save_auth、role_menu_button_permission.py 的全部 mutation |
| 配置批量保存 | 全部验证及变更+审计；任一失败全部回滚 | system_config.py::save_content，传递 ActorContext |
| 消息发布 | MessageCenter+去重后的收件人+审计 | MessageCenterCreateSerializer.save |
| bulk create/delete/import | 全集授权、所有写入+审计 | viewset.py；import_export_mixin.py |
| 未来提交/审核/批准/签发 | 锁对象/版本，状态转换、固定引用+审计 | 后续业务 service，不在普通 update 中实现 |

ImportSerializerMixin.import_data **已经有 @transaction.atomic**，不能说项目所有导入无事务。其问题是路径信任、字段/相关对象授权及大文件解析占用事务；整改为先验证受控文件并解析受限临时结构，再在事务中逐行授权并整体写入。显式导入更新的 ID 不存在/不在范围时必须拒绝，不能 first() 得到 None 后变成 create。超大导入以后设计分批作业，不悄悄改变“整批成功或失败”契约。

异常必须穿过 atomic 边界触发回滚，再转 HTTP；不能在事务内部 catch 后返回 ErrorResponse 使之前写入提交。IntegrityError 在 atomic 外转换业务错误。select_for_update 只能在事务中，锁定顺序统一；乐观锁 UPDATE 必须包含 expected_revision 并检查影响行数。

`transaction.on_commit()` 用于消息发送、Celery 入队、配置/权限缓存失效、文件后处理。当前 Dictionary/SystemConfig.save/delete 内直接 dispatch.refresh_*，应改为提交后失效；未提交时不能发布新配置。失败事务不发送消息、不启动任务、不删除文件。

on_commit 不提供“数据库与外部系统可靠同时成功”。一般通知可记录失败后重试；正式报告生成/文件处理等要求可靠执行时，事务内保存 outbox/job 记录，提交后唤醒 worker；worker 幂等，定期补偿遗漏任务。不要把回调失败等同数据库已回滚。当前 Celery 链路残缺，修复前可使用同步、可恢复的小流程；不可将关键审计交给异步任务。

## 10. Database Integrity

现有 PostgreSQL 配置可保留，不换数据库。B/coreadmin/system/models.py 的 db_constraint=False 不是“ORM 没有关系”，但数据库不能强制相应 FK 完整性。serializer validation 无法覆盖直接 ORM、导入、后台任务、并发竞争、SQL 和旧客户端，因此约束必须由数据库兜底。

| 关系类别 | 决策 | 删除/清理原则 |
| -- | -- | -- |
| Users.dept、Users.role/post 的中间表 | 恢复真实 FK；身份与授权属于安全边界 | Users→Dept 保留 PROTECT；Role/User 使用禁用优先，删除授权关联须有审计 |
| RoleMenuPermission、RoleMenuButtonPermission、FieldPermission 与 MenuField/MenuButton | 恢复 FK 与组合唯一 | 纯导航关联允许受控 CASCADE；API action grant 不能随菜单删除自动获得/丢失不明语义 |
| Dept.parent | 恢复 FK；部门树删除改 PROTECT/受控归档方向 | 检测环与孤儿；普通 FK/CheckConstraint 不能独自证明无环 |
| Menu.parent/MenuButton.menu/MenuField.menu | 恢复 FK，受控导航删除可 CASCADE | 预览引用影响，不能级联删除未来业务记录 |
| Dictionary.parent/SystemConfig.parent/Area.pcode | 恢复真实 FK 分期执行 | 被业务引用字典/标准不物理删除；配置不能装 Secret |
| MessageCenterTargetUser 与目标部门/角色 | 恢复 FK，去重收件人 | 生命周期清理按消息保留政策；审计另存 |
| CoreModel.creator | 同库用户推荐真实 nullable FK+SET_NULL 或用户禁用保留 | 必须同时保留历史 actor 快照；通用 legacy 表可暂缓回填 |
| modifier/dept_belong_id 文本 | 不是 FK，先核对 ID/username 混合数据再迁移 | 新业务对象使用真实关系和稳定 actor 身份，不复制文本关系 |
| 未来 TestRun→Task、Result→Run、Version→业务主体、RawDataFile→ManagedFile | 默认真实 FK，禁止 db_constraint=False | PROTECT/RESTRICT，防止破坏溯源链 |
| 外部存储 object key、外部历史 actor 标识 | 可使用普通字符串/快照，非同库 FK | 明确外部一致性校验；不能用假 FK 掩盖不受控来源 |

可暂时保留 db_constraint=False 的范围仅限尚未清理的 legacy 表，须有清单、只读/受控写入、补偿检查和退出批次；没有证据支持把当前同库核心关系永久豁免。跨库真实关系未来若存在，另立决策，本项目尚未确认此需求。

约束最小集：RoleMenuPermission(role,menu)、RoleMenuButtonPermission(role,menu_button)、FieldPermission(role,field)、MenuField(menu,field_name 对应实际字段名)、MessageCenterTargetUser(messagecenter,users) 的业务唯一性；核对实际模型字段后命名迁移。空 menu_button 的旧授权先隔离；不得把空值解释为全部权限。授权范围 CheckConstraint 限定枚举；跨 M2M “CUSTOM 必须有部门、其他类型不得有部门”由事务服务验证，必要时数据库触发器，不能声称普通 CHECK 可跨表。

SystemConfig 根节点 key 的 unique_together 对 NULL parent 不能当作完整唯一保证：PostgreSQL 使用 parent IS NULL 的条件唯一及非根组合唯一，先查重复再加。未来版本 `(aggregate_id,version)` 唯一、version>0、大小 size>=0、时间结束不早于开始等在字段成立后明确加入。不要把所有列都建索引：按授权/查询路径对 grant(role,action)、对象归属/时间、审计(object_type,object_id,timestamp)、版本(subject,version) 建组合索引；评估实际执行计划。

## 11. Delete / Archive Policy

| 策略 | 语义 | 适用对象 | 服务约束 |
| -- | -- | -- | -- |
| Hard Delete | 物理删除 | 未引用 Menu、无历史要求的 Dictionary 草稿、Draft Config | 专门权限、确认引用、事务、删除前审计；导航 CASCADE 仅限导航关系 |
| Soft Delete | 隐藏且可恢复 | 真有恢复需求的普通附件/管理记录 | 明确 deleted_at/deleted_by；唯一约束、默认查询和关联读取统一，不使用当前共享状态 SoftDeleteManager |
| Archive | 停止日常使用但历史可查 | 已用基础数据、已结项目、正式文件元数据 | 只改变生命周期，不删内容/引用 |
| Cancel | 取消未完成的计划 | 委托、未执行任务等未来对象 | 记录取消原因，不把已执行事实当未发生 |
| Invalidate | 标记已发生事实无效 | Specimen 不适用/报废、TestRun 无效、结果无效 | 历史与原始数据保留，禁 destroy/multiple_delete |
| Supersede | 新版本替代旧版本 | 方法/模板/结果/报告版本 | 链接新版本与旧版本，旧内容不变 |

Specimen 建立接收、测量、试验记录后不物理删除；TestRun 一经开始即保留，无效和重测通过动作记录；RawDataFile 正式确认后不覆盖、不普通删除；TestResult 与 ReportVersion 发布/批准后只追加更正或替代版本；AuditTrail 始终 append only。保留期限/依法处置流程需要未来实验室政策，本方案不虚构年限。

CustomModelViewSet 默认不应向未来所有模型自动暴露 destroy/multiple_delete；采用显式 deletion_policy/capabilities，未声明即拒绝。现有系统先逐资源列白名单并测试；不全局套当前 SoftDeleteModel。保留/作废策略由业务服务维护，不能让 is_deleted 字段任意 PATCH。

## 12. Audit Trail Foundation

**OperationLog 不是 AuditTrail。** 现有 OperationLog 可用于排障，修成只读不等于补足历史值、理由、对象版本与原子性。拟建立独立 B/coreadmin/audit/ app（未来实施时注册及迁移），最小 append_event 服务，先审计角色授权和配置变更。不要继承带普通 update/delete 行为的 CoreModel/ViewSet。

| 最小字段 | 契约 |
| -- | -- |
| event_id | 服务端 UUID，唯一；重试幂等键不得任意由客户端覆盖 |
| timestamp / created_at | 业务发生时间/事件入库时间，服务端 UTC aware；通常接近，分别定义 |
| actor_id / actor_username_snapshot | 稳定身份及当时名称；后台任务有明确 system actor，不能伪装用户 |
| action | 稳定业务动作 code |
| object_type / object_id / object_version | app_label.model_name + 规范化 ID + 可空版本；不只用类名 |
| reason | 更正、作废、授权高敏变更必填；普通无需原因的创建可空 |
| old_values / new_values | 允许审计的字段差异及必要引用，JSON 规范化；密码、token、私钥不记录 |
| request_id / ip | 服务端追踪 ID；IP 只信任已配置代理链，不直接信任任意 X-Forwarded-For |
| source | api / import / task / management 等受控枚举 |
| schema_version | 事件载荷契约版本，避免未来无法解读旧 JSON |

业务 AuditTrail：谁在何时因何对哪个对象版本做了什么，从什么改成什么。HTTP OperationLog：路由、耗时、状态、请求 ID 和有限脱敏摘要。运行日志：错误、任务、存储状态和 request_id，不存全业务对象。三类日志保留和读取权限分开。

业务数据变更与 audit.append_event 必须使用同一数据库连接和同一 atomic；审计写失败则业务回滚，业务回滚不留下“成功变更”事件。拒绝尝试可记独立安全日志，不能假装提交成功。对 M2M 保存明确的前后 ID 集合；对密码修改仅记“密码已变更”，不记前后哈希。大原始数据只记文件 ID/hash，不把曲线放审计 JSON。

append only 的执行层：公共 API 仅 list/retrieve，无 create/update/destroy/bulk mutation；审计事件由服务创建；Model/QuerySet 拒绝 update/delete 作应用防线；**数据库运行账号没有 audit UPDATE/DELETE/TRUNCATE 权限**，schema owner/migration 账号分离，必要时加数据库不可变触发器。仅覆写 Model.save 无法阻止 QuerySet.update/bulk_update/raw SQL。管理员不能通过普通 API 改历史；合法清理/保留例外是独立受控运维流程，不建“超级管理员随意删除审计”后门。

B/coreadmin/utils/middleware.py 将临时 log_id 放 request._operation_log_id，不能读写用户 request_data 中同名键；请求正文先归一化并递归脱敏、限长，认证/凭据配置不记录正文。移除顶层 password 单字段方案；PATCH 纳入 HTTP 日志，UPDATE 不是 HTTP method。现有历史日志不补造 old/new，不声称历史已可信；迁移导入旧日志需标注 legacy/unverified。

当前 USE_TZ=False，时间迁移必须先确认旧时间语义按 Asia/Shanghai 解释还是其他来源；测试转换，不直接重解释旧 timestamp。新审计统一 UTC，前端显示本地时间。

## 13. Versioning Foundation

本阶段定义契约和并发辅助接口，不建万能 VersionModel，也不建 Standard/TestResult/Report 表。version 使用**主体内单调递增正整数**，展示编号如报告修订码可另设，不用小数字符串代替排序。主键可为 UUID/自增，与 version 不是同一概念。

主体与版本分开：主体身份稳定，版本记录唯一 `(subject_id,version)`。主体可保存 current_version 指针，但更新必须锁主体且保证版本属于该主体；普通 FK 只能保证目标存在，不能自动保证归属正确。业务如“当前批准版本”与“最新草稿”不同，明确分开的指针/查询，不让一个 current 模糊代表两者。

草稿允许受控原位编辑，使用 revision 乐观锁且写审计；一旦提交/批准/生效，内容冻结。修改冻结内容是 create new version，说明 correction reason 和来源版本；已批准版本不得普通 update。current 指针只在规定状态转换时更新，不能创建任意草稿就替换当前正式版本。

status、effective_from、superseded_by 是可采用的字段，但正式版本 payload 不变。推荐版本内容不可变，生命周期事件追加记录；若使用 superseded_by/status 投影，只有专用服务可在事务内更新且写审计，不允许用户通用 PATCH，历史快照仍可重建。superseded_by 必须同主体、不能指自己/成环。

历史查询通过 subject/versions 和固定 version ID，报告只能引用固定 ResultVersion/MethodVersion/CalculationTemplateVersion，不查询“最新结果”重新渲染已签发报告。对象删除 PROTECT；current 指针、版本创建、审批事件和审计在一个事务中。

需要乐观锁：草稿 revision/If-Match 或 expected_revision；陈旧客户端更新返回 409。version 表示业务发布代次，revision 表示一次草稿并发控制，不混用。并发创建版本锁主体分配编号并由唯一约束兜底；批准/签发的幂等键防止双击或重试产生两个版本。基础验证可在后续测试专用模型/fixture 验证契约，不能借测试先创建正式 LIMS 表。

## 14. Managed File Foundation

现有 FileList 仅供普通附件兼容参考。拟新增 B/coreadmin/files/ app，ManagedFile + UploadSession（可先最小状态记录）及 StorageAdapter、ManagedFileService。首个实现可以是**私有本地存储**，无需先购买/部署 S3/MinIO；接口兼容未来 OSS/COS/S3。无论后端类型，不能依赖外网 URL 当文件身份。

| 字段 | 规则 |
| -- | -- |
| id | UUID；非授权凭证 |
| original_filename | 展示名，服务端净化，不参与路径 |
| storage_backend / object_key | 服务端选择后端，随机不可变 key；联合唯一 |
| storage_version_id | 后端支持时记录，用于固定读取对象版本 |
| size | 整数、服务器实际计数、非负 |
| mime / detected_type | 服务器检测与业务 profile；不能只信浏览器 |
| sha256 | 正式确认前服务器完整流计算，之后不可更新 |
| created_by / created_at | 受控用户身份、UTC 时间 |
| status | UPLOADING / QUARANTINED / AVAILABLE / ARCHIVED 等显式生命周期 |
| verified_at / profile / retention_hold | 验证时间、文件用途、安全保留要求 |

ManagedFile 不直接关联 TestRun；未来 RawDataFile 再通过真实 FK 关联 TestRun 和 ManagedFile。文件拥有者只表明上传者，不自动具有关联到任意对象或删除文件的权力。

| 操作 | 动作授权与对象条件 |
| -- | -- |
| 上传发起 | managed_file.upload + 用途/profile + 配额；创建上传 session |
| 上传内容 | 绑定 session 与 actor，限制 key/大小/过期；不接受任意服务端路径 |
| 确认 | managed_file.confirm + session 归属；服务器重新验证实际存储内容、hash、大小、扫描状态 |
| 元数据读取 | managed_file.view + 文件 scope；关联正式对象后依据父业务对象可见性 |
| 下载 | managed_file.download + 每次对象检查；归档/隔离/hold 按政策处理 |
| 删除 | 仅本人未确认临时上传或未引用且允许清理附件；正式文件无普通删除 |
| 归档 | managed_file.archive + 理由和审计；保留正式内容及引用 |

确认设计防 TOCTOU：直传只允许临时 key，不能把可再次 PUT 的 key 当正式原件。确认读取固定临时对象版本，验证后复制/写入新的最终 key，存储端禁止覆写；只有验证同一份内容才建立 AVAILABLE 元数据，记录实际 version_id/sha256。数据库提交前验证最终对象可读取且 digest 一致；失败产生的孤儿对象由独立清理清单/扫描回收。不要在数据库回滚时误删被其他事务引用的正式文件。

幂等确认：同一 session 重试返回同一 ManagedFile；竞争由锁+唯一约束保护。相同原名得到不同 key；重复内容可存两份元数据，跨客户不暴露“某 hash 已存在”；去重不是 MVP 必需功能。MD5 可保留旧系统比对/缓存提示，**SHA-256 是正式完整性指纹**；hash 本身不是签名，不能证明采集者身份，也不能阻止有存储权限的人同时改内容和元数据。

下载默认授权代理流式响应，Content-Disposition attachment、nosniff；必要时转后端短时 signed URL，签名服务先执行对象权限。已签 URL 在有效期内通常无法立即撤销；必须即时撤权的资料继续走授权代理，不能声称短链等于每次重新授权。前端不能永久保存公开下载 URL。

旧 FileList 只读兼容及映射到 ManagedFile，旧 id 保留映射关系；重算 hash 是迁移时完整性基线，不证明旧文件从未被改。缺失/重复/归属不明文件隔离，不猜 owner。旧 /media/ 和 CDN 公开入口必须同步撤掉或受控代理，单独加新下载 API 无法堵旧 URL。FastCrud 上传仍可兼容返回 id/url，但 url 应指授权下载入口；下载按钮通过 W/src/utils/service.ts 携带认证取得 blob，不能假设 img/a 标签会发送 JWT Header。预览另提供授权后短链或 blob，并及时回收。

## 15. Upload / Download Security

现有代码没有可据以确定实验室上限的文件大小参数，因此本方案**不虚构一个 MB 数值**。明确配置契约：每个启用 profile 必须提供 MAX_FILE_BYTES、MAX_BATCH_BYTES、USER_QUOTA_BYTES、并发/速率上限和解析限制；缺少上限时拒绝启用上传。实施者结合实际试验机导出样本和存储容量确定并提交配置决策，测试用配置值 L 的 L-1/L/L+1 验证。这是可执行边界，不是“以后再考虑限制”。

初始允许清单建议：csv、xlsx、pdf、png、jpg/jpeg、tif/tiff，按用途启用；txt 仅明确仪器文本 profile。初期不启用 html/svg/js/exe、可执行脚本、xlsm 和任意压缩包；旧 xls/专有仪器二进制需要专用解析器/profile 后才开放。扩展名仅一个信号，校验 MIME+Magic Bytes+实际解析；CSV 没有唯一 magic，需编码、分隔符、列/行/单元长度和文本解析验证。xlsx 是 ZIP 容器，限定展开总大小、条目数和压缩比，拒绝宏/外部链接等不允许内容；对图片限制像素与解压体积，对 PDF 禁止主动内容预览并使用下载模式。

文件名去路径分隔符、NUL/控制字符、驱动器/UNC 特征并限制长度；显示名不用于 object_key。key 为服务端随机值，不接受客户端指定目录、engine、file_url、sha256、creator。代理、Django 流式接收、存储和解析层一致执行大小限制，即使无 Content-Length 也累计字节；上传内存阈值不是拒收限额。超限立即停止并清理临时流，响应 413；类型不符 400/415，未验证不对外可用。

病毒扫描预留 Scanner.scan(file_version) 接口，QUARANTINED 文件不得被正式引用；扫描超时/失败不标成 clean。没有扫描器时只能按明确禁用/人工验证策略运行，不能返回虚假的扫描通过。是否启用扫描服务和完整原始设备格式库是 BEFORE MVP/DURING MVP 的用途决策；不可变存储和验证基线是 BLOCKER。

import_to_data 改接收已授权打开的文件流（底层不认识 HTTP 用户提交路径）；ImportSerializerMixin.import_data 接收 file_id，调用 ManagedFileService.open_for_import(actor,file_id,profile)。同时验证文件 AVAILABLE、用途 Excel 导入、用户和目标模型 import 权限；模板的关联选项也过滤 scope。旧 url 参数直接 400 并指导前端升级，不保留任意路径回退。若短期必须兼容旧附件 ID，仍通过受控映射，canonical path 必须落私有根目录且拒绝符号链接逃逸、绝对路径和 UNC，不直接 join 用户输入。

导出应用相同 scope/field，不输出密码或配置凭据；CSV/Excel 中用户文本按安全文本写出，避免公式注入；未来批量导出使用受控文件，不让 DownloadCenter 生成公共路径。

## 16. Authentication

证据：B/application/settings.py 的 JWT+Session 双认证、24 小时 access/1 天 refresh、rotate=True；B/coreadmin/system/views/login.py::LogoutView 仅返回成功；TokenRefreshView 直接路由；ApiLogin 是另一条 session 登录路径；Users.set_password、CustomBackend、user.py 的改密/导入使用不同 MD5/原文分支。当前 validate_complex_password 没有实际校验，不代表配置了 Django validators 就已执行。

推荐继续使用现有 SimpleJWT 能力，补服务端会话撤销与统一密码服务，不自制签名算法。

| 项目 | 推荐行为 |
| -- | -- |
| Access token | 短于 refresh；时长由明确配置和实验室终端风险决策确定，不直接沿用当前 24 小时，也不在此指定缺乏依据的数字 |
| Refresh token | 轮换、服务端 session/family 状态、单次使用；并发锁避免两次有效轮换，重放撤销对应会话族 |
| Logout | 撤销当前会话，清理前端 token/cookie；后续 access 和 refresh 都失效，不仅返回消息 |
| 改密/重置/禁用用户 | 增加 user auth_version 或等效凭据修订并撤销会话；每次 JWT 认证与 refresh 均校验，不仅校验 JWT 签名 |
| Reset password | 独立授权流程，短期一次性凭证；不回传/恢复旧密码，不批量使用共享默认密码 |
| 首次登录 | 服务端 must_change_password 状态；仅允许改密/注销等窄动作，前端弹框不能代替限制 |
| 角色变化 | token 中不冻结授权，后续请求读最新有效角色；不要求用户主动登出才能生效 |
| SessionAuthentication | 业务 API 逐步统一 JWT；会话仅明确需要的开发文档/受控后台启用，保留 CSRF；生产禁用 ApiLogin 或接入同一登录策略 |

SimpleJWT blacklist 只能解决其覆盖的 refresh/sliding token 问题，不能自动撤销所有 access。如果采用其 blacklist app，需要后续正式注册/迁移；与 session/auth_version 策略统一，避免两个状态源互相矛盾。B3 在隔离环境验证使用的确切依赖行为。

密码最终采用 TLS 上传原文、服务器 validate_password + Django hasher，一处编码入口；移除长期“原文/MD5/双 MD5 都试一遍”。旧存量凭据的外层哈希通常不能识别究竟哈希了哪种输入；不能猜测批量转码。采用明确 legacy 状态的短期兼容，成功验证后要求受控改密，无法确认的账号重置；兼容有截止条件与测试。联动 W/src/views/system/login/component/account.vue、changePwd.vue、用户导入和创建页面，不能只改后端让用户全锁死。密码任何时候不写响应/日志；UserCreateSerializer.password 必须 write_only。

Access 优先内存持有；refresh 推荐服务器设置 HttpOnly/Secure/适当 SameSite 的窄路径 cookie，刷新和注销接口执行 Origin/CSRF 防护。当前 storage.ts 用 JS cookie 保存 token，不能通过前端设置 HttpOnly；迁移须后端 Set-Cookie 与前端请求一并实现。若跨站部署需要不同 SameSite，必须基于实际拓扑决策，不一律 None。认证入口共享频控和错误策略；登录日志失败不能增加密码错误次数。限制锁定型 DoS、避免泄漏账号存在性，保留安全恢复方式。

## 17. Production Configuration

拟保留 B/application/settings.py 为兼容导入入口，把基础配置移入 settings_base.py，明确 settings_development.py、settings_test.py、settings_production.py。实际命名可小幅调整，但不把生产秘密放 conf/env.py 再从 settings 循环导入 BASE_DIR。环境配置通过部署变量/秘密挂载注入，env.example 仅名称与非秘密示例。

| 配置 | 开发/测试 | 生产 |
| -- | -- | -- |
| SECRET_KEY / JWT signing | 每环境不同的非生产测试值 | 必填、不同用途不同密钥、must rotate、无源码兜底；旧泄露 key 不作为兼容 fallback |
| DEBUG | 开发可 True，测试显式 | 固定 False，不允许缺省 True |
| ALLOWED_HOSTS | 精确本机/测试域 | 非空明确域名，拒绝 * |
| CORS | 本地前端白名单 | 精确 origin；仅确需 cookie 时 credentials=True，不能全来源 |
| CSRF/SESSION cookies | 隔离的开发行为 | HTTPS、Secure/HttpOnly/SameSite，受信 origin 列表；代理头只信指定代理 |
| PostgreSQL | 独立 test DB、不可误连生产 | 非 postgres 超级用户作为应用账号；migration owner 分开，TLS/备份按部署明确 |
| Redis | 不需要则关闭，测试内存替身 | 仅内网、身份/加密按拓扑；凭据独立，不在返回/日志中 |
| OSS/COS credentials | 不连接真实 bucket 的测试替身 | 最小权限、私有桶/前缀隔离、外部秘密；不经 SystemConfig CRUD 管理 |
| 日志/公共配置 | 控制台脱敏 | 限长脱敏、request_id；公共初始化仅允许清单 |

启动/部署检查：生产缺密钥、通配域名、未设文件上限、DEBUG=True 或不安全 CORS 组合必须报配置错误。检查器只报告配置名称/错误，不打印值；测试也不快照真实 Secret。上线密钥轮换强制旧会话失效，并沟通重新登录；不能回滚为旧泄露密钥。实际部署 Secret 使用情况目前未确认，但源码内值均需清理并轮换，不能把“conf 被忽略”当已安全。

## 18. Migration Strategy

B/.gitignore 排除迁移是已确认问题；当前存在 0001_initial.py 不代表后续能重建数据库。未来所有 migration 必须进入版本控制，禁止随意删除/重编已发布迁移，禁止生产 reset migration/清空 django_migrations，也不以 --fake 掩盖状态不一致。

推荐顺序：**盘点实际 schema/迁移历史与备份 → 验证数据 → 扩展兼容 schema → 数据回填/清理 migration → 再验证 → 收紧约束 schema migration → 应用读写切换 → 观察后移除旧入口**。新字段先 nullable 或兼容默认，再 backfill，再 NOT NULL；恢复已有 FK 可先清理后加约束。schema 和 data migration 分开、可分批恢复，数据库大表锁风险单独评估。

清理必须保留证据：孤儿授权禁用/隔离，不自动给其补万能角色；重复 grant 不直接取范围最大值，需核对来源并选择不扩大权限的归并；creator/modifier 文本无法映射时保留原值与未确认标记。唯一约束先检测重复，生产大表可以用 PostgreSQL 分阶段验证约束方案，但 Django migration state 必须与真实 schema 对齐，禁止只手工改 DB。

验证空库从零 migrate、现有脱敏快照升级、回填重复执行/中断恢复、约束违反、回滚前后应用兼容。migration rollback 不删除已经产生的正式审计/文件/版本数据；优先回退应用到兼容版本或前向修复。不可逆数据回填明确标注并有备份恢复演练。新旧写切换期间仅一个权威源。

未发现 Git 元数据，未来实施前先确认真实版本库位置/分支和干净基线；本文不擅自 git init。不能把当前文件目录和生产已部署版本直接视为一致。

## 19. Backend Test Matrix

优先使用已存在 Django/DRF 的 TestCase、TransactionTestCase、APIClient；无需先引入 pytest。当前 system/tests.py 是带 django.setup 的手工查询脚本，不是有效基础回归套件。拟新增 B/coreadmin/foundation_tests/（明确测试发现标签，避免与 system/tests.py 同名冲突），测试设置不引用生产 env、不触发 URL 导入时数据库初始化。未来 tests 的代码文件只是规划，本阶段不创建。

固定 fixture：部门 A、A1、B；normal、dept_a、dept_b、multi_role、disabled_role_user、superadmin；A/A1/B 与无部门对象；各角色分离的 view/update/delete/custom scope；字段敏感/普通各一；已有超级管理员不使用 ID=1 判断。每次请求断言 HTTP、响应字段、数据库前后值/行数、审计事件和外部副作用计数。范围测试同时覆盖普通 ID、有效 UUID 风格路由和不存在 ID，不依赖安全性来自难猜 ID。

| 测试 ID / 拟文件 | 场景与操作 | 必须断言 |
| -- | -- | -- |
| SEC-01 test_anonymous.py | 匿名 POST/GET/DELETE `/api/system/file/`、`file/get_all/`、`file/multiple_delete/`；角色更新；download_center/菜单排序/部门统计 | 有路由的受保护操作 401/403，禁用功能可 405；无文件/授权/数据库变化，无存储调用；匿名普通 file list 不能以 500“代替拒绝” |
| SEC-02 test_grant_management.py | normal 调用 role/{id}/set_role_users，set_role_menu、set_role_menu_btn、set_role_menu_field、set_role_menu_btn_data_range；直接 grant CRUD/save_auth | 全部 403；不能给自己/同伙加 admin role；原角色/M2M/范围未变 |
| SEC-03 同上 | 普通 user.update 权限、自身角色管理请求、无委派资格管理员、越范围目标、受保护管理员 | 不能突破 delegate 上限；B1 仅 superadmin 可管理；最终 service 校验目标且拒绝自提权 |
| SEC-04 test_user_fields.py | POST/PUT/PATCH 提交 is_superuser=true、is_staff、groups、user_permissions、role、creator、modifier、dept_belong_id；单键参数化、混合正常字段 | 400 且所有字段保持原状；PATCH 不回退宽 serializer；响应不含 password/hash；不能通过嵌套/导入绕过 |
| SEC-05 test_scope.py | User list 加 show_all/dept=A、B、缺省、分页开关；retrieve 同对象 | 所有列表分支不超 view scope，不出现被策略隐藏的超级用户；知道 B 的 ID 仍 404 |
| SEC-06 同上 | 指定部门 A 的 user.update，另一个 action 指定 B；变更 CUSTOM 部门 A→B→空→DEPT | update 不串入其他 action 的 B；替换后无旧 A 残留；空 CUSTOM 无范围；切类型清旧部门 |
| SEC-07 同上 | 本人+本部门+子部门+指定部门+全部，多角色不同排列；禁用其中角色 | union 与排列无关；无 early return；ALL 不越 envelope；禁用角色下一请求在 action/scope/field 全层失效 |
| SEC-08 test_bulk_scope.py | list/retrieve/update/PATCH/delete/custom/bulk 各访问 A/A1/B；bulk 一条授权+一条未授权/不存在/不可删除 | scope 一致；整批 404 或可见状态冲突 409；没有部分删除/审计成功；重复 ID 不重复操作 |
| SEC-09 test_lookup.py | get_table_data 配置指向 Users/敏感模型、未注册 lookup、嵌套搜索字段、跨部门；公共 init/settings | 未注册 403/400，无密码/secret/默认密码；允许 lookup 仅批准字段和实际 page，scope 不旁路 |
| SEC-10 test_fields.py | 无 read/create/update 权限、合法字段、未知字段、nested/RESTQL/export/filter/order；角色 A 有 A 敏感读，角色 B 有 B 普通读 | 三种字段能力独立；隐藏字段不输出/不可查询探测；禁写 400；B 敏感字段不因角色拼接可读 |
| SEC-11 frontend contract + test_messages.py | 保存含事件属性、危险链接的消息并让接收用户查看；同时 GET retrieve 未授权消息 | 纯文本策略下不执行 HTML；消息查看先授权，无未授权 read 标记副作用；富文本恢复前有净化测试 |
| SEC-12 test_action_registry.py | 所有 Router、自定义 as_view、HEAD/PATCH/OPTIONS；新未注册 action；ApiWhiteList 条目试图扩大权限 | 默认拒绝，无 method.index 500；白名单不能关闭生产安全层；metadata 不泄漏不可写字段 |
| AUTH-01 test_config.py | production 缺 signing key/secret、开发默认值、DEBUG/hosts/CORS 不合规 | 启动检查失败，不在输出中出现 Secret；轮换后旧 key token 无效 |
| AUTH-02 test_sessions.py | 登录、刷新轮换、旧 refresh 重放、注销后 access/refresh、改密/重置/禁用后旧 token | 新 token 正常；旧/已撤销 token 401；双刷新无两个有效继任；认证两入口一致 |
| AUTH-03 test_passwords.py | 首次登录访问普通 API、原文密码校验、legacy 凭据升级、改密失败、ApiLogin 旁路、日志写失败 | 强制改密不可绕过；密码错误/政策不符无变更；日志失败不计密码错误；不存在共享默认密码 |
| AUD-01 test_audit.py | 授权/配置更新成功；审计写失败；HTTP audit update/delete/bulk；ORM QuerySet.update/delete | 成功同事务有正确 old/new/reason/actor；审计失败业务回滚；公共写接口 405；应用层和运行 DB 账号拒绝修改历史 |
| AUD-02 test_logging.py | 请求携带他人的 log_id；嵌套 oldPassword/newPassword、token/credential/config secret；PATCH 请求 | 旧日志不被覆写；日志不出现原文或哈希/凭据；request_id 服务端生成；PATCH 有元数据日志 |
| TX-01 test_transactions.py | 批量创建第二项失败；M2M 保存失败；异常处理转 HTTP | 之前写入全部回滚，不能 get_serializer 的 atomic 假通过 |
| TX-02 同上 | save_auth 删除后新增失败；save_content 第 N 项失败；消息收件人生成失败 | 删除/新增/主记录全部回滚，原始集合完全保留 |
| TX-03 同上 | 提交/回滚分别触发 on_commit；任务发送失败重试 | 回滚零副作用；提交后才触发；回调失败不声称 DB 回滚；重试不重复业务变化 |
| DB-01 test_constraints.py | 无效 FK、重复 grant、重复收件人、非法 scope、根配置 key 重复 | 直接 ORM/DB 写入失败，不能仅测试 serializer；并发唯一性数据库兜底 |
| DB-02 test_concurrency.py | 两连接并发授权替换/创建版本、陈旧 revision；授权撤销与写入竞争 | TransactionTestCase+PostgreSQL；原子结果无混合集合，陈旧请求 409，顺序有定义 |
| DB-03 test_migrations.py | 空库和脱敏旧库升级，孤儿/重复回填，中断恢复 | 迁移链完整；异常数据报告清楚；未自动扩大角色权限；目标 schema 与 state 一致 |
| FILE-01 test_uploads.py | 超大小、无 Content-Length、错误扩展名/MIME/magic、路径名、ZIP 展开超限、扫描失败 | 流式边界生效，413/400/415；无 AVAILABLE 正式文件；临时数据可回收 |
| FILE-02 test_file_integrity.py | 相同原名不同内容、客户端自报 sha256/engine/key、重复内容跨用户 | 不同 key、服务器 digest/size；禁止自报元数据；不泄漏他人重复文件 |
| FILE-03 同上 | 确认后覆盖请求、临时 key 确认竞态、双确认、对象被篡改 | 正式内容/key/hash 不变；验证固定对象版本；双确认一个结果；digest 异常不可正式引用 |
| FILE-04 test_downloads.py | 非 owner/父对象范围外下载、过期 signed URL、直接旧 media URL、ARCHIVED/QUARANTINED | 按策略 404/403；隔离禁止下载；旧公开 URL 不泄漏；保留有效授权下载 |
| FILE-05 test_imports.py | 旧 url、../、绝对盘符、UNC、他人 file_id、非 Excel、越范围更新 ID、第二行失败 | url 400 且不打开文件系统路径；file_id 检查所有权/用途；更新不退化为创建；整批回滚 |
| CFG-01 test_config.py | dev/test/prod 配置、公共配置 allowlist、受信代理 IP | test 不连生产；prod 不安全组合拒启；IP 来源规则可验证 |
| ENG-01 工程检查 | 干净 checkout、locked install、migrate、测试、typecheck/lint/build | 无手工 DB 修补，无 missing migration，非零退出阻止合并 |

拒绝场景也要断言数据库未变，不能只测状态码。普通 happy path 必须存在，防止“全部请求都拒绝”伪装安全修复。已有管理员授权管理、合法部门编辑、合法附件上传下载应在对应批次仍可用。

数据库并发/约束测试使用隔离 PostgreSQL，不能用 SQLite 结果替代。Django TestCase 默认不实际提交，on_commit 用 captureOnCommitCallbacks 或 TransactionTestCase；事务锁与 DB 账号权限测试使用两个实际连接及受限应用账号。浏览器 XSS 测试属于前端验证，不能把后端字符串断言当作浏览器验证通过。

## 20. LIMS Foundation Test Matrix

以下为未来业务设计约束，当前没有这些模型，**不是当前测试已通过或当前功能已存在**。先固化接口契约，在相应业务模块实施时建立真实测试。

| ID | 未来行为 | 可验证结果 |
| -- | -- | -- |
| LIMS-01 | TestRun 标记 INVALID 后 DELETE/bulk_delete | 拒绝；原 Run、原数据、作废原因及操作者完整保留 |
| LIMS-02 | TestTask 发起 RETEST | 新 Run ID 且关联同 Task/前序 Run；前次 Run 不更新成新试验 |
| LIMS-03 | Result 已 APPROVED，普通 PUT/PATCH | 409/禁止接口；原版本内容未变 |
| LIMS-04 | Result correction | 理由必填，生成 V2，V1 可查；缺审计则整事务失败 |
| LIMS-05 | Report ISSUED | 固定引用 ResultVersion/方法/模板版本与文件 hash；之后结果更新不改变原报告 |
| LIMS-06 | RawData 重传同文件名或改 file key | 原始数据不覆盖；新文件独立身份，需要受控关联/作废流程 |
| LIMS-07 | 持 result.approve 但无有效资格 | 403；过期/暂停/错误方法版本资格均拒绝 |
| LIMS-08 | 自己试验自己复核/批准（政策禁止时） | BusinessPolicy 拒绝，不因 ALL scope 或 superuser 绕过 |
| LIMS-09 | 设备/传感器校准过期或范围不适用 | execute/使用确认拒绝或按明确例外审批，不能静默通过；保留实际使用快照 |
| LIMS-10 | 两人同时更正/批准同 revision | 仅合法一次转换；另一方 409，版本唯一，无双签发 |
| LIMS-11 | 指向别的客户/项目/Panel 的试样关联 | scope+对象关系验证拒绝；FK 不能代替客户隔离 |
| LIMS-12 | 删除 MethodVersion/Equipment/ManagedFile 被正式记录引用 | 数据库或服务 PROTECT/RESTRICT；历史可重现 |
| LIMS-13 | 原始→计算→报告数据链 | 分层引用固定来源，重新计算生成新结果；不更新原始采集文件 |
| LIMS-14 | 计算模板或标准新版本生效 | 新任务显式选择；旧试验继续引用固定旧版本，可复算和审查 |
| LIMS-15 | 审计写入失败/文件未确认 | 结果提交/签发整体不成功，不留下半批准状态 |

## 21. CI Baseline

B1 就引入隔离测试入口与安全回归，不等到最后才测试；B6 完成合并门槛。最小工具组合：Django test+DRF APIClient、既有 ESLint/TypeScript/Vite、一个已选包管理器及锁文件。pytest、mypy、pre-commit、完整浏览器 E2E 平台不是全部必装。

当前 W/package.json 仅有 lint-fix，无纯 lint/typecheck；build 不等于 TypeScript 类型检查；ESLint 9 与 .eslintrc.js 的旧配置及 ESM module.exports 需要调整。拟增加不写文件的 lint、typecheck；如需覆盖 Vue SFC，补一个与现有 Vue/TS 兼容的 vue-tsc 开发依赖即可，不把 tsc --noEmit 宣称为完整 Vue 检查。选择一个兼容、锁定的 Node/包管理器版本；不要沿用 Node>=16 与 Vite 需求不匹配的声明。package-lock.json/yarn.lock 同时存在，选定一个权威源，移除另一个属于后续获准工程变更。

| CI job | 最小执行内容 | 通过条件 |
| -- | -- | -- |
| Backend | 使用测试 settings 启动临时 PostgreSQL，migrate，manage.py test coreadmin.foundation_tests，注册动作覆盖检查 | 权限/事务/约束/API 正反例全通过，无生产网络和真实 Secret |
| Migration | makemigrations --check --dry-run，空库 migrate；有 schema 变更时脱敏旧快照升级 | 无漏迁移，版本控制包含迁移，模型/数据库状态一致 |
| Frontend | 确定的 locked install，npm run typecheck，npm run lint，npm run build（若选 npm） | 非修复模式，无新增错误，构建成功 |
| Config/Security | 生产配置拒启用例、公共端点 allowlist、禁止输入/响应/日志敏感字段回归 | 不安全配置和裸入口不能合并 |

未来示例后端命令使用 `--settings=application.settings_test`，明确临时数据库环境。上述命令本阶段未执行。当前 application/urls.py 导入时执行 dispatch.init_*，settings 会创建日志目录，现有 tests.py 手工 setup；B1 应移除启动时必须查询业务表的测试障碍，应用初始化改为安全的惰性读取/明确初始化流程。测试不能静默依赖开发数据库已存在。

W/vite.config.ts 加载会写 public/version-build；未来 CI 应在临时 checkout 构建并使生成物进入构建产物而非修改跟踪源码。本阶段不运行构建，避免违反唯一新增文件约束。已有工程错误需建立可复现清单并修复执行链；不允许将失败命令改成 always-success 通过验收。

## 22. Refactoring Batches

每批独立评审、测试和可回退。下列新增路径为拟议，不是当前文件。风险高入口可在后端禁用到对应批次通过；回滚永远不能恢复已确认的权限绕过、旧泄露密钥或公开原始文件。每批开始先确认真实 Git/部署基线，结束保留测试报告与部署差异。

### B1 — 测试入口与安全封堵

**涉及文件**：B/application/settings.py、conf/env.py、application/urls.py；B/.gitignore；utils/permission.py、exception.py、middleware.py；system/views/role.py、role_menu.py、role_menu_button_permission.py、user.py、file_list.py、download_center.py、menu.py、dept.py、system_config.py、operation_log.py、login_log.py；W/src/layout/navBars/breadcrumb/userNews.vue、W/src/utils/service.ts。拟新增测试 settings、foundation_tests/test_anonymous.py、test_grant_management.py、test_user_fields.py、test_config.py。拆小提交但一批内形成安全闭环。

**类/函数**：全部 set_role_* / save_auth 和 grant CRUD 临时管理员守卫；UserCreate/Update/PATCH 字段上限；FileViewSet/DownloadCenterViewSet 权限；InitSettingsViewSet.get 允许清单；get_table_data 和路径 import 先禁；OperationLog/LoginLog ViewSet 只读；ApiLoggingMiddleware 不信 request.log_id；CustomExceptionHandler 保留 HTTP；菜单排序和 dept_info 加守卫。settings 拆分、清理硬编码并轮换部署密钥属于明确运维步骤，不把 Secret 写进 commit。

**预期**：匿名/普通用户无法修改授权、敏感用户字段及文件元数据；危险功能关闭；消息文本安全展示；生产不安全配置拒启；迁移不再被忽略；基础测试不连接现有 DB。

**测试**：SEC-01～04、09、11、AUD-02、AUTH-01、CFG-01 的封堵子集；合法管理员/普通信息更新正例；明确禁用接口返回 405/403。

**风险**：前端全量表单提交只读字段变 400，消息富文本变纯文本，原 token 失效，导入/lookup 暂不可用。同步清理 payload 和提示，不恢复漏洞兼容。

**回滚**：保留安全守卫和新密钥；必要时关闭相关路由、回退 UI 到可用只读版本。配置回退只回到另一个安全值；无数据库大改。迁移忽略规则不能回退为重新忽略。

### B2 — 统一 Action / Scope / Object / Field

**涉及文件**：B/coreadmin/utils/permission.py、filters.py、field_permission.py、viewset.py、serializers.py；system/views/user.py、role.py、role_menu_button_permission.py、menu_button.py、system_config.py、message_center.py；system/urls.py；拟 coreadmin/access/{registry,policy,scopes,fields}.py；W/src/views/system/role/components/api.ts、user/crud.tsx、W/src/settings.ts、权限按钮与动态路由的调用处（实施时以引用搜索列出所有消费者）。

**类/函数**：CustomPermission.has_permission/has_object_permission；DataLevelPermissionsFilter.filter_queryset；CustomModelViewSet.get_object/get_serializer_class/get_serializer/filter_queryset/multiple_delete；FieldPermissionMixin.field_permission；UserViewSet.list；Users serializers；所有自定义动作 target resolver；SystemConfig lookup registry。后端访问管线不再由 set 乱序组合过滤器；FieldPermission 逐请求实例执行；disabled role 下一请求失效。

**预期**：稳定 code 映射旧 MenuButton；PATCH 与 PUT 同安全上限；所有 scope 一致；bulk 全集核验；作用域内 grant 字段合并；安全 lookup 可按注册清单逐个恢复。未适配动作保持关闭。

**测试**：SEC-02～12 全集，含多角色排列、禁用、无部门、跨动作 CUSTOM、隐蔽字段查询、M2M、导出和特定 show_all 分支；前端角色授权保存与合法字段编辑联调。

**风险**：历史授权隐含过宽、重复值/空按钮、前端过度提交、不同按钮合并可能扩大权限。映射必须显式复核，缺少映射拒绝，兼容适配按旧安全子集工作。

**回滚**：按资源切回 B1 的严格守卫/只读，不回到 URL 正则泛匹配+IsAuthenticated；新注册表和旧别名映射可保持，未做破坏性表替换。

### B3 — 事务、约束与认证生命周期

**涉及文件**：B/coreadmin/system/models.py、utils/models.py、utils/serializers.py、utils/viewset.py、utils/import_export_mixin.py；views/role.py、role_menu.py、role_menu_button_permission.py、system_config.py、message_center.py、user.py、login.py；utils/backends.py；application/dispatch.py、settings/urls；拟 system/services/{users,grants,config,messages}.py、coreadmin/access/authentication.py 及会话服务/必要模型；W 登录组件和 storage.ts/service.ts。新增经过评审的 schema/data migrations，本阶段仅规划。

**类/函数**：角色全部 mutation、save_content、MessageCenterCreateSerializer.save 移入服务 atomic；CoreModel.update 审计字段；Dictionary/SystemConfig.save/delete 缓存回调；Users.set_password、CustomBackend.authenticate、UserViewSet 改密/重置、LogoutView.post、Refresh serializer。关键授权 FK/组合唯一先恢复；可选 RoleActionGrant 回填采用单写源策略。

**预期**：跨表失败整体回滚；会话注销/改密可撤销；移除长期 MD5 分叉；禁用权限立即一致；新基础模型真实 FK。所有旧表 FK 不必一次迁完，但身份/授权关键约束与迁移可重现必须通过。

**测试**：TX-01～03、DB-01～03、AUTH-02/03、SEC-02～10 回归；PostgreSQL 双连接并发；旧用户登录/强制重置演练；空库及旧快照迁移。

**风险**：孤儿/重复导致 migration 失败、锁表、密码编码未知、改密造成登录中断、缓存不同进程不一致。先盘点、隔离、回填、验证；缺明确归属不自动扩权。

**回滚**：回到支持扩展字段的前一安全应用版本；旧会话不重新激活；密码单向升级不反解，采用重置恢复。新增审计/会话/授权记录不删；约束失败优先修数据或前向修复，生产不 reset migration。

### B4 — Audit / Versioning 最小基础

**涉及文件**：拟 B/coreadmin/audit/{models,services,serializers,views}.py、migrations；coreadmin/access/policy.py；system/services 的授权/配置变更；utils/middleware.py、request_util.py；system/views/operation_log.py、login_log.py；拟 coreadmin/foundation/versioning.py 仅定义 revision/契约辅助，不建万能模型。

**类/函数**：AuditEvent、append_event、只读审计视图；业务服务在同一 atomic 写审计；脱敏策略；乐观锁检查；BusinessPolicy/QualificationPolicy 接口。运行账号表权限与 migration owner 分离。

**预期**：至少角色授权和配置变更有可信同事务 old/new/reason/actor；审计不可普通修改/删除；冻结版本、版本整数和 revision 契约可测试。没有创建 Result/Report 模型。

**测试**：AUD-01/02、TX-01～03；服务模拟异常；DB 账号直接 update/delete 被拒；资格 provider deny 测试；并发 revision 契约；历史日志标注不补造。

**风险**：敏感字段误写 audit、将历史日志误认可信、时间迁移偏移、审计表权限与迁移冲突。明确允许字段、分离身份，先验证旧时间语义。

**回滚**：保留追加事件和表；可以停用相应写动作，不回到无审计写入；投影/读页面可回滚；不能删除已提交审计以匹配旧版本。

### B5 — Managed File / 安全导入下载

**涉及文件**：拟 B/coreadmin/files/{models,services,storage,validators,views,serializers}.py、migrations；system/views/file_list.py、download_center.py；utils/aliyunoss.py、tencentcos.py、import_export.py、import_export_mixin.py；settings/urls；W/src/settings.ts、components/importExcel/index.vue、utils/service.ts 及附件消费者。

**类/函数**：ManagedFileService initiate/confirm/open_for_import/download/archive；StorageAdapter 写入新 key/读取固定版本；FileSerializer.create 改兼容适配；import_to_data 接收授权流；ImportSerializerMixin.import_data 接 file_id；下载中心受控链接。部署同步关闭旧公开 media/CDN 入口。

**预期**：私有上传验证、服务器 SHA-256、正式不可覆盖、授权下载、导入不接路径；旧附件映射隔离且不篡改历史；首期可仅本地私有存储。

**测试**：FILE-01～05、SEC-01/08/10、TX-03；同名上传、临时覆盖竞态、事务失败孤儿清理、旧 URL 测试；FastCrud 上传→file_id 导入→授权下载正例。使用 stub 与隔离存储，不能写生产桶。

**风险**：数据库与文件不同事务、旧文件归属不明、图像标签无法带 JWT、signed URL 撤权延迟、历史已覆盖无法还原。不冒称迁移能够恢复旧原件；缺文件列待处理清单。

**回滚**：旧元数据只读/映射仍保留；新最终 key 和审计不删除；关闭新上传但保留授权下载。不能回滚成公开 URL 或可覆盖 key；不做破坏性批量搬移后无映射。

### B6 — 集成验收与 CI 门槛

**涉及文件**：B 测试配置/fixture、foundation_tests、requirements 与版本声明、迁移检查；W/package.json、权威锁文件、eslint 配置、tsconfig、vite.config.ts；真实版本库选定的 CI 配置（当前未发现 CI，不假定某平台）；部署安全配置文档和自动检查。

**类/函数**：动作注册覆盖检查、测试 runner 初始化、前端非修改 lint/typecheck/build、迁移从零重建、生产配置检查、受限账号/存储恢复演练。

**预期**：前五批联动回归、锁定依赖、后端测试/前端 typecheck+lint+build/migration check 必须成功，后续新增未保护 action 不能合并；不在这一批才首次引入测试。

**测试**：第 19 节全部适用用例；前端登录→角色授权→部门范围→字段编辑→上传/下载→注销；五个 gate 出具证据；第 20 节未实现业务用例标待业务实施，不能假通过。

**风险**：旧工具链存在不兼容、构建写源文件、CI 没有真实 PostgreSQL、只有拒绝测试无可用正例。按兼容版本最小修正，不并行引入多种框架。

**回滚**：回退有缺陷的工具版本到上一已锁定可用版本；安全测试/迁移门槛不删除，不通过忽略 exit code 放行；需要时暂停业务合并。

## 23. Compatibility Matrix

| 当前能力 | 保留 | 改造 | 废弃 | 新基础 |
| -- | -- | -- | -- | -- |
| Users | 用户 ID/现有资料、AbstractUser | 窄 serializer、密码/会话、受控角色归属 | all 字段写入、共享默认密码、MD5 多路长期兼容 | UsersService、AuthSession/修订机制 |
| Dept | 现有树与 ID | FK、环检测、范围 provider、归档 | 将 Dept 视作全部客户/项目隔离 | ScopeProvider 接口 |
| Role | 现有角色和成员概念 | active 一致、委派边界、事务 | 仅登录即可授权/硬编码 admin 身份 | GrantService |
| Menu | 动态导航 | 管理动作授权、引用约束 | 菜单作为业务安全依据 | 受控 action 展示映射 |
| MenuButton | value UI alias、api/method 展示 | 显式映射稳定 code | 任意 URL 正则决定权限 | ActionRegistry |
| FieldPermission | 页面字段配置素材 | action+object+scope 相关后端执行 | 只前端控制、跨角色无条件拼接 | FieldPolicy/硬字段上限 |
| DataLevelPermissionsFilter | 临时适配接口 | union、active、确定顺序、缺映射拒绝 | 跨动作 CUSTOM、early return、无 dept 即全量 | ScopeResolver |
| CustomPermission | DRF 调用入口 | 稳定 action/object policy | URL 正则最终决策、AdminPermission 错误字段 | ActionPolicy/ObjectPolicy |
| CoreModel | 旧系统表继承暂保留 | actor/时间服务器控制、关系清理 | LIMS 直接继承其全 CRUD/文本归属假设 | 窄基础 mixin/显式模型策略 |
| CustomModelViewSet | 分页/响应与现有 CRUD 接口 | scope/object/field/删除能力声明 | 自动开放 destroy/bulk、伪事务、吞全部异常 | 受控 ViewSet 适配层 |
| FileList | 旧 ID 和附件兼容映射 | 私有下载、校验/映射 | 正式原始数据直接使用旧可变 URL/key | ManagedFile/StorageAdapter |
| OperationLog | HTTP 排障查询 | 只读、脱敏、追踪、限长 | 当业务审计；用户指定 log_id | 独立 AuditEvent |
| SoftDeleteModel | 不迁移现有业务依赖（未发现具体使用） | 不作为 P0 全面修复对象 | 当前共享 manager/递归软删在 LIMS 中复用 | 明确 Archive/Cancel/Invalidate/Supersede |
| SystemConfig | 非敏感参数和 UI | lookup 允许清单、事务、缓存提交后失效 | 任意模型读取/凭据仓库/公开默认密码 | 公共配置 registry 与秘密注入 |
| Celery | 可保留现有依赖和扩展方向 | 实际启用前修 broker/结果依赖/幂等 | 未修链路承担关键提交/审计 | on_commit、必要时 durable outbox |
| Vue Dynamic Router | 路由/layout/menu | effective action 元数据、失效刷新 | 前端权限作为后端安全保证 | 服务端统一授权投影 |
| FastCrud | 表格/表单/CRUD 框架 | 窄 payload、受控上传下载、HTTP 错误兼容 | 自动把 all 字段对象提交当通用业务更新 | 业务动作表单及明确 DTO |

## 24. Foundation Architecture

```text
Vue + FastCrud + Dynamic Router
   |  UI menu/button/field hints (not authority)
   v
DRF API / existing system routes
   |
   +-- Authentication: active user + session + auth revision
   +-- ActionRegistry / ActionPolicy: stable code, default deny
   +-- SecurityEnvelope + ScopeResolver: effective grants union
   +-- ObjectPolicy: scoped ID / relations / operation conditions
   +-- FieldPolicy + explicit Serializer: read/create/update ceilings
   |
   v
Application Services (existing system first)
   +-- Grant / User / Config / Message commands
   +-- BusinessPolicy + QualificationPolicy extension
   +-- transaction.atomic + locks / expected revision
   +-- Versioning contract (no universal LIMS model)
   +-- Audit.append_event in SAME database transaction
   |
   +----------> PostgreSQL (existing database type)
   |              +-- real FK / UNIQUE / CHECK / indexes
   |              +-- append-only AuditEvent; restricted app account
   |              +-- optional outbox for reliable async work
   |
   +-- on_commit --> cache invalidation / notifications / worker wakeup
   |
   +----------> ManagedFileService
                    +-- upload session / quarantine / validation
                    +-- immutable key + server SHA-256 + fixed version
                    +-- authorized download / conditional short signed URL
                    |
                    v
                 Private StorageAdapter
                    +-- private local first
                    +-- OSS / COS / S3-compatible when verified
```

Audit 与主数据同库事务；对象存储不在 PostgreSQL 事务内，靠 staging、固定对象版本、幂等确认和补偿维护。未来 LIMS app 依赖 foundation policy/service，foundation 不反向 import samples/tests/results 具体模型；业务通过 registry/provider 注册，避免万能 CoreModel 和跨 app 循环依赖。

## 25. Blockers Before LIMS

**BLOCKER 数量：5。** 下表是正式 LIMS 核心开发的准入门槛，包含必要最小实现与能验证的契约，不要求实现尚不存在的全部业务能力。

| Gate | BLOCKER | 必须完成的最小范围 | 对应批次 |
| -- | -- | -- | -- |
| G1 | 权限执行边界不可信 | 授权越权封堵；action/scope/object/field 后端统一；匿名入口、动态 lookup、路径导入、XSS 受控或关闭；核心正反例通过 | B1/B2/B5/B6 |
| G2 | 认证与生产秘密不可信 | Secret must rotate、安全配置拒启、会话注销/改密失效、密码与首登一致；未统一旁路关闭 | B1/B3/B6 |
| G3 | 数据写入缺少可重现完整性 | 测试数据库隔离、迁移受控且可重建；关键授权真实 FK/唯一；服务事务、并发与回滚基线；新基础表不继承关闭约束 | B1/B3/B6 |
| G4 | 缺少可信变更历史与冻结契约 | 最小 AuditEvent 服务已在现有授权/配置上运行；同事务且 append only；版本/乐观锁/资格扩展契约有测试 | B4/B6 |
| G5 | 缺少受控不可变文件入口 | 至少一种私有存储实现、随机最终 key、服务器 hash、授权下载、file_id 导入契约和旧 URL 封闭；测试通过 | B5/B6 |

分类边界：

| 阶段 | 内容 |
| -- | -- |
| BLOCKER | 仅上面 G1–G5 的最小闭环；CI 可重复验证这些闭环也属于门槛 |
| BEFORE MVP | 实际使用的旧附件回填与归属确认、旧核心关系剩余约束修复、真实使用场景的文件大小/profile、备份恢复、首个业务模块真实资格/冻结版本测试、部署全部参数定版 |
| DURING MVP | samples→测试链具体资格模型、方法版本/结果/报告版本、工作流状态、设备校准策略；按模块接入 foundation，不先建万能流程引擎 |
| LATER | 富文本安全恢复、多云适配、跨客户物理去重、大曲线处理优化、大规模导出/完整 outbox 平台、普遍 N+1、UI 重复清理、全面软删框架、全量浏览器 E2E |

若 MVP 首次上线就需要高并发异步任务、报告签发或特定扫描政策，相应能力提前为 BEFORE MVP；不能因表中列为 LATER 就豁免实际关键要求。旧非关键功能关闭是安全的阶段措施；不能以关闭所有基础能力并使正常流程不可用来宣称五门槛通过。

## 26. Acceptance Criteria

这些是后续实施验收，不是本报告已完成的安全测试。所有条件必须有测试结果/迁移结果/部署检查证据，不接受“代码看起来正确”。

1. Anonymous POST `/api/system/file/`、GET `file/get_all/`、DELETE `file/multiple_delete/` → 401/403，数据库和存储无改变；已明确禁用路由为 405。普通 role mutation → 403，所有授权表完全不变。
2. 持 user.update 权限的普通用户提交 `is_superuser=true`（POST/PUT/PATCH 分别验证）→ 400，数据库仍 false；混合合法字段也不得部分保存；password/hash 不出现在任意用户响应。
3. 部门 A 用户对 B 对象 retrieve/update/delete/custom → 404；list 不包含 B。bulk 中包含一条 B 或不存在对象 → 整体 404，A 对象未删除；可见但不可删除对象 → 整体 409。
4. CUSTOM scope 只使用当前 action grant 的部门；A→B 替换后不留 A；多角色 union 与顺序无关；disabled role 在下一请求动作/字段/范围全部无效，已有 token 不保留旧授权。
5. 不可读字段在 list/retrieve/export/嵌套/lookup 都不出现；禁止 create/update 字段 → 400；通过 filter/order/search 猜测该字段被拒绝。角色 A 敏感字段不泄漏到仅角色 B 可访问的对象。
6. 未注册 action 默认拒绝；PATCH/HEAD 不返回 500；所有 custom as_view、白名单、导入模板/导出都有可追踪策略。合法已授权请求同时通过。
7. `get_table_data` 不能通过配置 model 名输出 Users 全字段；公共初始化不含默认密码或存储凭据；旧 url 导入 → 400，后端未按该路径打开文件。
8. 客户端 log_id 无法修改既有 OperationLog；认证/改密/敏感配置原文及哈希不出现在日志；消息危险 HTML 在浏览器中不执行；未授权 GET 不标记消息已读。
9. 角色/配置更新 → 一条或明确约定的事件集合记录真实 actor、reason、old/new；注入 audit 写失败 → 业务与 M2M 全回滚；AuditEvent 普通 update/delete API → 405，运行账号 SQL update/delete/truncate → 拒绝。
10. 授权替换/配置批量/消息收件人/批量创建中途失败 → 原表与关联全部保持；rollback 不发消息/任务；commit 后回调才发生；回调失败有可恢复记录且不伪称业务回滚。
11. 同名不同内容上传 → 不同最终 key；确认后覆盖正式对象 → 被拒；客户端传 sha256/key/engine → 400；服务器 hash 与固定对象版本一致；隔离文件不能下载/正式引用。
12. 篇幅上限以 profile L 验证：L 内符合类型的文件成功，L+1 返回 413（无 Content-Length 同样）；非法 magic/压缩展开超限被拒；私有存储直链和旧公开 media URL 不能绕过授权。
13. Logout 后同一会话的 access/refresh 均 401；改密/重置/禁用后旧凭据修订 token 均无效；refresh 重放不能再次成功；必须改密用户不得访问普通业务 API。
14. 生产配置缺秘密、DEBUG=True、通配 hosts、全来源凭据 CORS、启用上传却无上限 → 启动检查失败；输出不含 Secret。已泄露密钥不再用于有效签名或 fallback。
15. PostgreSQL 直接写孤儿关键 FK/重复 grant → 数据库拒绝；空库从受控迁移可重建；旧快照升级和中断恢复可复现；不存在为通过检查而删除旧迁移或生产 reset。
16. CI 后端权限/事务/约束/API tests、frontend typecheck/lint/build、migration check 全部成功；失败真正阻断合并，测试未连生产，前端合法授权流程可用。
17. 本阶段只交付设计文件；实施完成后的门槛判定不得把第 20 节尚未建立的 LIMS 业务模型测试标为已通过。对于版本/资格基础，须提供接口契约测试，业务行为在具体模块验收。

## 27. Recommended Implementation Order

执行顺序：**B1 封堵和测试入口 → B2 统一权限 → B3 事务/约束/认证生命周期 → B4 审计与版本契约 → B5 受控文件 → B6 集成准入**。B1 的测试/安全配置和 B2 的基础政策接口先于新增 foundation app；B4 使用 B3 的事务规范；B5 使用 B2 权限、B3 完整性、B4 审计。每批先写失败回归再修复，单批通过后继续；不要在整改过程中夹带 samples 等业务表。

给后续 Codex 的实施边界：每次明确一个批次或可独立验证子集，先读现有最新代码、迁移状态与本方案，不照抄已过时行号；允许的文件范围按批次声明；凡新权限 code 都登记动作映射和测试；不以通配权限、禁用测试、恢复旧公共 URL 解兼容问题；数据库破坏性清理需先形成可核对数据清单和回滚方案。本文是设计方案，不代表已经获得后续实际部署、数据库清理或 Secret 外发授权。

**最终七项决策：**

1. **真正的 LIMS 开发 Blocker 是什么？** 第 25 节 G1–G5 共 5 项：可信权限执行、可信认证/生产配置、事务与可重现数据库完整性、同事务不可变审计和版本契约、受控不可变文件基础。不是所有 UI/性能债务都阻止开始开发。
2. **修复顺序是什么？** 上述 B1→B6；封堵先于广泛重构，测试从 B1 开始，不等收尾补测试。已修安全边界不能因后续失败回滚成漏洞。
3. **哪些组件可以安全保留？** Django/DRF/PostgreSQL 技术栈、Vue/FastCrud/动态路由、Users/Dept/Role 现有身份与导航数据；前提是经统一安全边界包裹。菜单/字典/非敏感配置继续使用；保留价值不等于其当前所有写接口已安全。
4. **哪些抽象不能继续用于 LIMS？** URL+method 正则最终授权、仅前端字段权限、dept_belong_id 文本作为唯一数据隔离、fields='__all__' 写 serializer、无对象核验 bulk delete、通用 destroy 自动继承、当前 SoftDeleteModel、OperationLog 充当 AuditTrail、FileList 公共可变文件地址、关闭真实 FK、把 atomic 放 serializer 构造。应渐进替换这些行为，不删除整个 coreadmin。
5. **P0 修完之后，第一个应该建立的基础模块是什么？** 从实施顺序看，权限/事务封堵后第一个独立基础 app 是 **audit（B4）**，其后是 managed files（B5）；它们本身属于 P0 最小闭环，不能拖到“P0 全部修完”以后才开始。若这里的“P0 修完”指六批全部完成，则无需重复创建 audit；下一项基础工作是将资格/版本契约接入首个业务模块，而非再搭一个万能底座。
6. **基础整改后第一个正式 LIMS 模块仍推荐 samples 吗？** **是。** 先做 Material→Panel→Specimen 的追溯、编号、接收/测量、受控附件和作废路径，作为权限/审计/文件的第一条真实纵向验证。客户/项目/委托引用边界先明确，只实现 samples 所需最小依赖，不在 samples 内以无约束字符串长期替代这些主体；不要先展开全部结果计算与报告流程。
7. **怎样判断可以开始 LIMS MVP？** 五门槛有可重复证据，第 26 节适用条件全部满足，合法流程能用，遗留高风险入口已修复或明确关闭，迁移可从零重建/升级、运行配置和文件权限可验证，剩余任务按 BEFORE MVP/DURING MVP 排期。当前只有审查与设计，尚未满足该准入条件，因此**不建议现在开始正式 LIMS 开发**。
