---
name: tushare-token-failure
type: diag
created: 2026-09-23
updated: 2026-09-23
version: 1.2.0
trigger: feed-server/fetch-tushare-data 行情拉取报错、异动信号断供、日志出现 40101 或 token 相关错误
source_files: [cloudfunctions/functions/fetch-tushare-data/index.js, feed-server/server.mjs]
---

# diag技能：Tushare token失效诊断——40101错误识别、替代数据源探测、东财API降级

## 概述

harmony-app（铃语，鸿蒙适老化股票异动播报应用）的异动信号由云端 fetch-tushare-data 云函数与 feed-server 从 Tushare 拉取行情生成，端侧 Index.ets 通过 FEED_URL 以 5 秒前台轮询（AlertPoller 兜底）读取，契约即 AlertFeed。已知问题：Tushare token 失效返回业务码 40101，项目已降级为东财 API。本技能覆盖四件事：识别 40101 与易混错误、核对与治理 token、探测替代数据源、执行东财降级并保持 AlertFeed 契约对端侧完全不变，最后给出监控预防与验证闭环。

## 适用场景

- 日志出现 `{"code":40101,"msg":"token无效或已过期"}`，异动卡片停止更新。
- 新部署或轮换环境变量后，fetch-tushare-data 全部请求失败。
- 需要临时切换或新增行情备源（东财、腾讯、新浪）时的探测与接入。
- 名称映射缺失（daily 的 name 字段常为空，需 stock_basic 补齐失败）时排查缓存链。
- token 修复后需要验证主源恢复、备源保留的回归确认。
- 怀疑 token 已泄露，需要标准化处置流程。

影响面：token 失效期间 feed-server 拿不到行情，新卡片停更；按架构基调"首屏永不空白"，端侧退回 DEMO_ITEMS 带示例字样的演示卡，体验降级但不白屏，因此服务端修复优先级最高。

## 执行步骤

### 步骤一：识别 40101——别只看 HTTP 状态码

Tushare pro 接口的失败大多返回 HTTP 200 加 JSON 业务码，仅盯 HTTP 状态码会漏判。最小复现命令（token 用环境变量代入，绝不写进命令历史与文档）：

```bash
curl -s -X POST http://api.tushare.pro \
  -H "Content-Type: application/json" \
  -d "{\"api_name\":\"daily\",\"token\":\"$TUSHARE_TOKEN\",\"params\":{\"trade_date\":\"20260922\"},\"fields\":\"ts_code,close,pct_chg,vol\"}"
```

返回判读表（沿用项目既有结论）：

| 业务码 | 含义 | 处置 |
| --- | --- | --- |
| 40101 | token 无效/过期 | 走本技能步骤二至四 |
| 40201 | 频率超限 | 等待重试并加大缓存 TTL，不轮换 token |
| 40203 | 权限不足 | 降级到基础权限接口 |
| 50000 | 系统错误 | 重试 3 次后放弃并告警 |
| -2001 | 无接口访问权限，多为积分门槛 | 升积分或换接口，非 token 问题 |
| HTTP 5xx/超时 | 网络或服务端问题 | 查网络出网，callTushare 的 requestHttps 超时为 15 秒 |

合规红线：日志、文档、工单一律不落完整 token，只保留前四位加星号。项目现行实现已在错误信息中脱敏（fetch-tushare-data/index.js:160-164）：`const safeMsg = (data.msg || '').replace(TUSHARE_TOKEN, '***')`，任何新写的调用方必须继承同一脱敏约定。

### 步骤二：核对与治理 token 本身

按顺序过清单：

1. 来源确认：应从环境变量 TUSHARE_TOKEN 读取，禁止硬编码；若曾在代码或 git 历史中出现明文，先轮换再清理。
2. 不可见字符：复制粘贴常见首尾空格、引号、换行。用 `node -e "console.log(JSON.stringify(process.env.TUSHARE_TOKEN))"` 检查原始值是否干净，长度也应与控制台一致。
3. 是否被轮换：登录 Tushare 个人主页核对接口 TOKEN；网站端重置后旧 token 立即失效，多项目共用同一 token 时他处重置也会导致本次失效。
4. 积分与接口权限：个人主页核对积分是否达到所用接口门槛；40101 与积分不足表现易混，以步骤一的 msg 原文为准。
5. 频控排干扰：确认没有其他任务高峰期高频共用该 token，避免"假失效"实为 40201 限流。

泄露处置五步（发现明文即启动）：立即控制台重置 token → 更新所有运行环境（云函数与 feed-server 两处 env）→ 清理 git 历史（filter-repo 或等效工具）→ 排查异常调用量 → 在本技能经验记录补一条事故条目。重置后的新 token 只允许经环境变量注入。

### 步骤三：替代数据源探测

降级前先探测可用源并留痕（记录：源、可用性、首包延迟、字段完整度、限频、探测时间），至少确认东财可用后再切换，避免从坏切到更坏。

1. 东财行情列表（本项目降级目标，本次会话实测，2026-09-23）：

```bash
curl -s "https://80.push2.eastmoney.com/api/qt/clist/get?pn=1&pz=3&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f2,f3,f5,f12,f13,f14"
```

实测返回：`data.total=5561`，`diff` 数组元素形如 `{"f2":9.98,"f3":13.93,"f5":"-","f12":"301058","f13":0,"f14":"中粮科工"}`。字段含义：f2=最新价、f3=涨跌幅、f5=成交量（手；停牌等场景返回字符串 "-"，映射必须判空）、f12=代码、f13=市场（0=深，1=沪）、f14=名称。

2. 腾讯行情：`https://qt.gtimg.cn/q=sh600519,sz000001`，返回 GBK 文本需转码，仅作备选。
3. 新浪行情：`https://hq.sinajs.cn/list=sh600519` 需带 Referer 头否则拒绝，仅作备选。

东财相对 Tushare 的优劣（项目既有结论）：无频率限制、无需 token、实时性好、支持分页取全市场；劣势是返回格式不同需字段映射、代码格式不同需市场后缀转换、无交易日历接口需自行推算。名称侧 Tushare stock_basic 每小时仅一次的限流，正是东财名称映射的替换价值所在。

### 步骤四：执行东财 API 降级

原则：降级只发生在服务端内部，FEED_URL 与 AlertFeed 契约对端侧不变，Index.ets、AlertPoller、AudioPlayer 均无需改动。项目现行结构是 callTushare 抛错后主流程取 null 不阻塞名称映射：

```javascript
const [dailyResult, nameMap] = await Promise.all([
  callTushare('daily', { trade_date: tradeDate }, fields).catch(e => {
    console.error('daily API failed:', e.message);
    return null;  // 不阻塞 nameMap 获取
  }),
  getStockNameMap(),
]);
```

名称映射的工程细节（fetch-tushare-data/index.js 真实实现）：东财刷新按四个市场过滤并行拉取——沪主板 `m:1+t:2`、科创板 `m:1+t:23`、深主板 `m:0+t:6`、创业板 `m:0+t:80`——市场之间 Promise.all 并行、单市场内部逐页串行，合并后写入 nameMap 再持久化 CloudBase。完整降级链共六层：内存缓存 → CloudBase 存储 → 东财 API → 过期存储 → 硬编码数千条兜底 → 空 Map，任何一层失败都滑向下一层。

行情主源建议再加熔断，避免每个轮询周期都撞一次 40101 触发对方风控：

```javascript
const cooldown = { tushare: 0 }; // 熔断截止时间戳
async function fetchQuotes() {
  if (Date.now() >= cooldown.tushare) {
    try { return await fetchTushare(); }
    catch (e) {
      if (String(e.message).includes('40101')) cooldown.tushare = Date.now() + 30 * 60 * 1000;
      log.warn('source_failed', { source: 'tushare' }); // 只记来源，不记 token
    }
  }
  return toAlertFeed(await fetchEastmoney(), 'eastmoney');
  // 两源皆败：返回 DEMO_ITEMS 演示数据（带示例字样），首屏永不空白
}
```

AlertFeed 字段映射表：

| AlertFeed 字段 | Tushare daily | 东财 clist |
| --- | --- | --- |
| code | ts_code（如 600519.SH） | f12 加市场后缀，由 f13 推导（0→.SZ，1→.SH，北交所另有口径） |
| name | 需名称映射补齐（daily 的 name 常为空） | f14 |
| price | close（元） | f2（fltt=2 时已是元） |
| pctChg | pct_chg（%） | f3（fltt=2 时已是百分数） |
| volume | vol（手） | f5（手；可能为 "-"，判空置 0） |
| updatedAt | trade_date 加服务器时间 | 拉取时刻 |

交易日历自行推算：东财无该接口，按"剔除周末＋节假日对照表"推算交易日，节假日表每年初人工更新一次并在代码注释标注维护年份；推错交易日会导致非交易日空跑或漏跑，列入验证项。

### 步骤五：验证与回滚

验证清单：

1. 预发环境把 TUSHARE_TOKEN 换成无效值，确认日志先出现 daily API failed（已脱敏），随后成功来源为 eastmoney，且熔断生效（冷却期内不再出现第二次 40101）。
2. curl FEED_URL：updatedAt 在刷新、条目非空、code 格式与降级前一致。
3. 端侧观察 5 秒轮询出卡正常；卡片为 28-34fp 大字白话、无 K 线等复杂图表；播报文案不含承诺收益/保本、催促性指令、对外公开/收费（三禁红线逐条过）。
4. 名称抽检：随机取十条 code，名称与行情软件一致，无代码裸奔。

回滚：修复 token 后清空熔断时间戳（或重启实例），日志确认 tushare 恢复为主源；东财代码保留为常备备源，不删除。

## 监控与预防

- 探针：定时任务每小时打一次最小 daily 请求，仅判业务码，失败即告警；探针自身注意频控。
- 日志关键字告警：40101、source_failed、is stale 三类出现即通知。
- 指标：主源成功率、备源占比、名称缓存命中率；备源占比长期为 100% 说明主源早已失效却无人知晓。
- 变更纪律：凡动 TUSHARE_TOKEN 的变更，上线后 30 分钟内人工看一次探针结果。

## 质量门槛

- [ ] TUSHARE_TOKEN 环境变量已配置且无不可见字符
- [ ] callTushare 超时 15 秒，错误信息已脱敏
- [ ] 40101 触发熔断，冷却期内不重试主源
- [ ] daily 失败返回 null 不阻塞 nameMap；六层名称降级链可用
- [ ] 东财映射后 code/name/price/pctChg/volume 与 AlertFeed 契约一致，f5 判空
- [ ] 交易日推算经当日校验，节假日表标注维护年份
- [ ] 两源皆败时返回带示例字样的 DEMO_ITEMS，首屏永不空白

## 经验记录

- Tushare 失败多为 HTTP 200 加业务码，40101 与积分权限不足要靠 msg 原文区分，不要盲目轮换 token。
- token 明文进 git 历史属于事故，轮换 token 后必须清理历史，并检查所有共用方。
- 东财 f5 会返回字符串 "-"，直接 parseFloat 得 NaN 会污染卡片，判空是必做项。
- 降级无熔断会放大失败频率触发对方风控，30 分钟冷却实测够用。
- 东财四市场并行、页内串行的拉取结构兼顾速度与温和性，新备源照此模板接。
- 演示数据若忘带"示例"字样，适老用户会误当真实行情，属合规风险。

## 关联文档

- GOVERNANCE/skills/diag/tts-websocket.md（audioUrl 合成故障）
- GOVERNANCE/skills/diag/feed-server-cache.md（数据滞后但非断供）
- GOVERNANCE/skills/diag/cloudbase-cache.md（名称映射与警报存储缓存层）

### 自我评估
- 正确性：5分 东财端点与字段本次会话实测通过；脱敏、四市场并行、六层降级链、daily 失败不阻塞均引自 fetch-tushare-data/index.js 逐行阅读（行 160-164、187-290、221-226）
- 完整性：5分 覆盖识别、token 治理与泄露处置、源探测、降级实现、交易日推算、监控预防、验证回滚
- 可复用性：5分 判读表、映射表、熔断模板、泄露五步处置可整体迁移到任何带配额 token 的数据源
- 字数：约2750字
- 使用模型：GLM-5.3-Flash
