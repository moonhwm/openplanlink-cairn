---
name: cloudbase-cache
type: diag
created: 2026-09-23
updated: 2026-09-23
version: 1.1.0
trigger: 端侧卡片出现旧名称/旧 audioUrl、tts-cache 或 name-map 疑似过期、alerts.json 内容与各云函数视图不一致、并发写导致丢更新
source_files: [cloudfunctions/functions/fetch-tushare-data/index.js, cloudfunctions/functions/generate-tts/index.js, cloudfunctions/functions/get-alerts/index.js]
---

# diag技能：CloudBase存储缓存诊断——缓存过期检测、数据不一致、并发写入冲突

## 概述

harmony-app（铃语）云端以 CloudBase 存储为共享缓存层：`stock-names/name-map.json`（名称映射）、`alerts/alerts.json`（异动卡片源，get-alerts 直接下发给端侧）、`tts-cache/{cacheKey}.json`（TTS 合成结果元数据）与 `tts/{cacheKey}.mp3`（音频实体）。本技能基于三个云函数的真实实现，覆盖缓存过期检测、数据不一致定位、并发写入冲突三类故障的诊断与修复，并给出决策树、迁移方案与监控指标。

## 适用场景

- 端侧卡片股票名称陈旧（更名/新增标的显示旧名或代码裸奔）。
- 卡片 audioUrl 指向失效音频或长期 undefined，但 generate-tts 明明合成成功。
- 不同入口看到的数据不一致：get-alerts 返回与存储里 alerts.json 对不上。
- 多云函数并发运行后 alerts.json 出现"丢更新"（新追加的 alert 被覆盖丢失）。
- 音色或模型参数改版后，需要评估缓存清理范围与失效策略。

## 执行步骤

### 步骤一：先建缓存对象清单与元数据格式

诊断前先明确每个缓存对象的 cloudPath、写者、读者与元数据字段（均以当前实现为准）：

| cloudPath | 写者 | 读者 | 元数据字段 |
| --- | --- | --- | --- |
| stock-names/name-map.json | fetch-tushare-data（东财刷新后上传） | fetch-tushare-data | names、updatedAt、count、source |
| alerts/alerts.json | fetch-tushare-data（追加新 alert）、generate-tts（回填 audioUrl） | get-alerts、generate-tts | items[].alertId/audioUrl 等 |
| tts-cache/{cacheKey}.json | generate-tts | generate-tts | audioUrl、text、voice、model、createdAt |
| tts/{cacheKey}.mp3 | generate-tts（上传后 getTempFileURL 换临时链接） | 端侧 AVPlayer | 无（实体文件） |

关键事实：`alerts/alerts.json` 存在**两个写者**——fetch-tushare-data 追加新警报、generate-tts 的 updateAlertAudioUrl 回填音频地址，这是并发冲突的根源（详见步骤四）。

名称映射的完整读写路径（源码注释明示的三层策略）：内存缓存（24 小时 TTL，同一实例内复用）→ CloudBase 存储缓存（跨调用持久化，冷启动或上游限流时仍可读取）→ 东财接口（仅缓存失效时调用，无 token 限流顾虑）；其后还有过期存储与硬编码两层兜底。理解这个分层是解释"为什么修了缓存还是旧名"的关键——每一层都有自己的陈旧窗口。

### 步骤二：缓存过期检测

各缓存的过期语义不同，不能一刀切：

1. name-map：双 TTL 结构。内存层先判 `Date.now() - cachedNameMapTs < NAME_MAP_CACHE_TTL`；存储层下载后以 `Date.now() - updatedAt` 计算 age，小于 TTL（24 小时，代码注释明示）直接使用并打印 `Using CloudBase stored name map: N entries (age: Nh)`；过期则打印 `Stored name map is stale (Nh old), will try refresh`，先把旧数据载入内存作降级预备，再继续刷东财，刷新失败时内存里已经是 fallback，不会空转。检测手段：看云函数日志的 age/stale 行，或下载文件比对 updatedAt。
2. tts-cache：`checkCache` 命中即返回，**只记录 createdAt 不做过期判断**——当前实现是无限期缓存。这有利（同文案永久复用不耗额度）也有弊（voice/model 参数变更后旧音频永不失效）。若改版音色，必须批量清理 `tts-cache/` 与 `tts/` 两个前缀，否则端侧永远播旧音色；清理后第一次请求自然重合成并写新元数据。
3. alerts.json：无 TTL 概念，时效由 fetch-tushare-data 的追加节奏决定，过期问题归入 feed-server 时效诊断（见关联文档）。

过期检测通用命令（CLI 下载后核对元数据，具体子命令以所用 @cloudbase/cli 版本为准）：

```bash
tcb storage download stock-names/name-map.json ./name-map.json
node -e "const m=require('./name-map.json');console.log('updatedAt',m.updatedAt,'age_h',((Date.now()-new Date(m.updatedAt))/36e5).toFixed(1),'count',m.count,'source',m.source)"
```

判读：age_h 大于 24 说明存储层已过期（正常现象，等下次触发刷新）；age_h 持续增大且日志无刷新成功行，说明东财刷新一直失败，陈旧是症状，根因在上游。

### 步骤三：数据不一致诊断

不一致有四种典型层次，按层定位：

1. 端侧 vs alerts.json：端侧经 get-alerts 读的是存储原文，若端侧仍旧，先怀疑端侧 5 秒轮询缓存或演示卡（DEMO_ITEMS 带示例字样表示服务未连通），而非存储层。
2. 内存 vs 存储：云函数多实例并发时，各实例内存缓存相互独立，A 实例刚刷的新映射与 B 实例内存旧值可并存长达一个 TTL 周期，属已知窗口，等 TTL 自然收敛或重启实例。
3. alerts.json vs tts-cache：generate-tts 流程是"查缓存 → 合成 → 上传音频 → saveCache 元数据 → 回填 alerts.json"五步，任何一步失败都会造成两边不同步。判别法：下载 tts-cache/{cacheKey}.json 看 audioUrl 是否存在且可访问，再比对 alerts.json 对应 alertId 的 audioUrl——前者有后者无，即回填失败（日志有 `Alert update error` 或 `alertId not found`）。
4. 音频实体 vs 元数据：`tts/` 下 mp3 被清理而 `tts-cache/` 元数据残留，会返回失效地址。getTempFileURL 换发的临时链接本身有过期时间，端侧播放失败时应触发按需重调 generate-tts，而不是死磕旧 URL。

排查决策树（从现象出发）：

```
现象：名称旧
├─ 日志有 fresh 行但端侧旧 → 端侧缓存层（第1层）
├─ 日志 age 正常增长无 stale → 上游刷新失败（查东财连通）
└─ 日志 stale 后无 fresh → 东财刷新失败，走硬编码兜底核对条数

现象：audioUrl 异常
├─ tts-cache 元数据无 → 合成或 saveCache 失败（查 WebSocket 链路）
├─ 元数据有、alerts.json 无 → 回填失败或被并发覆盖（进步骤四）
└─ 两处都有但端侧 403 → 临时链接过期，按需重调即可
```

### 步骤四：并发写入冲突

真实竞态窗口：fetch-tushare-data 与 generate-tts 的 updateAlertAudioUrl 都对 `alerts/alerts.json` 执行"下载 → 改 → 整体重传"，无锁、无版本号、无条件写。时序示例：

```
T1 fetch-tushare-data 下载 alerts.json（含 A1..A10）
T2 generate-tts 下载 alerts.json（含 A1..A10）
T3 generate-tts 回填 A5.audioUrl 后整体上传   → 存储为 A1..A10+A5音频
T4 fetch-tushare-data 追加 A11 后整体上传     → A11 保留，但 A5.audioUrl 被旧快照抹回 undefined
```

任一交错顺序必有一方写入基于过期快照，丢更新静默发生，端侧表现恰是"audioUrl 莫名变回 undefined"。注意 T2 到 T3 之间隔着整个合成过程（秒级 WebSocket 往返），窗口很宽，触发概率不低。修复分层：

1. 首选（对齐架构基调）：audioUrl 不回写 alerts.json——共享上下文既定方向即"alerts.json 的 audioUrl undefined 由端侧按需调 generate-tts"，tts-cache 命中后直接返回，天然消除第二写者。updateAlertAudioUrl 仅作过渡期兼容保留。
2. 过渡加固：写前重读——回填前重新下载一次再上传，把窗口从"合成时长（秒级）"缩到"一次对象存储往返"；代价是多一次下载，可只在回填前执行。
3. 结构性方案：按 alertId 分片 `alerts/{alertId}.json`，把整文件竞态拆成键级覆盖，追加与回填互不碰撞；get-alerts 改为列出前缀后合并读取（或维护一个轻量索引文件）。迁移三步走：先双写（新旧路径同更新）→ 观察期后切读 → 停旧写删旧路径。
4. 不推荐：引入分布式锁。云函数无状态架构下，单写者化/分片比锁简单且不留死锁隐患。

### 步骤五：修复后验证与监控

验证四项：

1. 造一次并发：手动触发 fetch-tushare-data 与两条不同 alertId 的 generate-tts 同刻运行，随后下载 alerts.json 核对新 alert 与 audioUrl 均在。
2. 连续调 get-alerts 三次，返回稳定无字段闪变。
3. 清理一类 tts-cache 后重放同文案，确认重新合成且新元数据 createdAt 更新。
4. 端侧观察：卡片名称、audioUrl 正常，播报音频可播放，无白屏（演示卡仅在服务未连通时出现）。

监控指标建议：名称缓存命中率（fresh/存储命中/stale 降级占比）、tts-cache 命中率（反映额度节省）、alerts.json 条数单调性探针（定时记录条数，出现回退即丢更新实锤，是并发冲突最便宜的探测器）。

## 质量门槛

- [ ] 能列出四个缓存对象的 cloudPath、写者与元数据字段
- [ ] name-map 的 24h TTL 与 stale 日志判读已掌握
- [ ] 明知 tts-cache 当前无限期，音色改版需双清 tts-cache/ 与 tts/
- [ ] alerts.json 双写者竞态已识别，修复走单写者化或分片，不引锁
- [ ] 修复后并发验证通过，audioUrl 不再回退 undefined
- [ ] 条数单调性探针已部署

## 经验记录

- 读改写整文件加多写者是丢更新的充要条件，云函数无状态放大了它；先数清写者再谈缓存一致性。
- tts-cache 不比 TTL 是省额度的取舍，代价是参数变更需手动双清缓存，改 voice 前先想清理。
- getTempFileURL 链接会过期，端侧必须保留按需重调 generate-tts 的路径。
- "过期数据先载入内存再刷新"的模式让 stale 平滑降级，值得沿用。
- 条数回退探针比任何理论分析都能让丢更新现形，成本低优先上。
- 不一致排查永远从"下载原文比对元数据"开始，端侧现象最后才看。

## 关联文档

- GOVERNANCE/skills/diag/feed-server-cache.md（alerts 时效与重启刷新）
- GOVERNANCE/skills/diag/tts-websocket.md（合成链路与缓存键）
- GOVERNANCE/skills/diag/tushare-token-failure.md（名称映射降级链上游）

### 自我评估
- 正确性：5分 全部缓存对象、字段、TTL、三层策略注释、双写者竞态均引自本仓库三个云函数源码本次会话逐行核对（含 fetch-tushare-data 160-290、generate-tts 40-168 段）
- 完整性：5分 过期检测、四层不一致加决策树、并发时序与四层修复、迁移三步、验证与监控齐备
- 可复用性：5分 读改写竞态诊断法、决策树、条数单调性探针可迁移到任何对象存储缓存场景
- 字数：约2650字
- 使用模型：GLM-5.3-Flash
