# A21 云函数统一基础设施层设计——共享SDK初始化、共享错误处理、共享缓存层抽象方案

> 项目：harmony-app（鸿蒙适老化股票异动播报应用，代号铃语）
> 范围：`cloudfunctions/functions/` 下全部云函数（get-alerts、fetch-tushare-data、generate-tts、broadcast-a2a、push-token-register、init-db）
> 快照声明：本仓在 2026-09-23 当天经历多轮并发修改（云函数 08:21—09:30 波次、fetch-tushare-data 与 Index.ets 12:42 波次）。本文所有"现状"以 **12:42 后稳定版** 为准，引用行号来自当日对源文件的直接读取与 grep 核实；文中第 1.4 节记录了一次审查窗口内亲眼观察到的中间态事故，作为本方案必要性的直接证据。架构基调（端侧 List 卡片流 + 5s 前台轮询 + AlertFeed 契约）不因本层改造而改变：本方案只动云端内部实现，不动端云之间的 JSON 契约与 FEED_URL 语义。

---

## 一、背景与问题定位

### 1.1 为什么仍需要统一基础设施层

09:30 波次的改造已经把"每次调用都 `cloudbase.init`"的问题解决掉了：六个函数现在各自持有模块级 `_cloudbaseApp` 单例（grep 核实：`cloudbase.init` 全仓共 6 处，每函数恰好 1 处，均在单例工厂内）。但这轮收敛恰恰暴露了下一层问题——**同一段正确代码被复制了六份**。单例工厂、环境常量、HTTPS 封装、缓存样板，每一件都在多个函数目录里各存一份拷贝，拷贝之间已经出现行为分叉（见 1.3）。统一基础设施层要解决的是：

1. **分叉风险**：同一职责的多份实现迟早行为不一致，其中一份的修复不会自动同步到其余各份；
2. **漂移风险**：环境 ID、fileID 这类常量被复制到多处，换环境或迁数据路径时漏改一处就是线上事故；
3. **可观测性风险**：日志格式、错误返回结构各不相同，CloudBase 控制台无法按统一字段检索定位；
4. **无部署前校验**：函数目录各自独立打包，没有任何机制保证"上传的代码至少能通过语法检查"（1.4 节的实例证明这不是杞人忧天）。

### 1.2 现状证据清单（12:42 稳定版，逐项附行号）

**（a）六份单例样板。** `get-alerts/index.js:23-30`、`generate-tts/index.js:63-70`、`broadcast-a2a/index.js:55-62`、`push-token-register/index.js:19-26`、`fetch-tushare-data/index.js:28-37`、`init-db/index.js:12` 附近——六段结构完全相同的 `let _cloudbaseApp = null; function getCloudbaseApp() {...}`，仅函数名拼写（getCloudbaseApp vs getCloudBaseApp）和 envId 变量名有细微差别。

**（b）环境 ID 常量六处复制。** `const ENV_ID = process.env.TCB_ENV || 'a2a-commonwealth-d2eepjr928e9c4d'` 出现在全部六个函数（grep -rln TCB_ENV 命中 6 个文件）。`ALERTS_FILE_ID` 硬编码 `cloud://...6132-...-1475054847/alerts/alerts.json` 出现在 3 个文件：`get-alerts/index.js:20`、`generate-tts/index.js:25`、`broadcast-a2a/index.js:23`。

**（c）HTTPS 封装两份且已分叉。** `fetch-tushare-data/index.js:43-76` 的 `requestHttps`（JSON 解析失败的报错含 body length）与 `broadcast-a2a/index.js:28-52` 的同名函数（不含 body length）是两份独立演化副本；前者还配了指数退避重试 `requestHttpsRetry`（:81-92，500ms/1000ms 两档），后者没有重试。generate-tts 的 WebSocket 链路则是第三套超时/兜底逻辑（:201-205、:287-303）。

**（d）缓存三处三样。** 股票名称映射五级降级（内存 24h → 云存储 TTL 内 → 东财刷新 → 过期存储兜底 → 硬编码 → 空 Map，`fetch-tushare-data/index.js:176-324`）；交易日两级（内存 1h → 星期推算，:131-134、:308-373）；TTS 音频云存储缓存（sha256 前 16 位键，`generate-tts/index.js:56-58`、:76-120）。三处的 TTL 计算、存储键命名、降级链互不一致，且均无并发加载保护。

**（e）错误处理与日志口径不一。** 全仓 console.* 调用约百处（grep 计数 100），自由文本前缀风格（'get-alerts: ...'、'[compliance] ...'、'TTS ...'）混杂；仅 `fetch-tushare-data/index.js:160-162` 对 Tushare 报错做了 token 脱敏（`replace(TUSHARE_TOKEN, '***')`），而 `push-token-register/index.js:47、:59` 仍把设备 token 前 20 位打进日志。

**（f）downloadFile 用法不一致（疑似误用，需实测）。** `get-alerts/index.js:40-42`、`generate-tts/index.js:81`、`broadcast-a2a/index.js:71` 用 fileID 形态；`fetch-tushare-data/index.js:187-189、:291-293` 用 `cloudPath` 形态。`@cloudbase/node-sdk` 的 `downloadFile` 标准签名按 fileID 取文件，`cloudPath` 形态在部分版本直接抛错——若如此，name-map 的"存储缓存命中"路径从未生效，每次都走东财全量刷新兜底。此判断需测试环境实测确认，但"两种写法并存"本身就是必须收敛的理由。

**（g）配额计数不持久。** `generate-tts/index.js:28-51` 的 QUOTA 是纯内存对象，冷启动归零，"百万 token 预警/停机线"只在单次实例存活期内有效。

**（h）文档腐化。** `get-alerts/index.js:16` 注释端点写作 `/alertsD`（末尾多一个 D），实际路径 `/alerts`。

### 1.4 审查窗口内观察到的中间态事故（本方案的直接动机）

09:15 左右读取到的 `fetch-tushare-data/index.js`（当时 739 行，08:46 波次产物）在 `getStockNameMap` 内部残留了一段死代码：旧串行抓取循环的片段（当时的 :234-256）留在新的并行代码之后，其中 :235 的 `if (stocks.length === 0) break;` 位于任何循环之外，且引用了已不在作用域内的 `data`、`fs`、`page`——按 JavaScript 语义这是**编译期 SyntaxError，整个函数无法加载**。14:26 我对该文件执行了静态检查（Python 脚本：逐行剥离注释后统计花括号深度、检测循环外 break；`node` 不在 PATH，`node --check` 无法执行），结果显示当前 716 行版本花括号平衡（终深度 0）、无循环外 break，对照 12:42 的修改时间戳确认死代码已在后续波次被手工清除。

这个事件说明三件事：①并发编辑下没有语法门禁，坏代码可以静默上线；②同样一段"东财抓取"逻辑的两次改写（串行→并行）留下了尸体，正是因为它只存在于一个函数内部、没有共享抽象也就没有重构边界；③部署流水线需要一个比"人眼"更低的底线校验。统一基础设施层配合部署前检查（第 9.3 节）可以把这类事故挡在上线前。

---

## 二、设计目标与约束

### 2.1 目标

1. 六个函数共享同一份"配置解析 + SDK 单例 + 文件存取 + 缓存 + 错误码 + 日志"基础设施，消灭 1.2 节列举的八类重复与分叉；
2. 错误可分类、可检索、可降级，敏感信息（token、secret、API key）永不落日志；
3. 缓存抽象统一后，TTS 配额计数、name-map、trade-date、alerts.json 并发保护走同一套机制；
4. 端云契约零变更：`AlertFeed { items, serverTs }`（`entry/src/main/ets/model/AlertItem.ets:19-22`）、`/alerts` HTTP 端点、`generate-tts` 的 `{ alertId, text } → { success, audioUrl }` 入出参全部不变。

### 2.2 不可逾越的约束（继承治理红线）

- 不推翻架构基调：数据源仍以 alerts.json 为准，get-alerts 是唯一权威读端点；不引入新数据库替代存储方案，只把存储访问收敛为共享模块；
- 合规红线：DKnowC 合规检查（`fetch-tushare-data/index.js:434-488`）作为基础设施保留并可复用，任何新的文本产出路径必须经过它；不承诺收益/保本、不催促、不对外；
- 密钥红线：`TUSHARE_TOKEN`、`DASHSCOPE_API_KEY`、`DKNOWC_API_KEY`、`HUAWEI_PUSH_CLIENT_SECRET`、`BROADCAST_API_KEY` 全部只从环境变量读取（现状已如此），共享模块不得把它们写入持久化缓存或日志；
- 云函数侧允许 Node 三方依赖（`ws`、`@cloudbase/node-sdk` 已在用），共享模块本身零新增依赖；端侧零三方依赖约束与本方案无关，端侧代码不动；
- 兼容 broadcast-a2a 已实装的鉴权面：12:42 版 Web 模式已有 API Key 鉴权（:304-316，`/healthz` 豁免）与 CORS 白名单（:289-295），共享化不得弱化。

### 2.3 共享方式选型：同步脚本方案

CloudBase 函数按目录独立打包，`functions/A` 不能直接 `require('../_shared/x')`。三个候选：

1. **同步脚本（推荐）**：共享代码放 `cloudfunctions/_shared/`，`sync-shared.js` 在部署前复制进各函数的 `common/` 子目录，函数内 `require('./common/cbclient')`。零平台特性依赖、部署产物自包含、git diff 清晰；代价是多一步同步。仓库已有 `cloudbase-cmd.json`、`cloudbase-init.js` 等脚本化运维先例，与现有习惯一致。
2. 私有 npm 包：需要 registry 基础设施，对单人项目过重，否决。
3. Web 函数单体：推翻现有 Event 函数划分，违反"不推翻架构基调"，否决。

以下设计按方案 1 展开。部署命令链条固定为：`node sync-shared.js && 逐函数部署`——把同步写成链条第一步是硬要求，防止"忘记 sync 部署旧共享层"。

---

## 三、总体分层与目录规划

```
cloudfunctions/
  _shared/                     # 单一事实源，deploy 前由脚本同步
    config.js                  # 环境解析 + 常量注册表（ENV_ID、各 cloudPath、阈值）
    errors.js                  # AppError + 错误码表 + 脱敏工具
    log.js                     # 结构化日志（JSON 单行，带 code/func/level 字段）
    cbclient.js                # CloudBase 单例 + download/upload 封装（只认 cloudPath，内部换算 fileID）
    httpx.js                   # HTTPS 请求封装（超时/重试/退避，收敛两份 requestHttps）
    cache.js                   # 两级缓存（L1 内存 TTL / L2 云存储）+ single-flight
    quota.js                   # 基于 cache.js 的持久化计数器（供 generate-tts）
    compliance.js              # DKnowC 检查封装（从 fetch-tushare-data 抽出）
  functions/
    get-alerts/     （index.js + common/ 同步产物）
    fetch-tushare-data/
    generate-tts/
    broadcast-a2a/
    push-token-register/
    init-db/
  sync-shared.js               # 部署前置钩子
```

依赖方向严格单向：函数 `index.js → common/*`；common 内部只允许 `config → errors → log → cbclient/cache/httpx` 自底向上引用，禁止反向。compliance 依赖 httpx 与 errors，处于最顶层。

---

## 四、共享 SDK 初始化（config.js + cbclient.js）

### 4.1 config.js——常量注册表，单一事实源

```js
// _shared/config.js
const ENV_ID = process.env.TCB_ENV || 'a2a-commonwealth-d2eepjr928e9c4d';

// 存储路径注册表：全项目只在这里出现一次
const PATHS = {
  alerts: 'alerts/alerts.json',
  nameMap: 'stock-names/name-map.json',
  ttsCachePrefix: 'tts-cache/',
  ttsAudioPrefix: 'tts/',
};

// fileID 换算：桶序号来自现有三个函数中的硬编码，收敛于此
const BUCKET_SUFFIX = '6132-' + ENV_ID + '-1475054847';
const toFileID = (cloudPath) => `cloud://${ENV_ID}.${BUCKET_SUFFIX}/${cloudPath}`;

module.exports = { ENV_ID, PATHS, toFileID,
  THRESHOLD: parseFloat(process.env.ALERT_THRESHOLD || '5.0'),
  TTS_MODEL: 'cosyvoice-v3-flash', TTS_VOICE: 'longxiaochun_v3',
};
```

要点：密钥类环境变量（TUSHARE_TOKEN、DASHSCOPE_API_KEY、HUAWEI_PUSH_CLIENT_SECRET、BROADCAST_API_KEY、DKNOWC_API_KEY）仍由各函数自读，**不进 config 导出**，避免引用链过长导致意外输出。`toFileID` 消灭 1.2(b) 的三处硬编码 fileID 与 1.2(f) 的两种 downloadFile 形态——业务代码只写 cloudPath。

### 4.2 cbclient.js——单例收敛 + 存取封装

```js
// _shared/cbclient.js
const { ENV_ID, toFileID } = require('./config');
let _app = null;

function getApp() {
  if (!_app) {
    const cloudbase = require('@cloudbase/node-sdk');
    _app = cloudbase.init({ env: ENV_ID });
  }
  return _app;
}

async function readJson(cloudPath) {          // 统一只认 cloudPath
  const app = getApp();
  const result = await app.downloadFile({ fileID: toFileID(cloudPath) });
  if (!result || !result.fileContent) return null;
  return JSON.parse(result.fileContent.toString('utf-8'));
}

async function writeJson(cloudPath, obj) {
  const app = getApp();
  return app.uploadFile({
    cloudPath,
    fileContent: Buffer.from(JSON.stringify(obj), 'utf-8'),
  });
}

module.exports = { getApp, readJson, writeJson };
```

改造映射：`get-alerts` 的 `getLatestAlerts`（:35-59）改为 `readJson(PATHS.alerts)` 后排序切片；`generate-tts` 的 `updateAlertAudioUrl`（:126-168）改为 readJson → 改字段 → writeJson；`broadcast-a2a` 的 `getLatestAlerts`（:67-87）同样收敛；`push-token-register` 的数据库操作保留 `getApp()` 直用（数据库 API 无需封装）。alerts.json 的读改写集中在 cbclient 之上再包一层 `withAlerts(mutator)`（见 6.4），消除并发覆盖窗口。六份单例样板全部删除，`cloudbase.init` 全仓只剩 cbclient 一处。

---

## 五、共享错误处理（errors.js + log.js + httpx.js）

### 5.1 错误码表

沿用"Tushare 40101"式"来源前缀 + 数字/助记"风格，全项目登记于 errors.js：

| 错误码 | 含义 | 处置策略 |
|---|---|---|
| TUSHARE-40101 | token 失效/无权限 | 降级：名称映射走东财、交易日走星期推算（现有降级路径固化为码表语义） |
| TUSHARE-NET | 请求超时/网络失败 | requestHttpsRetry 已有两档退避，重试穷尽后本轮放弃 |
| EASTMONEY-NET | 东财抓取失败 | 单市场失败不阻塞其余市场（fetchEastMoneyMarket 现有 break 语义），全失败走存储兜底 |
| DASHSCOPE-NOKEY | API Key 未配置 | 返回现有文案 `'DASHSCOPE_API_KEY not configured'`（generate-tts:357）不变 |
| DASHSCOCE-TTS-FAIL | WebSocket 任务失败/超时 | 返回 null，audioUrl 留空，靠端侧 audioUrl 缺省行为兜底 |
| TCB-READ-FAIL | alerts.json 缺失/解析失败 | 读端点返回空 items（get-alerts:77-83 现语义），写端点跳过本次 |
| TCB-CONCURRENT | 并发写入冲突 | 跳过写入（fetch-tushare-data:551 现有保护） |
| DKNOWC-SKIP | 合规检查未配置/失败 | safeType=Unknown、放行（:457-460、:484-487 现语义） |
| AUTH-INVALID | broadcast-a2a API Key 不符 | 401 + 现有错误体（:311-315），不泄露期望值 |

### 5.2 errors.js——统一错误对象与脱敏

```js
// _shared/errors.js
const SENSITIVE = [process.env.TUSHARE_TOKEN, process.env.DASHSCOPE_API_KEY,
  process.env.DKNOWC_API_KEY, process.env.HUAWEI_PUSH_CLIENT_SECRET,
  process.env.BROADCAST_API_KEY].filter(Boolean);

function sanitize(msg) {            // 脱敏先于日志、先于返回，双保险
  let s = String(msg);
  for (const secret of SENSITIVE) s = s.split(secret).join('***');
  return s;
}

class AppError extends Error {
  constructor(code, message, { cause, fatal = false } = {}) {
    super(sanitize(message));
    this.code = code; this.cause = cause; this.fatal = fatal;
  }
}
module.exports = { AppError, sanitize };
```

脱敏把 `fetch-tushare-data:160-162` 的局部实践升级为全局规则。配套整改：`push-token-register:47、:59` 停止打印 token 前 20 位（改为只打 docId 与 token 长度）；`broadcast-a2a:225` 打印 push 结果前 200 字符——华为 Push 响应体不含密钥，保留；`generate-tts:344-348` 入口日志打印 text 前 50 字符——播报文本非密钥，保留但过 sanitize 以统一路径。

### 5.3 log.js——结构化单行日志

```js
// _shared/log.js
const { sanitize } = require('./errors');
function log(level, code, msg, extra = {}) {
  console.log(JSON.stringify({ ts: Date.now(), level, code,
    msg: sanitize(msg), ...extra }));
}
module.exports = { info: (c, m, e) => log('info', c, m, e),
  warn: (c, m, e) => log('warn', c, m, e),
  error: (c, m, e) => log('error', c, m, e) };
```

全部自由文本日志迁移为码表引用，控制台按 `code` 字段过滤即可定位（如 TCB-READ-FAIL 一键筛出所有读失败）。约百处 console 调用的迁移可机械化：按函数分批、每批一次人工抽查。

### 5.4 httpx.js——请求封装收敛

以 `fetch-tushare-data:43-92` 的 requestHttps + requestHttpsRetry 为底（它是两份副本中更完整的一份），增加两点：① 显式 `options.retries`（默认 0；东财调用配 2，与现行为一致）；② `raw` 模式返回文本（供需要读非 JSON 错误体的场景）。`broadcast-a2a:28-52` 的副本删除，其三处调用（:99、:172、:215）改引 httpx——顺带获得 Push Kit OAuth 调用的统一 10 秒超时（现 :180、:222 已各自传 timeout: 10000，收敛后为默认值）。

### 5.5 统一返回信封

Event 函数对外返回统一为 `{ success, code?, error?, ...data }`。兼容性核对：端侧 AlertPoller 走 `/alerts` HTTP 端点，响应体 `{ items, serverTs }`（get-alerts:73-76）**一个字段都不加**——端侧 `AlertPoller.ets:66` 直接 JSON.parse 后取 feed.items；`fetch-tushare-data → generate-tts` 的 callFunction 链路读取 `result.value.result.success/audioUrl`（fetch-tushare-data:707-710），信封变更时同步核对这两处。

---

## 六、共享缓存层抽象（cache.js）

### 6.1 两级缓存接口

```js
// _shared/cache.js
const { readJson, writeJson } = require('./cbclient');
const memory = new Map();              // key -> { value, expireAt }
const inflight = new Map();            // single-flight：同 key 并发 miss 只放一个 loader

async function get(key, { ttlMs, loader, l2Path }) {
  const hit = memory.get(key);
  if (hit && hit.expireAt > Date.now()) return { value: hit.value, src: 'l1' };
  if (inflight.has(key)) return { value: await inflight.get(key), src: 'flight' };

  const task = (async () => {
    if (l2Path) {
      try {
        const wrapped = await readJson(l2Path);   // { value, updatedAt }
        if (wrapped && wrapped.value !== undefined) {
          const fresh = Date.now() - new Date(wrapped.updatedAt).getTime() < ttlMs;
          memory.set(key, { value: wrapped.value, expireAt: Date.now() + ttlMs });
          if (fresh) return wrapped.value;
          // 过期仍作降级预备：刷新失败时 loader 抛错可回取此值
        }
      } catch (e) { /* 缓存不存在是常态 */ }
    }
    const fresh = await loader();
    if (fresh !== null && l2Path) {
      try { await writeJson(l2Path, { value: fresh, updatedAt: new Date().toISOString() }); } catch (e) {}
    }
    memory.set(key, { value: fresh, expireAt: Date.now() + ttlMs });
    return fresh;
  })();

  inflight.set(key, task);
  try { return { value: await task, src: 'loader' }; }
  finally { inflight.delete(key); }
}
module.exports = { get };
```

### 6.2 三处现有缓存归一后的形态

| 现状 | 归一后 |
|---|---|
| name-map 五级降级（fetch-tushare-data:176-324） | `cache.get('name-map', { ttlMs: 86400000, l2Path: PATHS.nameMap, loader: loadFromEastMoney })`；"过期仍作降级预备"对应 :203-209 的 stale-fallback；hardcoded-names 作 loader 内部最后一层保留 |
| 交易日缓存（:131-134、:308-373） | `cache.get('trade-date', { ttlMs: 3600000, loader: queryTradeCal })`；星期推算为 loader 内部兜底 |
| TTS 音频缓存（generate-tts:56-58、:76-120） | `l2Path: PATHS.ttsCachePrefix + cacheKey + '.json'`，包裹层 `{ audioUrl, text, voice, model, createdAt }` 命中语义不变；checkCache/saveCache 两函数删除 |

收益实例：name-map 的东财刷新（四个市场并行、每市场最多 20 页，:97-129、:221-233）在冷启动抖动期若被两个函数实例同时触发即双倍外呼；single-flight + L2 命中后，同实例内并发收敛为一次，跨实例靠 L2 命中吸收。

### 6.3 quota.js——持久化计数器

generate-tts:28-51 的内存 QUOTA 改为：`recordUsage(n)` 读改写 L2 文件 `tts-cache/_quota.json`，`shouldStop()` 读 L2。冷启动不丢计数，预警线 0.8 / 停机线 1.0 语义不变。写放大评估：单日 TTS 调用量级为个位数到十位数（信号卡最多 10 条/轮，:625-628），每次成功写一次计数文件，完全可接受。

### 6.4 alerts.json 的读改写与并发保护

现状：fetch-tushare-data:551 有 `existingServerTs > currentLatestTs` 跳过保护；generate-tts 的 `updateAlertAudioUrl`（:126-168）**没有**这层保护——两函数同时读改写 alerts.json 存在互相覆盖窗口（TTS 回填的 audioUrl 可能被 fetch 的旧快照覆盖掉）。归一方案：

```js
async function withAlerts(mutator) {
  const data = await readJson(PATHS.alerts) || { items: [], serverTs: 0 };
  const baseServerTs = data.serverTs || 0;
  const next = mutator(data);            // 返回 null 表示放弃写入
  if (!next) return { skipped: true };
  const cur = await readJson(PATHS.alerts);
  if (cur && (cur.serverTs || 0) > baseServerTs) return { skipped: true, reason: 'TCB-CONCURRENT' };
  next.serverTs = Math.floor(Date.now() / 1000);
  await writeJson(PATHS.alerts, next);
  return { skipped: false };
}
```

写前重读比对 serverTs 是对象存储无原子 CAS 现实下的最强乐观并发控制，与 :551 思路一致并推广到 audioUrl 回填路径。残余竞态（重读后写前仍有人写）如实承认：窗口极小，后果是 audioUrl 或一条旧异动回退，端侧下次轮询被定时触发自愈；不升级为数据库方案（违反约束）。

---

## 七、各函数接入改造清单

| 函数 | 改造点 | 引用现状（12:42 版） |
|---|---|---|
| get-alerts | readJson 替代内联下载；错误走码表；修正 :16 注释 typo | get-alerts:16,20,23-30,35-59,77-83 |
| fetch-tushare-data | 删除自建 requestHttps/Retry/单例/常量，换 httpx/cbclient/cache；name-map 与 trade-date 走 cache.get；downloadFile({cloudPath}) 疑似误用随封装消除；写库走 withAlerts | :28-37,43-92,131-139,176-324,527-587 |
| generate-tts | 删除 getCloudBaseApp/checkCache/saveCache，走 cache + withAlerts；QUOTA 换 quota.js | :24-25,28-51,63-70,76-120,126-168 |
| broadcast-a2a | 单例与 requestHttps 副本删除；三处调用改 httpx；**保留** API Key 鉴权与 CORS 白名单逻辑 | :23,28-52,55-62,67-87,99,172,215,289-316 |
| push-token-register | 单例换 cbclient；日志停打 token 子串 | :19-26,47,59 |
| init-db | 常量换 config；集合清单不变 | :12 附近 |

---

## 八、可观测性与验收

### 8.1 结构化日志的最低字段集

`ts / level / code / func` 四字段为最低集；错误额外携带 `err.code`（AppError 码）。检索示例：CloudBase 控制台日志过滤 `code=TCB-READ-FAIL` 直接列出所有读失败事件及其函数名。

### 8.2 验收清单（每项可机器或人工验证）

1. 六个函数目录中 `cloudbase.init` 出现总次数为 1 的倍数且仅存在于 common/cbclient.js（grep 验证）；
2. `functions/` 下 `a2a-commonwealth` 字符串出现次数为 0（只剩 _shared/config.js）；
3. 全量日志样例中 `***` 替换生效、无任何 token/secret/API key 原文；
4. 端侧联调回归：AlertPoller 轮询返回结构不变；generate-tts 缓存命中返回 `cached:true`；broadcast-a2a 带 `x-api-key` 头访问 200、错误头访问 401、`/healthz` 无鉴权 200；
5. 断网/坏 fileID 注入：get-alerts 返回空 items 而非 500（现 :77-83 语义保持）。

### 8.3 部署前语法门禁（针对 1.4 事故）

`sync-shared.js` 顺带执行语法检查：对每个 `functions/*/index.js` 与 `common/*.js` 调 `node --check`（ChildProcess 执行），失败即中止部署。本次任务环境 `node` 不在 PATH（已核实 `node -e` 失败），无法当场演示该命令输出；作为替代，我以 Python 脚本对当前 fetch-tushare-data 做了花括号平衡与循环外 break 检查（14:26 执行，结果：716 行、终深度 0、无违规），证明这类静态门禁可行且成本低。门禁落到 node 环境后以 `node --check` 为准。

## 九、实施步骤与风险

**分四步灰度**：① 建 `_shared/` 与 sync-shared.js，先迁 config + cbclient（收益最直接、风险最低，六个函数逐个切换）；② 迁 errors + log（机械化替换）；③ 迁 cache 与 quota（generate-tts 最后切，因其涉 WebSocket 主链路）；④ 迁 httpx 与 compliance（broadcast-a2a 最后切，保住已实装鉴权面）。每步之后手动触发一轮全链路验证再进下一步；任一函数出问题可单独回滚该目录。

**风险如实声明**：① 本方案为设计文档，文中代码未经运行验证（本任务环境无法部署 CloudBase 与真机联调）；② 1.2(f) 的 cloudPath 误用判断与 6.4 并发窗口分析基于源码阅读推断，实施前需测试环境以坏数据注入实测；③ 仓库处于高频并发修改中（当日至少三轮波次），本清单行号以 12:42 版为准，实施时以当时文件为准重新核对；④ 同步脚本引入人为遗漏风险，靠"部署命令链条第一步"硬性化解，并写入 GOVERNANCE 的部署说明。

### 自我评估
- 正确性：4分 现状论断全部附行号并经 grep/读取核实；1.4 节事故以两次实测（读取对比 + Python 静态检查）留痕；共享层代码为设计稿未运行，cloudPath 误用标注待实测，各扣部分分。
- 完整性：4分 覆盖三大主题 + 共享选型 + 逐函数清单 + 观测/验收/门禁/灰度；CI 流水线与 IAM 最小化等外围议题未展开。
- 可复用性：5分 码表、模块接口、改造映射、验收清单、语法门禁可直接转工单；记录了快照时间与并发修改背景，他人可复核。
- 字数：约4600字
- 使用模型：GLM-5.3-Flash
