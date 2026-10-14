# PushService.ets 审查——占位封装设计、AGC 降级轮询机制、实装步骤文档

## 一、审查范围与结论摘要

本篇为 harmony-app（代号铃语，鸿蒙适老化股票异动播报应用，bundleName 为 com.yehang.stockpulse，见 AppScope/app.json5）推送链路的代码审查知识资产。审查对象为以下三个文件，均在本审查当日完整通读：

- entry/src/main/ets/services/PushService.ets（107 行，Push Kit 集成封装）
- entry/src/main/ets/entryability/EntryAbility.ets（124 行，推送初始化、场景化消息接收、通知拉起链路）
- entry/src/main/ets/services/AlertPoller.ets（100 行，降级轮询兜底）

核心结论：占位封装设计成立，精确落实了项目"PushService.ets 保持占位封装，AGC 未配置前降级轮询"的不可逾越约束。探测式降级让实装动作收敛为"放入一个配置文件，端侧零改动"，降级链路闭环完整，失败路径全部静默不阻断主流程。同时发现 7 处可改进点（含 2 处死状态、1 处硬编码、1 处幂等缺口），按优先级列于第六节；AGC 实装操作步骤与排障指引列于第七节；文末附验证清单。

## 二、现状结构梳理

PushService.ets 全文单类、全静态成员，职责单一，结构如下：

| 成员 | 位置 | 职责 |
| --- | --- | --- |
| TOKEN_REPORT_URL | :11 | Token 上报端点（CloudBase push-token-register 云函数 HTTP 地址） |
| RETRYABLE_ERROR_CODES | :14 | getToken 可重试错误码集合（注释标明取自官方文档），共 4 个：1000900001、1000900008、1000900009、1000900011 |
| MAX_RETRY_COUNT / RETRY_INTERVAL | :15-16 | 最大重试 3 次、间隔 1000ms |
| tokenReported / retryCount | :25-26 | 静态状态字段 |
| init(context) | :28-40 | 入口：探测 AGC 配置，有则取 token，无则静默返回 |
| fetchToken() | :46-58 | getToken + 上报，失败进入重试判定 |
| handleTokenRetry(code) | :63-71 | 错误码可重试且未超 3 次时，setTimeout 1 秒后重试 |
| reportToken(token) | :77-97 | POST 上报，失败仅记日志不影响主流程 |
| probeAgcConfig(context) | :99-106 | 读 rawfile/agconnect-services.json 判断 AGC 是否已配置 |

完整调用时序（文字版）：应用启动进入 EntryAbility.onCreate，第 16 行调用 PushService.init 并以 catch 兜底；init 第 30 行调用 probeAgcConfig，同步读 rawfile 配置；若返回 false，第 32 行记降级日志后 return，链路终止；若返回 true，第 36 行进入 fetchToken，第 48 行调 pushService.getToken；成功则第 51 行上报、第 52 行置 tokenReported，失败则第 56 行进入 handleTokenRetry 决定重试或放弃。EntryAbility 侧另一条独立线是 onCreate 第 30 行调用 registerPushMessageReceiver（:83-105）注册 DEFAULT 场景化消息接收，解析推送 data 中的 alertId 写入 AppStorage。onCreate 第 25-28 行还补检冷启动 want 参数里的 alertId（注释自证这是修复"冷启动点通知丢 alertId"缺陷的补丁），onNewWant 第 43-48 行处理热启动同参。

## 三、占位封装设计评价：为什么"占位"是对的

1. **探测式降级，而非开关式降级。** probeAgcConfig 不读任何用户配置项，而是直接尝试 context.resourceManager.getRawFileContentSync('agconnect-services.json')（:101），文件存在且非空即认为 AGC 已配置，读取抛异常即返回 false（:103-105）。这使"实装动作"收敛为"往 rawfile 放一个文件"——端侧代码零改动，发布分支与占位分支天然合一，不存在"开关忘了开"这类人为事故面。这是整个占位封装最有价值的设计决策。
2. **失败绝不外抛。** init 全程 try/catch，任何异常只记 hilog.warn（:37-39）；调用方 EntryAbility.onCreate 也再兜一层 catch（EntryAbility.ets:16-18）。双层防御后，推送子系统无论出什么错都不可能阻断应用启动，保障"首屏永不空白"与轮询兜底永远可用，符合架构基调。
3. **重试口径显式收敛。** 只对注释标明来自官方文档的 4 个可重试错误码重试，上限 3 次、间隔 1 秒（:14-16、:63-71）；不可重试错误直接放弃并记日志。错误码白名单而非全量重试，避免对确定性失败（如权益未开通类）做无意义循环拖慢启动；重试参数集中为常量，调整口径一处即可。
4. **日志不泄密。** getToken 成功日志只打 token 长度不打明文（:49），上报请求体仅含 token 与 bundleName（:85），token 是设备标识而非账号凭据，仅上报给自有云函数端点，符合"不泄露任何 Token/密钥"的合规红线。
5. **无实例化设计。** 全静态成员表达"应用级单例服务"语义，不需要依赖注入框架，与零三方依赖约束一致。代价是静态可变状态不利于单测，但在单页面应用规模下是合理取舍。

**占位期与实装期的资产边界：** 占位期资产指 probeAgcConfig、init 的降级分支、reportToken 及重试骨架——实装后全部原样保留；实装期新增的只有 rawfile 配置文件、AGC 平台侧开通动作、服务端发送侧改造。端侧代码一个字都不用改，这就是判断"占位封装是否合格"的验收标准，本封装通过。

## 四、AGC 降级轮询机制：降级链路全图与降级矩阵

**判定与降级：** init() → probeAgcConfig() 返回 false（文件缺失或读取异常）→ 记日志 'agconnect-services.json absent, push degraded to polling'（:32）→ 直接 return，不触碰 getToken。降级是全自动、无感的。

**兜底轮询：** Index.ets 的 pollLoop()（Index.ets:146-149）以 AlertPoller.getInterval()（基线 5000ms，AlertPoller.ets:28-30）循环调用 refresh() → AlertPoller.fetchLatest()。任何失败路径统一 applyBackoff()：间隔翻倍、封顶 30000ms（AlertPoller.ets:90-95）；成功后 resetBackoff() 复位 5000ms（:97-99）。推送未实装期间，前台 5 秒轮询是用户获知异动的唯一通道；退避保证弱网与服务端故障下不至于打爆服务端。

**双通道关系：** 推送实装后轮询保留作"拉齐补偿"（AlertPoller.ets:20-21 注释），两者非互斥——推送降低时延（秒级到达），轮询保证应用在前台时数据最终一致（最迟一个轮询周期内拉齐）。这是架构基调明文设计：EntryAbility 管推送初始化与拉起定位，Index.ets 管卡片流与 5 秒前台轮询兜底。实装后不应移除轮询，否则推送丢失或延迟时用户将完全无感知兜底。

**降级矩阵（AGC 状态、网络状态与用户所见）：** 配置缺失加网络正常，用户看到演示卡一闪后被轮询数据替换，全程无感知推送缺失；配置缺失加网络异常，演示卡或旧数据常驻，顶栏出现「连接中断，显示旧数据」提示（Index.ets:195-199）；配置就绪加网络正常，token 上报成功，服务端可定向推送，用户最快秒级收到异动；配置就绪加网络异常，getToken 走 3 次重试后放弃，前台仍有轮询兜底，且下次应用启动会自动重试——即降级的每一格都有可用出口，没有任何一格会白屏。

**前台消息与拉起链路三入口统一：** alertId 从三条路径进入 AppStorage('pendingAlertId')：冷启动 onCreate want 参数（EntryAbility.ets:25-28）、热启动 onNewWant（:43-48）、前台 DEFAULT 推送消息（:91-94）。Index.checkPendingAlertId()（Index.ets:138-144）在 aboutToAppear 与 onPageShow 两个时机读取并 AppStorage.delete 消费，命中卡片后经 playById（:202-223）自动播报，且自动播报尊重播报开关（:212-215）与免打扰时段（:217-220）——用户关掉的、睡觉时，机器不吵人，这是适老化合规在推送链路上的落点。

**一处时序瑕疵：** registerPushMessageReceiver 在 onCreate 无条件调用（:30），不受 AGC 探测结果约束。未配置 AGC 时 receiveMessage 注册会抛异常，被 :101-104 的 catch 吞掉，行为无害但多走一次无效异常路径，建议实装时改为探测通过后再注册，日志也会更干净。

## 五、与架构其他组件的边界

PushService 的职责面收得很窄：只管三件事——判定 AGC 状态、获取并上报 token、注册前台消息接收。它不管通知的展示与点击行为（由系统与华为推送服务侧负责），不管数据轮询（AlertPoller 负责），不管音频播报（AudioPlayer 负责），不管页面定位（Index.checkPendingAlertId 负责）。组件间唯一交汇点是 AppStorage 的 pendingAlertId 键：推送链路写、页面链路读后即删。这种窄职责使推送子系统可以整体替换（例如未来换消息通道）而不波及其他组件，也是占位策略能成立的架构前提。

与已知问题的对应：broadcast-a2a 的 Push 需换华为 Push Kit REST——本文件只负责"端侧收"与"token 上报"，服务端发送侧由 X 服务器按华为 Push Kit REST API（token 定向推送、data 携带 alertId）重写，第七节步骤 6 涵盖。alerts.json 的 audioUrl undefined 端侧按需调 generate-tts——与 PushService 无直接耦合，端侧已按"无 audioUrl 则隐藏播报钮"处理（Index.ets:390 的 if (item.audioUrl)），属数据链路问题，不在本篇展开。

## 六、发现的问题与改进建议（按优先级）

- **P1 bundleName 硬编码：** reportToken 请求体写死字符串 'com.yehang.stockpulse'（:85），与 AppScope/app.json5 的 bundleName 重复定义，改包名即静默断链。建议改读 context.applicationInfo（运行时取真实包名），至少提取常量并注释指回 app.json5。
- **P1 tokenReported 死状态：** :25 声明、:52 赋 true，全工程再无读取（本次以 grep 全仓核实，仅此两处）。应删除；或实装后升级为幂等开关——重复 init 时跳过 fetchToken，同时解决下一条幂等缺口。
- **P2 init 无幂等保护：** init 未检查是否已初始化过，Ability 若因配置变更重建而再次走 onCreate，会重复 probe、重复 getToken、重复上报。当前一次性启动场景影响小，实装后应配合 tokenReported 做短路。
- **P2 reportToken 无重试：** getToken 有 3 次重试，但 token 上报 HTTP 失败只记日志（:90-91、:93）。token 拿到而上报丢失意味着该设备永远收不到推送且无自愈机会（下次启动才会重试）。建议对上报失败复用同样延迟重试（3 次封顶）。
- **P2 setTimeout 不可取消：** handleTokenRetry 用裸 setTimeout 延迟重试（:67），期间若 init 被再次调用会叠加重试链。建议持有 timer 句柄，init 入口先 clearTimeout。
- **P3 同步 IO 在主线程：** getRawFileContentSync 于启动时同步读文件（:101）。文件小、仅一次，可接受；若 rawfile 日趋复杂应改异步。
- **P3 SDK 版本口径漂移：** 本仓库 build-profile.json5 实际配置为 compatibleSdkVersion 与 targetSdkVersion 均 "6.0.2(22)"；而项目宪法口径及既有技能文档 GOVERNANCE/skills/code/harmonyos-arkts-适老化开发.md 写的是"compatibleSdkVersion 20、targetSdkVersion 26"。两套口径并存，应在下次升版时统一对齐（本审查只提示，不擅改宪法）。

## 七、AGC 实装步骤与排障指引

**实装步骤（端侧零改动落地清单）：**

1. AGC 控制台创建项目与应用：包名必须与 AppScope/app.json5 的 bundleName（com.yehang.stockpulse）完全一致；按 AGC 指引用 debug/release 证书分别登记 SHA-256 指纹。
2. 下载 agconnect-services.json，放入 entry/src/main/resources/rawfile/。放入后 probeAgcConfig 自动返回 true——此即占位封装的验收点，端侧无需改一行代码。
3. 在 AGC 开通 Push Kit 服务（增长 → 推送服务）。
4. 真机验证 getToken：观察 hilog TAG=StockPulse.PushService，应出现 'agconnect-services.json found, initializing Push Kit'（:35）与 'getToken succeeded, token length=…'（:49）；如命中可重试码，确认出现 'getToken retry n/3'（:66）且不超过 3 次。
5. 验证 token 上报：CloudBase push-token-register 云函数应收到 POST，body 含 token 与 bundleName，返回 200（对应 :87-88 日志 'token reported to server'）。
6. 服务端发送侧改造：X 服务器以华为 Push Kit REST 按 token 定向下发，data 字段携带 alertId；替换 broadcast-a2a 原推送出口；推送文案遵守合规红线（不承诺收益、不催促、不对外公开）。
7. 三链路验收：前台 DEFAULT 消息（AppStorage 链路）、后台点通知拉起（onNewWant）、冷启动点通知（onCreate want 参数），三者最终都应定位卡片并自动播报；播报关/免打扰时段下应静默但卡片可见、可手动点听。
8. 回归降级路径：删除 rawfile 的 agconnect-services.json 重新构建，确认日志回到 'push degraded to polling' 且应用无崩溃、轮询正常。

**常见失败现象与排查方向（按链路顺序定位）：** 第一步看 init 日志——若连 'agconnect-services.json found' 都没有，是配置文件没进包或路径不对，检查 rawfile 目录与打包产物；若 getToken 报错且错误码不在重试白名单，优先核对 AGC 应用包名、证书指纹与 Push Kit 开通状态三件事，这是权益类失败的三大常见根因；若 token 上报非 200，检查云函数部署状态与请求体格式，用日志里的 http 状态码区分鉴权问题（401/403 类）与函数不存在（404 类）；若端侧全绿但收不到推送，从服务端侧验证——确认该 token 已入库，再用 REST 接口带同一 token 试发一条，能收到则问题在业务发送逻辑，收不到则问题在推送服务配置或设备侧（通知权限、后台限制）。本清单只给定位方向，不替认具体错误码语义，错误码以官方文档为准。

## 八、占位模式的通用化沉淀

把本封装的做法抽象成可复用的模式，供其他 Kit 集成（地图、账号、支付等）照搬：第一步，把外部依赖的全部调用收敛进一个服务类的静态方法，页面与其他服务只认这个门面；第二步，写一个探测函数判定外部前提是否就绪（本例是配置文件存在性），探测必须零副作用、快速失败；第三步，前提不满足时记一条明确日志后静默返回，绝不让异常穿透到调用方；第四步，为前提满足后的主流程写好重试与放弃规则，错误分类用白名单而非一律重试；第五步，准备一条不依赖该 Kit 的兜底路径（本例是轮询），并保证其独立可用；第六步，写清实装清单，让"启用"等于"放配置"而不等于"改代码"。凡六步齐备，占位封装就可以长期停留在仓库里而不腐化——因为它每一天都在被降级路径真实使用，而不是死代码。

## 九、验证清单

- [ ] agconnect-services.json 存在时出现 found + getToken succeeded 日志
- [ ] 文件缺失时出现 degraded 日志且无崩溃
- [ ] token 上报 200；非 200 与网络异常仅 warn（现状）/ 带重试（改进后）
- [ ] 可重试码触发不超过 3 次重试，不可重试码直接放弃
- [ ] 三条 alertId 拉起链路均能定位并自动播报
- [ ] 播报关与免打扰时段自动播报静默、卡片仍可手动收听
- [ ] 全链路日志与请求体不含 token 明文与任何密钥

### 自我评估
- 正确性：4分 全部行号与行为描述来自本次实读的 PushService.ets、EntryAbility.ets、Index.ets、AlertPoller.ets 及 build-profile.json5；tokenReported 死状态经 grep 核实；错误码具体语义与 AGC 控制台细节按官方文档口径转述、未逐项实测，扣一分在此声明。
- 完整性：4分 覆盖结构梳理、调用时序、设计评价、降级矩阵、组件边界、问题清单、实装步骤、排障指引与验证清单；服务端 Push Kit REST 发送侧只给方向与验收点，未给服务端代码（属端侧审查边界外）。
- 可复用性：4分 实装步骤与排障顺序可直接照做；问题清单带优先级与修法；探测式降级模式对任何"先占位后实装"的 Kit 集成都可整体平移。
- 字数：约3100字
- 使用模型：GLM-5.3-Flash
