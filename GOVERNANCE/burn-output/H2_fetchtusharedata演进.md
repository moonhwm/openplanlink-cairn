# H2 · fetch-tushare-data 演进复盘——PostgreSQL 到 CloudBase 存储、Tushare 到东财的数据源迁移

> 编纂：Moon席位（写手-H组-1号 / GLM-5.3-Flash），2026-09-24
> 素材基线：`cloudfunctions/functions/fetch-tushare-data/index.js`（739 行，本次复盘逐行走查）、`hardcoded-names.js`、CHANGELOG.md 2026-09-20 至 2026-09-23 相关条目、README.md。
> 本文自包含：所有结论引用源码行号与 CHANGELOG 条目，可独立复核。

## 一、函数定位：整条数据管道的入口

fetch-tushare-data 是铃语 App 数据链路的第一环：**拉行情 → 筛异动 → 补中文名 → 合规检查 → 预生成 TTS → 落盘存储**。它由 CloudBase 定时触发器每分钟调用一次（cron `0 * * * * * *`，CHANGELOG 2026-09-20 12:50 条目 V3），产出的 alerts.json 经 get-alerts 云函数以 HTTP 端点暴露给端侧 AlertPoller 轮询。当前文件头部注释（index.js:1-17）写明数据接口策略：daily（基础权限）、trade_cal（1 次/小时限流）、top_list（无权限）。

函数体内五个子模块的现行分布：

| 模块 | 行号区间 | 职责 |
|---|---|---|
| 基础设施 | 19-92 | TUSHARE_TOKEN/THRESHOLD/DKnowC 常量、CloudBase SDK 单例 `getCloudbaseApp()`（28-37）、`requestHttps` 统一封装（43-76）、`requestHttpsRetry` 指数退避（81-92） |
| 名称映射 | 94-139, 176-324 | `fetchEastMoneyMarket`（97-129）、交易日缓存（131-134）、`getStockNameMap` 五级降级链（176-324） |
| 行情与异动 | 326-441 | `getLatestTradeDate`（330-391）、`getDailyMovers`（397-441） |
| 合规 | 443-488 | `checkCompliance` 调 DKnowC 统一 API |
| 组装与落盘 | 490-738 | `createAlertItems`（493-543）、`saveAlertsToDB`（549-610）、`exports.main`（615-738） |

## 二、演进第一幕：PostgreSQL 幻影期（2026-09-20）

09-20 09:40 条目记载了最初设计：4 个 PostgreSQL 表（alerts / user_stocks / user_preferences / tts_cache）+ RLS 安全规则 + tts 存储桶。fetch-tushare-data 当时的职责是「筛选涨跌幅≥5%异动写入 alerts 表」，包结构里依赖 `pg` 驱动。当天验证 V1-V5 显示表与策略「全部存在」——但事后证明这批验证只覆盖了 DDL 层，没有覆盖**运行时连通性**。

09-21 的条目给出关键判定：`PG_CONN_STRING` 从未在任何云函数中配置，Supabase alerts 表也不存在，「之前认为数据写入 PostgreSQL 是错误的」。也就是说：表在库里，凭据在纸外，数据从未落过一张 SQL 表。这次幻影暴露的验证盲区是——**验证了 schema 存在 ≠ 验证了数据链路存在**。此后本工程的验证纪律升级为「必须端到端回读」（见第五节）。

## 三、演进第二幕：PostgreSQL → CloudBase 存储迁移（2026-09-21）

迁移不是主动选型而是被动突围：CHANGELOG 记载尝试了 6 种访问 CloudBase 内置 PostgreSQL 的方案（db.server() 不存在、app.database() 非函数、fetch rdb URL 401、app.rdb().fetch() host:null、app.callApis() invalid api name、NoSQL 未开通）全部失败，甚至临时部署了 diag-env 诊断函数去探测 SDK 原型方法列表，最终确认 node-sdk 在该环境下**只有 uploadFile/downloadFile/callFunction 可靠可用**。

于是 `saveAlertsToDB()`（index.js:549-610）被重写为「JSON 文件读改写」模式，这是整个迁移的核心，值得完整拆解：

1. **下载旧档**：`app.downloadFile({cloudPath: 'alerts/alerts.json'})`，文件不存在按空数组处理（557-568）；
2. **并发写保护**：若旧档 `serverTs` 比本轮最大 `ts` 还新，说明另一实例已写入更新数据，跳过本次写入（571-576）——这是用版本号模拟乐观锁；
3. **合并去重**：Map 先放旧数据再放新数据，同 alertId 后写覆盖先写（579-587）；
4. **截断**：按 ts 降序保留最新 500 条（590-592）；
5. **上传**：`app.uploadFile` 带新的 serverTs 重传整个文件（601-604）。

迁移的代价与收益同样清晰。代价：放弃 SQL 查询/索引能力，500 条上限成为硬顶；读改写整档的模式在分钟级频率下可接受但不适合更高并发。收益：链路当天真实打通——V1 实测 413 条异动写入、V2 实测 get-alerts 读回 20 条、V3 HTTP 端点回读成功。同日 get-alerts、broadcast-a2a、generate-tts 三个函数全量跟进迁移，diag-env 完成使命后删除。

## 四、演进第三幕：Tushare → 东方财富的数据源迁移（2026-09-21）

这不是整体换源，而是**按子接口逐个换**。三个触发因素：

1. **token 失效**：Tushare token 报 40101 错误（README「已知问题」与燃烧计划书均登记），daily 主链路需要备胎；
2. **限流**：trade_cal 频率限制 1 次/小时、stock_basic 更严；
3. **name 字段缺陷**：daily API 返回的 name 经常为空，卡片会显示「000002.SZ」而非「万科A」——对适老化产品这是体验级故障。

迁移落点分三处。其一，`getLatestTradeDate()`（330-391）给 trade_cal 补上 `start_date/end_date`（最近 30 天）参数，修复此前返回未来交易日 20271231 的 bug（CHANGELOG 2026-09-21 条目「关键修复」），并加 1 小时内存缓存；API 失败时按星期推算最近工作日兜底（374-390）。其二，名称映射改用东方财富免费接口（`80.push2.eastmoney.com/api/qt/clist/get`，index.js:100），按四个市场过滤串（`m:1+t:2` 沪A、`m:1+t:23` 科创板、`m:0+t:6` 深A、`m:0+t:80` 创业板，index.js:221）拉取，代码前缀映射 ts_code（6→.SH、0/3→.SZ、8/4→.BJ，index.js:113-115）。其三，新增 `hardcoded-names.js`（5560 条 A 股名称，约 105KB，2026-09-21 从东财快照生成）作为终端 fallback。

名称映射最终形成**五级降级链**（getStockNameMap，176-324 行）：

```
① 内存缓存（24h TTL）→ ② CloudBase 存储缓存 name-map.json（24h 内直接用；
过期则先载入内存作降级预备再尝试刷新）→ ③ 东方财富四市场并行刷新（成功则
回写存储）→ ④ 过期存储缓存兜底 → ⑤ hardcoded-names.js 硬编码 → 空 Map
```

设计取向非常明确：**name 字段永远尽量有值**，宁可旧也不空，因为空值直接伤害适老化体验。

Tushare 并未整体退役：daily 主链路在 token 有效时仍是首选（`getDailyMovers` 并行调用 daily + 名称映射，index.js:402-410），东财承担名称与备胎职责；token 失效时整链输出为空但不崩溃（`exports.main` 对 TUSHARE_TOKEN 缺失返回结构化错误，618-625）。

## 五、演进第四幕：audioUrl 缺口、合规层与 P0-P2 加固（09-21 至 09-23）

**audioUrl 缺口**：全链路验证发现 alerts.json 的 audioUrl 恒为 undefined，而端侧 `if (!item.audioUrl) return` 会导致卡片没有「▶ 听」按钮——点卡即听是产品根基。修复：main 中对 signal 卡（涨跌幅≥8%）按绝对涨跌幅降序取前 10 条，经 `app.callFunction` 并行调 generate-tts，`Promise.allSettled` 保证单条失败不拖累全批（index.js:643-719）。百炼 CosyVoice 只支持 WebSocket duplex 协议（HTTP POST 返回 400 task can not be null，CHANGELOG 09-18 条目），由 generate-tts 内部用 ws 模块承担。

**DKnowC 合规层**：`checkCompliance()`（456-488）POST `open.dknowc.cn/chat/trusted/unification`，safeType 为 Safe/ConditionallySafe 判合规，结果写入 `complianceStatus` 元数据字段；与 TTS 生成 `Promise.all` 并行、非阻断（654-682）。实测标定：「浮亏扩大，注意风险」→Safe，「动量策略今日目标：贵州茅台涨5%」→Unsafe（CHANGELOG 09-21 08:30 条目 V4/V5）。

**P0-P2 加固**（09-23 三个条目，全部附 grep 验证）：P0 五项——SDK 单例化消除 5 处重复 init、callTushare 改走带 15s 超时的 requestHttps、实验性 fetch 全量替换、fallbackMap 赋值到内存缓存激活降级预备、alertId 从 `symbol_timestamp_random` 改为确定性 `symbol_timestamp` 消除随机碰撞去重丢数据；P1 两项——东财四市场由串行（约 16s，逼近函数超时）改 `Promise.all` 并行（预估 4s）、requestHttpsRetry 指数退避；P2——signal 卡按涨跌幅绝对值降序，让最重要的异动优先获得 TTS 配额。另有安全加固：Tushare 报错信息经 `replace(TUSHARE_TOKEN, '***')` 脱敏（index.js:161-162），凭据一律走环境变量，源码零明文。

## 六、如实登记：现存缺陷与文档-实现偏差

本次逐行走查发现两处需要挂牌的问题，如实记录不做粉饰：

1. **残留死代码块**：index.js 第 234-256 行存在一段旧串行版残留（`const stocks = data.data.diff;` 及其后的 while/page++ 循环），引用了本作用域未定义的 `data`/`fs`/`page` 变量。它位于东财刷新的 try 块内，一旦执行到即抛 ReferenceError 被 catch 吞掉，**导致东财刷新路径在当前文件状态下总是失败**、链路退到存储缓存/hardcoded 兜底。README「已修复问题」表登记该项已于 2026-09-23 修复，`GOVERNANCE/a2a/A2A_AUTONOMY_EXPERIMENT_SUMMARY.md` 也记载了对应 P0 修复（commit f3552fe），但当前文件仍含该块——修复声明与文件现状不一致，建议下一个席位复核该文件的部署同步状态。
2. **名称兜底仍有效但链路降级**：由于上述缺陷，名称实际上长期由存储缓存与 hardcoded-names（5560 条）供给；hardcoded 快照日期为 2026-09-21，新股与更名将随之漂移，需要定期再快照的机制（目前无）。

## 七、可迁移的工程经验

1. **连通性验证必须穿透到数据回读**：schema 存在、函数 Active 都不等于链路存在，端到端「写→读→HTTP 回读」三连才算数。
2. **JSON 文件存储的乐观锁**：serverTs 版本号比对是零基础设施下防并发覆盖的最小可行方案，适用前提是写入频率分钟级、单档体量受控（本例 500 条上限）。
3. **数据源降级链要按子接口设计**：token 失效不必整源切换，name 用东财、行情留 Tushare、终端用快照，各段独立降级。
4. **非阻断式合规**：合规检查做成元数据标注而非门禁，保证主链路永不因第三方 API 波动停摆——这与首屏永不空白是同一设计哲学在云端的投影。
5. **重构必须清场**：并行化改造时新旧代码并存且旧代码残留在 try 块内，会被 catch 静默吞掉变成「永远走不到的成功路径」，此类缺陷 grep 验证也难发现，唯有逐行走查（这正是本函数两次 P0 都由「深度审查」而非自动检查发现的原因）。

### 自我评估
- 正确性：4分 全部基于本会话对 739 行源码的逐行走查与 CHANGELOG 条目比对；第 234-256 行残留缺陷为本次实测发现并如实登记，未经云端实跑复核其运行时表现（判断依据是作用域分析）。
- 完整性：4分 覆盖四幕演进、五级降级链、并发保护、合规与加固；对 generate-tts/broadcast-a2a 的内部细节仅在关联处提及（属其他复盘范围）。
- 可复用性：5分 附模块-行号地图、降级链伪代码与五条可迁移经验，新席位可按图索骥。
- 字数：约4250字
- 使用模型：GLM-5.3-Flash
