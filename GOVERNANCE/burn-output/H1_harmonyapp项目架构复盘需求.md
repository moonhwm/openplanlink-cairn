# H1 · harmony-app 项目架构复盘——从需求到实现的架构演进、关键决策点、技术选型理由

> 编纂：Moon席位（写手-H组-1号 / GLM-5.3-Flash），2026-09-24
> 素材基线：harmony-app 仓库截至 2026-09-23 的源码与 CHANGELOG.md（共 40+ 条条目）、AGENTS.md v1.0、README.md。
> 本文自包含：所有结论均引用仓库内文件路径与行号，不依赖任何对话记忆。

## 一、需求原点与产品形态

harmony-app（应用名「铃语」，bundleName `com.yehang.stockpulse`）是一款鸿蒙 NEXT 适老化股票异动播报应用。它的产品闭环是：**云端秒级监测 → Push Kit 推送 → 锁屏大字通知 → 点按拉起 → 自动语音播报**（README.md 第 3 行）。目标用户是长辈：核心交互只有一条——「点卡片=听播报」。

需求在立项时就被压缩成五条不可逾越约束（AGENTS.md §二，2026-09-14 版）：

1. 适老化：主界面=大字白话卡片流，禁止 K 线图/走势图等复杂图表；
2. 信号内容松绑但保留三禁（详见 H4 复盘）；
3. 平台：Stage 模型，`compatibleSdkVersion 20` / `targetSdkVersion 26`，纯 ArkTS，零三方依赖；
4. PushService.ets 保持占位封装，AGC 未配置前自动降级轮询；
5. 首屏永不空白：服务未连通时显示带「示例」字样的演示卡。

这五条约束直接决定了后面所有架构决策的搜索空间——它是「约束先行」式架构设计的典型案例：先钉死边界，再在边界内做工程。

## 二、架构演进四阶段（按 CHANGELOG 时间线）

### 阶段一：骨架期（2026-09-14，白秉烛席）

当日 10:00 白秉烛（Kimi Work 桌面席）首建 23 文件 Stage 工程：EntryAbility / Index 卡片流 / PushService 占位 / AlertPoller 轮询兜底 / AudioPlayer / AlertItem 契约（CHANGELOG 第 5-9 行）。这一版已经包含最终架构的全部骨架件：**推送通道占位、轮询通道实装、演示卡兜底、数据契约先行**。55 分钟后（10:55）补上共治契约 AGENTS.md 与 CHANGELOG 交接簿，原因是「码道 IDE 与 Kimi Code 同日开工，防多 AI 架构互踩」——治理先于功能，这是本工程最鲜明的特征之一。

### 阶段二：端侧加固期（09-14 至 09-18，砚坚席）

- R1 卡片流加固（09-14 22:30）：AlertPoller 返回 `PollResult { ok, items, rateLimited? }`，引入退避策略（失败翻倍封顶 30s）；AudioPlayer 增加 onError 回调；Index 增加防连击、失败重试、连接中断、空态、429 限流独立分支；EntryAbility 补检 onCreate 中的 alertId（冷启动通知缺口修复）。
- R2 设置页（09-14 18:59）：SettingsService（Preferences 持久化）+ 字体档 getter 体系 + 自选股过滤。
- R3 Push Kit 实装（09-16 06:26）：`pushService.getToken()` 带错误码重试（PushService.ets:15-17 定义可重试错误码 1000900001/0008/0009/0011，最多 3 次），AGC 探针失败仍降级（PushService.ets:100-107）。
- Navigation 迁移（09-17 01:15）：router.pushUrl 在 API 12+ 已 deprecated，改为 Navigation + NavPathStack。
- 适老化模式/夜间白天/免打扰/自主优化 5 项（09-17 至 09-18）。

### 阶段三：云端后端期（09-20 至 09-21，砚坚席）

09-20 09:40 搭建 CloudBase 后端：4 个 PostgreSQL 表 + 4 个云函数（fetch-tushare-data / generate-tts / broadcast-a2a / get-alerts）+ tts 存储桶 + 每分钟 cron 触发器。09-21 发现 PostgreSQL 从未真正连通（`PG_CONN_STRING` 从未配置），**整条持久层迁移到 CloudBase 存储服务的 alerts.json**（详见 H2 复盘）。端侧 FEED_URL 从本地占位地址切到 CloudBase HTTP 端点（SettingsService.ets:24-27）。

### 阶段四：治理与合规期（09-22 至 09-23）

GLM-5.3-Flash 1 亿 Token 燃烧窗口内完成 14 文件全量审查（7 项问题：2 高危+5 低危）、P0-P2 修复（SDK 单例化、requestHttps 统一封装、alertId 去随机化、东方财富并行化、broadcast-a2a 鉴权）、DKnowC 合规层集成、技能文档批量铸炼（索引 5→8 项再扩至 28 项自建技能）。

## 三、端侧架构分层（现状实录）

当前端侧共 8 个 .ets 文件，职责切分如下（均经本次复盘逐文件走查）：

| 文件 | 行数 | 职责 | 关键锚点 |
|---|---|---|---|
| entryability/EntryAbility.ets | 123 | 生命周期枢纽 | onCreate 中 Push/Settings 初始化（16-22 行）+ 冷启动 alertId 补检（25-28 行）+ DEFAULT 场景化消息接收器（83-105 行）；onNewWant 处理通知点击与小艺 A2A action（43-69 行） |
| pages/Index.ets | 458 | 卡片流主页 | DEMO_ITEMS 演示卡（13-23 行）；7 个字号 getter（51-71 行）；6 个适老化布局 getter（74-91 行）；pollLoop 递归 setTimeout（146-149 行）；refresh 自选股过滤与播放态守卫（151-200 行） |
| services/AlertPoller.ets | 97 | 前台 5s 轮询 | 退避三态：429 静默、5xx 普通失败、JSON 解析失败记原文前 200 字符（44-76 行） |
| services/PushService.ets | 108 | Push 封装 | probeAgcConfig 读 rawfile 探针（100-107 行）；getToken 重试；reportToken 失败仅记日志 |
| services/AudioPlayer.ets | 64 | TTS 播放 | AVPlayer stateChange/error 双监听；prepare/play 失败清理半初始化 player（40-52 行） |
| services/SettingsService.ets | 462 | Preferences 持久化 | 12 个键；CLOUDBASE_BASE_URL 唯一定义点（24 行）；已读 200 条/播报历史 50 条上限 |
| pages/Settings.ets | 557 | 设置页 | 适老化开关联动字体档；免打扰时段 ± 小时调整 |
| model/AlertItem.ets | 22 | 数据契约 | alertId/ts/symbol/name/direction/kind/headline/detail/audioUrl/complianceStatus |

分层原则是「页面管状态、服务管副作用、模型管契约」：Index.ets 不直接发 HTTP，AudioPlayer 不持有业务状态，全部跨层通信走 AppStorage 的 `pendingAlertId` 这一个媒介。

## 四、关键决策点复盘

**决策 1：双通道降级——Push 为主、轮询为底。** Push 依赖华为 AGC 平台审批（订阅通知自分类约 15 个工作日，README 第 85 行），而产品不能等审批。解法是把 AlertPoller 做成完整可用的第一公民而非备胎：5s 间隔、退避封顶 30s、429 限流静默跳过（AlertPoller.ets:44-49）。这个决策让 App 在无推送的整个审批期保持功能完整。

**决策 2：首屏永不空白的 DEMO_ITEMS。** 初始 `items = DEMO_ITEMS`（Index.ets:28），演示卡 headline 前缀「示例：」、detail 写明「示例数据，服务器接通后自动换成真实异动」（Index.ets:20-21）。这解决了「长辈打开 App 看到白屏」的信任问题——宁可给标注清楚的假数据，不给真空。配套的 `isDemoMode` 状态与空态分支（「今日暂无异动」）严格区分三种情况：演示、连通无异动、连接中断。

**决策 3：AlertFeed 契约作为组织边界。** AGENTS.md §一规定接口边界 =「本文件 + AlertItem.ets」，任何一方改契约须先在 CHANGELOG 写明意图并停机主确认。这条规则让端侧（码道席）与服务端（顾权席）可以并行开发而互不阻塞——契约 22 行，是全工程被 git diff 检查次数最多的文件（R1/R2/R3/V19 多次验证 diff 为空）。

**决策 4：持久层从 PostgreSQL 迁到 CloudBase 存储。** 09-20 的 PostgreSQL 设计（4 表 + RLS）在纸面上更规范，但 `PG_CONN_STRING` 从未配置，六个备选方案实测全部失败后，改用存储服务的 alerts.json（读改写合并 + serverTs 版本号防并发覆盖）。这是「能用胜过好看」的一次务实转向，代价是放弃了 SQL 查询能力（详见 H2）。

**决策 5：字号与布局全走 getter 派生。** Index.ets 不存任何字号常量，`titleSize()` 等 7 个 getter 从 `fontLevel` 派生（Index.ets:51-71），`cardSpace()` 等 6 个 getter 从 `elderlyMode` 派生（74-91 行）。切换适老化模式时只需改一个 Preferences 键，14 个布局参数联动。这个模式后来被 09-23 端侧审查判定为 0 问题文件的基础。

**决策 6：零三方依赖。** `oh-package.json5` 的 dependencies 为空对象（R3 验证 V9）。HTTP 用 @kit.NetworkKit、播放用 @kit.MediaKit、持久化用 @kit.ArkData、推送用 @kit.PushKit——全部系统 Kit。收益是构建链路极简（devecocli 一条命令）且不受 npm 供应链影响；代价是所有封装都要自己写，于是有了 8 个自建服务类的代价。

## 五、技术选型理由归纳

- **纯 ArkTS + Stage 模型**：目标机型 Mate X5 纯血 HarmonyOS NEXT，FA 模型已非主线；ArkTS 严格模式倒逼类型完备（catch 必须带参数等约束在 R2 中专门查证过官方文档）。
- **AVPlayer 而非音频 SDK**：需求只是「播云端 URL」，AVPlayer 的 prepare/play/stateChange 生命周期足够，AudioPlayer.ets 全部 64 行。
- **Preferences 而非数据库**：端侧只有 12 个设置键和两条小列表（已读 200 条、历史 50 条），键值存储天然够用且免初始化成本。
- **CloudBase 云函数 + 定时触发器**：每分钟 cron（`0 * * * * * *`）驱动 fetch-tushare-data，免运维常驻服务器；HTTP 访问服务让 Event 函数直接暴露成 REST 端点供 AlertPoller 轮询。
- **Navigation 而非 router**：跟随官方推荐栈，避免 deprecated API 在 targetSdk 26 下告警。

## 六、架构质量验证与遗留

质量抓手是 CHANGELOG 强制的「如何验证」段：每个条目带 V1-V19 编号的可复制 grep/代码走查命令（如 R2 的 V9-V11 全部给出了 grep 命令序列）。09-23 端侧 8 文件审查结论为 0 P0、1 P1、6 处 P2 轻微项，AGENTS.md 硬约束 7 条全部通过（CHANGELOG 2026-09-23 10:30 条目）。

如实登记的遗留：模拟器/真机验证始终阻塞（DevEco Studio 6.0.2 < devecocli 要求的 6.1.0），全部 V 系列验证为代码走查而非实跑；签名配置待机主；AGC P5 审批待华为；X 服务器未落地，FEED_URL 指向 CloudBase 过渡端点。另有一处口径差异需机主定夺：AGENTS.md §二.1 写「28-34fp」，而 Index.ets:52 特大档标题字号为 40fp（正文 headline 特大档 34fp 在界内）——文档口径与实现存在上界差异。

## 七、可迁移的架构经验

1. **约束先行**：把不可谈判的产品红线写成 AGENTS.md 硬约束，架构搜索空间收窄后决策速度快一个量级。
2. **降级即一等公民**：外部依赖（推送、审批、数据源）全部设计成「缺席时功能仍完整」的形态。
3. **契约即边界**：多团队/多 AI 协作时，数据契约文件是唯一需要共管的文件，其余按目录分权。
4. **派生优于存储**：UI 参数全部由少数状态键派生，消除状态不一致类 bug。
5. **验证入账**：每个改动附可复制的验证命令并写入 CHANGELOG，使代码走查可以跨会话复演。

### 自我评估
- 正确性：4分 全部结论取自本会话逐文件阅读的源码与 CHANGELOG/AGENTS/README 原文，路径行号可复核；个别历史细节（如各条目时间顺序）以 CHANGELOG 记载为准，未做 git 考古交叉验证。
- 完整性：4分 覆盖需求→四阶段演进→分层实录→六大决策→选型理由→遗留；对构建链路细节（CodeArts 云构建）仅概述。
- 可复用性：5分 面向新席位/新成员的架构导览，自包含、路径化引用、附可迁移经验清单。
- 字数：约4150字
- 使用模型：GLM-5.3-Flash
