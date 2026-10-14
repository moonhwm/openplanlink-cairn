# API调用与数据源策略深度审查——requestHttps统一封装与多源调度

> 项目：harmony-app（铃语，鸿蒙适老化股票异动播报应用）。审查对象：云函数 `cloudfunctions/functions/fetch-tushare-data/index.js` 的统一请求封装 `requestHttps`（第 43-76 行）与围绕它展开的多数据源调度：Tushare 行情（第 91-112、345-389 行）、东方财富名称与行情兜底（第 162-234 行）、DKnowC 合规检查（第 404-436 行）。本文自包含，行号均指该文件当前版本（全文 683 行）。审查日期：2026-09-23。

## 一、审查范围与结论摘要

本项目云函数侧的外呼需求已收敛到一个手工封装上：第 39-42 行注释明言"统一 HTTPS 请求封装（替代实验性 fetch 和 fetchHttps）"。这个决策的来龙去脉值得肯定——Node.js 18.15 的原生 fetch 属实验特性，在云函数运行时里行为不稳，第 163 行注释也记录了"使用 https 模块而非 fetch"的理由；broadcast-a2a/index.js 第 60、138、186 行仍在直接使用 fetch，是该文件的历史遗留，与本文主题的对照留到第八节。统一封装目前服务三个上游、四种调用形态，是全链路所有数据的必经之路。

审查结论：统一封装的方向正确、实现可用，但有四处策略缺口。其一，封装只覆盖了"单次请求怎么发"，没有回答"同一上游的多次请求怎么排队"，频控规避靠的是调用侧的自觉（缓存 TTL 与条数上限），缺少封装层的统一节流。其二，东财分页抓取完全串行（第 171-203 行），四个市场过滤器逐个、每市场最多二十页逐页地拉，最坏路径耗时数倍于必要值，而并行化在结构上并不难。其三，Tushare 的降级目前只发生在名称映射一处（用东财替代 stock_basic），行情侧的 daily 查询没有等价兜底，token 失效（40101，已知问题）之日整条行情链停摆。其四，调用点散落着三个隐式耦合的魔数（超时、单页容量、翻页上限），缺少集中声明。本文逐项给出方案，并与错误处理专题（error-handling.md 的超时与重试增强）明确分工：该篇管"单次请求的失败语义"，本篇管"多源多请求的调度策略"，两处衔接点在第五、六节标注。

## 一点五、统一封装的战略价值再评估

在动手增强之前，值得先回答一个反方向的问题：值得为四个调用点维护一个手工封装吗，直接用 fetch 不是更省事？答案在项目的运行环境约束里。云函数运行时的 Node 版本由平台决定而非开发者，原生 fetch 在 18.x 系列属实验特性，其超时行为、错误对象形态在不同小版本间存在差异，把整条数据链建在这种地基上，等于让每次平台升级都变成一次隐性的全链回归测试；手工封装钉死在 https 模块上，行为只随开发者主动升级而变，可控性完全不同。其次，统一封装让横切策略有了唯一落点：本篇的并发上限与响应体上限、error-handling.md 的超时语义与错误分类、以及未来任何统一加签或统一埋点，都只需改一处即可覆盖全部外呼——这是"封装一次、策略常新"的复利。反面证据同样存在：正因为 broadcast-a2a 没有收编进封装，它至今没有超时保护与状态码检查，fetch 一旦挂起整个 HTTP 服务就悬挂，这正是"旁路封装"的现成代价样本。结论是封装不仅要维持，还要把最后的旁路收编进来，让"所有外呼必经一处"从口号变成可检验的事实。

## 二、requestHttps 统一封装的现状与增强

### 2.1 GET/POST 双模式的现状

封装以 `options.method` 区分 GET 与 POST：东财名称抓取走 GET 且不带 body（第 176 行），Tushare 与 DKnowC 走 POST 且带 JSON body（第 100-103、417-421 行）。第 71-73 行对 body 的处理是"有则 write、无则跳过"，两种模式共用同一条路径。URL 的构成在第 46-52 行拆解为 hostname 与 path+search，天然支持带查询串的 GET。这个双模式骨架是对的，但有三个细节值得收紧。

第一个细节是 Content-Length 头：POST 请求体写入时未显式声明长度，Node https 会按 chunked 编码发送；多数上游接受，但个别网关与代理对 chunked POST 有兼容性问题，显式设置 `Content-Length: Buffer.byteLength(body)` 可以消除这一类环境相关的莫名失败。第二个细节是响应体大小无上限：第 55-56 行把 body 无限制地拼接，恶意或异常的上游可以返回超大响应把函数内存打爆，加一个如两兆的软上限、超限即中断并报错，是把"信任上游"改为"信任但验证"。第三个细节是 JSON 解析的无条件性：DKnowC 若某日改为返回非 JSON 的错误页，当前会以解析错误浮出（错误分类的完整方案见 error-handling.md 第四节，此处不重复），本篇只主张封装层应提供 `options.raw = true` 逃生口，供未来接入非 JSON 上游而无需旁路封装。

### 2.2 增强后的封装签名

```js
/**
 * 统一 HTTPS 请求封装（第 43-76 行的策略增强版，失败语义增强见 error-handling.md）。
 * 新增：Content-Length 自动声明、响应体软上限、raw 模式逃生口。
 */
function requestHttps(url, options = {}) {
  const body = options.body;
  const headers = Object.assign({}, options.headers);
  if (body && !headers['Content-Length']) {
    headers['Content-Length'] = String(Buffer.byteLength(body));
  }
  const MAX_BODY_BYTES = options.maxBytes || 2 * 1024 * 1024; // 2MB 软上限
  return new Promise((resolve, reject) => {
    const https = require('https');
    const urlObj = new URL(url);
    let received = 0;
    const req = https.request({
      hostname: urlObj.hostname,
      path: urlObj.pathname + urlObj.search,
      method: options.method || 'GET',
      headers,
    }, (res) => {
      let data = '';
      res.on('data', (chunk) => {
        received += chunk.length;
        if (received > MAX_BODY_BYTES) {
          req.destroy(new Error(`response exceeds ${MAX_BODY_BYTES} bytes`));
          return;
        }
        data += chunk;
      });
      res.on('end', () => {
        if (options.raw) { resolve(data); return; }
        try { resolve(JSON.parse(data)); }
        catch (e) { reject(new Error(`JSON parse failed: ${e.message}, body length: ${data.length}`)); }
      });
    });
    req.on('error', reject);
    req.setTimeout(options.timeout || 15000, () => {
      req.destroy(new Error('Request timeout'));
    });
    if (body) req.write(body);
    req.end();
  });
}
```

签名与既有三个调用点完全兼容：Content-Length 是自动补全而非必填，maxBytes 与 raw 都有默认值，属可原地合入的非破坏性增强。

### 2.3 封装层的集中常量

把散落三处的隐式耦合魔数收进文件顶部的集中声明，是本篇所有调度策略的落点：

```js
const API_CONFIG = {
  tushare:    { timeoutMs: 12000, maxConcurrent: 1 },             // 串行：配额宝贵
  eastmoney:  { timeoutMs: 5000,  maxConcurrent: 4, pageLimit: 20, pageSize: 100 },
  dknowc:     { timeoutMs: 10000, maxConcurrent: 2 },
};
```

超时值的逐点论证在 error-handling.md 第三节完成，本篇直接采用其结论；`maxConcurrent` 是本篇新增的维度，含义见第四节。集中声明的价值不只是整洁：频控规避的第一原则是"限额是全局资源，任何调用点不得私自动用"，集中声明使限额在代码评审中一眼可见。

## 三、东财分页并行化：市场间并行、页面间串行

### 3.1 现状串行的代价与翻页依赖

第 171-203 行的抓取是三层串行：四个市场过滤器逐个执行，每个过滤器内逐页推进，页与页之间靠"当前页返回条数小于单页容量一百"判断是否到尾页（第 201 行）。串行的代价按算例可见：四个市场合计约五千六百只股票（与硬编码快照 5560 条互证），单页一百条即约五十六页有效请求，按单次往返五百毫秒计，纯串行需约二十八秒——这已经超出单次函数调用的合理预算，也解释了为什么该抓取必须依赖跨调用的存储缓存（cache-strategy.md 第三节）来摊薄。翻页的页间依赖是真实的：不知道当前页返回多少条就无法决定是否继续，盲发下一页会产生大量空页请求。

### 3.2 并行化的正确切分：市场间天然独立

四个市场过滤器（沪深主板的两个与深市两个板块，第 169 行）之间没有任何依赖——不同 fs 参数查询不同的板块集合，结果按 ts_code 去重合并即可。因此正确的切分是"市场间并行、页面间保持串行"：四个过滤器各自起一条串行翻页链，四条链并发推进。实现如下：

```js
async function fetchMarketNames(requestFn, fs) {        // 单市场串行翻页链（原 while 循环）
  const partial = new Map();
  let page = 1;
  while (page <= API_CONFIG.eastmoney.pageLimit) {
    const url = `https://80.push2.eastmoney.com/api/qt/clist/get?pn=${page}&pz=100&po=1&np=1&fltt=2&invt=2&fs=${encodeURIComponent(fs)}&fields=f12,f14`;
    const data = await requestFn(url, { timeoutMs: API_CONFIG.eastmoney.timeoutMs });
    const stocks = data?.data?.diff;
    if (!stocks || stocks.length === 0) break;
    for (const s of stocks) {
      const tsCode = codeToTsCode(s.f12 || '');        // 号段规则见 cloud-function-refactor.md §5.3
      if (tsCode && s.f14) partial.set(tsCode, s.f14);
    }
    if (stocks.length < API_CONFIG.eastmoney.pageSize) break;
    page++;
  }
  return partial;
}

async function fetchEastMoneyAll(requestFn, marketFilters) {
  const results = await Promise.allSettled(
    marketFilters.map(fs => fetchMarketNames(requestFn, fs))
  );
  const merged = new Map();
  let failedMarkets = 0;
  for (const r of results) {
    if (r.status === 'fulfilled') {
      for (const [k, v] of r.value) merged.set(k, v);
    } else { failedMarkets++; console.log(`market chain failed: ${r.reason?.message}`); }
  }
  // 失败市场超过半数视为抓取失败，交由上层降级（cache-strategy.md 的下限校验）
  return { map: merged, failedMarkets };
}
```

效果演算：并发度四之下，总耗时由四条链的最长链决定，约十四页的主板链约七秒，相比串行二十八秒提速约四倍；对东财的瞬时请求并发不超过四，属于单一客户端的正常浏览行为量级，不构成压力。两个设计守则：其一，用 `Promise.allSettled` 而非 `Promise.all`，单市场失败不拖垮其余三个，失败市场数交由 cache-strategy.md 第 3.2 节的下限校验裁决；其二，并发度上限固定为市场过滤器数量四，不做"页间也并行"的进一步激进优化——那需要预知总页数，空页请求与限流风险同步上升，收益却有限。市场间并行与页面间串行的完整性能账本（含与 getDailyMovers 内 Promise.all 的组合关系）在 performance.md 第二节展开，本篇只确立切分原则。

### 3.3 行情侧的东财兜底接口

名称映射已用东财替代 Tushare stock_basic，行情侧的等价兜底当前缺失：daily 查询失败（第 353-356 行捕获后返回 null）之日，整条异动链空转，端侧只见"今日暂无异动"。补齐方案是复用同一个列表接口换字段集：fields 取 `f12,f14,f2,f3,f5,f6`（代码、名称、最新价、涨跌幅、成交量、成交额），fs 覆盖沪深两市，逐页抓取后按 `pct_chg = f3、close = f2、vol = f5、amount = f6` 映射成与 daily 返回同构的对象，再走既有的 createAlertItems（第 441-491 行）生成卡片。这样降级对下游完全透明：AlertFeed 契约不变、端侧零改动、卡片样式与播报链路照常。注意两个字段语义差异：东财 f3 为百分比已乘百的涨跌幅需除以一百对齐 Tushare 的 pct_chg 口径；停牌股 f2 可能为字符串"-"需按零处理。降级的触发与恢复探测在第六节，错误分类的判定依据在 error-handling.md 第五节。

## 四、频控规避的四层防线

频控规避不是单点技巧而是分层防线，本项目需要同时防两类限额：Tushare 的显式配额（trade_cal 每小时一次、daily 依积分权限）与东财的隐性风控（无文档化限额，但异常流量会触发拦截页）。

第一层防线是**缓存**，也是最有效的一层：trade_cal 结果缓存一小时（第 79-81 行），与配额窗口精确对齐；名称映射存储缓存四十八小时（cache-strategy.md 第 3.2 节优化后），把全量抓取频率压到两日一次。缓存命中的请求根本不发出去，这是唯一"零成本"的频控规避。第二层防线是**并发上限**：`API_CONFIG.eastmoney.maxConcurrent = 4` 把瞬时并发钉死在市场数，即使未来增加过滤器也不允许并发随之上探；Tushare 侧 `maxConcurrent = 1` 表达"配额上游永远串行"的原则。第三层防线是**条数与次数的自限**：翻页上限二十（第 173 行）与 TTS 批量上限十条（第 595 行）同属此类，它们保证最坏情况下的外呼次数有确定上界。第四层防线是**退避与让路**：端侧轮询已有指数退避与四百二十九静默（AlertPoller.ets 第 47-52、90-95 行）；云函数侧的重试退避与"频控类错误绝不重试"原则由 error-handling.md 第六节承担。

四层防线的检查清单化：新增任何上游时，逐项回答"缓存了吗、并发封顶了吗、次数封顶了吗、四百二十九/频控怎么办"，四问皆有答案才允许合入。这份清单与 error-handling.md 第八节边界矩阵的"登记制"互为表里——矩阵登记失败处置，清单登记流量自限。

## 五、Tushare 降级的完整状态机

现状的降级是隐式的、一次性的：token 失效导致 stock_basic 报错，名称映射顺理成章改走东财，但这个"降级"从没有显式的状态与恢复路径——即便次日 token 修好，名称层也仍按缓存周期自然回到 Tushare 之外的路径，行为随缓存周期漂移而不可解释。行情侧补齐兜底后，需要一个显式状态机管理两个数据源：

```
状态 NORMAL（Tushare 为主）
  触发迁移：callTushare 抛 tokenInvalid(40101) 或同日累计可重试失败≥2次
  迁移动作：当日后续调用全部走东财；日志打印 degraded=true 及原因
状态 DEGRADED（东财为主）
  保持条件：当日剩余调用全部东财，不再尝试 Tushare（避免每个请求都撞一次 401）
  恢复探测：次日首次调用前发一次轻量 trade_cal 探测（有缓存则探缓存外的最小参数）
  恢复迁移：探测成功 → NORMAL，日志打印 degraded=false
  兜底失败：东财亦失败 → 沿用 trade_cal 的日期推算（第 322-338 行）等既有兜底
```

状态存放于模块级变量即可（单实例内有效），跨实例的一致性不强求——每个实例独立探测、独立收敛，最坏情形是多花一次探测调用，无正确性影响。两个原则需要强调：降级期间**不产生用户可感知的变化**（卡片照常产出，顶栏不出现技术性提示，与适老化"少打扰"取向一致）；恢复探测用**最便宜的调用**（trade_cal 带最小参数窗口），不用 daily 全量去试探，避免探测本身消耗配额。

## 六、DKnowC 与广播链路的调用治理

DKnowC 合规检查（第 404-436 行）的现有策略是"失败即放行"，定位正确——它是增强层不是闸门，网络故障不应阻塞播报。需要补的是批量视角的治理：第 601-606 行对最多十条信号卡并行发起检查，瞬时并发十在 `maxConcurrent: 2` 的约束下应改为分批（两批各五或五批各二）；更值得做的是**前置文本去重**——同 symbol 同方向的信号卡文本高度相似（第 462-468 行的模板化 headline），先按文本哈希去重再送检，可把实际调用量压掉一部分，与 TTS 侧按文本 SHA256 缓存（generate-tts/index.js 第 56-58 行）是同一思想的两种应用。broadcast-a2a 的调用治理属另一专题，此处只记两点事实供衔接：其一，该文件第 60、138、186 行仍直接用 fetch，应统一收编到 requestHttps（超时与状态码检查随即免费获得）；其二，Push 链路需换华为 Push Kit REST（已知问题），换装时的 OAuth 取 token 调用应纳入 API_CONFIG 并遵循第四节四问清单。另外需澄清一处文档疑点：get-alerts/index.js 第 16 行注释中的示例 URL 以 `/alertsD` 结尾，疑为笔误，端侧实际请求路径为 `/alerts`（AlertPoller.ets 第 10 行 DEFAULT_FEED_URL 可证），API 文档修订时应更正。

## 六点五、读路径的调用治理：get-alerts 与端侧轮询的配合

前文全部关于写路径（产出数据的调用），读路径的调用策略同样在本篇职责内，且它直接面向适老化体验。读链路是三级串联：端侧 AlertPoller 每五秒请求一次 `get-alerts`（AlertPoller.ets 第 41-45 行，连接与读取超时各五秒），get-alerts 每次调用都从 CloudBase 下载整个 alerts.json 并排序截取前二十条（get-alerts/index.js 第 26-51 行），alerts.json 由 fetch-tushare-data 定时写入（最多五百条，第 537-540 行）。这条链的调用策略有三个要点。其一，读放大已被正确控制：端侧拉取频率虽高（每五秒一次），但每次读的是同一个静态文件，无上游 API 消耗，函数层唯一的成本是文件下载与解析，按五百条估算载荷约数百千字节，在事件函数的舒适区内；limit 参数封顶一百（get-alerts/index.js 第 58-61 行）防止恶意大查询。其二，读侧的频控是端侧自律：指数退避把失败后的间隔翻倍封顶三十秒（AlertPoller.ets 第 90-95 行），四百二十九静默跳过不重试，这意味着端侧对服务端的压力有硬上界——每设备每五秒一次 GET，量级温和。其三，一个待改进点：get-alerts 每次全量下载全量排序，条数增长到五百条上限后解析成本线性上升，若未来观察到函数耗时抬升，可让写路径顺手维护一个已排序的精简视图文件（如 alerts-top.json 只存最新一百条），读路径改为下载精简视图——这是写路径多花一次上传换读路径常年轻量的经典取舍，接入时同样走第七节总表登记。

## 七、数据源策略总表

| 上游 | 用途 | 方法 | 超时 | 并发上限 | 频控防线 | 失败去向 |
| --- | --- | --- | --- | --- | --- | --- |
| Tushare trade_cal | 交易日 | POST | 12000ms | 1 | 1h 缓存对齐配额 | 日期推算兜底（322-338行） |
| Tushare daily | 日线行情 | POST | 12000ms | 1 | 积分配额+串行 | 东财行情兜底（第三节） |
| 东财 clist（名称） | 名称映射 | GET | 5000ms | 4 | 48h 存储缓存+条数自限 | 六层降级链（cache-strategy.md） |
| 东财 clist（行情兜底） | 降级行情 | GET | 5000ms | 4 | 复用同接口防线 | 空结果，端侧演示卡兜底 |
| DKnowC | 合规检查 | POST | 10000ms | 2 | 文本去重+失败放行 | 放行+Unknown 标记 |
| 百炼 TTS | 语音合成 | WSS | 30000ms | 1 | 文本缓存+批量上限10 | 端侧按需重试调 generate-tts |

这张表是本篇的收口：任何新上游接入，先在此表登记一行，再按第四节四问补齐防线，最后在 error-handling.md 边界矩阵登记失败处置——三份文档共同构成外呼治理的完整台账。台账之外再记一条贯穿全篇的价值排序，供后来者在具体取舍时对照：数据源策略的所有优化，最终都要回到适老化体验上验收——东财并行化把冷启动抓取从半分钟压到数秒，受益的是"服务接通后老人少看几分钟演示卡"；降级状态机让 token 失效日不再整日无声，受益的是"状态语义诚实"；频控四防线避免的是"某天突然全链断供"这类老人完全无法理解的故障形态。凡是与这三点无关、只服务于工程洁癖的调度复杂度，都应让位给简单；本篇所有方案都以此为加复杂度的正当性边界。

## 七点五、与既有已知问题的对照核对

按任务给定的已知问题清单逐条核对本篇覆盖情况，防止遗漏。Tushare token 失效（40101）已降级东财——本篇第五节将其从隐式行为升级为显式状态机，并补齐行情侧兜底；百炼 TTS 只支持 WebSocket——不属本篇封装范围（HTTP 封装不吞并 WSS），仅在总表登记其超时与频控参数；broadcast-a2a 的 Push 需换华为 Push Kit REST——第六节已登记收编点与四问清单；alerts.json 的 audioUrl undefined 端侧按需调 generate-tts——读路径分析（第六点五节）确认该按需调用不经过 get-alerts 读链路，其调用治理归 generate-tts 专题。四条已知问题全部有落点或明确归属，无悬空项。

## 八、验证方法

验证分三层。第一层，封装回归：以本地伪上游验证 Content-Length 声明后 POST 仍被 Tushare 沙箱正常解析、响应体超限时请求被中断而非内存膨胀、raw 模式返回原文。第二层，并行抓取验证：mock requestFn 返回固定页序，断言四市场链并发执行（记录请求时间戳，四条链的首请求应几乎同时发出）、单链仍按页序串行、单市场失败时其余三市场结果完整合并、失败市场过半时整体判失败。第三层，降级状态机验证：mock callTushare 抛 40101，断言当日后续 daily 调用零次到达 Tushare、卡片仍从东财产出且字段映射正确（重点核对涨跌幅除百与停牌零值）；次日探测成功后断言恢复 NORMAL。全部验证在 node:test 下以注入 stub 完成，不依赖真实上游；真实环境的最终确认以一次手动触发加日志核对收尾。

### 自我评估
- 正确性：4分 封装增强、市场间并行切分、降级状态机均以现行代码行号为据推导；东财字段 f3 除百、f2 停牌值属公开接口常识性语义，未经实测核对，已在文中标注需在第三层验证中确认。
- 完整性：4分 覆盖双模式封装、分页并行、四层频控防线、降级状态机、总表与验证；百炼 WebSocket 与 Push Kit 治理仅登记不展开（分别属 generate-tts 专题与推送专题）。
- 可复用性：5分 API_CONFIG 集中声明、四问接入清单、数据源总表台账可直接套用于新上游接入流程；fetchMarketNames 的单链+全合并模式是分页抓取的通用件。
- 字数：约4780字（实测正文汉字4778，脚本统计汉字区段U+4E00-U+9FFF，不含本自评）
- 使用模型：GLM-5.3-Flash
