# code技能：ArkTS云函数开发模式——requestHttps封装、CloudBase单例、错误降级链

> 编写时间：2026-09-23
> 编写席位：Moon席位批次写手-B组-1号（GLM-5.3-Flash）
> 适用范围：harmony-app（铃语）项目 `cloudfunctions/functions/` 下全部 CloudBase 云函数的编写、审查与重构
> 前置事实：本文所有代码引用均来自仓库现网文件，路径可直接定位；无源码支撑处会显式标注"规划"。

## 0. 项目背景与硬约束（自包含说明）

铃语是鸿蒙适老化股票异动播报应用，架构为「纯ArkTS端侧 + CloudBase云函数服务端」。端侧 `Index.ets` 以 5 秒前台轮询（`entry/src/main/ets/services/AlertPoller.ets`）拉取 `FEED_URL`，契约即 `AlertFeed`（`entry/src/main/ets/model/AlertItem.ets:19-22`）。数据源地址默认指向 CloudBase 云函数 HTTP 端点：`DEFAULT_FEED_URL = ${CLOUDBASE_BASE_URL}/alerts`（`entry/src/main/ets/services/SettingsService.ets:27`），基础域名为 `https://a2a-commonwealth-d2eepjr928e9c4d-1475054847.ap-shanghai.app.tcloudbase.com`（同文件 24 行）。

云函数承担四类职责：行情拉取（`fetch-tushare-data`）、异动聚合（`get-alerts`）、TTS 生成（`generate-tts`）、推送广播（`broadcast-a2a`），另含 `push-token-register`、`init-db`。已知问题须内化进设计：Tushare token 失效（错误码 40101）已降级东方财富 API；百炼 TTS 只支持 WebSocket（`cloudfunctions/functions/generate-tts/index.js:6,16`）；`broadcast-a2a` 的 Push 通道需换华为 Push Kit REST；`alerts.json` 中 `audioUrl` 为 undefined 时由端侧按需调 `generate-tts`。

合规红线（云函数同样适用）：不承诺收益/保本、不输出催促性指令、不涉对外公开/收费、不泄露任何 Token/密钥。

## 1. requestHttps 统一封装规范

### 1.1 为什么禁用 fetch

CloudBase Node 运行时的 `fetch` 属实验性实现，存在字段行为不一致、超时不可控、无法精细监听流式错误等缺陷。云函数的执行计费与总超时是硬边界，网络请求必须自带超时与错误语义。因此规定：**云函数内一律使用 Node 内置 `https` 模块封装的 `requestHttps`，禁止直接调用 `fetch()`**。

### 1.2 标准实现（逐段讲解）

```javascript
// 云函数内通用 HTTPS 请求封装（返回 Promise<object>）
function requestHttps(url, options = {}) {
  return new Promise((resolve, reject) => {
    const https = require('https');
    const urlObj = new URL(url);
    const reqOptions = {
      hostname: urlObj.hostname,
      path: urlObj.pathname + urlObj.search,   // 显式拼接查询串
      method: options.method || 'GET',
      headers: options.headers || {},
    };
    const req = https.request(reqOptions, (res) => {
      let body = '';
      res.on('data', (chunk) => { body += chunk; });
      res.on('end', () => {
        try { resolve(JSON.parse(body)); }
        catch (e) { reject(new Error(`JSON parse failed: ${e.message}`)); }
      });
      res.on('error', reject);                 // 响应流本身的错误也要接住
    });
    req.on('error', reject);                   // 只监听真实存在的 'error' 事件
    req.setTimeout(options.timeout || 15000, () => {
      req.destroy(new Error('Request timeout')); // destroy(err) 会触发上面的 error 回调
    });
    if (options.body) req.write(options.body);
    req.end();
  });
}
```

四个易错点，审查时逐条核对：

1. **事件名必须是 `'error'`**。历史文档曾出现 `req.on('error+timeout', reject)` 这种写法，Node 没有该事件名，监听形同虚设，超时会静默漏掉。超时走 `setTimeout` 回调里 `req.destroy(new Error(...))`，销毁错误会转发到 `error` 处理器统一 reject。
2. **超时默认 15 秒**，且每个调用点可覆盖（见 1.4 超时表）。云函数总执行时长有限，单请求超时必须小于函数总预算。
3. **JSON 解析失败按异常处理**，不允许把半截 JSON 当有效数据继续走。端侧对解析失败同样按失败计并记原文前 200 字符（`AlertPoller.ets:67-71`），两端语义对齐。
4. **`res.on('error')` 不可省**。请求建立后响应流仍可能中断，只挂 `req.on('error')` 会漏接这类失败。

### 1.3 带重试的版本（指数退避）

```javascript
async function requestHttpsRetry(url, options = {}, maxRetries = 2) {
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await requestHttps(url, options);
    } catch (e) {
      if (attempt === maxRetries) throw e;
      const delay = 500 * Math.pow(2, attempt);   // 500ms → 1s → 2s
      console.log(`retry ${attempt + 1}/${maxRetries} in ${delay}ms: ${e.message}`);
      await new Promise(r => setTimeout(r, delay));
    }
  }
}
```

重试纪律：**只对幂等的读请求重试**（行情查询、名称映射、日历）；写操作与推送类请求默认不重试，防止重复副作用；4xx 业务错误（如鉴权失败）不该靠重试解决，40101 类 token 失效要走降级链而非重试轰炸。

### 1.4 超时基准表

| 调用对象 | 超时 | 重试 | 理由 |
| --- | --- | --- | --- |
| Tushare 日线接口 | 15s | 最多2次 | 数据量中等，主数据源 |
| 东方财富分页列表 | 15s | 最多2次 | 每页100条，是降级主力（`fetch-tushare-data/index.js:100`） |
| 百炼 TTS WebSocket | 15s | 不重试 | 长连接另见 generate-tts 内部超时与"部分音频"兜底（`index.js:202,296`） |
| 华为 Push OAuth/发送 | 10s | 不重试 | 认证与下发需快速失败，由 broadcast 层面另行补偿 |
| 合规检查类旁路 | 10s | 不重试 | 非阻塞流程，超时可跳过 |

## 2. CloudBase SDK 单例模式

### 2.1 问题

`@cloudbase/node-sdk` 的 `cloudbase.init()` 每调用一次就创建一个新实例。云函数实例是跨调用复用的（实例暖存期间 module 作用域存活），若在 handler 体内反复 `init`，会叠加连接与初始化开销，极端情况下拖垮函数执行时长。

### 2.2 标准单例

```javascript
// 模块级缓存：同一云函数实例内只 init 一次
let _cloudbaseApp = null;
function getCloudbaseApp() {
  if (!_cloudbaseApp) {
    const cloudbase = require('@cloudbase/node-sdk');
    _cloudbaseApp = cloudbase.init({
      env: process.env.TCB_ENV || 'a2a-commonwealth-d2eepjr928e9c4d',
    });
  }
  return _cloudbaseApp;
}
```

使用规则：

- **禁止**在 handler 函数体内直接调用 `cloudbase.init()`；
- **必须**通过 `getCloudbaseApp()` 取实例；数据库、存储、云调用一律经该实例发起；
- **每个云函数各自持有一份**该定义——云函数之间不共享 module 作用域，不要幻想抽一个公共文件就全局单例；
- 环境变量 `TCB_ENV` 优先，缺省回退到项目实际环境 ID（该 ID 已出现在端侧 `SettingsService.ets:24` 的域名里，不属于密钥）；
- 冷启动时首次调用会付出 init 成本，属预期；不要为了"预热"在模块顶层就 init 并阻塞加载，惰性获取即可。

### 2.3 存储访问注意

经单例访问 CloudBase 存储（如 `alerts.json`、股票名称缓存）时，读到的内容要按"不可信外部数据"处理：JSON 解析包 try-catch，结构字段逐一判空。写回时必须带并发保护（见第 4 节）。

## 3. 错误降级链设计

### 3.1 设计原则

云函数每个外部依赖都可能失败，核心功能（端侧能拿到一份可解释的异动列表）必须活到最后。降级链模板：

```
主数据源 → 降级源1 → 降级源2 → 过期缓存 → 硬编码兜底 → 有效空值
```

四条硬规则：

1. **每层独立 try-catch**，一层失败只影响自己，不允许异常冒泡中断整条链；
2. **失败即落下一层**，不做无谓等待（除非该层自带短超时）；
3. **每次降级必须留日志**，例如 `console.log('tushare degraded to eastmoney')`——没有日志的降级等于线上黑箱；
4. **终点必须是"有效空值"**（空数组/空 Map/空对象），禁止把 null/undefined 抛给端侧，端侧 `AlertPoller` 对畸形数据只能整轮作废（`AlertPoller.ets:64-72`）。

### 3.2 本项目现网降级链实例

**行情数据源链**：Tushare `daily` 接口 →（40101 token 失效或网络异常）→ 东方财富行情 API（现网 `fetch-tushare-data/index.js:100` 的分页拉取、272 行 `source: 'eastmoney'` 标记）→ 端侧演示卡兜底（`Index.ets:13-23` 的 `DEMO_ITEMS`，首屏永不空白约束的最后一环）。

**股票名称映射链**：内存缓存（24h TTL）→ CloudBase 存储缓存（24h TTL）→ 东方财富 API → 过期存储缓存（聊胜于无）→ 硬编码映射 → 空 Map。名称缺失时 headline 退化为纯代码展示，不能因名字缺失丢弃异动。

**交易日历链**：内存缓存（1h TTL）→ Tushare `trade_cal` → 本地日期推算（工作日/最近周五）。判断"今天是否开市"是轮询前置闸门，这条链保证它永不阻塞。

**TTS 链**：百炼 WebSocket 正常合成 → 超时/异常时若已收到部分分片则用"部分音频"拼装（`generate-tts/index.js:296`）→ 端侧按需重调；`alerts.json` 里 `audioUrl` 为 undefined 时，端侧按需调 `generate-tts` 补齐，卡片上无播报钮即静默无音频。

### 3.3 降级链的端侧镜像

服务端降级与端侧降级要成对设计：端侧 `refresh()` 在 `ok=false` 时**保持当前数据不清空**，连续 2 次失败才置 `connectionBroken` 提示"连接中断，显示旧数据"（`Index.ets:194-198`）；429 限流静默跳过不惊动用户（`AlertPoller.ets:44-49`）。云函数在高压时返回 429 是合法的降级信号，不要把它当故障报警。

## 4. 并发写入保护与确定性 ID

### 4.1 多实例写同一文件的防覆盖

云函数水平扩出多实例同时写 `alerts.json` 时会互相覆盖。防覆盖两板斧：

```javascript
// 其一：serverTs 新鲜度检查——存量比增量还新就放弃写入
const currentLatestTs = alerts.length > 0 ? Math.max(...alerts.map(a => a.ts)) : 0;
if (existingServerTs > currentLatestTs) {
  console.log(`skip write: existing serverTs=${existingServerTs} > latest=${currentLatestTs}`);
  return;
}
```

```javascript
// 其二：按 alertId 去重合并，新盖旧，截断保留最新500条
const alertMap = new Map();
for (const item of existingItems) alertMap.set(item.alertId, item);
for (const a of alerts) alertMap.set(a.alertId, a);
const merged = Array.from(alertMap.values()).sort((a, b) => b.ts - a.ts).slice(0, 500);
```

### 4.2 确定性 ID

- ID 由业务关键字段拼出，如 `${symbol}_${ts}`——同一股票同一秒天然唯一；
- **禁止** `Math.random()` 参与 ID 生成：碰撞会导致去重时丢数据，且不可复现、不可排查；
- ID 保持人类可读，日志里一眼定位。

## 5. 出口契约、日志与密钥安全

1. **响应形状统一**：`{ code, message, data }` 或与端侧约定的 `AlertFeed` 原形（`items` + `serverTs`），错误码枚举固化进文档，禁止随手发明；
2. **Token 脱敏**：错误信息拼装前先替换，现网范式 `const safeMsg = (data.msg || '').replace(TUSHARE_TOKEN, '***')`（`fetch-tushare-data/index.js:161`）；日志只允许打 `token: TUSHARE_TOKEN ? 'set' : 'not set'`（616 行），密钥本体与 `e.stack`（可能带环境变量路径）一律不打；
3. **密钥只走环境变量**：`process.env.TUSHARE_TOKEN`（`index.js:20`），缺失时返回明确错误（618-621 行的 `TUSHARE_TOKEN not configured`），不要硬编码兜底密钥；
4. **输入校验**：外部 API 返回逐条验形，股票代码必须 `/^\d{6}$/`，名称非空且长度合理，不合规条目直接丢弃而不是带病入库。

## 6. 审查清单（云函数合入前过一遍）

- [ ] 全部 HTTPS 请求走 `requestHttps`/`requestHttpsRetry`，无 `fetch`；
- [ ] 每个请求显式设置超时，且小于函数总执行预算；
- [ ] `req.on('error')` 与 `res.on('error')` 均已挂载，超时用 `destroy(err)` 收口；
- [ ] CloudBase 实例经 `getCloudbaseApp()` 获取，handler 内无裸 `init()`；
- [ ] 每个外部依赖都有降级路径，降级发生时有日志，终点是有效空值；
- [ ] 共享文件写入有 serverTs 检查或去重合并，ID 为确定性生成；
- [ ] 日志无 Token/密钥/完整 stack；外部数据入库前已验形；
- [ ] 429/5xx 语义与端侧 `PollResult`（`AlertPoller.ets:10-14`）约定一致。

## 7. 冷启动、执行预算与模块作用域纪律

云函数实例跨调用存活，module 作用域里的变量（第 2 节单例、第 3 节内存缓存）在暖实例期间持续有效——这是它们存在的前提；但冷启动时全部归零，因此**任何正确性都不许依赖内存缓存的存活**：缓存只做加速器，不做唯一真源，唯一真源永远是 CloudBase 存储与外部 API。执行预算的纪律是"四段分账"：一次调用按「读外部 → 合并 → 写存储 → 返回」分段，每段独立超时，任何一段超时不拖垮整函数；串行外呼的超时总和必须给写存储与出口留出余量，否则出现"数据拉到了却没来得及写回"的白忙一轮。

## 8. 服务端外呼的安全边界

在 requestHttps 之上再叠两层硬校验，合入验收时逐条过：

1. **协议白名单**：仅允许 `http:`/`https:` 两个协议，`file:`、`data:` 等一律在发请求前拒绝——`requestHttps` 用 `new URL(url)` 解析后先判协议再建连接；
2. **目标地址校验**：请求发起前校验 host，**拒绝 localhost、环回地址（127.0.0.0/8、::1）、私有网段（10/8、172.16/12、192.168/16、169.254 链路本地）与保留地址**——云函数入参一旦可控 URL，不校验就是 SSRF 直通道；目标域名收敛为白名单常量表（api.tushare.pro、80.push2.eastmoney.com、百炼网关、华为 Push 域），不在白名单内的 host 直接拒绝并记日志；
3. **凭据零字面量**：源码、示例、测试里都不许出现可用的密钥字面量，一律 `process.env` 读取（第 5 节第 3 条的延伸，含测试用的假 token 也要写成显式占位符）。

## 9. 推送链路的云侧设计要点（broadcast-a2a 演进）

已知 broadcast-a2a 的 Push 通道需换华为 Push Kit REST，云侧规范四条：

1. **OAuth token 服务级缓存**：access_token 在有效期内以模块级变量复用，过期再取；取 token 单独 10s 超时、失败不重试——认证类失败重试没有意义；
2. **下发接口不做自动重试**：按 token 维度失败即记日志放行。推送是"尽力而为"通道，可靠性兜底由端侧 5 秒轮询完成（架构基调：轮询兜底，不可推翻）；
3. **端侧行为已定型，云侧对齐即可**：端侧 getToken 失败按官方可重试错误码白名单（1000900001/0008/0009/0011）最多 3 次、间隔 1s（`PushService.ets:14-17,64-72`）；AGC 未配置时探测 rawfile 缺失即静默降级轮询（`PushService.ets:100-107`）。云侧不因端侧未拿到 token 而重发轰炸；
4. **payload 只带 alertId**：音频地址由端侧拉 feed 获得，不在推送报文里塞大字段，报文瘦身同时降低敏感信息外泄面。

## 10. 标准 handler 骨架

```javascript
exports.main = async (event) => {
  try {
    const input = validate(event);              // 1. 入口校验：白名单参数、类型
    const data = await loadWithFallback(input); // 2. 降级链取数（第3节）
    await persistIfFresh(data);                 // 3. 新鲜才写、并发保护（第4节）
    return { code: 0, message: 'ok', data: shape(data) };  // 4. 固定出口
  } catch (e) {
    console.log('handler fatal:', e.message);   // 只打 message，不打 stack/token
    return { code: 500, message: 'internal error' };       // 对外不泄漏内部细节
  }
};
```

骨架四段论：校验、取数、落库、出口。新云函数一律从这份骨架起步再填业务；校验失败的出口 code 与内部异常的出口 code 必须可区分，端侧与运维才能分清"调用方错"还是"服务方错"。

### 自我评估
- 正确性：4分 核心范式取自现网 `fetch-tushare-data/index.js` 与端侧源码并逐处标注行号；修正了历史文档中 `error+timeout` 伪事件写法，该修正是依据 Node 事件语义判断的，未在本环境运行 Node 验证。
- 完整性：4分 三大主题（requestHttps/单例/降级链）均展开到代码级，另覆盖并发保护、确定性ID、日志安全与清单；generate-tts 的 WebSocket 细节仅引用未展开（属另篇范围）。
- 可复用性：4分 封装代码可直接粘贴进新云函数，超时表与审查清单可直接作为 CR 模板；单例需每函数复制一份的约束已显式说明。
- 字数：约3100字
- 使用模型：GLM-5.3-Flash
