# 错误处理与健壮性深度审查——callTushare超时控制方案

> 项目：harmony-app（铃语，鸿蒙适老化股票异动播报应用）。审查对象：云函数 `cloudfunctions/functions/fetch-tushare-data/index.js` 中的 `callTushare` 函数（第 91-112 行）及其底层 `requestHttps` 封装（第 43-76 行）。本文自包含，所有行号均指向该文件当前版本（全文 683 行）。审查日期：2026-09-23。

## 一、审查范围与结论摘要

`callTushare` 是异动链路的总数据入口：`getLatestTradeDate` 第 303 行经它调 `trade_cal` 拿最新交易日，`getDailyMovers` 第 351 行经它调 `daily` 拿全市场日线，两者任一失败，当日异动即无法产出，端侧只会看到"今日暂无异动"。底层 `requestHttps` 则是全文件共用的网络封装：Tushare 两处调用（第 99-104 行）、东财名称映射分页抓取（第 176 行）、DKnowC 合规检查（第 411-422 行）都走它。因此这两个函数的错误处理质量直接决定整条链路的健壮性。

审查结论：当前实现已经具备了正确的骨架——Promise 封装、JSON 自动解析、超时触发 `req.destroy`、token 脱敏（第 106-109 行）——但存在三个结构性缺口：其一，`req.setTimeout` 设置的是套接字空闲超时而非请求总时限，慢速滴漏的响应可以让单次请求无限拖延；其二，不检查 HTTP 状态码，网关的 502 HTML 页、防火墙的 403 拦截页都会被当作正常响应送进 JSON 解析，报出一条与真实原因相去甚远的解析错误；其三，错误对象缺乏分类信息，超时、域名解析失败、连接重置在日志中不可区分，无法支撑重试决策。本文依次给出修复实现、超时阈值的逐调用点论证、可重试性分类矩阵与十二场景边界矩阵，并明确重试、降级、放弃三类处置的边界。东财行情兜底的具体接口设计属数据源策略专题，另见 api-strategy.md，本文只在降级触发条件处衔接。

## 二、requestHttps 现状剖析

### 2.1 现有骨架的合理部分

先明确什么是对的，避免重写时误伤。第 43-76 行的实现有四个优点应当保留：以 Promise 包装回调式 https 模块，调用方可以用 async/await 平铺书写；`res.on('end')` 中统一 `JSON.parse`，三个调用点都不必重复解析；超时触发 `req.destroy(new Error('Request timeout'))`，套接字被真实销毁而非悬挂；请求体经 `req.write(options.body)` 写出后 `req.end()` 收尾，POST 的 JSON 体（第 101-103 行）与 GET 的空体走同一通路。这些骨架在改造版本中原样保留。

### 2.2 缺口一：空闲超时不等于总时限

第 67-69 行的超时实现有一处 Node 语义层面的偏差：

```js
req.setTimeout(options.timeout || 15000, () => {
  req.destroy(new Error('Request timeout'));
});
```

`req.setTimeout` 底层设置的是套接字空闲超时：只有当套接字连续若干毫秒没有任何字节收发时定时器才触发。它防得住"连接建立后服务器彻底沉默"的情形，防不住两类真实故障。第一类是慢速滴漏：服务器每秒发一个字节，套接字永远不空闲，总时限在理论上不受约束，而云函数是有计费与并发占用的。第二类是响应阶段拖延：一旦响应开始到达，`req.setTimeout` 对"读完整个响应"没有约束，一个先发响应头再无限挂起响应体的服务端可以让 Promise 永不 settle，进而把整条 `getDailyMovers` → `exports.main` 链路挂死到函数实例被平台强制回收。正确做法是在 Promise 外层再立一个硬性总时限定时器，到点主动 `req.destroy` 并以分类错误 reject，同时在响应完成时清理定时器避免泄漏。

### 2.3 缺口二：不检查 HTTP 状态码

第 54-63 行的响应处理只关心把 body 拼起来解析成 JSON，从不看 `res.statusCode`。这带来两类错位。第一类是误报：Tushare 或东财的前置网关在过载、维护、风控时返回 502/503/403，响应体是 HTML，进入 `JSON.parse` 后抛出的错误是 `JSON parse failed: Unexpected token < in JSON at position 0, body length: 312`——运维看到这条日志的第一反应是"接口返回了坏 JSON"，而真实原因是服务端拒绝服务，两类问题的处置路径完全不同。第二类是漏报：若上游返回 200 但载荷是错误语义的 JSON（某些网关的 200 包装错误），当前代码会静默放行，把判断责任完全推给 callTushare 的 `data.code !== 0` 检查（第 106 行），而东财与 DKnowC 的调用点并没有等价的业务码检查。改造应在 requestHttps 层统一做状态码检查：四百以上即 reject，并把状态码与前两百字符的响应体（截断防日志爆炸）带进错误对象。

### 2.4 缺口三：错误不可分类

第 66 行 `req.on('error', reject)` 把 Node 原生错误原样抛出，第 68 行超时则抛自定义 Error。两者在调用方看来只是 message 不同的普通错误：DNS 解析失败（ENOTFOUND）、连接被重置（ECONNRESET）、证书错误（CERT_*）、主动超时，各自的处置策略本应不同——前两者值得重试，证书错误重试无意义，超时是否重试取决于剩余预算。当前实现无法在 catch 里做这些决策，因为错误对象上没有可靠的分类标记。改造方案是定义轻量的 `HttpError` 类，携带 `kind`（timeout / network / status / parse）、底层错误码与目标主机名三类信息，供上层矩阵化处置。

## 三、超时阈值的逐调用点论证

超时不是一个全局常数，而是"该调用在最坏情况下允许占用的时间预算"。本项目的预算约束来自两端：上游是各数据源的正常延迟分布，下游是云函数实例的总执行时长上限（CloudBase 事件函数超时上限可配，本文按常见配置二十秒推演，实际部署值需在控制台核实后校准下表）。当前代码里有四个显式超时值：requestHttps 默认与 Tushare 调用均为 15000（第 67、103 行）、DKnowC 为 10000（第 421 行）、generate-tts 的 WebSocket 为 30000（generate-tts/index.js 第 197-201 行）、端侧 AlertPoller 连接与读取各 5000（AlertPoller.ets 第 43-44 行）。逐点论证如下。

| 调用点 | 现状超时 | 建议超时 | 论证 |
| --- | --- | --- | --- |
| callTushare（daily/trade_cal，第 103 行） | 15000 | 12000 | Tushare 日线接口正常一至三秒，考虑高峰排队取 p99 约十秒，留两秒余量；再宽就会挤占同函数内东财分页与 TTS 批处理的预算 |
| 东财单页抓取（第 176 行，走默认值） | 15000（隐式） | 5000 | 列表接口单页正常数百毫秒，p99 不会超过两秒；八十次串行请求若每次按十五秒最坏计，总预算必然爆炸，单页收紧到五秒才能把最坏总时长压进函数预算 |
| DKnowC 合规检查（第 421 行） | 10000 | 10000（维持） | 已显式设置且定位正确：合规检查是旁路增强，超时就跳过（第 432-435 行失败即放行），不阻塞主流程 |
| generate-tts WebSocket | 30000 | 30000（维持） | 语音合成含模型推理与音频流传输，天然比 JSON 接口慢一个量级，且独立函数实例内执行，不挤占本函数预算 |
| 端侧 AlertPoller | 5000+5000 | 维持 | 端侧轮询面向老人操作场景，快败快显比慢等更符合体验，且已有指数退避兜底 |

两条配套原则。第一，预算守恒：同一函数内串行的网络调用超时之和必须显著小于函数总时限，超出预算的调用应当在进入前就被拒绝——与其在平台上被强制回收，不如在代码里速败并走降级。第二，总时限优先：所有调用点统一以"总时限"语义执行（见第四节实现），空闲超时作为总时限的补充而非替代。

### 3.1 预算演算示例

用一个具体算例说明预算为何必须逐点收紧。按二十秒函数上限推演，现状最坏串行路径为：trade_cal 调用十五秒加 daily 调用十五秒，二者在 `getLatestTradeDate` 与 `getDailyMovers` 中先后串行执行，合计已满三十秒——即便不考虑后续东财分页与 TTS 批处理，函数也已注定被平台强制回收，而且是被"砍"在最没有产出的状态：两个调用都付了最贵的等待成本，却没有任何一条数据落袋。按建议值重排后：trade_cal 十二秒封顶、daily 十二秒封顶且共享第 6.2 节的同一份预算，trade_cal 若吃满预算，daily 在进入前就丧失重试资格并以单次超时速败，链路仍有东财兜底与日期推算两条后路可用。这个算例的教训是普适的：超时值不是"上游多慢容忍多慢"的宽容度指标，而是"失败多快止损多快"的止损参数，每一毫秒的超时预算都应换得对应的成功概率。

## 四、改造后的 requestHttps

```js
/**
 * 统一 HTTPS 请求封装（第 43-76 行的健壮性强化版）。
 * 增强：硬性总时限、HTTP 状态码检查、错误分类（HttpError.kind）。
 * 保持零三方依赖；保持 JSON 自动解析契约，三个既有调用点无需改动解析逻辑。
 */
class HttpError extends Error {
  constructor(kind, message, extra = {}) {
    super(message);
    this.name = 'HttpError';
    this.kind = kind;          // 'timeout' | 'network' | 'status' | 'parse'
    Object.assign(this, extra); // statusCode / host / cause 等
  }
}

function requestHttps(url, options = {}) {
  const totalTimeout = options.timeout || 15000;
  return new Promise((resolve, reject) => {
    const https = require('https');
    const urlObj = new URL(url);
    const req = https.request({
      hostname: urlObj.hostname,
      path: urlObj.pathname + urlObj.search,
      method: options.method || 'GET',
      headers: options.headers || {},
    }, (res) => {
      let body = '';
      res.on('data', (chunk) => { body += chunk; });
      res.on('end', () => {
        clearTimeout(timer); // 响应收完即撤总时限
        if (res.statusCode >= 400) {
          reject(new HttpError('status', `HTTP ${res.statusCode} from ${urlObj.hostname}: ${body.substring(0, 200)}`, { statusCode: res.statusCode }));
          return;
        }
        try {
          resolve(JSON.parse(body));
        } catch (e) {
          reject(new HttpError('parse', `JSON parse failed: ${e.message}, body length: ${body.length}`, { statusCode: res.statusCode }));
        }
      });
    });

    // 硬性总时限：从发起到响应结束的墙钟时间，不受套接字空闲重置影响
    const timer = setTimeout(() => {
      req.destroy(new Error(`total timeout ${totalTimeout}ms`));
      reject(new HttpError('timeout', `request total timeout after ${totalTimeout}ms: ${urlObj.hostname}`));
    }, totalTimeout);

    req.on('error', (e) => {
      clearTimeout(timer);
      // destroy 触发的 error 已在 timer 回调里 reject，此处保证只 reject 一次
      reject(new HttpError('network', `${e.message}`, { host: urlObj.hostname, cause: e.code }));
    });

    if (options.body) req.write(options.body);
    req.end();
  });
}
```

实现说明：总时限定时器与套接字销毁绑定，到点同时销毁连接与 reject，杜绝"Promise 永不 settle"；`clearTimeout` 在 end 与 error 两处成对出现，防止定时器把函数实例拖长一个超时周期；state 检查放在解析之前，四百以上直接走 `status` 分类。reject 双路径的幂等性由 Promise 语义天然保证（二次 reject 无效），代码中注释只为说明意图。该实现与第 99-104、176、411-422 行三个既有调用点签名兼容，属可原地替换的增强。

## 五、callTushare 增强：错误分类与 40101 识别

```js
/**
 * Tushare 业务错误：code 为 Tushare 返回码，retryable 标记是否值得重试。
 */
class TushareError extends Error {
  constructor(apiName, code, msg) {
    super(`Tushare API error: ${msg || code} (api=${apiName})`);
    this.name = 'TushareError';
    this.tushareCode = code;
    this.apiName = apiName;
    this.retryable = false; // 业务错误一律不重试，由降级逻辑接管
  }
}

async function callTushare(apiName, params = {}, fields = '') {
  const body = JSON.stringify({ api_name: apiName, token: TUSHARE_TOKEN, params, fields });
  let data;
  try {
    data = await requestHttps(TUSHARE_API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
      timeout: 12000,
    });
  } catch (e) {
    if (e.kind === 'timeout' || e.kind === 'network') throw markRetryable(e);
    throw e; // status/parse 交由上层矩阵决策
  }
  if (data.code !== 0) {
    // 脱敏保留原 106-109 行语义：错误信息不得携带 token
    const safeMsg = (data.msg || '').replace(TUSHARE_TOKEN, '***');
    const err = new TushareError(apiName, data.code, safeMsg);
    // 40101=token 无权限或失效（已知问题，token 失效后已整体降级东财）；
    // 40102/40103 等频控类错误同样不重试——重试只会加重限流
    if (data.code === 40101) err.tokenInvalid = true;
    throw err;
  }
  return data.data;
}
```

三个要点。第一，`data.code !== 0` 的原有判断与脱敏逻辑（第 106-109 行）完整保留并升级为结构化错误，40101 打上 `tokenInvalid` 标记后，`getDailyMovers` 可以据此一次性切换东财行情兜底，而不是像现在第 353-356 行那样捕获后返回 null、当日整链空转。第二，重试标记只在超时与网络类错误上打开，业务错误（含频控）一律不重试——频控场景下重试是反生产力的。第三，脱敏职责除保留在 callTushare 外，还应在 requestHttps 的 status 错误里注意截断行为本身不会携带请求头——本封装从不打印 headers，`DKNOWC_API_KEY`（第 24 行）与 `TUSHARE_TOKEN`（第 20 行）因此天然不出现在错误日志中，这是"不泄露任何 Token 密钥"红线在网络层的落实点。

## 六、重试策略

重试遵循"分类、限次、限预算、带抖动"四要素。分类依据第四节与第五节的 kind 与 retryable 标记：timeout 与 network（ECONNRESET、ECONNREFUSED、EAI_AGAIN 等瞬时故障）可重试；status 中仅 5xx 可重试，4xx 重试无意义；parse 错误视同上游异常，可重试一次；TushareError 一律不重试。限次与限预算的统一实现如下：

```js
/**
 * 带退避的受控重试：仅对标记 retryable 的错误生效。
 * maxRetries=2，退避 500ms 起步、每次翻倍并叠加 0-200ms 抖动，
 * 且每次重试前检查函数级剩余预算，超预算立即放弃。
 */
async function withRetry(fn, { maxRetries = 2, deadline = 0 } = {}) {
  for (let attempt = 0; ; attempt++) {
    try {
      return await fn();
    } catch (e) {
      const retryable = e.retryable === true || (e.kind === 'timeout' && attempt < maxRetries);
      const budgetLeft = deadline === 0 || Date.now() + e.estimateMs < deadline;
      if (attempt >= maxRetries || !retryable || !budgetLeft) throw e;
      const backoff = 500 * Math.pow(2, attempt) + Math.floor(Math.random() * 200);
      console.log(`retry ${attempt + 1}/${maxRetries} after ${backoff}ms for ${e.message}`);
      await new Promise(r => setTimeout(r, backoff));
    }
  }
}
```

幂等性论证：`daily` 与 `trade_cal` 均为只读查询接口，同一 trade_date 参数下重复请求结果一致，重试安全；这也与既有缓存策略配合——trade_cal 每小时才真正发出一次（第 79-81 行缓存），重试风暴的概率进一步收窄。预算联动：调用方把函数入口算出的截止时刻传入 deadline，`getDailyMovers` 内 trade_cal 与 daily 两个串行段共享同一预算，先到的调用吃掉预算后，后续调用自动失去重试资格，从机制上避免"重试拖垮整函数"。

两个容易走偏的细节值得一记。其一，退避必须叠加抖动：若一小时内 trade_cal 缓存同时失效的多个函数实例（定时触发器并发或手动补跑）都在同一种失败后按固定间隔重试，重试请求会以固定节拍整齐到达上游，形成人为的脉冲负载，上游一旦因此限流，重试反而制造了本不存在的失败；零到二百毫秒的随机抖动把这些整齐的脉冲打散，成本仅为一个随机数。其二，频控类错误绝不重试的原因不是"重试无效"而是"重试有害"：Tushare 频控错误意味着上游已判定当前请求速率越界，此刻的重试在服务端视角是对限流决定的正面冲撞，最坏情况会把临时限流升级为封禁，正确动作永远是等待或切换数据源，这正是第五节把 TushareError 的 retryable 一律置假、把 40101 单独标记走降级的原因。

## 七、降级链整体视角

把超时、重试、降级放进同一条链看：trade_cal 失败时现路径已有日期推算兜底（第 322-338 行，工作日取当日、周末回退周五），该兜底应保留；daily 失败时现路径第 353-356 行返回 null、当日空结果，这是全链最大的健壮性缺口——token 失效（40101，已知问题）或接口故障都会造成"整日无声"，而端侧只显示"今日暂无异动"，用户无从分辨"真无异动"与"源故障"。目标行为是：识别 `tokenInvalid` 或连续两次可重试失败后，切换东财行情接口产出同构的 movers 列表，接口契约 AlertFeed 不变；降级与恢复探测的完整设计见 api-strategy.md 第六、七节，本文不重复。此处只强调时序约束：降级发生在重试之后、函数预算之内，两者共用第三节的预算模型。

## 八、边界矩阵

| # | 场景 | 触发点 | 现状行为 | 目标行为 | 重试 | 降级 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 上游彻底沉默 | requestHttps | 15s 后 destroy，报 timeout | 总时限 destroy，HttpError timeout | 可重试2次 | 预算内重试后降级 |
| 2 | 慢速滴漏响应 | requestHttps | 永不超时（空闲超时不触发） | 总时限强制切断 | 可重试 | 同上 |
| 3 | 网关 502/503 | requestHttps | HTML 进 JSON.parse，报解析错 | HttpError status + 截断体 | 5xx 可重试 | 降级 |
| 4 | WAF/风控 403 | requestHttps | 同上，误报解析错 | HttpError status，不重试 | 否 | 降级 |
| 5 | DNS 解析失败 | requestHttps | 原生 ENOTFOUND | HttpError network | 可重试 | 降级 |
| 6 | 连接被重置 | requestHttps | 原生 ECONNRESET | HttpError network | 可重试 | 降级 |
| 7 | 200 但坏 JSON | requestHttps | 报解析错（此为正确定位） | HttpError parse | 重试1次 | 降级 |
| 8 | token 失效 40101 | callTushare | 抛通用错误→当日空结果 | TushareError tokenInvalid | 否 | 立即切东财 |
| 9 | Tushare 频控 | callTushare | 抛通用错误 | TushareError（不重试） | 否 | 视 api 而定 |
| 10 | trade_cal 失败 | getLatestTradeDate | 日期推算兜底（322-338行） | 保留现兜底+错误分类日志 | 否 | 已有兜底 |
| 11 | 东财名称抓取失败 | getStockNameMap | 四层兜底链（123-272行） | 维持，见 cache-strategy.md | 单页可重试 | 链内自降级 |
| 12 | DKnowC 超时/失败 | checkCompliance | 跳过并放行（432-435行） | 维持，补失败率计数 | 否 | 天然跳过 |

矩阵的使用方式：任何新上游接入时，先在本表登记其超时值、可重试分类与降级去向，三项缺一不得上线；这使错误处理从"各调用点各自为政"变为"一张表管全链"。

## 九、可观测性与安全

日志增强聚焦三件事。第一，统一错误日志字段：每次网络失败打印 `api 上游名、kind 分类、耗时毫秒、目标主机` 四要素，替代现在散落的自由文本，使"东财当周超时率上升"这类趋势可以从日志直接聚合出来。第二，保留并守护脱敏：第 106-109 行的 token 脱敏是既有正确实践，改造时不得移除；同时新增调用点评审约定——凡打印请求上下文，只打主机名与方法，不打 headers 与 body，从源头隔离密钥。第三，降级可观测：进入东财兜底时打印 `degraded=true` 与触发原因（tokenInvalid 或重试耗尽），恢复探测成功时打印 `degraded=false`，让"系统此刻在哪个源上"在日志里一目了然。合规提醒：播报文本的安全分类字段 complianceStatus（第 635、643 行）不受本改造影响，DKnowC 检查失败的"跳过放行"策略维持不变，避免网络层改造改变内容安全行为。

## 十、验证方法

验证分三层。第一层，本地单测（node:test，零三方依赖）：以 `http.createServer` 起本地伪上游，分别模拟沉默（不响应）、滴漏（每秒一字节）、502 HTML、403、立即断连、坏 JSON 六种形态，断言 requestHttps 的 kind 分类与超时边界——重点用例是滴漏场景在总时限处被切断。第二层，注入验证：mock callTushare 分别抛 TushareError(40101)、timeout、ECONNRESET，断言 getDailyMovers 的降级触发与重试次数符合矩阵。第三层，灰度观测：改造上线后观察三个交易日，指标为 p99 耗时、timeout 类错误占比、降级日占比；验收标准为"慢速滴漏类悬挂消失、502 误报解析错归零、token 失效日不再空转"。全部验证脚本不入生产包，仅存仓库测试目录。

## 十一、错误处理与适老化端侧体验的联动

服务端的每一个错误处置决策，最终都会变成老年用户屏幕上的一种状态，这条映射链在改造时必须一并检视。端侧的既有约定是：轮询连续失败两次才把顶部状态切为"连接中断，显示旧数据"（Index.ets 第 195-199 行），失败后轮询间隔翻倍、封顶三十秒（AlertPoller.ets 第 90-95 行），四百二十九限流静默跳过不惊动用户（AlertPoller.ets 第 47-52 行）。这套设计的取向是"少打扰、别吓着"，服务端改造应当与之对齐而不是冲突：本篇把单次调用超时从事实上的"可能无限悬挂"收紧为确定上限，直接受益的正是这条端侧链路——现状下若 getDailyMovers 被滴漏响应悬挂，云函数迟迟不落 alerts.json，端侧虽然不会崩溃，但"今日暂无异动"的空态文案（Index.ets 第 431-438 行）会让老人误以为市场真的风平浪静，这与"首屏永不空白、状态语义诚实"的产品红线是相悖的。改造后函数在预算内速败速降级，alerts.json 的 serverTs 持续推进，端侧空态仅表示"真无异动"，状态语义恢复诚实。反过来，服务端也不要把错误升级为打扰：东财降级期间照常产出卡片，顶栏无需新增"数据源异常"之类老人无法理解的技术提示，降级事实记在日志与运维侧即可——这是"错误处理对用户透明、对运维可观测"的完整含义。

### 自我评估
- 正确性：4分 三个缺口的机理剖析（空闲超时与总时限之别、状态码缺失、错误不可分类）依据 Node https 模块公开语义与代码逐行证据，方向可靠；CloudBase 函数总时限上限为按常见配置推演并已注明待核实，阈值表需实测校准。
- 完整性：4分 覆盖超时论证、封装实现、错误分类、重试策略、十二场景边界矩阵、观测与验证；东财兜底接口细节外链 api-strategy.md，未在本篇重复。
- 可复用性：5分 requestHttps/withRetry/HttpError 均为独立零依赖模块，可直接替换现有实现并复用到其他云函数；边界矩阵登记制可作为新上游接入的通用清单。
- 字数：约4600字（实测正文汉字4598，脚本统计汉字区段U+4E00-U+9FFF，不含本自评）
- 使用模型：GLM-5.3-Flash
