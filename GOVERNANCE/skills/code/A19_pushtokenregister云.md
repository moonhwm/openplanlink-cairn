# A19｜push-token-register 云函数审查——Push Token 注册流程、存储、更新机制

> 项目：harmony-app（铃语，鸿蒙适老化股票异动播报）。本篇自包含成文，结论全部来自本仓库源码逐行通读，引用给路径与行号；华为 Push Kit token 生命周期相关行为处标注"以华为官方文档为准"。

## 一、审查范围与端侧契约

审查对象：`cloudfunctions/functions/push-token-register/index.js`（95 行，全文通读）与同目录 package.json（仅依赖 `@cloudbase/node-sdk ^3.0.0`）。参照物：部署配置 `cloudfunctions/cloudbaserc.json`（push-token-register 段：Nodejs18.15、timeout 10 秒、无环境变量）；端侧唯一调用方 `entry/src/main/ets/services/PushService.ets`（107 行）；下游消费方 `cloudfunctions/functions/broadcast-a2a/index.js`（293 行）；建库方 `cloudfunctions/functions/init-db/index.js`。

端侧契约（PushService.ets:11、80-86）：POST 到 `https://a2a-commonwealth-d2eepjr928e9c4d-1475054847.ap-shanghai.app.tcloudbase.com/push-token-register`，`Content-Type: application/json`，body 为 `{ token, bundleName: 'com.yehang.stockpulse' }`。超时 connect/read 各 5000ms，失败仅记日志不影响主流程（PushService.ets:77-97）。云函数头注释（index.js:9-12）声明同一契约，两侧一致。

## 二、注册流程审查

### 2.1 现有流程逐步拆解

main（index.js:72-92）：解构 `event.token/bundleName` → 非空校验（77-83）→ 调 `registerToken`（85-87）→ 返回 `{success, action, docId}`。`registerToken`（index.js:21-52）：`where({token}).get()` 查重 → 命中则 `doc(docId).update({lastReportTs, updatedAt})` 并返回 action='updated'（31-40）→ 未命中则 `add({token, bundleName, createdAt, lastReportTs, active:true})` 返回 action='created'（42-51）。日志对 token 做 `substring(0,20)` 脱敏（38、50）——脱敏意识正确。

event 解析的一个前提值得固化：该函数经 HTTP 访问服务触发，端侧以 `application/json` 请求体提交，CloudBase 会把 JSON body 解析后作为 event 传入（端侧 PushService.ets:84 已正确设置该头）。若未来有非 JSON 调用方直连，`event.token` 将恒为 undefined 并落入 77 行的校验拒绝——这是当前实现能安全兜住的形态，但应在文档里写明"只接受 JSON body"，避免后人改契约时踩空。

### 2.2 流程缺陷清单

1. **无 token 格式校验**：任何非空字符串都入库。华为 Push Kit 的 token 是定长格式串（以官方文档为准，长度量级在百字节），至少加长度区间与字符集校验，把脏数据挡在门外。
2. **无 bundleName 白名单**：端侧恒传 `com.yehang.stockpulse`（PushService.ets:85），服务端却接受任意值。加白名单一行代码即可把"任意第三方构造的注册请求"挡掉大半。
3. **查重-插入非原子**：29 行查重与 43 行插入之间存在竞态窗口。同一设备并发上报（如冷启动 PushService.init 与用户手动触发并存）、或两端网络重发，都会造出重复 token 文档。后果：broadcast-a2a 推送时同 token 收双份通知——对适老化用户是"铃响了两次"的体验事故。
4. **无频控**：公网可无限频调用，虽只写库不发推送，但可灌满集合。
5. **重复注册的更新语义偏弱**：重复路径只刷新 lastReportTs/updatedAt（34-37），不刷新 bundleName、不累计 reportCount——bundleName 理论上不变，可接受；但缺 reportCount 使后续"活跃设备统计"无从做起。

修复示例（2.2-3 的原子化，两选一）：

```js
// 方案A：token 指纹作主键的幂等 upsert（推荐，配唯一索引见 A18 篇四）
const fingerprint = crypto.createHash('sha256').update(token).digest('hex').substring(0, 16);
await collection.doc(fingerprint).set({   // set 为整文档覆盖写，天然幂等
  token, bundleName, active: true,
  createdAt: new Date().toISOString(),
  lastReportTs: Date.now(),
}, { upsert: true });                     // node-sdk doc().set upsert 能力以官方文档为准
// 方案B：保留查重-插入，但 token 建唯一索引，插入冲突时捕获后转 update
```

## 三、存储审查

### 3.1 集合与字段现状

存储集合 `push_tokens`（index.js:26）。**交叉发现（与 A18 篇联动）**：init-db 的集合清单是 `['alerts','user_stocks','user_preferences','tts_cache']`（init-db/index.js:15），**不含 push_tokens**——而全仓库唯一真正被读写的集合恰是它（push-token-register 写、broadcast-a2a/index.js:122 读）。新环境部署时 push_tokens 只能手工建，漏建则注册链路直接报错。这是存储层的 P0 修复项：要么把 push_tokens 加进 init-db 清单，要么控制台立即手工创建。

字段现状 `{token, bundleName, createdAt, lastReportTs, active}`。评估：最小可用，缺三样——设备维度（同一账号多设备/重装场景无法区分）、上报次数、失效原因记录。建议的目标结构已在 A18 篇 3.2 给全（tokenFingerprint 主键/deviceModel/reportCount/lastPushError），此处不重复，只强调一条原则：**token 明文存库可以接受**（它是推送地址不是密钥，合规红线管的是 API key/secret 一类凭证），但日志脱敏（现有 substring(0,20)）与集合权限收紧（安全规则禁止客户端直读，只留云函数管理态）必须配齐，防止 token 集合被第三方拉走后定向推垃圾消息。

### 3.2 查重查询的成本

`where({token}).get()` 无索引时全集合扫描（A18 篇四已列 token 唯一索引方案）。当前设备量个位数无感；该查询也可换成 `where({token}).count()` 先判存在再操作，但不如直接上唯一索引 + upsert 一劳永逸。

## 四、更新机制审查

### 4.1 更新路径现状

现有更新只有一条：重复 token 刷 lastReportTs（2.1）。缺失的三条更新路径才是本函数的核心欠账：

1. **失效回收（对端是华为侧错误码）**：Push Kit 的设备 token 在卸载重装、清除应用数据等场景会失效/更换（以华为官方文档为准）。失效 token 留在库中且 active:true，broadcast-a2a 每次广播都会向它发推送（broadcast-a2a/index.js:186-204），华为侧返回失败错误码，白白消耗推送配额并污染日志。正确闭环：broadcast-a2a 推送失败且错误码属"token 无效"类时，回写该 token 的 active:false；本函数应暴露这一能力（加 `deactivate` 动作或单独函数），并配一个按 lastReportTs 的定时清理（如 90 天未上报置 inactive——设备长期不打开 App 时其 token 不值得继续推）。
2. **重装换 token 的收敛**：同一设备重装后产生新 token，旧 token 若只靠"推送失败回收"会有一个广播周期内的双推窗口；若端侧在上报时附带旧 token（或设备唯一标识）做关联迁移，可即时 deactivate 旧档。当前端侧 PushService.ets 未传设备标识，属可选优化，非必须。
3. **active 标志的写入入口**：现库中 active 恒为 true（index.js:48），无任何代码会写 false——"支持 token 过期更新与设备去重"（index.js:7）这句头注释承诺的能力，实际只落地了去重的一半。

### 4.2 getActiveTokens 导出无效（代码级确认）

index.js:58-67 定义并第 95 行导出 `getActiveTokens`，注释称"供 broadcast-a2a 云函数调用"。**这个导出在跨函数场景下不可达**：callFunction 只能触发目标函数的 main 入口（event/context 传入 main），无法调用其模块级导出；而 broadcast-a2a 的实际实现也确实没走这条路，是直接查库（broadcast-a2a/index.js:119-123）。结论：`exports.getActiveTokens` 是死代码，且注释有误导性。处置：删除导出或改注释为"供函数内/未来 HTTP 查询用"；若真要做跨函数读 token，保持现状直查库即可（同库低频读，无需中转一跳）。

## 五、鉴权与滥用防护

该函数是全仓库攻击面最宽的入口之一：公网可达、无鉴权、无频控、写入不可逆（只增不减）。最现实的攻击是垃圾注册——灌入大量伪造 token，broadcast-a2a 广播时全部携带（broadcast-a2a/index.js:183 `token: deviceTokens` 是数组整体下发），华为侧对无效 token 返回错误，虽然不至于推送成功，但会持续烧推送配额并触发华为侧风控（以官方文档为准）。防护组合拳（按性价比排序）：

1. bundleName 白名单（2.2-2，一行）；
2. token 格式校验（2.2-1，两行）；
3. 单 token 上报频控：同 fingerprint 一小时内重复上报直接短路返回成功（既防刷又符合"端侧每次冷启动都上报"的真实频率——冷启动上报本就该幂等短路）；
4. 可选：HTTP 访问服务层对 /push-token-register 路径限流，与 get-alerts 的限流策略统一配置。

合规面核对：本函数无任何密钥/凭证处理（依赖 CloudBase 管理态鉴权），日志脱敏已有，白名单校验后也不会成为对外公开的数据通道——满足共享红线"不泄露任何 Token/密钥、不涉对外公开"。

## 六、端侧协同与降级链路

注册链路的完整生命周期（端侧视角，供联调对照）：EntryAbility.ets:16 冷启动调 PushService.init → probeAgcConfig 探测 agconnect-services.json（PushService.ets:99-106）→ **AGC 未配置则静默降级为轮询**（PushService.ets:31-33，本函数零流量，符合共享约束"PushService 保持占位封装，AGC 未配置前降级轮询"）→ 配置到位则 getToken（46-58）→ 可重试错误码（1000900001 等四种，第 14 行）最多 3 次、间隔 1s（14-16、63-71）→ reportToken POST（77-97）。两侧超时对齐检查：端侧 readTimeout 5000ms（PushService.ets:84），云函数 timeout 10 秒（cloudbaserc.json）——端侧会先超时，云函数还在跑完注册，结果不丢只是端侧不确认，语义安全。但有一个真实缺口：**reportToken 失败后无补报机制**（PushService.ets:89-91 仅记日志，tokenReported 置 false 后无人再触发），冷启动恰逢弱网则该设备在下次冷启动前收不到推送。建议端侧补一条：上报失败把 token 存入本地 Preferences，下次任意时机（前台恢复/轮询成功后）重试一次——改动小，收益直接。

另核对 broadcast-a2a 的容错衔接：云函数读库失败时有 env 单 token 兜底（broadcast-a2a/index.js:124-129 的 HUAWEI_PUSH_TOKEN），注册链路故障不会立即断推送——这是链路上现成的降级设计，保持即可。

## 七、修复优先级清单

| 级别 | 事项 | 位置 | 依据 |
|---|---|---|---|
| P0 | push_tokens 纳入 init-db 清单（或控制台立即建集合） | init-db/index.js:15 | 3.1，链路建库缺失 |
| P0 | bundleName 白名单 + token 格式校验 | index.js:75-83 | 2.2-1/2、五 |
| P1 | token 唯一索引 + 指纹主键 upsert 消竞态 | index.js:21-52；A18 篇四 | 2.2-3，双推事故 |
| P1 | 失效回收：broadcast 推送失败回写 active:false + 90 天未上报清理 | index.js（新增 deactivate）；broadcast-a2a/index.js:195-201 | 4.1-1 |
| P1 | 单 token 频控短路 | index.js:main | 五-3 |
| P2 | 字段扩展 reportCount/deviceModel/lastPushError | index.js:43-49 | 3.1 |
| P2 | 删除 getActiveTokens 死导出或改注释 | index.js:58-67, 94-95 | 4.2 |
| P2 | 端侧补报机制（失败 token 本地暂存重报） | PushService.ets:77-97 | 六 |
| P3 | 集合安全规则收紧（禁客户端直读写） | 控制台 | 3.1 |

## 八、未实测项

未做：云端实调（无测试设备 token，无法验证注册-推送全链路）；华为 Push Kit 失效错误码的具体码表（"推送失败回写 inactive"的匹配规则需按官方文档施工，本文只定机制不定码表）；node-sdk doc().set 的 upsert 支持形态（方案A 施工时以官方文档为准，方案B 为保底路径）。以上均如实标注，未作为已验证结论。

## 九、注册流程状态机（含规划态）

把 token 的生命周期画成显式状态机，避免更新机制散落各处后无人看得全貌：

```
[未注册] --端侧冷启动上报--> [active] --推送失败(失效类错误码)--> [inactive]
[active] --90天未上报(清理任务)--> [inactive]
[active] --端侧重复上报--> [active](仅刷lastReportTs，幂等短路)
[inactive] --同token再次上报--> [active](复活：重装后华为可能发同一token)
```

现状只实现了第一条边和第三条边的一半（更新路径，index.js:31-40）；第二条、第四条是第四节列的欠账；第五条复活边是唯一有坑的：如果清理任务已把 token 置 inactive，之后同一 token 重新上报（华为 token 有跨重装复用的可能，以官方文档为准），现有"重复路径"只刷 lastReportTs 而不动 active（index.js:34-37），复活边断死——设备永远收不到推送。修复：重复路径的 update 里加 `active: true` 一并回写。一行改动，堵住状态机的死胡同。

## 十、验收标准（与第七节清单一一对应）

- **P0-建集合**：listCollections 输出含 push_tokens；全新环境下端侧冷启动后日志出现 `Token registered`（index.js:50 的成功分支）。
- **P0-白名单+格式**：bundleName 传 `com.other.app` 返回明确错误；token 传 `abc`（过短）被拒；正常端侧上报仍成功。
- **P1-唯一索引+upsert**：并发 20 次同 token 上报后集合中该 token 恰好 1 个文档；随后上报返回 action='updated' 而非 created。
- **P1-失效回收**：人为写入一个失效 token 并触发 broadcast-a2a，推送返回失效错误码后该文档 active 变为 false，且下次广播不再包含它（broadcast-a2a/index.js:122 的 where({active:true}) 生效）。
- **P1-频控**：同 token 一小时内第二次上报立即返回（日志耗时应为毫秒级，无数据库写放大）；跨小时后恢复写路径。
- **P2-补报机制（端侧）**：飞行模式冷启动→恢复网络→不做新冷启动的情况下，token 最终抵达服务端（Preferences 暂存路径生效）。
- **P2-死导出删除**：grep 全仓库无 getActiveTokens 引用残留。

## 十一、数据治理与合规边界

三件事说清楚：其一，push_tokens 属设备标识数据，集合里没有用户个人信息字段（bundleName 是应用标识、token 是推送地址），合规面干净；但 token 一旦泄露可被用于定向推送骚扰，因此 3.1 的"安全规则禁客户端直读"与日志脱敏（现有 substring(0,20)）是两道必须同时存在的闸门。其二，留存策略：inactive 文档不必物理删除（保留排障线索），但建议 180 天后归档或清理，量级个位数到百位数，无成本压力，纯粹是数据卫生。其三，对账口径：active 数量 = 预期在网设备数，偏差大时优先查垃圾注册（reportCount=1 且 lastPushError 有值的文档），这也是 3.1 建议加 reportCount 字段的排障用途。

## 十二、与广播链路的联调检查单

注册链路的最终价值在链 3（broadcast-a2a）兑现，联调时按序核对五点：①端侧 getToken 成功（PushService.ets:48 有 token.length 日志）；②POST 返回 success:true 且 action 符合预期；③集合中出现/更新文档；④broadcast-a2a 日志显示 `Push sent to N devices`（broadcast-a2a/index.js:197）且 N 等于 active 文档数；⑤端侧收到通知，点击后 onNewWant 拿到 alertId（EntryAbility.ets:43-48）并定位到卡片。任一环断掉，先查第七节 P0 两项——当前最可能的断点是集合未建（3.1），其次是 AGC 三环境变量未配置（此时 broadcast-a2a:111-114 直接跳过推送，日志有明确 skip 字样，属设计内降级而非故障）。

## 十三、性能预算与容量估算（估算值）

链路的时序预算：端侧 connect+read 超时各 5 秒（PushService.ets:82-83），云函数超时 10 秒（cloudbaserc.json）。正常路径耗时构成——SDK 初始化与一次 `where({token}).get()` 查重在无索引时随集合规模线性增长，百级文档估 50-200ms，加唯一索引后降到个位数毫秒；update/add 一次往返同量级；合计远低于 1 秒，10 秒预算裕量充足。容量侧：设备数=活跃用户数，适老化应用量级估十到百；即便按千级设备、每日一次冷启动上报算，日写入千次、集合千文档，count 查询与唯一索引都是毫秒级——**本函数不存在量能焦虑，所有优化（索引、频控）都为正确性与防滥用，不为性能**。这个结论的价值是把后续优化精力从"快"转向"对"：状态机补全（第九节）与失效回收（4.1）比任何查询优化都重要。

## 十四、威胁模型小结（STRIDE 视角的简化版）

针对本入口的四个现实威胁与对应缓解：**伪造注册（Spoofing）**——攻击者灌伪造 token 换取推送资格：缓解=白名单+格式校验（P0）+频控（P1），伪造 token 在华为侧推送时会失败，真正的代价是配额与风控，所以第五节的限流配置是最后闸门；**重复通知（用户侧 DoS 体验）**——竞态双档导致同一设备收双推：缓解=唯一索引+upsert（P1）；**数据投毒（Tampering）**——恶意 bundleName 或超长字段污染集合：缓解=白名单天然限定 bundleName，建议再对 token 长度设上限（与格式校验同批）；**信息泄露（Information disclosure）**——token 集合被拉取后定向骚扰：缓解=安全规则禁直读（P3）+日志脱敏（已有）。列这张表不为形式：四个威胁恰好映射第七节的四组工单，安全项不是附加题而是缺陷单的一部分。

## 十五、返回契约的规范化建议

现状返回三种形态：成功 `{success:true, action:'created'|'updated', docId}`（index.js:39、51）、参数错误 `{success:false, error:...}`（78、82）、内部错误同形态（90）。建议补两个字段使端侧可做无歧义分支：`code`（机器可读：OK/INVALID_PARAM/RATE_LIMITED/DB_ERROR）与 `serverTs`（便于端侧日志对齐）。端侧现状只看 HTTP 200 与否（PushService.ets:87-91），加 code 后未来可在 RATE_LIMITED 时退避重报而不盲目重试。规范化的同时保持向后兼容：新增字段不删旧字段，端侧不升级也不受影响——与 A17 篇增量协议同一条升级纪律：**加字段安全，改语义危险**。

## 十六、与华为 Push Kit 协同的细节核对

注册链路的对端协议细节，逐条与 broadcast-a2a 侧实现核对：其一，token 批量上限——broadcast-a2a 把全部活跃 token 一次放进 `message.token` 数组下发（broadcast-a2a/index.js:183），华为侧对单请求 token 数有上限（以官方文档为准），设备量过百时需分批发送，本函数的 getActiveTokens 若未来真的被启用（4.2 修复后转正或删除），应同步支持分页；其二，推送失败回写的依据——华为侧响应中会逐 token 返回成功/失败及错误码，失效回收（4.1）的匹配规则要对着这个响应结构写，而不是猜错误码；其三，通知点击链路——broadcast-a2a 的 click_action intent 指向 `EntryAbility`（broadcast-a2a/index.js:171-175），data 内联 alertId（:177-182），端侧 EntryAbility.ets:85-95 解析同一份数据——注册链路本身不碰这些字段，但要知道**注册的质量直接决定这些精心构造的 payload 有没有人收到**；其四，本函数与 broadcast-a2a 之间靠 push_tokens 集合间接耦合（无函数间调用），集合 schema 的任何变更（如 3.1 字段扩展）必须两侧同步评审——这是 A20 篇读写矩阵的治理要求在本篇的落地。

## 十七、本函数的"完成态"画像

把全部修复项落实后的目标形态固化，作为重构完成的定义：入口有白名单与格式校验、频控短路毫秒级返回幂等成功；写入走指纹主键 upsert、并发零重复；状态机五条边全通（第九节）、失效由推送结果驱动回收、长期未上报由清理任务收敛；返回体带 code 与 serverTs；集合有唯一索引与组合索引、安全规则禁直读；端侧失败补报兜住弱网窗口。到那时这个函数约 150 行，职责单一（登记设备推送地址）、零外部依赖（只碰 CloudBase 库）、零密钥处理（合规红线天然满足）——它应该是六个云函数里最"无聊"的一个，无聊即正确：**注册这种基础设施工序，全部价值在于可靠，任何趣味都是隐患**。

## 十八、结语

push-token-register 是六个云函数中离"华为设备生态"最近的一环：它登记的每一个 token，都是 broadcast-a2a 精心构造的 notification 能找到收件人的唯一凭据。本篇的审查结论浓缩成三句话：流程对了一半（幂等查重有了，状态机残缺）；存储差一块基石（集合不在初始化清单）；更新机制几乎空白（失效回收与复活路径都未落地）。三件事的修复成本都不高——最高的一件也不过几十行加一个索引——但它们共同决定推送链路从"调试机能响"走向"每台设备都响"。按第七节清单施工，按第十节验收收口，按第十二节联调闭环，这个函数就能达到十七节画出的完成态。

### 自我评估
- 正确性：4分 流程拆解与竞态、死代码、清单缺集合三处发现均有行号级证据；华为侧行为与 SDK upsert 细节如实标注未实测。
- 完整性：4分 覆盖注册流程、存储、更新机制、鉴权防护、端侧协同全链；未展开华为错误码码表与多设备同步方案。
- 可复用性：4分 P0-P3 清单与修复片段可直接施工，与 A18/A20 的联动边界写明；方案A 需按平台文档二次确认。
- 字数：约4400字（正文汉字，实测统计，不含本自评）
- 使用模型：GLM-5.3-Flash
