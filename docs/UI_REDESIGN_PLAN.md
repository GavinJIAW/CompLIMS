# CompLIMS UI Redesign Plan

> 2026-09-14 · 视觉体系与重构规划，非代码实施。
> 推荐 **Direction B — Industrial / Engineering Precision（工业工程精密型）**；Logo 原始品牌橙 **#FF6900**；建议 **6 个 UI Batch**。
> 本阶段只新增本报告，不修改任何现有文件，不实施 LIMS 业务。

## 1. Current UI Assessment

### 分析依据与边界

已扫描 `src/web/src` 的 layout、views、components、router、stores、plugin、directive、utils、assets、theme、i18n，读取入口、依赖及代表性页面。以下现状来自源码与本地文件；建议是设计推导，不能理解为已有业务。未启动服务、登录真实账户或执行构建，不能声称浏览器、权限账号或 API 回归已通过。根目录没有可用 Git 仓库，本阶段使用前端源码、Logo、依赖文件的 SHA-256 前后比对验证未改动。

路径缩写：`W/` = `src/web/`；`S/` = `src/web/src/`，均相对项目根目录。“拟新增”表示未来文件，本阶段不创建。

| 技术 | package.json 声明 | package-lock.json 锁定 | 实际依据 |
|---|---|---|---|
| Vue | ^3.4.38 | 3.5.42 | main.ts createApp；script setup/defineComponent 两种写法 |
| Element Plus | ^2.8.0 | 2.14.5 | main.ts 全局安装；App.vue el-config-provider |
| FastCrud | ^1.21.2 | 1.28.7 | settings.ts 安装 FastCrud、ui-element、编辑器、上传扩展 |
| Pinia | ^2.0.28 | 2.3.1 | stores/index.ts；main.ts 安装 persist 插件 |
| Vue Router | ^4.4.3 | 4.6.4 | router/index.ts，createWebHashHistory |
| vue-i18n | ^9.14.0 | 9.14.5 | i18n/、App.vue、菜单与登录文案 |

锁定版本不等于已验证运行版本。另有 yarn.lock，实施前确定团队实际安装流程，不在 UI 批次升级依赖或重生成锁文件。还有 VXE Table、Tailwind、ECharts、Iconify、e-icon-picker、Font Awesome 等，需考虑第三方样式影响。

| 范围 | 已确认现状 | 重设计边界 |
|---|---|---|
| 动态路由 | themeConfig.isRequestRoutes 默认 true；beforeEach 在 routesList 为空时执行 initBackEndControlRoutes；handleMenu、backEndComponent、动态 import、addRoute 串联 | 保留 path/name/component_name/meta、守卫、参数、外链/iframe，不改成静态 LIMS 路由 |
| 动态菜单 | routesList → aside.vue 递归过滤 meta.isHide → vertical.vue/subItem.vue；另有 horizontal/columns | 改呈现，保留后端顺序和递归、隐藏机制 |
| 按钮权限 | directive/index.ts 注册 v-auth/v-auths/v-auth-all；authFunction.ts 提供函数；CRUD 使用 show:auth(...) | PageHeader/更多菜单必须保留原判断、回调 |
| 重复权限 | stores/btnPermission.ts 与 plugin/permission/store.permission.ts 均 defineStore('BtnPermission')；路由加载后者，常用函数/指令读取前者 | 记录技术债，不借 UI 修改权限规则 |
| 权限插件 | main.ts 导入 RegisterPermission，但未见调用；plugin 与常用 auth 不是同一入口 | 不声称所有权限插件已启用，不擅自重注册 |
| 列权限 | utils/columnPermission.ts 控制 column.show、columnSetDisabled、addForm/editForm；areas 和 log/loginLog 调用后 resetCrudOptions | 接入不一致，不能声称全站已覆盖；不扩大授权逻辑范围 |
| CRUD | template 使用 useFs；user 使用 useExpose+useCrud；均有 index.vue/crud.tsx/api.ts | 保留两种现有写法，不为外观重写 API |
| Layout | layout/index.vue 选择 defaults/classic/transverse/columns；默认 defaults | 默认布局渐进改造，其他布局保留兼容 |
| Header/Breadcrumb | 导航行50px；Breadcrumb 按路由构造；classic/transverse 有隐藏分支 | 不用面包屑产生新权限数据源 |
| Tabs | tagsView.vue 726行，关闭、刷新、右键、拖动、固定标签、缓存、全屏和参数处理 | 强保留行为，只统一呈现与可访问性 |
| Main/Footer | defaults 外层与 main 内层双 scrollbar；main 按85/51px计算高度；Footer 默认开但内容空 | 优先解决滚动所有权和空占位 |
| Dialog/Drawer | FastCrud wrapper；角色授权80% Drawer+700px授权用户Dialog；文件选择嵌套Dialog | 保留 before-close、destroy-on-close、挂载位置和提交 |
| Table/Form | FastCrud、components/table、Element 表单/树表并存；settings 默认文本和字典居中、字典auto染色 | 统一密度、对齐与状态语义 |
| Upload | FsExtendsUploader、fileSelector、avatarSelector、importExcel 多入口 | 统一外观反馈，保留参数、URL、header、值转换 |
| Dashboard | home/index.vue 655行，静态homeOne/homeThree和图表数组，订单/计划/访问等演示指标 | 不得包装成真实实验室数据 |
| 重复Dashboard | home/backup/index.vue 与 home/index.vue 哈希完全相同 | 清理前核对后端component引用 |
| Login | 账号、条件验证码、首次改密；手机/扫码/OAuth区域隐藏或注释；有条件申请试用入口 | 不启用未接入的登录方式，不改认证流程 |
| Personal Center | 头像、组织/角色、资料更新、账号安全，533行 | 保留功能，改为信息/编辑/安全分区 |
| Theme/Dark | themeConfig、setings.vue、App.vue缓存样式、dark.scss共同控制 | 功能存在，覆盖完整性未通过运行验证 |
| i18n | 简中/繁中/英文；settings的FastCrud i18n参数注释；页面有硬编码中文 | 保留行为，新文案进入资源文件，不声称全站已国际化 |

**不可变契约**：settings.ts 的 transformQuery 将 currentPage/pageSize 转成 page/limit，排序转 ordering；transformRes 将 data/page/limit/total 转为 records/currentPage/pageSize/total。crud.tsx 的 request 回调调用 api.ts，后者使用 service。上传 `/api/system/file/` 使用 multipart，结果转换为 url/key 等字段。请求、返回、字典转换、提交成功判断、刷新时机不属于视觉替换范围。

## 2. Brand / Logo Analysis

### 资源清单

| 文件 | 尺寸/格式 | 用途及判定 |
|---|---|---|
| docs/logo.png | 1421×1005，RGBA PNG | 用户指定正式 Logo，Applus+ Laboratories；主品牌设计依据 |
| S/assets/logo.png | 1421×1005，RGBA PNG | 与docs文件SHA-256相同；登录/Sidebar代码回退资源，继续复用 |
| W/public/favicon.ico | 默认解码16×16，ICO | index.html默认favicon；完整横向字标过小；不据默认帧断言只有一帧 |
| docs/FastCrud-doc/images/logo.svg | 160mm×160mm，viewBox 0 0 160 160 | FastCrud文档标识，非公司品牌 |
| docs/FastCrud-doc/images/logo.png | 0字节，无法解码 | 空文件，无可用尺寸，非备选 |
| src/backend/static/logo.icns | ICNS多图容器，含16/32/64/128/256/512/1024px对应类型 | 未确认Web主界面引用；尺寸由容器类型判断，未逐帧视觉核验，不作主Logo |
| src/backend/static/drf-yasg/redoc/redoc-logo.png | 227×227 PNG | ReDoc文档资产 |
| src/backend/static/drf-yasg/swagger-ui-dist/favicon-32x32.png | 32×32 PNG | Swagger模板favicon |
| src/backend/static/rest_framework/docs/img/favicon.ico | 默认解码32×32 ICO | DRF模板favicon；同目录.gz为压缩副本 |
| S/assets/login-bg.png | 1920×1080 PNG | 登录背景回退，非Logo，不用于反推品牌规范 |

排除node_modules第三方包自带Logo。配置 `login.site_logo`、`base.web_favicon` 可覆盖资源；没有读取部署配置，不能保证运行环境显示本地图。

### 颜色、明暗与品牌推导

正式图为橙色首字母/加号、暖灰字标、透明背景。每隔2px采样主要不透明色：**#FF6900**、**#746661**；预览黑底不是图片黑色背景。非透明内容约 x=72–1352、y=254–666，原画布大量透明留白，直接把整图缩成40px将不可读。

- 事实：主橙#FF6900、辅助暖灰#746661来自像素，不等于取得官方品牌手册。
- 推导：工程服务、检测技术、稳健、强识别。不能据此推断资质或认证。
- 浅底：原色Logo适合白/极浅灰；不变形、不加阴影。
- 深底：暖灰字标对比不足；完整Logo放白色底板，四周8px安全区。未获得反白版本前不擅自反色/滤镜处理。
- 品牌橙不直接用于白色小字按钮；派生交互橙Light #B74700，Dark #FF9A52配深字。
- 石墨中性色、青色辅助、状态紫、派生橙、字体/spacing/Dark均是本项目设计推导，不是既有官方规范。

| 场景 | 展示规范 |
|---|---|
| 展开Sidebar | 品牌区88px；可见图形约176×57px，按内容约3.1:1显示；CompLIMS作为独立产品文字，不改公司字标 |
| 折叠Sidebar | 64px栏中32px产品缩写“CL”，橙细边框与可读深字；Tooltip完整名称。这是产品占位标记，不冒充公司简标 |
| 正式小标识 | 未来有公司认可资源后替换CL；不能截取加号声称官方简标 |
| Login | 可见完整Logo宽280–320px；保证Laboratories可读 |
| Favicon | 后续用可读产品缩写或正式小标，制作16/32/48px，不缩完整字标 |

未来可导出“仅裁去透明外边距”的展示副本，原图不变；本次不处理图片。若沿用原图，BrandLogo集中定义视窗裁切参数，不在多个页面复制偏移。配置提供的任意图片只contain显示，不套用本地图裁切。没有必要重新生成或重画公司Logo。

## 3. Product Design Principles

定位：**Composite Materials Mechanical Testing LIMS**，面向第三方复合材料力学性能测试实验室。

| 用户 | 优先信息 | 未来交互原则 |
|---|---|---|
| 实验员 | 执行任务、方法、条件、异常 | 任务表优先，读数紧邻单位 |
| 样品管理员 | 编号、接收/制样/调湿、位置 | 编号可复制，批量范围明确 |
| 项目负责人 | 进度、交期、资源 | 汇总可下钻，不只看图 |
| 技术复核人员 | 原始数据、结果、版本、异常 | 并列阅读，结论有来源 |
| 质量人员 | 异常、无效、追溯 | 状态、原因、操作者和时间分层 |
| 报告批准人员 | 待批准报告与复核结论 | 批准与保存明确区分 |
| 设备管理员 | 可用性、维护、预警 | 身份清晰、异常优先 |
| 系统管理员 | 组织、角色、配置 | 保留现有管理机制 |

信息密度中等偏紧凑；内容优先；关键值可准确读取；状态不只靠颜色；操作保留上下文；真实零值与未接入分开。禁止装饰大渐变、玻璃拟态、3D营销图、大圆角、持续动画。产品应专业、可靠、精密、长期使用不疲劳，不能靠虚构KPI体现“专业”。

## 4. Visual Direction Options

| 维度 | A Scientific / Precision | B Industrial / Engineering Precision | C Modern Laboratory |
|---|---|---|---|
| 关键词 | 科研、秩序、清晰 | 工程、稳健、精密、追溯 | 明亮、协作、易进入 |
| 色彩 | 蓝灰交互、品牌橙局部 | 石墨中性主体、派生橙交互、少量青色数据辅助 | 浅灰白/柔和青绿、品牌橙识别 |
| Sidebar | 浅蓝灰、细蓝激活线 | 浅石墨灰、4px橙标记与浅橙激活底 | 白底、弱分组线 |
| Header | 白色紧凑上下文 | 白/暗石墨、细边界、工具收敛 | 白色、更多留白 |
| Card | 1px边框、4px圆角 | 1px边框、8px圆角、无常态阴影 | 8px圆角、轻阴影 |
| Table | 40px行、严谨网格 | 40默认/32紧凑、横线与固定关键列 | 48px行、弱边界 |
| Form | 对齐标签、数值分区 | 两列分区、单位公差相邻、审计信息分层 | 宽松顶部标签、更多解释 |
| Dashboard | 图表/任务各半 | 待办/风险/到期先于图 | 角色入口与协作活动优先 |
| 密度 | 中高 | 中高，可切换 | 中 |
| 优点 | 科研属性、读数清晰 | 品牌契合、长时操作、迁移成本低 | 入门友好 |
| 风险 | 蓝色可能盖过品牌 | 橙色滥用与告警混淆、过密 | 卡片化浪费1366屏幕空间 |

仅规划一套B；A/C是决策备选，不新增三套Theme切换。

## 5. Recommended Visual Direction

推荐 **B — 工业工程精密型**。以白色/中性色承载主要阅读面积，Applus+橙/暖灰用于识别，能自然容纳测量条件、任务表格和审批上下文；继续使用Element Plus/FastCrud交互习惯，减少迁移风险。

执行：主动作/当前位置使用派生橙；警告琥珀且带图标；复核紫、执行蓝；表格40px、控件32px、页面标题24px、卡片圆角8px；每活动页面层级一个主动作。Light/Dark是同一体系的明暗映射。

## 6. Design Tokens

CSS统一命名 `--lims-<token>`。页面只能引用token，不复制色值。原始品牌色跨主题不变，交互色随主题变化；品牌、告警和选择不能因为同属暖色就共用语义。

| Token | Light | Dark | 用途 |
|---|---|---|---|
| brand-primary | #FF6900 | #FF6900 | Logo源色、非文本品牌装饰 |
| brand-secondary | #746661 | #746661 | Logo暖灰，不直接充当正文色 |
| brand-accent | #176B7A | #6BC4D1 | 非状态类数据辅助 |
| action-primary | #B74700 | #FF9A52 | 主按钮与交互强调 |
| action-primary-hover | #963A00 | #FFB27A | Hover |
| action-primary-active | #7A2F00 | #E8833B | Pressed |
| action-on-primary | #FFFFFF | #20170F | 主按钮文字 |
| action-primary-soft | #FFF0E5 | #3B281D | 弱选中背景 |
| action-primary-border | #E9B995 | #8C5A36 | 激活项边界 |
| success | #237A45 | #7FD49F | 成功前景 |
| warning | #8A5A00 | #F2CA6B | 需注意，不是品牌橙 |
| danger | #B42332 | #FF9AA5 | 错误、破坏性操作 |
| info | #245FB5 | #95BFFF | 信息提示 |
| text-primary | #202833 | #E8EDF3 | 标题/主值 |
| text-regular | #3D4856 | #C6D0DC | 表格/表单/正文 |
| text-secondary | #626F7E | #A3AFBD | 辅助说明 |
| text-disabled | #929CAA | #728092 | 禁用控件，不用于关键数据 |
| background-page | #F3F5F7 | #111820 | 页面 |
| background-card | #FFFFFF | #1B2531 | 表格/表单/卡片 |
| background-sidebar | #EEF1F4 | #171F29 | 侧栏 |
| background-header | #FFFFFF | #1B2531 | 顶栏 |
| background-hover | #EDF1F5 | #283545 | 通用Hover |
| background-input | #FFFFFF | #17212C | 输入区域 |
| background-disabled | #EDF0F3 | #222C38 | 禁用底 |
| background-table-header | #F0F3F6 | #243140 | 表头 |
| background-selected | #FFF0E5 | #3B281D | 选择行/当前菜单 |
| background-overlay | #FFFFFF | #243140 | Select/Popover/DatePicker |
| brand-plate | #FFFFFF | #FFFFFF | 原色完整Logo载体，刻意保留白底 |
| border-default | #D4DBE3 | #435367 | 卡片/表格 |
| border-light | #E7EBF0 | #303E4F | 行分隔 |
| border-strong | #7D8998 | #7E8FA4 | 输入轮廓/重点边界 |
| focus-ring | #245FB5 | #95BFFF | 键盘焦点 |
| overlay-mask | rgba(20,28,38,.40) | rgba(0,0,0,.60) | 模态遮罩 |
| skeleton-base | #E7EBF0 | #303E4F | 骨架底 |
| skeleton-highlight | #F4F6F8 | #3B4A5E | 骨架高光 |
| chart-grid | #E7EBF0 | #435367 | 图表网格 |
| chart-series-1 | #245FB5 | #95BFFF | 第一非状态系列 |
| chart-series-2 | #176B7A | #6BC4D1 | 第二系列 |
| chart-series-3 | #6951A8 | #C3AFF5 | 第三系列 |
| chart-series-4 | #B74700 | #FFB27A | 第四系列，辅以线型/标签 |

### 状态色组

各组定义 `--lims-status-<group>-fg/bg/border`，调用方不可传任意color。

| Group | Light fg / bg / border | Dark fg / bg / border |
|---|---|---|
| neutral | #536171 / #EDF1F5 / #CCD5DF | #C6D0DC / #2A3543 / #526277 |
| pending | #8A5A00 / #FFF6DE / #DBC181 | #F2CA6B / #382F1D / #856B35 |
| progress | #245FB5 / #EDF4FF / #B3CBEF | #95BFFF / #1E304C / #456995 |
| review | #6942A3 / #F4EFFF / #CEB9E7 | #D0B6F6 / #322641 / #78599D |
| approved | #237A45 / #ECF8EF / #AACFB7 | #7FD49F / #20392B / #487F5D |
| rejected | #B42332 / #FFF0F1 / #E4ACB4 | #FF9AA5 / #42272D / #925C66 |
| invalid | #8D3440 / #F6ECEE / #CDA5AD | #E9ADB6 / #382A30 / #805965 |
| completed | #176B7A / #EBF7F8 / #AACED3 | #6BC4D1 / #1C343B / #447783 |
| archived | #626975 / #F0F1F3 / #CCD0D6 | #B3BBC5 / #2C3038 / #59616F |

success/approved、warning/pending、danger/rejected、info/progress前景同源；Alert/Message浅底引用相应色组。Invalid不能用disabled灰，因为“无效”是重要结论。Completed只表示流程完成，不代表已批准或检测合格。

### 派生与状态优先级

Element Plus主色映射action-primary，Logo映射brand-primary。`primary-light-3/5/7/8/9`在token构建时按当前交互色与当前surface混合30/50/70/80/90%的surface，Dark不能继续机械混白；语义色同理。按钮hover/active使用显式值。禁用使用专门fg/bg，不对整个控件简单降opacity。

表格选择底覆盖普通hover，焦点始终有独立轮廓；错误以单元格标记呈现，避免整行红底压过状态标签。正文和主值目标对比至少4.5:1，大标题至少3:1，输入轮廓/焦点至少3:1；实施中检测实际渲染组合，本报告数值不是已通过浏览器验收的断言。原始橙只做品牌图形，不做白字小按钮。

## 7. Typography

主字体栈：`-apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Noto Sans CJK SC', Arial, sans-serif`。Noto仅在系统已有时命中；不下载字体，不依赖商业授权。

| 类型/token | 字号/行高/字重(px) | 规则 |
|---|---|---|
| Page Title / type-page-title | 24/32/600 | 每页一个h1 |
| Section Title / type-section-title | 18/24/600 | 业务分段 |
| Card Title / type-card-title | 16/24/600 | 表格/任务块标题 |
| Table Text / type-table | 14/20/400 | 表头600，紧凑模式也不缩到11px |
| Form Label / type-form-label | 14/20/500 | 中英文同等级 |
| Form Value / type-form-value | 14/20/400 | 只读也可读 |
| Helper Text / type-helper | 12/20/400 | 不承载唯一关键结论 |
| Caption / type-caption | 12/16/400 | 来源、时间戳、图注 |
| Numeric Data / type-numeric | 14/20/500 | tabular-nums lining-nums |
| Metric / type-metric | 28/36/600 | 仅真实汇总，未接入为— |

编号代码栈：`ui-monospace, 'Cascadia Mono', Consolas, 'Liberation Mono', monospace`；中文名称保留主字体。关键编号可复制、有完整Tooltip；不能删前导零。数值有效位来自字段规范，不统一强制两位小数。0、空、未测、不可计算分别表达；切换语言不改变API日期格式和数值含义。

## 8. Spacing / Radius / Shadow

| 项目 | Token基线 | 场景 |
|---|---|---|
| spacing | space-1/2/3/4/6/8 = 4/8/12/16/24/32px | 图标gap8、控件组8/12、卡片16/24、页面24、分区24/32 |
| 控件高度 | compact28/default32/comfortable40px | 登录40，普通默认32 |
| 表格行 | compact32/default40/comfortable48px | 密度可选，字体不变小 |
| radius-button | 4px | 按钮 |
| radius-input | 4px | Input/Select |
| radius-card | 8px | Card |
| radius-dialog | 8px | Dialog；Drawer边缘0 |
| radius-tag | 4px | 状态/普通标签 |
| border-width/focus-width | 1/2px | 焦点offset2px；是描边尺度例外 |
| active-marker | 4px | 当前菜单定位 |
| shadow-card | none | 用边框区分 |
| shadow-overlay Light | 0 8px 24px rgba(20,28,38,.12) | 浮层 |
| shadow-overlay Dark | 0 8px 24px rgba(0,0,0,.32) | 同时有边框 |
| motion-fast/normal | 120/160ms | 仅反馈/展开；无数字翻滚 |

非颜色token跨明暗一致，阴影分主题；头像圆形为图像形状例外。禁止新增无规律5/6/7/9/11/13/15px间距，不机械替换图像比例、科学数值或第三方内部值。`prefers-reduced-motion`下关闭位移、骨架闪动。

## 9. Layout

```text
┌──────────────────┬─────────────────────────────────────────┐
│ Company Brand    │ 56px Header：折叠 / Breadcrumb / Tools   │
│ + CompLIMS       ├─────────────────────────────────────────┤
│                  │ 36px TabsView（保留现有多任务行为）       │
│ Dynamic Sidebar  ├─────────────────────────────────────────┤
│                  │ PageHeader：标题 / 上下文 / 页面操作      │
│ 一级 / 二级菜单   │ Search / Filters                        │
│                  │ Main：Table 或分区 Form                  │
│                  │ Pagination / 页面结果                   │
└──────────────────┴─────────────────────────────────────────┘
```

Sidebar240px/折叠64px，主区域min-width:0，外边距24px。Header56px、Tabs36px；PageHeader随内容，不加入新的硬编码calc。240px是扩展建议，不要求四种布局一次统一重写。

保留layout/index.vue、routerView/parent.vue、keep-alive、routesList、tagsView store。主要调整defaults.vue、component/main/header/aside的呈现与滚动。

- 列表：固定Header/Tabs，筛选与分页保持可访问，数据区内部滚动；flex/grid与min-height:0分配空间。
- 表单：主内容整体纵滚，Header/Tabs固定，保存栏可sticky；各SectionCard不再各加滚动条。
- 保留isFixedHeader旧偏好兼容；不能删scrollbar而让updateScrollbar或Backtop引用失效。
- 现有85/51px高度、500ms后更新双scrollbar不能作为新页头基准。88vh样式也应移除后才接入。
- Footer现在空内容，不再留空白栏；保留配置能力，仅在需要时显示真实版本/版权。

**不建议重写整个Layout**。重整默认布局视觉/滚动结构，保留控制骨架；classic/transverse/columns仍兼容同套token。是否退役自由布局切换是后续产品决策。

## 10. Sidebar

品牌区88px，只有菜单区域纵滚。一级40px高，左右16px，图标20px，图文gap12px，字体14/500；二级36px，文字起点增加24px。保留三级递归支持，未来IA尽量两级，不能UI强行裁掉三级。

Active=selected底+4px橙标记+action-primary文字；Hover=background-hover。当前祖先仅适度加粗，不把所有祖先涂成同等强激活。折叠64px内图标居中，Tooltip全名，点击/键盘可开子菜单浮层，仍保留激活形状。

未来可规划“工作台、项目、委托、样品、检测、设备、方法、报告、质量、系统”，只是未来信息架构，不能凭空创建业务菜单/路由。分组基于授权后菜单树与明确展示配置；没有组信息不猜分组；保持后端排序，空组不留标题，隐藏路由不因分组重现。

Badge只展示有真实来源且已授权的计数，未知不显示0，99以上99+，有可读说明。图标复用SvgIcon适配层，新图标优先Element。长名称可完整查看。折叠按钮置Header，Logo不再承担不明显的折叠交互；过渡时保留快捷行为须有提示。权限仍由已有菜单与meta.isHide控制，不以CSS代替。

## 11. Header

当前user.vue并列密度、语言、搜索、主题设置、通知、全屏、用户，低频偏好与常用操作同等权重，通知为hover popover。

推荐左侧折叠+Breadcrumb，右侧**菜单搜索、通知、主题入口、用户**。命中区至少32×32px、间隔8px；密度/语言/全屏/高级布局配置进入用户“界面偏好”，保留原动作。Breadcrumb常显最多3层，过深中间可展开；当前页无需重复图标；标题沿用meta/i18n。

通知采用点击可控与键盘可打开，保留messageCenter/UserNews与空/错态；user.vue的getMessageCenterCount调用已注释，不能声称该SSE已活跃。头像统一回退，不应依赖socket在线才可见。

search.vue是tagsViewRoutes驱动的**菜单搜索**，不改名“全局样品搜索”。Global Search/Quick Create只预留插槽，无API/权限前不显示空按钮。Help只有真实帮助内容或配置目标才出现。主题入口继续兼容现有设置功能，不静默删除自定义选项。

## 12. Page Header

统一title、可选description/context、primary action与secondary actions插槽。标题和操作左右排，描述下间4px，至筛选16px；不足时两行，按钮不可覆盖标题。PageHeader不产生权限或调用API。

每活动页面层级一个Primary；创建/导入放PageHeader，表格工具只留刷新/列设置/密度/可选导出。迁移时复用原权限、disabled/loading、回调上下文，移除重复可见入口。

未来示例：Samples / 样品；“管理接收与制备中的试样”；主按钮“接收样品”、次按钮“导入”。本阶段不创建业务，实施先用现有用户/角色/文件管理页验证。

## 13. Tables

| 项目 | 规范 |
|---|---|
| Header | 40px，14/20px、600，background-table-header，上下1px边界 |
| Row | 默认40/紧凑32/舒适48px；单元左右12px；换行可增高，不能截错误提示 |
| Hover/Selected | 专用token，选中覆盖hover，选择框/标记辅助；不误当业务状态 |
| Border | 默认横线；矩阵/数值比对opt-in纵线；不强制重网格/斑马纹 |
| Numeric | 数值右对齐，表头同向，tabular-nums，单位在列头或邻列；null为—，0为0 |
| Code/Number | 试样号/报告号当字符串左对齐，保留前导零，不当数值排序 |
| Date | 左对齐、等宽数字；日期约112px，时间戳168–184px；有时区上下文，不改服务端含义 |
| Text | 项目/材料/人员左对齐，长文两行或省略+详情；编号可复制 |
| Status | StatusTag，稳定宽度、左对齐，不字典自动染色 |
| Actions | 固定右侧，常显查看+最多一个高频动作，其余更多；128–160px按可见按钮适应 |
| Pagination | 表格下16px，32px控件；保持total/sizes/prev/pager/next/jumper、page/limit和现有页大小 |
| Empty | 无数据/无搜索结果不同；约160–200px区域，有权限才创建 |
| Loading | 初载保留表头列宽和有限骨架；刷新区域遮罩保留上下文，不显示0条成功 |
| Error | 区域内错误+重试，保留搜索条件，不伪装暂无数据 |

未来列宽预算：Specimen No.160、Project176、Material144、Test Method160、Status112、Assigned To112、Due Date112、Actions144px，共约1120px；选择列再加40。1366屏在240侧栏与48边距后约1078px，允许**表格内部横滚**，不靠10px字体或隐藏唯一编号解决。固定首列和操作列背景不透明且有边界；默认可见列仍受列权限/用户配置约束。本阶段不开发这些业务字段。

搜索区按容器宽度2–4列，单控件最小200px，gap12px；查询Secondary，Primary留给页面任务。高级筛选可折叠，展开状态与值分开；批量操作显示“已选N项”和作用范围，取消选择不清空筛选。“更多”菜单不得重新露出无权限动作。

## 14. Forms

| 类型 | 结构 |
|---|---|
| Simple Form | 1–6字段，1或2列，Dialog内标签统一位置 |
| Section Form | 身份/条件/尺寸/附件/备注等语义分区，明确Section Title |
| Multi-column | 默认2列，水平24px、垂直16/24px；可用宽≥1200且每列≥280px才3列 |
| Readonly Data | InfoItem label/value，少用disabled input；无读权限不渲染原值 |
| Measurement Input | 值/单位/精度说明同组；负值、步长、范围来自字段规范 |
| Unit Input | 固定单位append；允许切换才select；不隐式换算单位 |
| Tolerance | 名义值+上下偏差或对称公差，依方法选择，不能强行全部± |
| 温湿度 | °C、%RH邻接数值，时间同区；示例单位不代表现有约束 |
| 尺寸 | 长/宽/厚各自命名和单位，不能只给placeholder |
| 日期时间 | 日期与时间范围用明确控件，保持格式和时区含义 |
| Required | 星号+表单“*必填”说明，不将所有label变红 |
| Validation | 沿用rules与触发时机；提交定位首错，长表单顶部摘要，保留输入 |
| Help Text | 字段下12/20px，说明格式/单位/来源，Tooltip只补充 |

默认顶部label适应中英；管理弹窗可用统一112px侧label，不混用。备注/附件跨列，不把复杂表单做成长达数屏单列。只读审核的数据来源、操作者、时间低一级呈现；没有接口不伪造审计记录。

Upload显示文件名/大小/进度/成功失败/重试移除。保留每个入口现有类型、大小限制、单多选、预览、回传ID/URL，失败不得显示成功附件。统一呈现不等于增加文件服务或改上传策略。

## 15. Dialog / Drawer

| 容器 | 场景 | 尺寸与交互 |
|---|---|---|
| Dialog | 少字段编辑、确认、小型选择 | 480/640/800px，max-width:calc(100vw - 48px)；头/内容/底24px；内容约视口70%上限后滚动 |
| Drawer | 保留列表上下文的详情、中等复杂编辑 | 640/800/960px，最大calc(100vw - 48px)；头尾固定，中部滚动 |
| Full Page | 检测执行、结果审核、批准、多表与复杂分步 | 未来独立业务页；本阶段仅容器规范，不开发流程 |

RoleDrawer现有80%+splitpanes为高密度授权场景，先统一表面/标题/滚动、保留尺寸行为，验证后再选宽度档；不能为了规范改变授权提交时机或改成新路由。

所有弹层有可见关闭/取消；保持原close-on-click-modal、before-close、destroy-on-close与既有未保存策略，不全局改遮罩关闭。新复杂表单的脏数据确认需另行定义验证。必须测试进入焦点、Tab约束、原Esc策略、关闭回触发点。避免新增嵌套，现有授权用户/文件选择嵌套保留兼容。

## 16. Buttons

| 类型 | 视觉 | 用途 |
|---|---|---|
| Primary | action-primary底、action-on-primary字、4px圆角 | Create/Submit/主要Save；一个活动层级一个 |
| Secondary | surface、边框、text-regular | Cancel/Import/Search/辅助操作 |
| Text | 透明底、可读交互色、hover底 | View Details等非破坏动作 |
| Danger | danger字/边框，最终删除确认可实底 | Delete/已有撤销，不用普通主色表示删除 |
| Icon | 32px命中区、16/20px图标、Tooltip+aria-label | 刷新、列设置、折叠 |

gap8px、普通高32/登录40、字14px。Loading宽度不跳，防重复提交；Disabled可提供确切原因。活动Dialog的Primary属于模态层，背景不可交互，不算竞争主动作。删除继续调用原确认与API，不借视觉改变操作策略。

## 17. Status System

拟新增 `S/components/statusTag/index.vue`、`S/ui/status.ts`：业务枚举→显示label/i18n key→semantic group→fg/bg/border+图标。组件props为status/domain/size，不开放color，不转换业务状态。

| 状态 | Group | 图标语义/中文 |
|---|---|---|
| Draft | neutral | 编辑/草稿 |
| Pending | pending | 时钟/待处理 |
| Received | neutral | 收件/已接收 |
| Preparing | progress | 工具/制备中 |
| Conditioning | progress | 条件控制/调湿中 |
| Ready | neutral | 就绪/已就绪，不用绿色暗示批准 |
| In Progress | progress | 进行/处理中 |
| Testing | progress | 检测/检测中 |
| Review | review | 复核；待复核或复核中由业务定义，不能混为一个步骤 |
| Approved | approved | 勾选/已批准 |
| Rejected | rejected | 退回/已退回 |
| Invalid | invalid | 禁止/无效 |
| Completed | completed | 完成/已完成 |
| Archived | archived | 归档/已归档 |

默认高24px、横padding8、字12/16、边框1、圆角4；不能只剩色点。未知枚举neutral+“未知状态”，不默认Draft，更不能Approved。原值显示服从权限。逾期/优先级/异常为独立维度，用warning/danger说明，不覆盖生命周期。现有启用/禁用不可自动重释为Approved/Invalid。本阶段仅设计映射，不新增后端枚举、状态机、审核流程。

## 18. Dashboard

当前home/index.vue与backup完全相同，含静态订单、月度/年度计划、访问和温压图表数组，**不是实验室实时统计**。不能把示例值换名“检测中”继续展示。

建议12列桌面网格，gap16px，任务优先：

```text
PageHeader：工作台 + 当前用户上下文
[我的待办 —] [到期样品 —] [检测中 —] [待复核/批准 —]
[我的任务列表                     8列] [提醒/异常 4列]
[近期项目                         8列] [设备提醒  4列]
[工作量概览：有真实数据后启用                    12列]
```

| 区域 | 未来结构与数据条件 |
|---|---|
| My Tasks | 任务、对象编号、到期、状态、单一进入动作；真实权限过滤 |
| Samples Due | 截止时间、负责人、状态；区分逾期/即将到期 |
| Tests In Progress | 简洁表格摘要，不虚构在线设备 |
| Pending Review/Approval | 区分角色动作，复核/批准不合并成业务状态 |
| Equipment Alerts | 设备、异常类型、时间、真实详情 |
| Recent Projects | 仅可访问项目，更新来源真实 |
| Workload | 指标定义/时间范围/API明确后才条形图，有列表替代 |

未接入=—与“该模块尚未接入”；真实空数组=暂无待办；真实0=0；请求失败=错误态。未来UI首版可仅展示用户上下文和现有授权菜单快捷入口，预留模块不生成假曲线、百分比、项目或无效链接。MetricCard不能自己计算KPI。保留ECharts，从token读颜色/字体，resize与主题切换同步处理。

## 19. Login

采用**Brand Area + Login Form**：1440/1920左右约52%/48%，1366约48%/52%；表单max-width400px、左右安全区≥32px，品牌区padding48px，浅灰背景。完整Logo可见宽280–320px，下24px放CompLIMS与“复合材料力学性能测试实验室管理系统”。可用极淡token工程网格，不用无关插画、3D、玻璃或大渐变，不添加未提供的认证标志。

表单标题“登录”，可见用户名/密码label、40px控件、24px间距、密码开关有可访问名称。验证码遵循base.captcha_state，保留刷新/校验/参数。保留Loading、Enter、错误提示、密码处理、token、redirect和首次改密；首次改密只换内容与标题，不跳新流程。

恢复当前被注释的siteLogo展示，保持site_title/site_name/login_background配置回退能力。没有配置背景时建议中性品牌区代替默认大背景；已配置图片在受控区显示，不能删配置能力。申请试用保留已有条件逻辑，显示时为低权重文字入口。手机/扫码/OAuth隐藏项不启用。

`login-main.svg`被import但assets扫描未找到，属于静态构建风险；后续确认死引用可移除，不声称已运行构建失败，本阶段不修。Dark表单用深surface，完整Logo白色载体不反色。平板单列顶部品牌，手机仅保障登录/基本导航，不承诺完整LIMS执行。

## 20. Empty / Loading / Error

| 状态 | 内容 | 操作 |
|---|---|---|
| Empty State | 暂无记录+列表说明，32px简洁图标 | 有权限才创建 |
| No Search Result | 未找到匹配记录 | 调整/清空条件，保留输入 |
| Loading | 正在加载，区域遮罩 | 表头不消失，提交只按钮Loading |
| Skeleton | 初载结构占位，最多5行 | 减少运动下静态 |
| No Permission | 无权查看 | 不显示敏感摘要/数量，返回可访问页 |
| 403 | 访问受限的新设计语义 | 使用现有无权限页时不擅改/401路由或API码 |
| 404 | 页面不存在或已移动 | 保留原返回首页等处理 |
| 500/服务异常 | 暂时无法完成请求 | 重试/返回，真实请求ID才展示 |
| 离线/超时 | 连接失败 | 保留值，不自动重放创建/删除 |

当前错误页为401.vue/404.vue，401远程插画，二者height calc字符串缺少闭合括号。统一ErrorState外观，先保留路由和按钮含义；500是复用错误视图，不要求新增后端机制。状态文案进入i18n，动态提示aria-live；字段错误常驻，不能只Toast。失败不能归零或显示空成功。

## 21. Icons

现有多源：Element Plus（other.elSvg注册ele-）、SvgIcon多源包装、三套iconfont、Font Awesome、e-icon-picker默认彩色集、FastCrud内部图标；依赖包含Iconify。App调用setIconfont，但其CDN数组当前为空，不应声称运行依赖在线字体。

**新增UI默认Element Plus icons-vue**，16/20/24px网格、单色，不再加Emoji或另一图标库。保留SvgIcon兼容后端保存的ele-、iconfont、fa和图片路径；不能直接卸载旧字库。图标选择器优先Element分类，但可回显旧值。

FastCrud内部图标经UI适配/插槽统一尺寸色彩，先核对本地版本配置能力，不假定SvgIcon能替换全部内部renderer。main.ts和theme/index.scss重复引Font Awesome，后期可清理。命中区、Tooltip、aria-label与键盘焦点统一。

## 22. Responsive Strategy

桌面优先，按内容可用宽度决定列数，不只看屏幕宽度。

| 视口 | 侧栏/边距 | 策略 |
|---|---|---|
| 1920 | 240/24px | 表格占可用宽，表单max-width1280–1440，Dashboard8+4 |
| 1440 | 240/24px | 4摘要卡、2列表单、复杂表格内横滚 |
| 1366 | 240/24px | 主体约1078px；操作换行、1120px样例表横滚，不自动隐藏业务列 |
| 1000–1279 | 可保留64px折叠偏好/16px | 2摘要卡，面板上下排，40px触控区，1–2列表单 |
| <1000 | 保留现有overlay/16px | 单列、表内横滚，基本访问，不牺牲桌面密度 |

现有<1000和<=1000边界要测999/1000/1001，统一时保证蒙版关闭。验收1366×768、1440×900、1920×1080，桌面125%缩放、英文长标签、低窗口高度。Sidebar可滚、弹层不越界、分页可达，根页面不能因局部卡片产生横滚。Tablet次要，Mobile不要求完整实验室工作流。

## 23. Dark Mode

**保留，重建为统一token明暗映射。**已有偏好和入口，移除会变功能；多套任意颜色加页面补丁会持续放大成本。

setings通过html data-theme切换，根style.setProperty注入主色，App恢复Local整段themeConfigStyle；dark.scss大量!important、有`--el-fill-colo`拼写和旧分页/编辑器选择器；RoleDrawer/reset/home独立色值仍在。静态证据说明不完整风险高，未运行验证不能断言具体每个区域实际失效。

保留data-theme/isIsDark契约，不另加竞争性.dark源。theme adapter集中应用，页面不自己逐个set color。旧偏好按白名单迁移并版本化，不用Local.clear作为常规视觉发布；迁移单独回归，不改认证存储。自定义旧配色兼容输入与规范默认预设分开，不能静默丢用户设置。

Batch1即有完整Light/Dark；之后逐组件同步适配，Batch6全面审查。覆盖body级teleport的Dialog/Drawer/Select/DatePicker/Tooltip/MessageBox、文件预览、树、VXE、编辑器、ECharts和插件。跨域iframe仅统一宿主，不承诺注入主题。

## 24. Element Plus Strategy

不更换、不fork。优先CSS Variables，其次范围明确的Global Overrides，再以轻包装减少结构重复；SCSS变量只做确需的编译期参数，不为配色重打组件库。

| 组件 | 重点覆盖 | 保持 |
|---|---|---|
| el-button | 类型、色、尺寸、焦点、Loading | click/disabled/提交 |
| el-input | surface、轮廓、placeholder/focus | v-model、校验、清空/密码 |
| el-select | 输入/浮层/多选Tag | value/label、远程搜索 |
| el-table | 头、密度、选中、固定列 | row-key、排序/筛选/选择、列权限 |
| el-card | padding/边框/圆角/无悬浮影 | header/body slots |
| el-dialog | 尺寸、标题、正文滚动、底部 | v-model/before-close/teleport |
| el-drawer | 头尾/surface/分区 | 关闭/销毁/方向 |
| el-tag | 密度/4px，业务走StatusTag | 关闭/多选展示 |
| el-tabs | 下划线/间距/focus | pane key/切换，区别TagsView |
| el-menu | 高度/缩进/active/折叠浮层 | router/index/展开/动态树 |
| el-pagination | 32px/焦点/当前页 | page/limit/total/事件 |
| el-form | label/间距/帮助/错误 | rules/prop/validate/reset |
| el-date-picker | 日期格/范围/popper/Dark | 格式/范围/接口字段 |

tree/checkbox/radio/upload/notification/tooltip/popconfirm/message-box亦做状态抽查。覆盖集中theme/element.scss，避免各页:deep依赖私有DOM；依据锁定版本验证，不在本轮升级库。

## 25. FastCrud Strategy

### 保留当前分层

- index.vue：保留fs-page/fs-crud、crudBinding/ref、初始化、slots、refresh；仅增加布局与PageHeader。
- crud.tsx：保留request、dict、权限show、valueBuilder/valueResolve、rules、回调；可以显式配置align/width/表单分组/操作呈现。
- api.ts：不改URL、method、参数、返回、导出路径。
- settings.ts：继续安装ui-element、FastCrud、扩展；视觉默认在commonOptions或纯视觉工厂集中，不能修改transformQuery/Res。

| 层 | 应包含 | 禁止 |
|---|---|---|
| Global FastCrud Theme | fs-page surface、工具gap、搜索、表格密度、分页、form wrapper | 88vh/全局白底；请求转换 |
| Reusable Component | PageHeader、StatusTag、EmptyState、附件展示；测量字段有多个真实用例再建 | 重写fs-crud、另建分页状态 |
| Page-specific | 树+表、字段单位/宽度、权限抽屉、特殊单元格 | 页内硬编码主色、复制全套表格样式 |

settings当前文本居中、字典auto色，迁移先在试点显式配置，不让全部字典一次变色；未来业务状态opt-in StatusTag，普通字典保留兼容直到逐页审查，不重释现有enum。

从actionbar搬到PageHeader的操作复用已解析的show/disabled/loading/click及CRUD上下文，不在Header重新写API；也不同时保留两个可见创建按钮。“更多”按相同权限过滤。不得套全量DataTable导致named slots、columnSetDisabled、wrapper、exposed methods丢失。

本地docs/FastCrud-doc可查API，最终以锁定版本实现为准。`theme/fastCrud.scss`在theme/index.scss和源码引用中未发现接入，不能声称其88vh已对全站生效；未来先改写再引入，不能直接导入旧白底样式。

## 26. Reusable Components

| 候选 | 决策 | 最小职责与依据 |
|---|---|---|
| PageContainer | 建立 | list/form模式、padding/滚动，不加载数据 |
| PageHeader | 建立 | title/context/action slots；用户/角色/文件页复用 |
| SectionCard | 轻包装或统一class | 至少两处相同结构再抽取，不包所有el-card |
| DataTable | 暂不全量建立 | 先统一FastCrud和components/table视觉，避免第三套表格 |
| StatusTag | 建立显示抽象 | 注册表/语义色，未来枚举再接入 |
| MetricCard | 按工作台需要 | title/value/loading/unavailable，不算KPI |
| InfoItem | 建立 | label/value/empty、代码/单位slot；个人信息/详情复用 |
| EmptyState | 建立 | empty/no-result/unavailable/error结构与action slot |
| ConfirmAction | 优先公共配置函数 | 文案/按钮，保留调用方确认回调，不再造模态管理 |
| FilePreview | 演进现有 | 复用fileSelector/el-image显示，不兼任上传服务/权限加载 |
| UserAvatar | 轻组件 | 头像/回退/用户名；Header/用户表/个人中心 |
| BrandLogo | 建立 | 资源、透明留白、浅/深载体；Sidebar/Login复用 |

保留importExcel、fileSelector、avatarSelector、tableSelector、dvaSelect、foreignKey、manyToMany、editor、auth组件功能接口，优先改呈现。新UI组件不隐式请求API或重写RBAC；单页独有结构留页面。MeasurementInput/UnitInput有两个以上真实字段用例后再抽象，不能为未来概念造空组件。

## 27. CSS / Theme Architecture

已有theme目录，继续演进，不新建竞争性的styles体系。

```text
src/web/src/theme/
  index.scss              # 唯一应用主题入口，现有
  tokens.scss             # 拟新增：明暗颜色/状态/尺寸/排版
  semantic.scss           # 拟新增：语义别名与--next-*兼容
  typography.scss         # 拟新增：字体、数据排版
  element.scss            # 现有：Element变量与必要覆盖
  fastCrud.scss           # 现有：改写后接入
  layout.scss             # 拟新增：尺寸、容器、滚动
  components.scss         # 拟新增：公共UI结构样式
  dark.scss               # 现有：迁移补丁逐步缩减
  app.scss / other.scss   # 现有：工具类兼容后清理
  media/                  # 现有：逐批迁移，统一断点
src/web/src/ui/
  status.ts               # 拟新增：显示注册表，非状态机
  crudVisual.ts           # 按需拟新增：纯视觉，无API
src/web/src/utils/theme.ts # 现有：主题应用/兼容收敛入口
```

目标顺序：Tailwind基础→第三方CSS（Element/FastCrud/扩展/VXE）→theme/index.scss。当前main/settings分散import，不能只看文本顺序断言最终cascade；用构建CSS和computed styles验证。应用覆盖在vendor后，reset.scss不应最后重新硬编码颜色。

主题内部token→semantic/legacy aliases→typography→component adapters→layout→兼容补丁。`--next-bg-menuBar`暂映射`--lims-background-sidebar`，保持未迁移页。themeConfig旧色字段是兼容输入，不允许store、DOM缓存和token持续互相覆盖；规范预设默认，旧自定义仍可读取。未来限制自由调色另行决策。

页面scoped CSS仅布局；不在全站宽泛覆盖el-row高度/el-menu宽度，用宿主class限定。Teleport用根token和明确popper-class，不仅依赖PageContainer祖先。VXE/编辑器/插件有范围适配，不改node_modules。Token→Component Theme→Page是唯一新样式流向。

## 28. Existing UI Technical Debt

以下是源码证据，不等于本次修复；部分必须独立于UI批次处理。

| 文件 | 问题 | 影响 | 建议/边界 |
|---|---|---|---|
| layout/logo/index.vue；views/system/login/index.vue | Logo标签/折叠分支注释 | 品牌缺失、留空 | Batch2/4统一BrandLogo |
| assets/logo.png；public/favicon.ico | 源图大量透明留白，小图完整字标 | 不可读 | 原图保留，后续展示副本/产品小标 |
| stores/themeConfig.ts；setings.vue；App.vue | 颜色store、内联CSS、缓存多来源 | token被覆盖 | 集中适配、旧值兼容 |
| App.vue | themeConfigVersion变化时Local.clear+reload | UI发布影响其他存储 | 单独测试白名单迁移，不动认证逻辑 |
| theme/dark.scss | !important、--el-fill-colo、旧选择器 | 暗色/升级失配风险 | 明暗token+实测替代补丁 |
| theme/fastCrud.scss | 白底、10px圆角、88vh!important，未找到引用 | 接入后可能破坏布局 | 改写再接入，不能把死样式当已生效 |
| assets/style/reset.scss | thead #606266、placeholder #dcdfe6 | 暗色冲突、低对比 | 合并组件适配 |
| theme/element.scss | 菜单全局220/64px、56行高；form末项22/18px；图标距5px | 密度混杂、覆盖过宽 | 宿主class+token |
| theme/app.scss；personal/index.vue | 逐像素工具类、mb6/mb18/mt35/gutter35 | 间距无尺度 | 渐进替换，保留兼容 |
| layout/main/*.vue；component/main.vue | 多布局包装重复，双scrollbar/硬编码高度 | 页头叠加后滚动/分页问题 | 先默认布局试点 |
| component/aside.vue；breadcrumb/index.vue | 递归菜单过滤重复 | 改一处漏另一布局 | UI保留逻辑，未来独立提只读辅助函数 |
| setings.vue824行；tagsView.vue726行 | 配置/事件/持久化/样式混合 | 改动风险高 | 先分离样式，不一次拆全部交互 |
| stores/btnPermission.ts；plugin/permission/store.permission.ts | 相同Pinia ID重复定义 | 引用入口不清晰 | 独立技术债；不随UI改变授权 |
| main.ts；plugin/permission/index.ts | RegisterPermission未调用 | 易误认插件启用 | 如实记录入口，不擅自注册 |
| settings.ts | 字典auto染色、文本居中、form取消隐藏 | 状态随机色、退出不统一 | 逐页视觉opt-in，保留关闭行为 |
| home/index.vue；home/backup/index.vue | 同哈希655行静态演示 | KPI误导、重复维护 | 工作台任务化；核对component后再清理backup |
| views/system/demo；views/template | demo路由与VIEWSETNAME占位模板 | 不应冒充业务 | 保留模板用途，删除前查动态引用/生成链 |
| user/index.vue | Tailwind字体粗细混杂、树缩进38、头像50px | 与其他管理页不一致 | 统一排版/头像/缩进，保留组织筛选 |
| role/components/RoleDrawer.vue | pane 100vw/100vh、padding10、#fff | 嵌套视口、暗色风险 | 父容器自适应/surface，授权逻辑不变 |
| components/table/index.vue | 自有分页/工具条、primary删除、固定stripe | 与FastCrud体验不一致 | 统一视觉，不立即换契约 |
| components/fileSelector/index.vue521行 | 行内布局、嵌套弹层、选择上传集中 | 维护/回归成本高 | 先壳后纯展示，保留v-model/事件 |
| avatarSelector；cropper；fileSelector | 相近裁剪/图片能力 | 可能重复但契约不同 | 不凭名称合并，先核对事件和用例 |
| components/importExcel/index.vue | inline color:red提示、400px弹层 | 帮助当错误、尺寸不一 | helper与danger区分 |
| main.ts；theme/index.scss；assets/iconfont | 多图标源、Font Awesome双入口 | 风格/维护负担 | 新增Element，旧值兼容后清理 |
| personal/index.vue533行 | 励志文案、hover卡片、分散spacing | 实验室语境不合 | 信息/编辑/安全分区 |
| login/index.vue375行 | 未找到login-main.svg导入、旧背景布局 | 潜在构建问题 | 单项确认，不改认证 |
| error/401.vue；404.vue | 远程插画/动画/round，height calc未闭合 | 可靠性/统一性差 | ErrorState呈现，原路由含义保留 |
| settings.ts；i18n；views/system | FastCrud i18n注释、硬编码中文 | 英文溢出/翻译不足 | 新文案国际化，逐批审查，不改接口格式 |

不能认定所有旧theme字段无用、演示页不可达或相近组件必然重复；删除前查后端component路径及部署配置。

## 29. Files Expected To Change

**未来清单，不是本次已修改列表。**

| 层 | 文件 |
|---|---|
| Foundation | S/theme/index.scss、app.scss、element.scss、dark.scss、fastCrud.scss；拟新增tokens.scss、semantic.scss、typography.scss；S/assets/style/reset.scss |
| Theme Integration | S/main.ts、App.vue、stores/themeConfig.ts、utils/theme.ts、layout/navBars/breadcrumb/setings.vue；必要时types/pinia.d.ts |
| Layout | S/layout/main/defaults.vue、component/aside.vue、header.vue、main.vue、logo/index.vue、footer/index.vue；拟新增theme/layout.scss |
| Navigation | S/layout/navMenu/vertical.vue、subItem.vue、horizontal.vue；navBars/index.vue；breadcrumb/index.vue、breadcrumb.vue、user.vue、search.vue、userNews.vue；tagsView/tagsView.vue、contextmenu.vue |
| Components | 第26节拟新增组件、ui/status.ts；现有table/fileSelector/avatarSelector/importExcel/svgIcon呈现层；拟新增theme/components.scss |
| CRUD Visual | S/settings.ts仅视觉默认；按需ui/crudVisual.ts；views/template/index.vue、crud.tsx后续模板 |
| Entry Pages | S/views/system/login/index.vue、component/account.vue、changePwd.vue；home/index.vue；personal/index.vue；error/401.vue、404.vue |
| System Pages | user、role、menu、dept、dictionary/subDict、areas、fileList、messageCenter、downloadCenter、whiteList、log/loginLog、log/operationLog、config、columns中的实际index.vue/crud.tsx/手工表单组件 |
| Responsive/i18n | S/theme/media/*.scss、i18n/lang/*.ts、i18n/pages/login/*.ts，仅呈现/文案 |
| Brand | 未来S/assets/brand/展示副本、W/public/favicon.ico；必要时W/index.html，原docs/logo.png不变 |

禁止范围：Django Models/API、数据库/迁移、后端RBAC、LIMS业务、各CRUD api.ts、service/request协议、Router守卫/菜单转换规则、权限store/指令授权规则、node_modules。绝对必要的前端兼容问题单独记录和实施，不扩大到后端。

## 30. Implementation Batches

推荐**6批**，依赖顺序为基础→布局→核心组件/CRUD试点→入口页面→管理页面→全面审查。Dark/响应式每批同步，不拖到最后首次处理。

### UI Batch 1 — Design Tokens + Theme Foundation

- 范围：拟新增theme/tokens.scss、semantic.scss、typography.scss；修改theme/index.scss、app.scss、element.scss、dark.scss、fastCrud.scss、assets/style/reset.scss；最小调整main.ts、App.vue、utils/theme.ts、stores/themeConfig.ts、setings.vue主题接入。
- 风险：旧Local缓存/内联样式覆盖、vendor顺序、Dark浮层。先保留旧变量别名，自定义旧值走兼容入口。
- 验证：按钮/输入/表格/浮层Light/Dark computed styles；新用户和旧偏好分别刷新；登录/路由冒烟；FastCrud请求转换无变化，不升级依赖。
- 出口：主色单源、双主题token可用；不迁移整个业务页。settings.ts视觉默认主要留第3批，第1批仅允许必要CSS入口顺序调整。

### UI Batch 2 — Layout + Sidebar + Header + Brand

- 范围：defaults.vue、component/{aside,header,main}.vue、logo/index.vue、navMenu/*、navBars相关呈现、footer；拟新增BrandLogo/theme/layout.scss；必要品牌展示副本。
- 风险：双滚动、Tabs缓存、折叠菜单、蒙版、Logo留白、旧布局兼容。
- 验证：1366/1440/1920；长三级菜单、折叠、深链接刷新、外链/iframe；Tags关闭/刷新/右键/拖动/固定/全屏；classic/transverse/columns冒烟。
- 出口：无多余页面横滚，关键动作/分页可达，动态菜单和Tabs行为不变。

### UI Batch 3 — Core Components + CRUD Pilot

- 范围：PageContainer/PageHeader/StatusTag/InfoItem/EmptyState/UserAvatar；theme/components.scss；settings.ts纯视觉项、components/table；先迁移areas（列权限）与user（组织树+CRUD）。
- 风险：动作搬移失去权限或上下文、列设置泄漏、wrapper/分页回归。
- 验证：同账户前后可见菜单/动作一致；GET查询/排序/page/limit、增改删payload一致；禁读列不能在列设置恢复；组织树筛选、表单错误/取消保持。
- 出口：形成两个真实页面范式，不重写FastCrud，不引入LIMS枚举或API。

### UI Batch 4 — Login + Dashboard + Personal + Error

- 范围：login/index.vue、account.vue、changePwd.vue；home/index.vue；personal/index.vue；error/401.vue、404.vue与相关i18n。
- 风险：验证码/首次改密/redirect、假KPI、头像上传、配置Logo回退。
- 验证：验证码开关、错误/成功登录、首次改密、回跳、退出；工作台无伪造数据；个人资料/安全原动作；配置与默认Logo均可读；错误恢复可用。
- 出口：入口页同一语言，数据未接入/零/空/错明确。

### UI Batch 5 — System Management Pages

- 范围：role及授权组件、menu、dept、dictionary、fileList、config、columns、message/download/whiteList/log；fileSelector/avatarSelector/importExcel外观；template模板视觉。
- 风险：RBAC配置页高风险、嵌套弹层、字典、上传/导出/批量。
- 验证：用现有不同权限账号；授权查看/修改遵原能力；组织树/子字典/文件选择/导入导出；每个CRUD按钮、表单、筛选、分页与原请求一致，不改api.ts。
- 出口：主系统管理页面采用同一token/排版/状态显示规则；未国际化项如保留则登记。

### UI Batch 6 — Cleanup + Responsive + Dark Audit

- 范围：theme/media/*、残留硬编码和兼容覆盖、图标重复引入；确认引用后才清理home/backup、空资产/死样式。
- 风险：删除后端动态引用、插件/VXE样式、历史主题偏好。
- 验证：全回归矩阵；桌面缩放、键盘、实际对比度、teleport、编辑器/插件/VXE；删除前记录component映射；未证实无用不删。
- 出口：第32节验收全部完成或明确登记阻断，不以“主页面能打开”代替回归。

每批独立提交和可回退；截图/请求基线通过再扩面。实施前确认可构建基线，login-main.svg等已有问题若阻断，作为独立前端兼容项处理，不能算UI新增故障或跳过后声称通过。package scripts未提供test/typecheck，lint-fix会写文件，本阶段不运行；未来优先现有build与非修复lint，必要回归测试工具纳入实施批次。

## 31. Regression Risks

| 风险 | 必须保持 | 验证场景 |
|---|---|---|
| Login | token、验证码、密码处理、首次改密、redirect | 未登录深链接、错/对密码、验证码开关、首次账户、退出 |
| Dynamic Router | path/name/component/meta/参数 | 二三级刷新、query/params、iframe/外链、404 |
| Dynamic Menu | 后端顺序/isHide/授权范围 | 普通/受限/管理员、空菜单、长名称、展开 |
| Button Permission | v-auth/auths/auth-all、auth函数语义 | 单/任一/全部，Header/更多/批量均受控 |
| Column Permission | 列/新增/编辑隐藏、列设置禁用 | areas/loginLog禁读/禁增/禁改、原例外字段保持 |
| Pinia/cache | persist、Tabs、keep-alive | 多页编辑切换、刷新、旧主题恢复 |
| CRUD/Pagination/Search | endpoint/method/payload、page/limit/ordering | 新增/编辑/删除、分页、排序、筛选/清空、组织树 |
| Upload | 类型/限制/header/FormData/回传值 | 图片/文件/Excel、失败重试取消、预览移除、既有限制 |
| Dialog/Drawer | 守卫/销毁/提交/层级 | 嵌套、遮罩、Esc原策略、Tab焦点、长内容滚动 |
| Theme/i18n | 明暗/语言/密度偏好 | 新/旧缓存、首屏、英文长文、所有浮层 |
| Tabs | affix、刷新/关闭、拖动/右键/全屏、参数区分 | 同路径不同query、关闭当前后激活正确页 |
| Plugins/Other tables | VXE/编辑器/动态插件可用 | CSS顺序、浮层、Dark，不改插件API |

写操作回归只在测试环境/测试数据执行，设计阶段不请求真实新增/删除。UI不是安全边界，后端授权仍由原后端负责；前端重复权限store/挂载时机问题保留基线并独立登记，不在“样式改造”里暗改。

## 32. Acceptance Criteria

### 本次设计阶段

- [x] 栈、路由、权限、CRUD、布局与主题基于代码，区分声明与锁定版本。
- [x] 查看正式Logo，测量尺寸/透明背景/主色，区分资源与设计推导。
- [x] 3个方向、1个推荐，完整token、组件规范、6批实施与回归矩阵。
- [x] 明确静态Dashboard和未来业务预留，不虚构真实数据。
- [x] 唯一交付UI_REDESIGN_PLAN.md，不继续实施代码。

### 未来实施验收（尚未执行）

- [ ] 所有主品牌色来自统一token；Sidebar/Header/Table/Form/Dialog不独立硬编码主色。
- [ ] Logo在Login/展开/折叠Sidebar均可读；源图不变形，CL产品标记不冒充正式简标。
- [ ] Element Plus、FastCrud、手工表格使用统一字体、密度、边界、按钮语言。
- [ ] 动态菜单/路由行为不变，包括顺序、隐藏、外链/iframe、组件匹配与参数。
- [ ] 按钮/列权限不变，Header/更多/列设置不绕过判断。
- [ ] CRUD API、分页/筛选/排序转换、上传下载契约不变，前后请求快照一致。
- [ ] Pinia/keep-alive/Tabs与主题语言偏好可恢复，不以清空全部Local实现迁移。
- [ ] 1366×768、1440×900、1920×1080正常使用，125%缩放可读，操作/分页可达。
- [ ] 数值右对齐，编号左对齐且保留前导零，单位明确、时间含义不变。
- [ ] 每活动层级一个主动作，删除Danger，图标有名称和键盘焦点。
- [ ] Login/Dashboard/System Pages同一语言，无假项目、任务、设备指标或曲线。
- [ ] 状态统一映射，文案+图标+颜色，Completed不等于Approved，Invalid不等于Disabled。
- [ ] Light/Dark含teleport区域无明显不可读；正文4.5:1、控件边界/焦点3:1目标有实测记录。
- [ ] Empty/No Result/No Permission/Loading/Error/Unavailable区分；失败不归零。
- [ ] 键盘可操作菜单/按钮/表单/弹层，关闭回焦点，减少运动偏好生效。
- [ ] 原i18n行为保留，新文案入资源，英文不溢出；未解决存量翻译明确登记。
- [ ] 每批回归通过后扩面，后端Models/API/数据库/RBAC/LIMS逻辑不修改。

### 明确结论

1. **方向**：B — Industrial / Engineering Precision（工业工程精密型）。
2. **Logo主色**：#FF6900，辅助#746661；Light交互派生#B74700，Dark派生#FF9A52，派生色不是官方色号。
3. **五个首要问题**：品牌被注释与Logo缩放；主题多来源/Dark覆盖风险；Layout滚动高度耦合；Table/Form/PageHeader缺少统一层级和状态语义；重复静态Dashboard与入口风格断层。
4. **保留**：Element Plus/FastCrud适配、Pinia/Router、动态菜单、Tabs/keep-alive、原权限入口、CRUD三层、上传/导入/选择器、ECharts、SvgIcon兼容层。
5. **重设计**：品牌呈现、Sidebar/Header/Breadcrumb/Tabs外观、PageHeader、Table/Form/Dialog/Drawer视觉、StatusTag、Login/Dashboard/Personal/Error/Empty，保留各自业务处理。
6. **更换Element Plus？** 不需要，以变量/集中覆盖/轻包装实现。
7. **更换FastCrud？** 不需要，保留配置与API，统一视觉默认和呈现。
8. **重写Layout？** 不整体重写，渐进重整默认布局视觉/滚动，保留控制骨架及其他布局兼容。
9. **批次数**：6，Dark/响应式每批纳入，最后全面审查。
10. **第一批具体文件**：拟新增 `src/web/src/theme/tokens.scss`、`semantic.scss`、`typography.scss`；修改 `src/web/src/theme/index.scss`、`app.scss`、`element.scss`、`dark.scss`、`fastCrud.scss`，`src/web/src/assets/style/reset.scss`；最小主题接入修改 `src/web/src/main.ts`、`App.vue`、`utils/theme.ts`、`stores/themeConfig.ts`、`layout/navBars/breadcrumb/setings.vue`。不含业务api.ts、后端和权限规则。

**设计阶段至此结束；以上实施清单均为后续计划，本次未执行。**
