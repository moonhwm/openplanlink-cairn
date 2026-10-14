# A17｜get-alerts 云函数审查——CloudBase 存储读取优化、缓存策略、降级方案

> 项目：harmony-app（铃语，鸿蒙适老化股票异动播报）。本篇自包含成文，全部结论基于本仓库源码通读，引用给路径与行号；未做云端压测（无环境），量化估算处均标注为估算。

## 一、审查范围与现状画像

审查对象：`cloudfunctions/functions/get-alerts/index.js`（76 行，全文通读）与同目录 package.json（仅依赖 `@cloudbase/node-sdk ^3.0.0`）。参照物：部署配置 `cloudfunctions/cloudbaserc.json`（get-alerts 段：Nodejs18.15，timeout 10 秒，无环境变量）；端侧消费方 `entry/src/main/ets/services/AlertPoller.ets`（100 行）与数据契约 `entry/src/main/ets/model/AlertItem.ets`；写入方 `cloudfunctions/functions/fetch-tushare-data/index.js`。

函数职责一句话：Event 函数 + CloudBase HTTP 访问服务（`--path /alerts`，文件头注释 15-16 行），每次请求从云存储下载 `alerts/alerts.json`，按 ts 降序取前 limit 条，返回 `{items, serverTs}`。它是端侧 5 秒轮询的唯一数据出口（AlertPoller.ets:10 默认地址 `https://a2a-commonwealth-d2eepjr928e9c4d-1475054847.ap-shanghai.app.tcloudbase.com/alerts`，可被 SettingsService.getFeedUrl 覆盖，SettingsService.ets:351-356），是全应用"首屏永不空白"链条的第一环。契约与 `AlertItem.ets:19-22` 的 `AlertFeed{items,serverTs}` 完全一致。

## 二、读取链路审查

### 2.1 现状链路逐步拆解

`getLatestAlerts`（index.js:26-51）：require SDK → `cloudbase.init` → `app.downloadFile({fileID: ALERTS_FILE_ID})` → `JSON.parse` → `data.items.sort((a,b)=>b.ts-a.ts)` → `slice(0,limit)`。四个结构性事实：

1. **全量下载**：alerts.json 由 fetch-tushare-data 保留最新 500 条（fetch-tushare-data/index.js:537-540），单条 AlertItem 约 300-500 字节，全文件估 150-250KB。每次轮询都下载全量，**下载放大比** = 500/limit（limit 默认 20，即 25 倍）。
2. **每次请求重新 init**：`cloudbase.init({env})` 在函数体内（index.js:28-29），冷热启动都执行。对照 fetch-tushare-data/index.js:28-37 的单例模式（注释明言"避免重复 init 导致连接泄漏"），get-alerts 未跟进。
3. **fileID 硬编码**（index.js:21）：env 变更时需改代码，且与 generate-tts/index.js:25、broadcast-a2a/index.js:22 三处重复同一串 fileID——三胞胎常量，任何一处漂移都静默读旧桶。
4. **排序在读侧**：sort 每请求执行 O(n log n)，n=500 时微不足道，真正的成本全在下载与解析，不是排序。

### 2.2 下载放大的量化估算

端侧行为：前台每 5 秒一次（AlertPoller.ets:30 `currentInterval=5000`），失败退避翻倍封顶 30 秒（AlertPoller.ets:90-95）。假设 100 台在网设备、正常时段 5 秒节奏：100 × 12 次/分 × 200KB ≈ **每分钟 240MB 出口流量**，全部是重复内容（alerts.json 只在 fetch-tushare-data 定时触发后才变化，一天变化次数有限）。即使只有 10 台设备也在 24MB/分钟量级。HTTP 访问服务按流量计费且轮询是永久背景行为——这是当前架构里最贵的一条路，优化收益直接。

## 三、读取优化三方案

### 方案A：增量协议（改动最小，收益最大）

端侧 5 秒轮询的本质诉求是"有没有新条目"，绝大多数轮询答案是"没有"。给出口加 `since` 参数，命中"无更新"时返回极小响应：

```js
exports.main = async (event, context) => {
  const limit = Math.min(parseInt(event?.query?.limit || '20', 10), 100);
  const since = parseInt(event?.query?.since || '0', 10); // 端侧传上次 serverTs
  const data = await readAlertsFile();          // 见 3.1 缓存化
  const items = since > 0
    ? data.items.filter(i => i.ts > since).sort((a,b)=>b.ts-a.ts).slice(0, limit)
    : data.items.sort((a,b)=>b.ts-a.ts).slice(0, limit);
  const changed = data.serverTs > since && items.length > 0;
  return {
    items: changed ? items : [],   // 无更新时空数组，几百字节
    serverTs: data.serverTs,       // 数据水位，不是 Date.now()
    changed,
  };
};
```

两个关键点：其一，`serverTs` 必须回传**文件内的数据水位**（fetch-tushare-data/index.js:544 写入的 serverTs），而不是现在的 `Date.now()`（index.js:67）——现在端侧拿到的 serverTs 每次都变，根本没法当水位用；其二，端侧 AlertPoller 需配套记住上次 serverTs 并在 URL 拼接 `?since=`，AlertPoller.ets:41 的请求拼串处是唯一改动点。**注意语义变化**：AlertItem.ts 是秒级时间戳（AlertItem.ets:8），fetch-tushare-data 的 createAlertItems 用 `alertId: ${symbol}_${now}` 且同一秒内可能产出多条同 symbol 条目（fetch-tushare-data/index.js:476-489），用 `i.ts > since` 过滤是安全的（水位比较），但端侧去重逻辑（若靠 alertId）不受影响，需在联调时确认同秒多条不丢。

### 方案B：函数实例内存缓存

无论是否上增量协议，都应在实例内缓存 alerts.json 解析结果，TTL 1-2 秒：

```js
let _cache = null, _cacheTs = 0; const TTL = 2000;
async function readAlertsFile() {
  if (_cache && Date.now() - _cacheTs < TTL) return _cache;
  const app = getCloudbaseApp();               // 单例，同 fetch-tushare-data 纪律
  const result = await app.downloadFile({ fileID: ALERTS_FILE_ID });
  _cache = JSON.parse(result.fileContent.toString('utf-8'));
  _cacheTs = Date.now();
  return _cache;
}
```

效果：同一实例 2 秒内的 N 次轮询合并为 1 次下载。云函数实例常驻窗口内（SCF 热实例通常存活数十秒到数分钟），热路径下载次数可降一个数量级。代价是实例间缓存不一致——但 TTL 2 秒的陈旧度完全在"5 秒轮询"的容忍度内。方案A+B 叠加是推荐落点。

### 方案C：迁数据库集合（治本，配合 A18/A20）

文件总线（alerts.json）的根问题是"读放大 + 写覆盖竞态 + 无索引"。把 alerts 迁入数据库集合（fetch-tushare-data 写入时按 alertId upsert；get-alerts 查询 `collection.where({}).orderBy('ts','desc').limit(limit)`，ts 建降序索引）后：读取量 = limit 条而非全文件；get-alerts 出口直接查库，downloadFile 从热路径消失；generate-tts 的 audioUrl 回写也变成单字段 update（根治 A16 篇 6.4 的覆盖丢数据问题）。这是与 A18（init-db 集合与索引设计）、A20（架构演进）联动的方向，建议作为二期，一期先落 A+B 止血。

## 四、缓存策略分层总览

全链路现有与建议的缓存层次：

| 层 | 现状 | 建议 |
|---|---|---|
| 端侧内存 | AlertPoller 每轮全换、Index 卡片流按 alertId 合并（Index.ets:226-250 一带） | 维持；增量协议下只 append 新条目 |
| 端侧退避 | 失败翻倍封顶 30s（AlertPoller.ets:90-95）；429 静默（47-52） | 维持，是服务端限流的对端契约 |
| HTTP 访问服务 | 无缓存头可控性（Event 函数形态） | 如需 `Cache-Control` 需转 Web 函数模式，非必需 |
| 函数实例内存 | 无 | 方案B，TTL 2 秒 |
| 存储层 | alerts.json 本身就是上游产物快照（500 条滚动） | 维持；二期集合化后此层退役为备份 |

一个明确结论：**不建议在 get-alerts 里做"演示数据兜底缓存"**。首屏永不空白由端侧演示卡实现（共享约束），服务端掺演示数据会让"连通但无异动"与"故障"两种状态在协议上无法区分，污染契约。

## 五、语义缺陷：读失败伪装成"无异动"

现有两层 catch 都把异常吞成空数组：`getLatestAlerts` 内层 catch 返回 `[]`（index.js:47-50），main 外层 catch 返回 `{items:[], serverTs}`（index.js:69-75），加上文件不存在也是 `[]`（index.js:46）。于是**服务端故障与真实无异动对端侧完全同形**：都是 HTTP 200 + items:[]。端侧 PollResult 的三态设计（ok=false 网络/HTTP 异常、ok=true items 空 = 连通但无异动，AlertPoller.ets:12-17 注释写得很清楚）在服务端这一侧被破坏了——云存储故障时，用户看到的是干净的空列表，AlertPoller 认为 ok=true 不退避，还会以 5 秒频率继续打在故障的服务上。

修复：让失败显式失败。文件读取异常时向上抛，让 HTTP 访问服务返回 5xx（端侧 54-58 行已有 5xx 分支会退避）；或保守起见返回带 degraded 标记：

```js
} catch (e) {
  console.error('get-alerts error:', e.message);
  throw e;   // 推荐：映射为 5xx，端侧已有退避分支承接
  // 或：return { items: [], serverTs: 0, degraded: true };
}
```

注意 `serverTs: 0` 的降级返回不可与"正常水位"混淆——端侧若已用方案A，收到 serverTs=0 应视作异常不更新本地水位。同时建议区分"文件不存在"（首次部署前的正常态，返回空列表即可）与"文件存在但 JSON.parse 失败"（数据损坏，应告警并抛错），现在是混在一处 catch 里（index.js:47-49）。

## 六、降级方案设计

### 6.1 故障面盘点

get-alerts 的依赖只有两样：CloudBase 存储（alerts.json）与 CloudBase 平台本身。对应故障面：a) alerts.json 缺失（首次部署/误删）；b) alerts.json 损坏（写覆盖竞态的产物，A16 篇 6.4 已证实回写无保护）；c) 云存储服务故障；d) HTTP 访问服务限流/故障。

### 6.2 分级降级

- **c/d 级（平台级）**：函数侧无能为力，交给端侧既有机制——5xx/网络异常 → ok=false → 演示卡兜底 + 退避轮询。这符合共享约束"服务未连通显示带示例字样演示卡"，服务端不要画蛇添足返回假数据。
- **b 级（数据损坏）**：建议引入**双写备份**。写入方 fetch-tushare-data 在覆盖 alerts.json 前先把旧文件复制为 `alerts/alerts-backup.json`（或写入数据库 alerts_backup 集合）；get-alerts 读主文件 JSON.parse 失败时自动回退读备份并在响应中带 `source:'backup'`，控制台日志告警。改动集中在写入方一行 + 读取方一个 fallback 分支，收益是把"单文件损坏 = 数据全灭"变成"最多丢最近一个写入周期"。
- **a 级（文件缺失）**：返回空 items 是正确行为（端侧演示卡接管），但要打 `console.error` 级别日志（现在 catch 内是 error 级，可保持），避免首部署静默无数据无人发现。
- **限流协同**：端侧对 429 的静默处理（AlertPoller.ets:47-52，rateLimited 单独标记不惊动用户）是现成的对端契约，建议在 CloudBase HTTP 访问服务上对 /alerts 路径配置并发/频率限流，把方案A/B 的收益转化为真实的成本保护，而不是裸奔。

### 6.3 与上游降级的边界

共享上下文已知问题"Tushare token 失效(40101)已降级东财 API"发生在 fetch-tushare-data 层（其 index.js:123-272 的名称映射五级降级），get-alerts 自身零外部数据源依赖，不需要也不应该复刻任何数据源降级逻辑——它的降级问题全部围绕"自己那份文件的可用性"。

## 七、其余小项

limit 解析（index.js:58-61）已做 Math.min(…,100) 上限保护且容忍 query 与顶层两种入参形态，正确保留。`sort` 前未校验 `ts` 类型：若上游某条目 ts 为字符串，`b.ts - a.ts` 会算出 NaN 破坏排序——当前写入方恒写数字（fetch-tushare-data/index.js:443 `const now = Math.floor(Date.now()/1000)`），风险低，但集合化改造时应在 schema 层约束。日志面：请求级日志未记录 limit/since 与命中情况，方案A落地时建议补 `console.log(JSON.stringify({limit, since, changed, took}))` 便于观察轮询命中率。

## 八、修复优先级清单

| 级别 | 事项 | 位置 | 依据 |
|---|---|---|---|
| P0 | 失败显式化：读异常抛错/带 degraded，区分损坏与缺失 | index.js:47-50, 69-75 | 五，故障被伪装成无异动 |
| P0 | serverTs 回传数据水位而非 Date.now()（配合 since 增量） | index.js:67 | 方案A，端侧已备好三态 |
| P1 | 实例内存缓存 TTL 2s + SDK 单例化 | index.js:28-29 | 方案B/2.1-2 |
| P1 | since 增量参数 + 端侧 AlertPoller 拼接联动 | index.js:57-76 | 方案A，降流量 25 倍起 |
| P1 | 上游双写备份 + 读取 fallback | fetch-tushare-data/index.js:549 附近 | 6.2-b |
| P2 | HTTP 访问服务配置 /alerts 限流 | cloudbaserc.json（访问服务侧） | 6.2-限流协同 |
| P2 | alerts 集合化与 ts 降序索引 | 联动 A18/A20 | 方案C |

## 九、未实测项

未做：真实环境压测（下载放大与缓存命中率是估算值）、CloudBase HTTP 访问服务对 Event 函数抛错时的具体状态码映射（建议施工 P0 第一项时用 curl 验证一次 5xx 形态）、AlertPoller 端侧 since 联动的联调（属端侧任务）。上述均已标注，不作为已验证结论。

## 十、可观测性设计

现状日志只有读失败一条（index.js:48、70），无法回答"轮询流量长什么样"。建议每请求一条结构化日志：`{limit, since, changed, items, tookMs, source}`——source 区分 memory/file/backup（方案B 与 6.2 落地后）。三个关键指标与告警阈值（基线为估算，上线一周后校准）：实例缓存命中率（方案B 后应高于六成，低于三成说明实例频繁冷启动，去查函数并发度配置）；changed 率（轮询绝大多数应返回未变更，长期 100% 说明 since 未生效或上游写入过频）；5xx 率（连续 5 分钟高于 1% 告警，对应存储故障）。指标从日志离线聚合即可，不引入监控组件，符合零三方依赖基调。

## 十一、HTTP 触发形态的两个施工注意点

其一，**5xx 映射必须先验证**：P0 第一项落地后，临时加一个 force_error 测试分支，用 `curl -i "https://{env}.app.tcloudbase.com/alerts?force_error=1"` 看函数抛错时 HTTP 访问服务回什么状态码；若平台把函数异常统一映射为 200 加错误体（以实测为准），"抛错"路线不成立，必须改走 degraded 字段路线——这是两条 P0 路线的分岔点，施工第一天就要定，不能等联调时才发现。其二，Event 函数形态下响应头不可控（加不了 Cache-Control），若未来确需 HTTP 层缓存，唯一路径是迁移为 Web 函数模式（参照 broadcast-a2a/index.js:258-293 的 http.createServer 形态）；迁移成本可控但收益有限，除非限流与缓存压力实测顶不住，否则不做。

## 十二、端侧联动改造清单（AlertPoller 侧）

服务端三处改动需要端侧三处对应（AlertPoller.ets）：1) since 参数——fetchLatest 增加 since 入参，由轮询循环方持久化上次 serverTs（复用 SettingsService 的 Preferences 封装），URL 拼接 `?since=`；2) changed 字段——PollResult 增加 changed，false 时跳过卡片流 diff 直接进入下一轮等待；3) degraded 字段——ok=true 且 degraded=true 时按 ok=false 走退避但不弹"连接中断"提示（白皮书 §3.2.4 的不惊动用户纪律）。三处都是小改，但必须与服务端同批上线：端侧未带 since 时服务端按 since=0 全量处理，**向后兼容安全**；端侧先上、服务端未上时 since 被忽略也只是退化为全量，同样安全。回滚策略：端侧去掉 since 参数即回到全量模式。兼容性是增量协议设计的硬前提，两条升级顺序都安全，才敢改。

## 十三、与 broadcast-a2a 读路径的协同

get-alerts:26-51 与 broadcast-a2a:27-48 是近乎逐行相同的两份 getLatestAlerts。本篇的内存缓存与单例改造应同步复制到 broadcast-a2a——它触发频率低（手动/Event），复制收益小，但保持两份行为一致能避免"一个读了旧缓存、一个读了新文件"的排障困惑；三处硬编码的同一 fileID（get-alerts:21、broadcast-a2a:22、generate-tts:25）也应顺手改为同一环境变量注入。此项列为连带工单而非阻塞项，随方案B 一起施工最省。

## 十四、limit 与请求面安全

现有 limit 上限 100（index.js:58-61）已防住巨值参数。剩余的请求面风险是无鉴权下任意频次全量拉取：方案A 的 since 与内存缓存落地后，不带 since 的高频请求仍会每次穿透缓存打 downloadFile，因此 6.2 的限流不是可选项，而是方案A 的配套项——按预期设备数的两倍配 QPS 上限（估算 5-10 QPS 起步），超限 429 由端侧既有分支静默承接。建议对 limit>20 的请求单独设更低限流档位，把容量倾斜给默认轮询流量；同时拒绝带未知查询参数组合的重放请求可暂不做（收益低），优先保住带宽大头。

## 十五、与首屏永不空白约束的配合语义

共享约束"服务未连通显示带示例字样演示卡"在本函数视角的精确语义：演示卡是**端侧**状态，服务端永远不应该产出演示数据。四种服务端形态与端侧呈现的对应关系——200+有数据：正常卡片流；200+空 items（真实无异动或文件缺失）：端侧应呈现"暂无异动"的空态而非演示卡（此时服务是连通的，演示卡只在未连通时出现，这个区分目前依赖端侧对 ok 的判定，AlertPoller.ets:12-17 的注释已定义该语义）；5xx/网络异常：ok=false，退避+按约束显示演示卡；429：ok=false 但静默（rateLimited 标记，AlertPoller.ets:51）。要害在于第二种：本篇第五节指出"故障被伪装成空 items"后，端侧会把故障态误判为连通态——**演示卡契约的失守不是端侧代码的错，而是服务端把两种语义压成了一个返回**。这就是 P0 显式化在产品层的意义：它不只关乎日志好看，直接决定适老化用户看到的是"今天没有异动"还是"服务出问题了正在重试"。

## 十六、方案对比总表（三方案横向对照）

| 维度 | A：增量协议 | B：实例缓存 | C：集合化 |
|---|---|---|---|
| 改动面 | 云函数出口+端侧拼参（两处小改） | 仅云函数内部（一处） | 三函数+数据迁移（大） |
| 流量收益 | 无更新轮询降到百字节级 | 同实例合并下载，约一个数量级 | 读取量=limit 条，彻底消除放大 |
| 生效周期 | 端侧发版后全量生效 | 部署即生效 | 二期窗口 |
| 风险 | 端云两侧需同批上线（兼容性已论证安全） | 实例间短暂不一致（TTL 内） | 迁移期双写/双读复杂度 |
| 依赖 | 需 serverTs 改为数据水位（P0） | 无 | 依赖 A18 集合与索引就绪 |

落地建议重申：B 先行（部署即收益、零风险），A 跟进（端侧可发版时同批上），C 作为二期治本与 A16/A18/A20 的同类项合并施工。单做 B 不做 A 时收益有限（实例冷启动即失效），单做 A 不做 B 时高频穿透仍在——两者是互补关系而非替代关系，表里看不出的是这个组合逻辑，文字说明补上。

## 十七、轮询节奏与服务端节拍的错位分析

上游 fetch-tushare-data 按定时器节拍写入（交易日日频量级，非秒级），端侧却按 5 秒节奏轮询——两个节拍差着数量级，意味着 5 秒轮询的绝大多数请求注定扑空。这个错位不是缺陷而是设计（推送未通时轮询是唯一实时性来源），但它量化了 A/B 两方案的价值上限：两次写入之间的全部轮询理论上都可被 A 方案压成空响应、被 B 方案合并成一次下载。进一步的方向（记录不实施）：若未来 X 服务器落地、FEED_URL 切换到真正的秒级监测源（共享上下文"数据源 FEED_URL 待 X 服务器落地"），轮询节奏与服务端节拍差距收窄，A 方案收益同步收窄，届时评估升级为长连接或推送为主的模式——但那是换数据源的事，与本函数当前形态无关，本篇不展开。

## 十八、响应体契约字段表

把返回体的每个字段讲清楚，作为端云两侧共同的接口文档（现状字段 + 方案落地后新增字段，新增者标注）：

| 字段 | 类型 | 语义 | 备注 |
|---|---|---|---|
| items | AlertItem[] | 按 ts 降序的最新异动 | 空数组语义见第十五节四形态 |
| serverTs | number | 秒级时间戳 | **现状为 Date.now()（index.js:67），必须改为数据水位**（P0）；端侧拿它做 since 增量基准 |
| changed | boolean | 本次是否有新条目 | 方案A 新增；false 时端侧跳过 diff |
| degraded | boolean | 读失败降级标记 | 五节新增；true 时端侧按故障退避不弹提示 |
| source | string | 数据来源：file/memory/backup | 可观测性用（第十节），端侧可忽略 |

AlertItem 各字段（alertId/ts/symbol/name/direction/kind/headline/detail/audioUrl/complianceStatus）的契约由 AlertItem.ets:6-17 唯一定义，本函数不增删不改——**服务端是契约的搬运工不是定义者**，这是端云协作的第一纪律。历史上最容易出的偏差是服务端私自给 item 加字段或改字段名，端侧 ArkTS 接口是编译期检查不了的（JSON.parse 直转），运行时才炸——所以字段表要放进评审清单：任何对本表的改动必须端云两侧同评审。

### 自我评估
- 正确性：4分 全部结论有行号证据；"失败伪装成无异动"与"serverTs 不能当水位"两处为源码直读所得的关键发现；下载放大比标注为估算。
- 完整性：4分 读取优化三方案、四层缓存、分级降级、优先级清单齐备；未展开 HTTP 访问服务计费细则。
- 可复用性：4分 方案A/B 代码可直接粘贴，P0 两项可独立施工；方案C 依赖 A18/A20 联动已明示边界。
- 字数：约4300字（正文汉字，实测统计，不含本自评）
- 使用模型：GLM-5.3-Flash
