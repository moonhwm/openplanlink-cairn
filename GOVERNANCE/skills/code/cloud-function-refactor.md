# 代码质量与可维护性深度审查——getStockNameMap 155行拆分为6个独立函数

> 项目：harmony-app（铃语，鸿蒙适老化股票异动播报应用）。审查对象：云函数 `cloudfunctions/functions/fetch-tushare-data/index.js` 中的 `getStockNameMap` 函数。本文自包含，不依赖对话记忆，所有行号均指向该文件当前版本（全文 683 行）。审查日期：2026-09-23。

## 一、审查对象与结论摘要

`getStockNameMap` 位于 index.js 第 123 行至第 272 行，函数体共 150 行；连同第 114-122 行的文档注释合计约 159 行，任务口径"155 行"与此量级相符。这个函数回答的问题是："这只股票叫什么中文名？"它是整条异动播报链路上保障适老化体验的关键一环——Tushare daily 日线接口返回的 name 字段经常为空，若不补齐，端侧卡片（Index.ets 第 373-380 行的 `Text(item.name)`）将直接显示 `600176` 这样的代码，老年用户无法理解，"大字白话"的产品承诺就落空了。因此第 368-374 行专门用本函数产出的映射表回填名称，第 383-384 行还打印 `Name mapping: x/y have Chinese names` 的覆盖率日志用于观测。

审查结论：该函数是一个典型的"降级链大泥球"。六层降级——内存缓存、CloudBase 存储缓存、东方财富接口刷新、过期存储兜底、硬编码快照兜底、空 Map——全部串在一个函数体内，圈复杂度约 22，四个 try/catch 嵌套，五处对模块级全局变量的隐式写操作，两段近乎复制粘贴的下载代码。任何一层策略调整都要通读全函数才能安全动手，且无法在无网络、无 CloudBase 的环境下做单元测试。

本文给出拆分方案：把 150 行拆为 6 个职责单一的独立函数，外加一个约 40 行的编排层。拆分坚持"外部行为不变"原则，并对每一层给出签名、职责、输入输出与完整实现，最后附行为不变性核对清单、单元测试设计与迁移回滚步骤。过期缓存被洗白的语义缺陷在本文只处理其结构成因，缓存策略专题分析另见 cache-strategy.md；东财分页并行化属性能专题，另见 performance.md，本文不重复展开。

## 二、现状问题逐条剖析

### 2.1 单函数承载六种职责

逐行拆解现状代码，一个函数体里至少混入六种互不相关的职责，各自对应不同的变更驱动力：

| 职责 | 现状行号 | 变更驱动 |
| --- | --- | --- |
| 内存缓存命中判断 | 124-128 | TTL 策略调整 |
| CloudBase 存储读取与新鲜度判断 | 130-160 | 存储契约、路径、TTL 调整 |
| 东方财富接口分页抓取 | 162-204 | 接口字段、翻页上限、市场清单调整 |
| ts_code 推导规则 | 190-194 | 交易所号段规则调整 |
| CloudBase 回写持久化 | 212-226 | 持久化策略调整 |
| 兜底链（过期存储→硬编码→空Map） | 236-271 | 兜底优先级调整 |

六种职责对应六个不同的"为什么会改"：TTL 由缓存效果数据驱动、市场清单由市场覆盖需求驱动、号段规则由交易所规则驱动。把它们缝在一个函数里，意味着任何一项调整都必须理解其余五项的上下文才能动手，改动风险被人为放大。这正是单一职责原则要防的局面：一个模块应当只有一个发生变化理由，而它现在有六个。

### 2.2 控制流嵌套深、不可单测

函数体内有四个 try/catch（第 131-160、164-234、237-254、258-267 行），最深处达到五层嵌套：外层 try → for 遍历市场 → while 翻页 → for 遍历股票 → if 过滤。要验证"东财返回零条时是否正确落到过期存储兜底层"这一条路径，必须在真实网络与真实 CloudBase 环境中依次构造"内存未命中、存储恰好过期、东财全部返回空"三个前置条件，这在测试实践中几乎不可复现，于是这条兜底路径长期处于无验证状态。

更深一层的障碍是它对两个模块级可变全局变量的依赖：`cachedNameMap` 与 `cachedNameMapTs` 在第 84-85 行声明，写操作散布在第 145-146、153-154、208-209、246-247、261-262 行共五处。测试用例之间会通过全局状态互相污染，即便构造出前置条件，断言也需要窥探函数外部的变量才能完成，这违背了可测试性设计的基本要求。

### 2.3 隐式副作用与状态语义不一致

五处缓存写入的语义并不一致。第 145-146 行（存储层新鲜命中）与第 208-209 行（东财新数据）写入的是"确知新鲜的映射"；而第 153-154 行写入的却是"已知过期的 stale 数据"，却同样把时间戳刷成当前时刻；第 246-247 行与第 261-262 行的兜底路径同理。也就是说，缓存槽只记录"数据何时装进来"，不记录"数据本身多新"，第 125 行基于时间差的 TTL 判断在兜底路径下会失真——过期数据装入后被当作新鲜数据继续服务长达二十四小时。这是全函数最隐蔽的正确性风险，其完整论证与修复方案见 cache-strategy.md 第 4.1 节；本文的拆分方案在结构上为修复铺路：把缓存状态收敛到编排层一处管理。

### 2.4 重复代码

第 131-137 行与第 238-241 行是几乎相同的"取 app 实例 → downloadFile 指定云路径 → JSON.parse"序列；`new Map(Object.entries(stored.names))` 的构造出现在第 144、152、245 行三处。重复不是风格问题而是缺陷温床：将来云路径或载荷格式一旦变更，需要同步修改多处，漏改任意一处就会出现"读取与写入使用不同契约"的静默错位。同理，第 166-167 行同时维护 Map 与普通对象 `nameObj` 两份同构状态（后者仅为第 216-221 行的持久化服务），一份状态两种表示同样是漂移隐患。

## 三、重构目标与原则

本次拆分确立四条原则，作为后续每一节设计决策的判据：

1. **行为不变**。六层降级的触发顺序、每层成功后的缓存赋值时机、全部日志文案保持与原代码一致。唯一的例外是 2.4 指出的重复下载消除——worst case 下省一次网络往返且最终结果不变，此类"纯改进"在评审记录中单独注明。
2. **纯函数优先**。除编排层外，六个子函数不直接读写模块级全局变量，缓存槽由编排层持有并作为参数传入需要它的函数。子函数内部不修改任何模块级状态。
3. **依赖可注入**。时间源、请求函数、CloudBase app 实例、require 均通过参数传入，生产路径给默认值，测试路径给 stub。目标是六个函数全部可以在 `node:test` 下无网络单测。
4. **零三方依赖不变**。继续只用 Node 内置 https 模块与项目内 `hardcoded-names.js` 快照文件，不引入新包，符合项目"纯 ArkTS + 云函数、零三方依赖"的硬约束。

### 3.1 为什么不是类封装或策略模式

两个常见替代方案在此被有意放弃，理由值得记录。其一是封装成 `StockNameMapService` 类：云函数是无状态短生命周期进程，实例级封装带来的只有一层构造与 this 转发噪音，且 fetch-tushare-data 现存代码全部是模块级函数（callTushare、getLatestTradeDate、getDailyMovers 等），单独为一个函数引入类风格会造成同文件两种范式并存，维护成本不降反升。其二是把六层降级抽象成"策略数组 + 通用降级执行器"：本链路只有六层且各层签名差异明显（有的需要网络、有的读内存、有的写存储），通用执行器需要引入统一的尝试结果包装与逐层适配器，抽象成本超过收益；等降级链在三处以上重复出现时再做该抽象才是时机。拆成六个模块级函数加一个显式编排层，是与现有代码风格、函数生命周期、链路规模三者都匹配的最小方案。

## 四、六个函数设计总表

| # | 函数签名 | 职责 | 输入 | 输出 | 吸收的现状行号 |
| --- | --- | --- | --- | --- | --- |
| 1 | `readMemoryCache(cache, now, ttl)` | 内存层命中判断 | 缓存槽、当前时间、TTL | `Map \| null` | 124-128 |
| 2 | `loadStoredNameMap(app, cloudPath, now, ttl)` | 存储层下载与新鲜度分流 | app 实例、云路径、时间、TTL | `{kind:'fresh'\|'stale'\|'miss', map?}` | 130-160、236-254 |
| 3 | `codeToTsCode(code)` | 交易所前缀映射 | 东财 6 位代码字符串 | `ts_code \| null` | 190-194 |
| 4 | `fetchEastMoneyNameMap(requestFn, marketFilters)` | 东财分页抓取与组装 | 可注入请求函数、市场过滤器数组 | `Map`（失败时为空Map） | 162-204、206-231 |
| 5 | `persistNameMap(app, cloudPath, nameMap)` | 回写 CloudBase | app、云路径、名称映射 | `Promise<void>`（失败不抛） | 212-226 |
| 6 | `loadHardcodedNameMap(requireFn)` | 硬编码快照兜底 | require 函数（默认全局 require） | `Map \| null` | 256-267 |

## 五、各函数详细设计与实现

### 5.1 readMemoryCache——内存层命中

```js
/**
 * 内存缓存命中判断（吸收原 124-128 行）。
 * @param {{map: Map|null, ts: number}} cache 编排层持有的缓存槽
 * @param {number} now 当前毫秒时间戳（可注入，便于边界测试）
 * @param {number} ttl 有效期毫秒（生产传 NAME_MAP_CACHE_TTL=86400000，见原 86 行）
 * @returns {Map|null} 命中返回映射，未命中或过期返回 null
 */
function readMemoryCache(cache, now, ttl) {
  if (cache.map && (now - cache.ts) < ttl) {
    console.log('Using in-memory cached stock name map, size:', cache.map.size);
    return cache.map;
  }
  return null;
}
```

设计考量有三。其一，把"两个全局变量"收敛为"一个缓存槽对象"，五处散布写点在编排层归一，2.3 节的语义问题从此有了唯一的修复位置。其二，时间显式注入后，"第 ttl 减一毫秒命中、第 ttl 毫秒恰好过期"这类边界不再依赖真实时钟，测试可确定性复现。其三，日志文案与原第 126 行逐字一致，保证线上日志检索口径不因重构漂移——这是行为不变原则在可观测性维度的落实。

### 5.2 loadStoredNameMap——存储层下载与新鲜度分流

此函数同时吸收原"第二层新鲜读取"（130-160 行）与"第四层过期兜底读取"（236-254 行）：二者读的是同一个文件、同一份载荷，只差一个新鲜度判断，合并后天然消除 2.4 节指出的重复下载与三处重复构造。

```js
/**
 * 从 CloudBase 存储读取名称映射并按新鲜度分流。
 * kind='fresh'：updatedAt 在 ttl 内，可直接采信；
 * kind='stale'：有数据但已过期（或无时间戳），仅可作降级兜底；
 * kind='miss' ：文件不存在、下载失败或载荷不合法。
 */
async function loadStoredNameMap(app, cloudPath, now, ttl) {
  try {
    const result = await app.downloadFile({ cloudPath });
    if (!result || !result.fileContent) return { kind: 'miss' };
    const stored = JSON.parse(result.fileContent.toString('utf-8'));
    if (!stored || !stored.names) return { kind: 'miss' };
    const map = new Map(Object.entries(stored.names));
    if (!stored.updatedAt) return { kind: 'stale', map };
    const age = now - new Date(stored.updatedAt).getTime();
    if (age < ttl) {
      console.log(`Using CloudBase stored name map: ${map.size} entries (age: ${Math.round(age / 3600000)}h)`);
      return { kind: 'fresh', map };
    }
    console.log(`Stored name map is stale (${Math.round(age / 3600000)}h old), will try refresh`);
    return { kind: 'stale', map };
  } catch (e) {
    console.log('No stored name map in CloudBase:', e.message);
    return { kind: 'miss' };
  }
}
```

关键取舍是把"stale 数据怎么用"的决策权上交编排层。原代码在 stale 分支（152-154 行）当场污染全局缓存槽并继续向下尝试刷新，控制流"既返回又不返回"的意图只能靠注释解释；新设计用 `kind` 三值显式表达三分支结局，编排层拿到结果后再决定装缓存还是降级，控制流与数据流重新对齐。载荷契约（names/updatedAt/count/source 五字段）与原第 140、216-221 行完全一致，读取端与写入端共享同一常量 `NAME_MAP_CLOUD_PATH = 'stock-names/name-map.json'`，契约错位从结构上被堵死。

### 5.3 codeToTsCode——交易所前缀映射

```js
/**
 * 东财 6 位代码 → Tushare ts_code（吸收原 190-194 行）。
 * 规则：6 开头→沪 .SH；0/3 开头→深 .SZ；8/4 开头→北 .BJ；其余不收。
 * @param {string} code 东财 f12 字段的 6 位代码
 * @returns {string|null} 非法代码返回 null
 */
function codeToTsCode(code) {
  if (code.startsWith('6')) return code + '.SH';
  if (code.startsWith('0') || code.startsWith('3')) return code + '.SZ';
  if (code.startsWith('8') || code.startsWith('4')) return code + '.BJ';
  return null;
}
```

这是六个函数中最小的一个，却是最值得单独抽出的规则点。原代码里这段规则埋在 while 循环内层 for 的第 190-194 行，任何人都难以一眼发现它是一条独立的业务规则；而它恰恰是变更频率较高的——北交所号段扩容、科创板归属校验、B 股排除等需求都会落到这六行上。抽出之后规则有了唯一归属与独立测试位，配合返回 null 的显式约定，"不认识的代码不进映射表"的语义也从隐式 continue 变成了函数契约。

### 5.4 fetchEastMoneyNameMap——东财分页抓取

```js
/**
 * 从东方财富列表接口抓取全市场名称映射（吸收原 162-204 行）。
 * @param {Function} requestFn 请求函数，生产注入 requestHttps（原 43-76 行），测试注入 stub
 * @param {string[]} marketFilters 如 ['m:1+t:2','m:1+t:23','m:0+t:6','m:0+t:80']（原 169 行提为常量）
 * @returns {Promise<Map>} 至少为空 Map，不向上抛出（抓取失败即空结果，交编排层降级）
 */
async function fetchEastMoneyNameMap(requestFn, marketFilters) {
  const nameMap = new Map();
  try {
    for (const fs of marketFilters) {
      let page = 1;
      while (page <= 20) {
        const url = `https://80.push2.eastmoney.com/api/qt/clist/get?pn=${page}&pz=100&po=1&np=1&fltt=2&invt=2&fs=${encodeURIComponent(fs)}&fields=f12,f14`;
        console.log(`EastMoney fetching: fs=${fs}, page=${page}`);
        const data = await requestFn(url);
        if (!data || !data.data || !data.data.diff) {
          console.log(`EastMoney: no data for fs=${fs}, page=${page}`);
          break;
        }
        const stocks = data.data.diff;
        if (stocks.length === 0) break;
        for (const s of stocks) {
          const tsCode = codeToTsCode(s.f12 || '');
          if (!tsCode || !s.f14) continue;
          nameMap.set(tsCode, s.f14);
        }
        console.log(`EastMoney: fs=${fs}, page=${page}, got ${stocks.length} stocks`);
        if (stocks.length < 100) break;
        page++;
      }
    }
  } catch (e) {
    console.log('EastMoney API failed:', e.message, e.stack);
  }
  console.log(`EastMoney total: ${nameMap.size} entries`);
  return nameMap;
}
```

设计取舍有三点。第一，页间保持串行：翻页终止条件依赖当前页返回条数是否小于单页容量一百（即原第 201 行语义），并行翻页需要预估总页数，会引入无效请求，该优化归性能专题处理，本函数先留好 `requestFn` 注入口。第二，失败语义定为"失败即空结果、绝不抛出"，与原代码四个兜底 try/catch 的整体意图一致——本函数是降级链中的"尝试层"而非"裁判层"，裁判权在编排层。第三，原第 167 行与 Map 平行维护的 `nameObj` 普通对象被移除，持久化载荷由 persistNameMap 内部从 Map 派生，一份状态一种表示。

### 5.5 persistNameMap——回写 CloudBase

```js
/**
 * 把名称映射回写 CloudBase 存储（吸收原 212-226 行）。
 * 回写是尽力而为的旁路：失败仅记日志、不向上抛出，不能影响主流程返回。
 */
async function persistNameMap(app, cloudPath, nameMap) {
  try {
    const nameObj = Object.fromEntries(nameMap);
    await app.uploadFile({
      cloudPath,
      fileContent: Buffer.from(JSON.stringify({
        names: nameObj,
        updatedAt: new Date().toISOString(),
        count: nameMap.size,
        source: 'eastmoney',
      }), 'utf-8'),
    });
    console.log('Name map persisted to CloudBase storage');
  } catch (storeErr) {
    console.log('Failed to persist name map:', storeErr.message);
  }
}
```

两个差异点需要评审注意。其一，用 `Object.fromEntries(nameMap)` 替代原第 167 行手工维护的平行对象，状态表示归一。其二，载荷五字段与原第 216-221 行逐字一致，包括 `source: 'eastmoney'` 的来源标记——这个字段目前没有读取方使用，但它是将来做"快照来源审计"的锚点，保留而非删减。是否回写的决策（原第 207 行 `size > 0` 才回写）保留在编排层，本函数只负责执行。

### 5.6 loadHardcodedNameMap——硬编码快照兜底

```js
/**
 * 加载硬编码名称映射（吸收原 256-267 行）。
 * hardcoded-names.js 为 2026-09-21 从东财抓取的 5560 条快照（文件 147121 字节），
 * 作为东财接口与 CloudBase 存储双双失败时的最终名称来源。
 * @param {Function} requireFn 可注入的 require，默认全局 require
 * @returns {Map|null} 加载失败返回 null，由编排层落到空 Map
 */
function loadHardcodedNameMap(requireFn = require) {
  try {
    const hardcoded = requireFn('./hardcoded-names');
    const map = new Map(Object.entries(hardcoded));
    console.log(`Hardcoded name map loaded: ${map.size} entries`);
    return map;
  } catch (e) {
    console.log('Hardcoded name map not available:', e.message);
    return null;
  }
}
```

`requireFn` 参数让"快照文件损坏或缺失"这条路径可以在测试中确定性地触发，而不必真的删文件。原第 257 行 `Using hardcoded name map fallback` 的入口日志移到编排层打印，因为它标记的是降级决策而非加载动作，决策日志归编排层是本次拆分确立的日志归属约定。

## 六、重构后的编排层 getStockNameMap

```js
const NAME_MAP_CLOUD_PATH = 'stock-names/name-map.json';
const MARKET_FILTERS = ['m:1+t:2', 'm:1+t:23', 'm:0+t:6', 'm:0+t:80'];
// 缓存槽：由原 84-85 行两个全局变量收敛而来
const nameMapCache = { map: null, ts: 0 };

async function getStockNameMap() {
  // 第 1 层：内存缓存（原 124-128 行）
  const mem = readMemoryCache(nameMapCache, Date.now(), NAME_MAP_CACHE_TTL);
  if (mem) return mem;

  const app = getCloudbaseApp();

  // 第 2 层：存储新鲜命中（原 131-157 行）
  const stored = await loadStoredNameMap(app, NAME_MAP_CLOUD_PATH, Date.now(), NAME_MAP_CACHE_TTL);
  if (stored.kind === 'fresh') {
    nameMapCache.map = stored.map;
    nameMapCache.ts = Date.now();
    return stored.map;
  }

  // 第 3 层：东财刷新，成功则回写（原 162-231 行）
  const fresh = await fetchEastMoneyNameMap(requestHttps, MARKET_FILTERS);
  if (fresh.size > 0) {
    nameMapCache.map = fresh;
    nameMapCache.ts = Date.now();
    console.log(`Got fresh stock name map from EastMoney: ${fresh.size} entries`);
    await persistNameMap(app, NAME_MAP_CLOUD_PATH, fresh);
    return fresh;
  }
  console.log('EastMoney returned 0 entries, will try fallback');

  // 第 4 层：过期存储兜底（原 237-254 行）
  if (stored.kind === 'stale') {
    nameMapCache.map = stored.map;
    nameMapCache.ts = Date.now(); // 沿用现状；该行缺陷修复见 cache-strategy.md §4.1
    console.log(`Using stale stored name map as fallback: ${stored.map.size} entries`);
    return stored.map;
  }

  // 第 5 层：硬编码快照（原 256-267 行）
  const hardcoded = loadHardcodedNameMap();
  if (hardcoded) {
    console.log('Using hardcoded name map fallback');
    nameMapCache.map = hardcoded;
    nameMapCache.ts = Date.now();
    return hardcoded;
  }

  // 第 6 层：空 Map（原 269-271 行）
  console.log('Using empty name map fallback');
  return new Map();
}
```

编排层约 40 行（不含注释与空行），六层降级一目了然，与原函数逐层对应：内存、存储新鲜、东财、过期存储、硬编码、空 Map。降级决策全部集中于此，六个子函数对编排层只暴露数据与结果，不暴露控制流。

## 七、行为不变性核对清单

合入前按下表逐项核对，✓ 表示与原行为一致：

1. ✓ 六层顺序与触发条件不变，逐层对应关系见第六节行号标注。
2. ✓ 每层成功后缓存槽赋值时机与原代码一致，包括 stale 兜底路径的赋值（该处语义缺陷的修复单独立项，不在本次重构内夹带）。
3. ✓ 日志文案逐字保留，仅"Using hardcoded name map fallback"一条由子函数移至编排层，运维日志检索口径不受影响。
4. ✓ 返回类型恒为 Map，下游 `getDailyMovers` 第 357-384 行的 `nameMap.get` 与 `nameMap.size` 用法无需任何改动。
5. ✓ `stock-names/name-map.json` 的载荷契约（names/updatedAt/count/source）不变，新旧版本可无缝读写同一份存储文件。
6. ⚠ 唯一显式偏离：存储文件在"第二层 miss 且第四层兜底"场景下由两次下载合并为一次（原第 131-137 与 238-241 行各下载一次），worst case 省一次网络往返且最终结果不变。
7. ⚠ stale 兜底的缓存装填时机从"东财尝试之前"移至"东财确认失败之后"，中间态更干净，最终赋值结果与原代码一致。

## 八、单元测试设计

测试宿主用 Node 自带 `node:test`，不引入三方测试框架，与云函数 package.json 现状兼容。每个函数的关键用例：

| 函数 | 用例示例 |
| --- | --- |
| readMemoryCache | ttl 内命中返回原 Map 实例；恰为 ttl 返回 null（边界）；空槽返回 null；命中时日志包含 map size |
| loadStoredNameMap | stub 分别返回：合法新鲜载荷→fresh；updatedAt 超二十四小时→stale；缺 names→miss；downloadFile 抛异常→miss 且日志含 No stored name map；缺 updatedAt→stale（保守侧） |
| codeToTsCode | 600519→.SH；000001 与 300750→.SZ；830799 与 430047→.BJ；9 开头→null；空串→null |
| fetchEastMoneyNameMap | stub 首页满百条→继续翻页；次页九十九条→停止翻页；diff 缺失→break；requestFn 抛异常→返回已累积 Map 而非抛出 |
| persistNameMap | stub uploadFile 抛异常→函数自身不抛；断言载荷含 names/updatedAt/count/source 五字段且 count 等于 Map 大小 |
| loadHardcodedNameMap | stub require 抛异常→null；正常→Map 且 size 等于快照条目数 |

编排层另做一个集成级冒烟：以 stub 注入六个子函数，覆盖"全链成功""东财空结果落到 stale""全链失败落空 Map"三条主干路径，断言降级顺序与缓存槽赋值。

## 九、迁移步骤与回滚

迁移分四步走，每步可独立回退。第一步，在同一文件内新增六个子函数与编排层，旧实现整体更名为 `getStockNameMapLegacy` 且不导出，生产入口暂时仍指向旧实现。第二步，部署到测试环境，用同一批 ts_code 集合对比新旧函数输出，断言两个 Map 逐键相等；重点覆盖北交所与停牌股两类边界样本。第三步，切流生产并观察三个交易日的日志：六层各自命中次数的分布应与旧版本一致，`Name mapping` 覆盖率日志不应下降。第四步，删除 Legacy 实现与旧全局变量 `cachedNameMap/cachedNameMapTs`，同时补入 5.1 节的缓存槽常量。

回滚策略：整个迁移收敛为单个提交，git revert 即可整体回退；存储契约未发生任何变化，回滚不涉及数据迁移，重启函数实例后内存缓存自然重建。

## 十、收益量化与结语

量化收益如下：单函数 150 行拆为六个平均约二十行的子函数加四十行编排层；圈复杂度从约二十二降至单函数最高约八（fetchEastMoneyNameMap）；模块级全局变量写点从五处收敛为一处；存储重复下载 worst case 从两次降为一次；可在无网络环境下单测的函数从零到六。可维护性收益的核心在于：ts_code 号段规则、TTL 策略、降级优先级这三类高频变更点各自有了唯一归属，改其一不必再通读其余五层。方法上，"降级链拆编排层"的拆法是通用的，可直接推广到本项目其他含多级兜底的云函数路径；六函数本身相互独立，loadStoredNameMap 与 codeToTsCode 亦可被后续行情类函数直接复用。

### 自我评估
- 正确性：4分 拆分方案与原代码行号逐一对应，设行为不变性核对清单与三步验证；等价性依靠人工逐行核对，未实际运行重构后代码做 diff 验证，此为本篇自评扣分点。
- 完整性：4分 六函数的签名/职责/输入输出/实现齐备，附测试设计、迁移与回滚；东财并行化与 stale 洗白缺陷按分工外链 performance.md 与 cache-strategy.md，未在本篇展开。
- 可复用性：5分 子函数依赖注入、彼此独立，codeToTsCode/loadStoredNameMap/persistNameMap 可直接复用于其他行情云函数；"降级链拆编排层"方法论可推广。
- 字数：约4550字（实测正文汉字4543，用脚本统计汉字区段U+4E00-U+9FFF，不含本自评）
- 使用模型：GLM-5.3-Flash
