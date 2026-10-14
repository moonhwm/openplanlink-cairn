---
name: feed-server-cache
type: diag
created: 2026-09-23
updated: 2026-09-23
version: 1.1.0
trigger: 端侧异动卡片停更或显示陈旧数据、怀疑 feed-server 缓存旧数据、需要判断重启是否有效
source_files: [feed-server/server.mjs, feed-server/audio-postprocess.mjs, feed-server/manage-feed-server.ps1, feed-server/start-feed-server.bat]
---

# diag技能：feed-server缓存旧数据诊断——缓存机制识别、重启刷新策略、时效验证

## 概述

feed-server 是 harmony-app（铃语）的 X 服务器落地前的数据源服务：端侧 Index.ets 以 5 秒前台轮询（AlertPoller 兜底）拉 FEED_URL，feed-server 每 30 秒刷新一次缓存数据（内存 cachedAlerts + CloudBase alerts.json 上游 + 本地 tts-cache 音频），契约即 AlertFeed。"数据是旧的"在这条链路上有多个可能的滞留点，误重启、误清缓存都源于没先定位层。本技能提供缓存机制识别、重启刷新策略与时效验证三段诊断法，附运维操作手册与延迟预算表。

## 适用场景

- 端侧卡片长时间不更新，或 updatedAt 停留在过去时刻。
- 新出现的异动迟迟不上卡片，旧卡片反复出现。
- 判断"该不该重启 feed-server"、重启后仍旧数据的原因分析。
- 区分"缓存故障"与"非交易时段本来就没有新数据"的正常现象。
- 新卡片配了旧音频，怀疑音频缓存错配。
- 运维接手，需要标准化的启停与核查流程。

## 执行步骤

### 步骤一：缓存机制识别——数据在哪儿停留

以 feed-server/server.mjs 真实实现为准，链路上有四个滞留点，从上游到端侧：

1. 上游行情源：Tushare（token 失效 40101 时降级东财 API），行情本身不新鲜则全链路旧。
2. CloudBase 存储 `alerts/alerts.json`：refresh 优先尝试 CloudBase 代理拉取 feed.items，直接采用存储里的现成数据。
3. feed-server 进程内存：`cachedAlerts` 与 `lastRefreshTs` 两个模块级变量缓存全量卡片，`REFRESH_INTERVAL = 30000`（30 秒）定时刷新；refresh 失败时保留旧缓存继续服务（日志 `[feed-server] refresh failed:`）。
4. 端侧：5 秒轮询 AlertPoller 拿到数据后的去重与渲染（以 alertId 判重，属端侧逻辑，不在本技能展开）。

refresh 的完整取舍（server.mjs:517-532）：先走 CloudBase 代理，成功则 `cachedAlerts = feed.items`；代理不可用或返回空时回落本地 `detectAlerts()` 自行检测生成；两者都抛错则打印 refresh failed 并**保留旧缓存**——这是刻意的可用性取舍，宁可旧不可空，与端侧"首屏永不空白"的兜底思想同源。

每层判别手段速查：

| 层 | 判别命令/证据 | 旧数据时的表现 |
| --- | --- | --- |
| 行情源 | 按数据源技能排查 token/降级 | 全链路停更，alerts.json 也无新条目 |
| CloudBase 存储 | 下载 alerts.json 比对最新 alertId | feed-server 重启后仍旧 |
| 进程内存 | /health 的 lastRefresh 与 refresh failed 日志 | /health 时间戳停滞或滞后 |
| 端侧 | 换设备/重装对比 | 仅单设备旧 |

识别口诀：**先问数据停在 1 到 4 哪一层，再动手刷新**。

### 步骤二：重启刷新策略

重启的确切效果（依据 server.mjs 启动序列，行 666-670）：进程启动即 `await refresh()` 一次，随后 `setInterval(refresh, 30000)`，并打印启动横幅标明数据刷新间隔与 TTS 模式（配置了 DASHSCOPE_API_KEY 时显示百炼模型与高保真口径，未配置时明确提示跳过合成）。因此：

- 重启**必定**清掉第 3 层内存缓存（进程级变量随进程消失）并立即触发一次刷新——内存层的所有"旧"一次重启归零。
- 重启**不一定**带来新数据：refresh 优先走 CloudBase 代理取 alerts.json，若存储里的数据本身就旧（fetch-tushare-data 定时任务未跑、token 失效未降级成功），重启后拉回的还是旧数据。**重启治内存不治上游。**
- 正确的重启姿势（manage-feed-server.ps1 提供管理入口，start-feed-server.bat 为启动入口）：
  1. 先看 /health 确认 lastRefresh 与失败日志，判断旧数据在第 2 还是第 3 层。
  2. 第 3 层（内存）→ 重启即愈。
  3. 第 2 层（存储）→ 触发一次 fetch-tushare-data 云函数刷新上游，再重启或等 feed-server 下个 30 秒周期。
  4. 第 1 层（行情源）→ 按 tushare-token-failure 技能修复源，再依次刷新第 2、3 层。
- 禁止用"循环重启"掩盖上游问题：每 30 秒本就有一次自然刷新，重启频率高于刷新间隔毫无增益，只会反复清掉正在进行的合成与后处理现场。

### 步骤三：音频缓存链路（旧音频错配排查）

本地 TTS 缓存 `data/tts-cache/{alertId}.wav`：refresh 检测到新 alert 后按 alertId 查本地音频，存在直接复用；不存在则现场合成（百炼 WebSocket），先写 `.mono.wav` 原始文件，经 audio-postprocess.mjs 做 HRTF 后处理，成功后 renameSync 原子替换成品——后处理失败时旧成品不被半成品污染。另有一条 CloudBase 代理路径，代理失败时回退本地缓存服务。

错配排查：新卡片播旧内容，先核对 `data/tts-cache/` 下该 alertId 文件的修改时间——文件比卡片新属正常（先有卡后有音），文件明显早于卡片且内容不匹配，查 alertId 生成规则是否含时间窗导致复用。批量换音色时的清理对象就是本目录，清后 refresh 会按需重合成。

### 步骤四：时效验证

三个口径由粗到细：

1. /health 口径（最快）：`GET <FEED_URL 根>/health`，返回 `alerts`（缓存条数）与 `lastRefresh`（ISO 时间）。判读：`now - lastRefresh ≤ 30s + 网络延迟` 为健康；超过 60 秒说明 refresh 连续失败（看 refresh failed 日志）；条数为 0 且端侧有卡片，说明端侧在吃演示卡 DEMO_ITEMS（服务未连通时的兜底），属链路断而非缓存旧。
2. updatedAt 口径（最准）：连续两次 `curl FEED_URL` 间隔 35 秒以上，比对返回 items 的 updatedAt/最新 alertId。有变化 → 链路活着；无变化 → 结合交易时段判断（见下）。
3. 端到端口径：制造一个已知新异动（或等真实异动），计时从发生到卡片出现的延迟，对照下方预算表定位超时环节。

端到端延迟预算分解（各环节正常耗时）：

| 环节 | 预算 | 超预算时的嫌疑 |
| --- | --- | --- |
| 上游检测出异动 | 定时任务周期 | fetch-tushare-data 未触发或源故障 |
| alerts.json 追加 | 秒级 | 存储写入失败或并发覆盖 |
| feed-server 刷新 | ≤30 秒 | refresh 连续失败 |
| 端侧轮询呈现 | ≤5 秒 | 端侧轮询停摆或网络 |
| 合计感知延迟 | 约 1 个刷新周期加轮询 | — |

**交易时段判别（防误诊的关键）**：异动数据源依赖行情更新，非交易时段（收盘后、周末、节假日）updatedAt 不前进、无新卡片是**正常现象**，不是缓存故障。验证前先确认当前处于交易时段；调试可选盘中或人为触发 fetch-tushare-data 造数。

## 步骤五：常见误诊清单与运维手册

| 现象 | 直觉判断 | 实际原因 | 处置 |
| --- | --- | --- | --- |
| updatedAt 长期不动 | 缓存坏了 | 非交易时段 | 无需处置 |
| 卡片反复出现旧的几条 | 缓存没清 | 上游 alerts.json 未追加新数据，refresh 只能取到旧的 | 刷第 2 层 |
| 重启后仍旧 | 重启无效 | 旧数据在第 2/1 层 | 按步骤二分层刷 |
| 端侧完全无卡片 | 数据断供 | 服务未连通，端侧走演示卡 | 查 feed-server 存活与 FEED_URL |
| 播报声音内容旧 | 行情缓存旧 | tts-cache 按 alertId 命中旧音频或 alertId 规则复用 | 核对 alertId 与音频修改时间 |

运维速查：日常核查 = /health 一次加日志尾部一眼；启停走 manage-feed-server.ps1；改刷新间隔改 server.mjs 顶部常量并重启；所有操作避开正在进行的合成窗口（看 TTS 相关日志静止再动手）。

## 质量门槛

- [ ] 能说出四个滞留点及其判别手段
- [ ] 重启前已查 /health，明确旧数据在哪一层
- [ ] 时效验证至少跑通 updatedAt 口径（两次 curl 间隔 ≥35s）
- [ ] 已排除非交易时段误诊
- [ ] 音频修改时间与新卡片 alertId 一致
- [ ] 延迟实测对照预算表归因到具体环节

## 经验记录

- 重启只清内存层；refresh 优先吃 CloudBase 现成数据，上游不新则重启白重启。
- /health 的 lastRefresh 是第一入口，30 秒阈值记牢。
- 非交易时段的"旧"是正常态，先看盘再看病。
- refresh 失败保留旧缓存是刻意的可用性取舍，别当 bug 修掉。
- tts-cache 按 alertId 键控，alertId 生成规则若含时间窗，音频错配要第一时间怀疑它。
- HRTF 后处理的临时名加 renameSync 模式值得在所有文件替换场景复用。

## 关联文档

- GOVERNANCE/skills/diag/cloudbase-cache.md（alerts.json 存储层细节与并发写）
- GOVERNANCE/skills/diag/tushare-token-failure.md（第 1 层行情源故障）
- GOVERNANCE/skills/diag/tts-websocket.md（音频合成链路）

### 自我评估
- 正确性：5分 30 秒刷新、启动即 refresh、CloudBase 优先与 detectAlerts 回落、refresh 失败保旧缓存、/health 字段、音频链路与 renameSync 均引自 feed-server/server.mjs 本次会话逐行核对（行 32/160/316-317/434-454/517-532/584-585/635/663-670）
- 完整性：5分 机制识别含分层判别表、重启策略、音频链路、三口径时效验证、延迟预算表、误诊清单与运维手册齐备
- 可复用性：5分 先分层再刷新与预算归因法可迁移到任何轮询型缓存服务
- 字数：约2650字
- 使用模型：GLM-5.3-Flash
