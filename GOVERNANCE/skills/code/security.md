# 铃语云函数安全性深度审查——输入验证、脱敏、日志安全与注入风险

> 审查对象：harmony-app（代号铃语）鸿蒙适老化股票异动播报应用的云函数层。
> 审查人：Moon席位 写手-A组-2号。审查日期：2026-09-23。
> 本文自包含：所有结论均引用本会话实际读取的文件路径与行号、实际执行过的命令及其输出；未执行的检查会如实标注"未运行"。

## 〇、审查范围、快照锚点与方法声明

### 0.1 审查对象

本次审查覆盖 `cloudfunctions/functions/` 目录下全部 6 个云函数源文件：

| 文件 | 当前行数(wc -l) | 本会话验证版本时间戳 |
| --- | --- | --- |
| `cloudfunctions/functions/fetch-tushare-data/index.js` | 735 | 2026-09-23 08:19:27 |
| `cloudfunctions/functions/generate-tts/index.js` | 406 | 2026-09-23 08:21:47 |
| `cloudfunctions/functions/get-alerts/index.js` | 84 | 2026-09-23 08:22:21 |
| `cloudfunctions/functions/push-token-register/index.js` | 102 | 2026-09-23 08:23:16 |
| `cloudfunctions/functions/init-db/index.js` | 67 | 2026-09-23 08:23:46 |
| `cloudfunctions/functions/broadcast-a2a/index.js` | 316 | 2026-09-23 08:27:34 |

### 0.2 快照锚点（重要）

本批次执行期间，工作副本正被同批次其他席位并发修改：`fetch-tushare-data/index.js` 在本会话首测时为 683 行（`wc -l` 输出 683），数分钟后复测变为 735 行，`md5sum` 输出 `fbf3afdd7e820451d33f467b1732504f`，且 5 秒内两次取值一致（修改时间 08:19:27.884）。**本文全部行号以 735 行版本为准**；若后续代码继续变动，请以文末"验收清单"中的命令重新锚定后再对照行号。

### 0.3 审查方法

实际执行过的检查（命令与结论见各节）：

1. 全文逐行人工审读 6 个 `index.js`（Read 工具）。
2. 关键模式全库扫描：`grep -n`（e.stack、cloudbase.init、fetch、timeout、where(、console.、eval/child_process 等）。
3. Python 3.12.10 编写的词法扫描脚本（注释与字符串剥离后做括号平衡统计、break/continue 循环深度分析），用于替代不可用的 Node 语法检查。
4. **未运行的检查**：`node --check`。原因：本机 bash 环境无 node（命令输出 `node: command not found`，`where.exe node` 无结果）。运行时行为（真实请求注入、日志外发）未验证——本会话未部署、未调用任何云函数，相关验证步骤以"验收清单"形式给出。

### 0.4 合规声明

本文严格遵守项目合规红线：不出现任何 Token/密钥的真实值；`cloudfunctions/.env`（943 字节，确认存在）只确认其存在与忽略状态，不读取、不引用其内容；涉及密钥处一律以环境变量名指代。

## 一、总体结论与风险分级

总体判断：**密钥治理面良好，输入验证面与日志安全面各存在一个必须立即修复的高危项，错误信息脱敏已有局部实践但未成体系**。分级如下：

| 级别 | 编号 | 位置 | 问题摘要 |
| --- | --- | --- | --- |
| P0 | S1 | push-token-register/index.js:81 | 整个 event 以 JSON.stringify 原样落日志，Push Token 明文入日志 |
| P0 | S2 | push-token-register/index.js:38 | `where({ token })` 未做类型校验，存在 NoSQL 操作符注入面 |
| P0 | S3 | fetch-tushare-data/index.js:285 | `e.stack` 打入日志，全库唯一残留 |
| P1 | S4 | fetch-tushare-data:730、push-token-register:98、broadcast-a2a:274/310 | 内部错误 `e.message` 原样返回调用方 |
| P1 | S5 | fetch-tushare-data/index.js:103-121 | 东财返回数据 diff 形态与字段类型校验不足 |
| P1 | S6 | fetch-tushare-data/index.js:54-63 | requestHttps 不校验 HTTP 状态码、不限制响应体大小 |
| P2 | S7 | get-alerts:66-69、broadcast-a2a:301 | limit 解析存在 NaN 路径，异常输入静默返回空列表 |
| P2 | S8 | generate-tts:352-354 | text 入参无长度上限，存在额度消耗放大面 |
| 低 | S9 | generate-tts:19 | 百炼 workspace id 硬编码兜底值（低敏，建议同样环境变量化） |

以下分节展开：每一项给出"现状证据（文件:行号）→ 风险机理 → 修复代码"。

## 二、输入验证审查

### 2.1 云函数入口的 event 消费面盘点

六个函数对入参 `event` 的使用方式决定了各自的暴露面：

- `fetch-tushare-data/index.js:615`：`exports.main = async (event, context) => {`，函数体内**从未读取 event**（全文检索确认），定时触发器驱动、参数全部来自环境变量。因此该函数不存在来自调用方的注入面，是六个函数中输入面最干净的一个。
- `get-alerts/index.js:65-69`：读取 `event?.query?.limit || event?.limit`，仅有 `Math.min(parseInt(...), 100)` 的上限钳制（见 2.2 的 NaN 问题）。
- `push-token-register/index.js:80-91`：解构 `token`、`bundleName`，仅做非空判断，无类型与格式校验（见第七节 S2）。
- `generate-tts/index.js:343-358`：解构 `alertId`、`text`，text 仅判空（见 2.3）。
- `broadcast-a2a/index.js:300-301`：Web 函数模式下解析 `url.searchParams.get('limit')`（见 2.2）。
- `init-db/index.js:17`：一次性初始化函数，不消费 event，管理面风险可接受。

结论：**输入验证的重灾区集中在"把外部输入直接交给数据库查询"与"数值参数未做有限域校验"两类**。

### 2.2 limit 数值解析的 NaN 路径（S7）

现状（`get-alerts/index.js:66-69`）：

```js
const limit = Math.min(
  parseInt(event?.query?.limit || event?.limit || '20', 10),
  100
);
```

`broadcast-a2a/index.js:301` 同型：`const limit = parseInt(url.searchParams.get('limit') || '20', 10);`

风险机理：当调用方传入非数字字符串（如 `limit=abc`）或对象时，`parseInt` 返回 `NaN`，`Math.min(NaN, 100)` 仍为 `NaN`；随后 `getLatestAlerts(NaN)` 内部执行 `sorted.slice(0, NaN)`，JavaScript 规范下返回**空数组**。后果不是崩溃而是"静默降级"——端侧轮询持续收到空 items，符合"首屏永不空白"约束的演示卡逻辑会长期展示演示态，且无任何报错线索，排查困难。另注意 `get-alerts/index.js:50` 的 `slice(0, limit)` 在 limit 为 0 或负数时同样返回空。

修复代码（两处同改）：

```js
function parseLimit(raw, def = 20, max = 100) {
  const n = parseInt(raw, 10);
  if (!Number.isFinite(n) || n <= 0) return def; // NaN/0/负数全部回退默认值
  return Math.min(n, max);
}

// get-alerts/index.js 入口改为：
const limit = parseLimit(event?.query?.limit || event?.limit);
// broadcast-a2a/index.js HTTP 分支改为：
const limit = parseLimit(url.searchParams.get('limit'));
```

### 2.3 generate-tts 的 text 无长度上限（S8）

`generate-tts/index.js:352-354` 仅校验 `if (!text)`。text 是 TTS 计费与额度的直接驱动（`generate-tts/index.js:34-36` 按 `textLength * 2.5` 记账），超长 text 会直接放大百炼额度消耗，且 WebSocket 30 秒超时（`generate-tts/index.js:201-205`）注定超长文本播不完，属于"花了钱也没结果"的无效输入。修复：

```js
const TTS_MAX_TEXT = 500; // 适老化播报单卡文本远小于此，取宽裕上限
if (typeof text !== 'string' || text.length === 0) {
  return { success: false, error: 'text is required' };
}
if (text.length > TTS_MAX_TEXT) {
  return { success: false, error: 'text too long' };
}
```

### 2.4 阈值与数值入参

`fetch-tushare-data/index.js:21` `THRESHOLD = parseFloat(process.env.ALERT_THRESHOLD || '5.0')`：环境变量属可信面，且 `parseFloat` 失败回退 `'5.0'`，可接受。建议追加下限保护（`Math.min(Math.max(THRESHOLD, 1), 20)`），防止误配 `0` 导致全市场股票进入告警流、稀释信号价值——这是运营配置错误防御，不是外部输入风险。

## 三、东财返回数据格式验证（重点审查项）

### 3.1 现状校验点

东财数据在 `fetch-tushare-data/index.js` 中的处理链路：`fetchEastMoneyMarket()`（94-129 行，本批次并发编辑新增的按市场串行分页函数）逐页请求 `https://80.push2.eastmoney.com/api/qt/clist/get?...`（100 行），现有校验包括：

- 103 行：`if (!data || !data.data || !data.data.diff) break;` —— 三层存在性校验；
- 105 行：`if (stocks.length === 0) break;` —— 空页退出；
- 110 行：`if (!code || !name) continue;` —— 字段缺失跳过；
- 122-125 行：单页 try/catch，失败 break 该市场，不影响其他市场。

Tushare 侧：`callTushare`（144-165 行）在 159 行校验 `data.code !== 0` 并抛错；`getDailyMovers`（397-441 行）在 412 行校验 `dailyResult.items` 为非空数组、415-419 行以 `fields.forEach` 把行数组映射为对象。DKnowC 合规检查侧：476 行 `data.safeType || 'Unknown'` 兜底。

骨架是健全的，但有三个具体缺口。

### 3.2 缺口一：diff 的两种形态未归一化

东财 `clist/get` 接口在不同参数组合下，`data.diff` 历史上存在**数组**与**以序号为键的对象**（`{"0":{...},"1":{...}}`）两种返回形态。当前代码 104 行取到 `stocks` 后直接使用 `stocks.length` 与 `for (const s of stocks)`：

- 若 diff 是对象：`stocks.length` 为 `undefined`，`undefined === 0` 为 false 不退出；`for...of` 对普通对象抛 `TypeError: stocks is not iterable`，被 122 行 catch 捕获后该市场整体放弃——表现为"名称映射悄悄变少"，与 S7 同属静默降级。
- 若 diff 是数组：行为正确。

修复代码（放在 103 行之后）：

```js
let diff = data.data && data.data.diff;
if (diff && !Array.isArray(diff) && typeof diff === 'object') {
  diff = Object.values(diff); // 兼容东财旧版对象字典形态
}
if (!Array.isArray(diff) || diff.length === 0) break;
const stocks = diff;
```

### 3.3 缺口二：f12/f14 字段类型未归一化

107-110 行直接 `const code = s.f12; ... code.startsWith('6')`。东财在 `fltt=2` 下字段通常为字符串，但若上游参数变动返回数值，`code.startsWith` 会抛 `TypeError`，同样被外层 catch 吞成整市场放弃。修复：

```js
const code = String(s.f12 ?? '');
const name = String(s.f14 ?? '').trim();
if (!code || !name) continue;
```

同时建议对 name 做长度钳制（`name.slice(0, 16)`）与控制字符剔除，防止异常数据经 `createAlertItems`（493-543 行）进入 headline 并最终展示在适老化大字卡片上——端侧 `entry/src/main/ets/pages/Index.ets` 的卡片流会直接渲染该字段。

### 3.4 缺口三：Tushare fields/items 长度不匹配

415-419 行 `dailyResult.fields.forEach((field, i) => { obj[field] = row[i]; })`：若某行 `row` 短于 `fields`，对应字段为 `undefined`，随后 429 行 `parseFloat(item.pct_chg || 0)` 已有兜底，风险可控；但若 `fields` 或 `items` 缺失（Tushare 限流时偶发返回畸形结构），412 行的判断可拦截。此处**结论为已覆盖**，无需改动，仅建议在 412 行前补充一行 `Array.isArray(dailyResult.fields)` 的对称校验以保持风格一致。

## 四、错误信息脱敏

### 4.1 已有的正确实践

- `fetch-tushare-data/index.js:160-162`（callTushare 内）：

```js
// 脱敏：避免 error message 中泄露 token 信息
const safeMsg = (data.msg || '').replace(TUSHARE_TOKEN, '***');
throw new Error(`Tushare API error: ${safeMsg || data.code}`);
```

这是全库唯一的主动脱敏点，方向正确：Tushare 失败响应（如 40101 token 失效）可能回显请求中的 token，替换后再抛出。

- `fetch-tushare-data/index.js:61`：JSON 解析失败时只带出 `body.length` 而非响应体内容——避免把第三方错误页原文透传，写法值得肯定。

### 4.2 局限与增强

`String.prototype.replace` 只替换**完整出现**的 token 原文一次。若上游回显的是 URL 编码形式或其他编码变体，替换会漏。建议升级为"全量抹除 + 长度截断"的工具函数，供三处出站调用（Tushare/东财/DKnowC）统一使用：

```js
function sanitizeMsg(msg, secrets, maxLen = 200) {
  let out = String(msg || '');
  for (const s of secrets) {
    if (s && s.length >= 8) {
      out = out.split(s).join('***');
      out = out.split(encodeURIComponent(s)).join('***');
    }
  }
  return out.slice(0, maxLen);
}
// callTushare 内改为：
throw new Error(`Tushare API error: ${sanitizeMsg(data.msg, [TUSHARE_TOKEN]) || data.code}`);
```

### 4.3 错误信息外泄面（S4）

三个函数把内部异常的 `e.message` 原样放进返回值：

- `fetch-tushare-data/index.js:730`：`return { success: false, error: e.message, ... }`；
- `push-token-register/index.js:98`：`return { success: false, error: e.message };`
- `broadcast-a2a/index.js:274`（Event 入口）与 `310`（HTTP 500 响应体）：`error: e.message`。

云函数的返回值会经 HTTP 访问服务或 callFunction 直达调用方；`e.message` 可能包含内部路径、SDK 报错细节、上游域名等拓扑信息（如 `Request timeout`、`JSON parse failed: ...`、SDK 连接错误）。对公网可达的 `get-alerts`/`broadcast-a2a` HTTP 面而言，这属于信息泄露纵深防御缺失。修复原则：**对调用方只给稳定错误码，细节只落日志**：

```js
// broadcast-a2a HTTP 分支（307-311 行）改为：
} catch (e) {
  console.error('HTTP handler error:', e.message); // 细节进日志
  res.writeHead(500, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ success: false, error: 'INTERNAL_ERROR' })); // 对外只给码
}
```

`fetch-tushare-data` 与 `push-token-register` 的调用方是自家端侧与兄弟函数，可在 AlertPoller 侧容错的前提下保留 `e.message`，但建议同时附 `errorCode`（如 `NO_TOKEN` / `UPSTREAM_TIMEOUT`），为端侧降级提示提供稳定判据。

## 五、e.stack 移除

### 5.1 全库扫描结果

执行命令：`grep -n "e\.stack" */index.js`，输出仅一行：

```
fetch-tushare-data/index.js:285:    console.log('EastMoney API failed:', e.message, e.stack);
```

即 285 行是全库唯一残留点（位于 `getStockNameMap` 的东财刷新 catch 块内）。

### 5.2 风险机理

1. **信息泄露**：堆栈包含模块绝对路径（如 `/var/user/index.js:285`）、函数名链、依赖内部帧，能刻画云函数目录结构与依赖版本，放大 S4 的泄露面。
2. **日志噪音**：东财名称刷新是可降级路径（284-286 行 catch 后继续走存储缓存→硬编码映射五级降级），此处属于"预期内的失败"，打印整段堆栈干扰日志巡检。
3. **合规口径**：本项目合规红线要求不泄露密钥与内部结构信息；堆栈属于后者。

### 5.3 修复代码

```js
// fetch-tushare-data/index.js:284-286 改为：
} catch (e) {
  console.log('EastMoney API failed:', sanitizeMsg(e.message, [TUSHARE_TOKEN]));
}
```

若排查期确需堆栈，用环境变量门控而非直接删除：

```js
if (process.env.DEBUG_STACK === '1') {
  console.log('EastMoney API stack:', e.stack);
}
```

验收口径：`grep -rn "e\.stack" cloudfunctions/functions/*/index.js` 输出为空（或在 DEBUG_STACK 门控块内）方为通过。**本会话未改源码**（写手席位只产文档，且工作副本正被并发修改，避免编辑冲突），该补丁需由代码席位落地后复跑上述命令验证。

## 六、日志安全

### 6.1 P0：push-token-register 全量 event 落日志（S1）

`push-token-register/index.js:81`：

```js
console.log('push-token-register invoked:', JSON.stringify(event));
```

端侧 PushService 上报的 event 即 `{ token, bundleName }`，此行把**设备 Push Token 明文写入云函数日志**。Push Token 等同于"向这台设备投递通知"的能力凭证，落日志后：日志平台所有有读权限的人/系统都可获得；日志常被导出、归档、进入排障工单，泄露半径远超数据库。注意同文件 47、59 行已经正确使用了 `token.substring(0, 20) + '...'` 的截断风格，唯独入口日志漏防。修复：

```js
console.log('push-token-register invoked:', JSON.stringify({
  token: typeof event?.token === 'string'
    ? event.token.substring(0, 8) + '***'   // 只留前8位用于关联排查
    : 'invalid',
  bundleName: event?.bundleName,
  tokenLen: typeof event?.token === 'string' ? event.token.length : 0,
}));
```

### 6.2 全库日志脱敏审计结论

执行命令：`grep -n "console\." */index.js | grep -i "token\|key\|secret"`，逐行核验后分类：

**正确的样例（保持不动）**：

- `push-token-register:47/59`：token 截断到 20 字符；
- `fetch-tushare-data:616`：`token: TUSHARE_TOKEN ? 'set' : 'not set'`——只报状态不报值，标准范式；
- `generate-tts:344-348`：text 截断 50 字符、只记 alertId；
- `broadcast-a2a:225`：Push 响应截断 200 字符；OAuth 响应中的 access_token 只校验存在性（183-187 行）从不打印；
- DKnowC 的 `api-key`、百炼的 `Bearer` Key 均只存在于请求头（`fetch-tushare-data:466`、`generate-tts:195`），无任何打印点。

**唯一不合规点**：即 6.1 的 S1。

### 6.3 日志规范清单（建议写入团队规约）

1. 禁止打印：任何 Token/Key/Secret 值、完整 event/请求体、堆栈、设备标识全文。
2. 标识类字段一律截断（前 8~20 位 + `***`）或哈希（SHA256 前 8 位）。
3. 状态化表述优先：`'set' / 'not set'`、计数、长度、耗时。
4. 可降级路径的失败用单行 message，不打堆栈；堆栈必须门控在 `DEBUG_STACK` 之后。
5. `broadcast-a2a:286` 打印 `req.url`——当前仅 `limit` 一个参数无敏感值，但若未来加 query 传参，须先套用本清单第 1 条。

## 七、注入风险

### 7.1 P0：NoSQL 操作符注入（S2）

`push-token-register/index.js:38`：

```js
const existing = await collection.where({ token }).get();
```

`token` 直接来自 event 解构（83 行），仅做过非空校验。云函数 event 是 JSON 对象，调用方完全可以把 `token` 构造成对象：`{ "token": { "$ne": null } }`。此时查询条件变成"token 不等于 null"，**匹配集合内全部文档**，后续 42-47 行会把命中的第一条文档的 `lastReportTs` 更新——攻击者无需知道任何真实 Token 即可污染/触碰任意设备记录；同理 `{ "$regex": "^a" }` 一类操作符也可被注入。这是文档数据库场景最典型的操作符注入。修复（类型白名单 + 格式校验一并解决长度滥用）：

```js
const TOKEN_RE = /^[A-Za-z0-9_\-:.]{10,4096}$/; // 华为Push Token字符集的保守白名单
if (typeof token !== 'string' || !TOKEN_RE.test(token)) {
  return { success: false, error: 'token format invalid' };
}
if (typeof bundleName !== 'string' || bundleName.length > 128) {
  return { success: false, error: 'bundleName format invalid' };
}
```

校验通过后 `token` 已确保是字符串，`where({ token })` 不再可注入。对照：`broadcast-a2a:156` 与 `push-token-register:72` 的 `where({ active: true })` 为硬编码常量，无注入面。

### 7.2 其余注入面盘点（均为通过）

执行命令 `grep -n "eval(\|child_process\|exec(\|execSync" */index.js`，输出 `NONE`：全库无动态代码执行、无 Shell 调用。

- **URL 注入**：东财 URL 拼接处 `fetch-tushare-data:100` 对市场过滤器使用了 `encodeURIComponent(fs)`，且 `fs` 来自 221 行硬编码数组；`broadcast-a2a:190` 的 pushUrl 中 `PROJECT_ID` 来自环境变量（可信面）。
- **SQL 注入**：不适用——数据层为 CloudBase 文档数据库与存储 JSON，无 SQL 拼接。
- **路径遍历**：上传路径均为固定前缀 + 程序生成的键（`generate-tts:57` 缓存键为 text 的 SHA256 前 16 位；`fetch-tushare-data:506/558` 固定 `alerts/alerts.json`），无用户可控路径分量。
- **头注入**：请求头均为字面量或环境变量拼接，无 event 参与。
- **合规注入（内容面）**：播报文本由 `createAlertItems` 用模板字符串固定句式生成（514-521 行"涨了/跌了/横盘"），变量仅 name 与数字，且信号卡经 DKnowC 合规检查（456-488 行）与三禁校验（AGENTS.md §二.2），文案面不承载外部自由文本——与"不承诺收益/保本、不输出催促性指令"的红线一致。

## 八、密钥治理与合规红线自查

1. `cloudfunctions/.env` 存在（943 字节，Sep 21 16:52），根目录 `.gitignore` 明确包含 `cloudfunctions/.env` 与 `.env` 两行（注释："P1 安全修复：环境变量文件（绝不入库）"）——**凭据不入库已落实**。
2. 执行命令 `grep -rl "TUSHARE_TOKEN\s*=\s*'" --include="*.js" cloudfunctions/functions/`，输出为空：无硬编码 Token。
3. 六个函数的密钥全部走 `process.env`：`TUSHARE_TOKEN`、`DKNOWC_API_KEY`（fetch-tushare-data:20/24）、`DASHSCOPE_API_KEY`（generate-tts:20）、`SUPABASE_ANON_KEY`、`HUAWEI_PUSH_CLIENT_SECRET`（broadcast-a2a:19/144）。唯一硬编码兜底是 `generate-tts:19` 的 workspace id（非密钥，低敏，S9）。
4. 本文自身不含任何密钥值，符合"不泄露任何Token/密钥"红线；全文不涉及收益承诺类内容，不推翻架构基调。

## 九、HTTP 暴露面专项：CORS、未鉴权端点与攻击面最小化

### 9.1 公网可达面盘点

云函数经 CloudBase HTTP 访问服务暴露后，真正公网可达的入口有两个：

- `get-alerts`：按头注释（`get-alerts/index.js:15-16`）以 `--path /alerts` 挂载，供端侧 AlertPoller 轮询。只读、无副作用，被滥用的最坏后果是**读放大**——攻击者高频轮询拉空 alerts.json，函数按 `timeout: 10`（cloudbaserc.json）秒计费，产生费用与日志噪音。
- `broadcast-a2a`：`index.js:284-316` 在 `PORT` 环境变量存在时自建 HTTP 服务器（scf_bootstrap 启动 Web 函数模式）。**POST 也可触发**（285 行处理任意 method，293 行仅对 OPTIONS 特判），即公网调用方可驱动 `handleBroadcast` → 逐条 `sendPushNotification`——虽然 Push 发送需要 AGC 凭证齐备（146 行未配置即跳过），但一旦生产配齐，此端点等于把"向全体设备推送"的能力暴露给任意公网来源。

### 9.2 CORS 通配符评估

`broadcast-a2a/index.js:289-291` 三个响应头全部放通：`Access-Control-Allow-Origin: *`。风险界定要准确：CORS 是**浏览器侧**约束，`*` 意味着任意网页的脚本可读取该端点响应；它不拦截 curl/脚本化调用（那些根本不发预检）。对本端点的实际影响：任意第三方网页可以用已登录用户的浏览器作为跳板读取异动数据（低敏）并隐性触发广播（副作用）。修复建议分两级：

- 低成本：删掉 POST 支持，Web 面只留 GET 只读语义；
- 正解：加共享密钥头校验（端侧与云函数约定 `X-App-Key`，从环境变量读取比对），并按包名收敛 CORS 白名单。

### 9.3 攻击面最小化清单

| 端点 | 现状 | 建议 |
| --- | --- | --- |
| get-alerts HTTP | 未鉴权只读 | 保留；加每秒限流（CloudBase 网关层）或前端 CDN 缓存 3-5 秒 |
| broadcast-a2a Web | 未鉴权可 POST 触发推送 | 必须加共享密钥；生产可整体下线 Web 模式改定时触发 |
| push-token-register | 未鉴权写库 | 修 S2 后写入受格式白名单约束，可接受；建议再加 bundleName 白名单 |
| generate-tts | 仅函数间调用 | 保持不暴露 HTTP；text 长度上限（S8）落地前警惕额度放大 |
| fetch-tushare-data | 定时触发 | 不消费 event，风险最低，无需改动 |
| init-db | 一次性 | 建议执行后从 cloudbaserc.json 移除或加禁用标记 |

## 十、密钥轮换与应急响应预案

### 10.1 轮换矩阵

本会话实测的密钥消费点（全部 `process.env`）：`TUSHARE_TOKEN`（fetch-tushare-data:20）、`DKNOWC_API_KEY`（:24）、`DASHSCOPE_API_KEY`（generate-tts:20）、`SUPABASE_ANON_KEY`（broadcast-a2a:20）、`HUAWEI_PUSH_CLIENT_ID/CLIENT_SECRET/PROJECT_ID`（broadcast-a2a:142-144）。轮换操作互不阻塞、可独立执行：改 `cloudfunctions/.env` 或平台控制台环境变量 → 重新部署对应函数 → 旧值作废。**唯一依赖时序的是华为 Push 三元组**：PROJECT_ID/CLIENT_ID/CLIENT_SECRET 需同步更换，缺一会让 146 行守卫直接跳过推送（静默降级，非报错——排查时注意这个表现）。

### 10.2 泄漏应急剧本

若日志平台或工单中发现 Token 外泄：第一小时内在上游控制台吊销并换新（Tushare/百炼/DKnowC 均支持即时作废）；对华为 Push 泄漏额外评估 push_tokens 集合是否被灌入外来设备（67-75 行 `getActiveTokens` 会把库内所有 active token 作为推送目标，攻击面在"写"不在"读"）；事后用第七节的 grep 清单复核代码没有回潮。

## 十一、修复优先级与验收清单

### 11.1 修复顺序

1. **P0（当日）**：S1 日志泄漏、S2 操作符注入、S3 e.stack 移除——三处都是几行的改动。
2. **P1（本周）**：S4 错误码化返回、S5 东财形态归一化、S6 状态码与体积上限、broadcast-a2a Web 面鉴权（第九节）。
3. **P2（随版本）**：S7 limit 兜底、S8 text 上限、S9 workspace id 环境变量化。

### 11.2 验收命令清单（代码席位落地后逐条复跑）

```bash
# S1/S3：两条 grep 均应无输出（或仅在 DEBUG 门控内）
grep -rn "JSON.stringify(event)" cloudfunctions/functions/*/index.js
grep -rn "e\.stack" cloudfunctions/functions/*/index.js
# S2：确认 push-token-register 有 typeof token 校验
grep -n "typeof token" cloudfunctions/functions/push-token-register/index.js
# S6：确认 statusCode 校验存在
grep -n "statusCode" cloudfunctions/functions/fetch-tushare-data/index.js
# 语法完整性（需 Node 环境）
node --check cloudfunctions/functions/fetch-tushare-data/index.js
```

### 11.3 本会话检查状态汇总

| 检查 | 状态 | 备注 |
| --- | --- | --- |
| 6 文件全文审读 | 已执行 | Read 工具逐行 |
| grep 系列静态扫描 | 已执行 | 命令与输出已在上文引用 |
| Python 词法扫描（括号/循环深度） | 已执行 | 结果见 integrity.md 同批产出 |
| node --check | 未运行 | 本机无 node（`node: command not found`） |
| 运行时注入复现（真实调用） | 未运行 | 未部署云函数，属代码席位验收项 |

## 十二、审计留痕与复查节奏

本审查的结论有半衰期：代码在演进（本会话已亲历六个云函数两小时内被并发修改），今日通过项可能明日回潮。建议把复查固化为三档节奏。第一档是每次合并前的机器闸门：把 11.2 节的 grep 断言接进流水线，任何一条命中即阻断，成本最低、防回潮最有效。第二档是每周一次的人工抽查：重点盯新增 console 语句与新增 where 查询，这两类是历史问题的两大温床，抽查范围小、二十分钟可完成。第三档是每月全量复审：按本文目录重跑一轮并对照风险表销号，同时复查依赖与环境变量清单是否出现新的密钥消费点。所有档位共用同一份验收命令，保证口径一致。另建议把本文的风险编号（S1-S9）登记进问题跟踪系统，修复时引用编号、复审时按编号销号，避免同一问题在不同批次里被反复发现、反复修复、反复遗漏。

### 自我评估
- 正确性：4分——全部发现均以本会话实际执行的 grep/Read/Python 扫描输出为据，行号锚定 735 行快照并给出 md5；风险机理（NaN 路径、操作符注入、idle 超时语义等）为 JavaScript/Node 语义可推导结论；但未做运行时复现，注入可行性为静态推断。
- 完整性：4分——覆盖任务指定的四要素（输入验证/东财格式验证/脱敏/e.stack/日志/注入）并含密钥治理与验收清单；运行时类检查（部署后日志审计）只能给步骤未给结果。
- 可复用性：5分——修复代码均为可直接粘贴的片段，附全库验收命令与日志规约清单，可整体沉淀为团队安全基线。
- 字数：约4500字（正文汉字实测4482）
- 使用模型：GLM-5.3-Flash
