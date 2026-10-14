# fetch-tushare-data 云函数代码完整性验证——requestHttps 到 exports.main 全链路逐段验证、截断检测与逻辑闭环确认

> 验证对象：`cloudfunctions/functions/fetch-tushare-data/index.js`（任务指定的 685 行全链路对象）。
> 验证人：Moon席位 写手-A组-2号。验证日期：2026-09-23。
> 结论速览：**当前快照（735 行）不是被截断，而是被并发编辑注入了 23 行编辑残片（第 234-256 行），导致语法损坏——文件无法通过解析**。逻辑设计本身闭环完整，删除残片即可恢复。全过程证据如下。

## 〇、任务口径与快照事实链

### 0.1 三个行数的事实

任务口径写"685 行"。本会话实际测得两个值，均不等于 685：

| 时点 | 行数 | 来源 |
| --- | --- | --- |
| 首测（本会话开始时） | 683 | `wc -l fetch-tushare-data/index.js` 输出 `683 fetch-tushare-data/index.js` |
| 当前快照 | 735 | `wc -l` 复测输出 `735`；`md5sum` 输出 `fbf3afdd7e820451d33f467b1732504f`；`ls -la --time-style=full-iso` 显示修改时间 `2026-09-23 08:19:27.884262500 +0800`；间隔 5 秒两次 md5 取值一致，确认快照稳定 |

事实链还原：本批次执行期间，同批次其他席位正在同一工作副本上做 P0 修复与重构（六个云函数的修改时间全部落在 08:19-08:27 区间内）。当前 735 行版本相对首测 683 行版本的差异是：新增 `requestHttpsRetry`（78-92 行）与 `fetchEastMoneyMarket`（94-129 行）两个函数，并把 `getStockNameMap` 内联的东财拉取循环改为调用 `fetchEastMoneyMarket`——**但旧循环体没有删干净**，残留为 234-256 行。685 行口径无法对应到本会话任何一次实测快照，如实存疑：可能是任务编制时的中间版本或统计口径差异（CRLF 不影响 `wc -l` 计数，可排除换行符因素；`python` 按字符统计 `\n` 亦为 735）。

**本文全部行号以 735 行快照为准。**

### 0.2 验证工具链声明

- `node --check` **未运行**：本机 bash 环境执行 `node --check` 报 `node: command not found`，`where.exe node` 无结果，`C:/Program Files/nodejs` 不存在。生产运行时为 Node 18（`cloudfunctions/functions/broadcast-a2a/scf_bootstrap` 内容为 `/var/lang/node18/bin/node index.js`），与本机环境无关。
- 替代方案：Python 3.12.10 编写的两个静态扫描脚本（本会话实际运行）：
  1. 词法剥离扫描器——用状态机（code/行注释/块注释/单双引号串/模板串五态）剥离注释与字符串后统计三种括号配对、统计各函数定义与调用点数；
  2. 循环深度分析器——在剥离后的代码上跟踪花括号栈（区分 loop 块与普通块）与 for/while/switch 关键字，定位"脱离任何循环的 break/continue"与"深度归零前的多余闭括号"。
- 局限如实声明：该扫描器不解析正则字面量（本文件经人工核对无正则字面量），不等于完整语法树解析；最终判定仍需代码席位在 Node 环境复跑 `node --check`。

## 一、全链路结构图谱（逐段验证的总纲）

对剥离后代码的统计输出（脚本实际运行结果）：

```
{}: open=134 close=136 balanced=False
(): open=314 close=314 balanced=True
[]: open=8 close=8 balanced=True   （首次运行口径，与第二次 [] 23/23 的差异源于注释剥离顺序修正，结论一致：方括号配平）
getCloudbaseApp defined: True callsites: 5
requestHttps defined: True callsites: 3
requestHttpsRetry defined: True callsites: 1
callTushare defined: True callsites: 2
getStockNameMap defined: True callsites: 1
getLatestTradeDate defined: True callsites: 1
getDailyMovers defined: True callsites: 1
checkCompliance defined: True callsites: 1
createAlertItems defined: True callsites: 1
saveAlertsToDB defined: True callsites: 1
exports.main count: 1
last line: };
ends with newline: True
hardcoded-names.js exists: True
@cloudbase/node-sdk in package.json: True
```

十个函数全部"有定义、有调用、调用数与人工审读一致"，`exports.main` 唯一，文件以 `};` 收尾且带末换行——**顶层骨架完整，唯一的不配平正是花括号多出 2 个闭合**（134 对 136），定位见第三节。

## 二、逐段验证（按行区间）

### 2.1 头注释与模块常量（1-25 行）

1-17 行块注释说明四个功能与触发方式；19-25 行定义 `TUSHARE_API_URL`、`TUSHARE_TOKEN`（`process.env.TUSHARE_TOKEN || ''`）、`THRESHOLD`、`DKNOWC_API_KEY`、`DKNOWC_API_URL`。验证点：**无任何密钥字面量**（`grep -rl "TUSHARE_TOKEN\s*=\s*'" --include="*.js" cloudfunctions/functions/` 输出为空）。✅ 通过。

### 2.2 CloudBase 单例（27-37 行）

`let _cloudbaseApp = null; function getCloudbaseApp() {...}`，模块级惰性单例。验证点：本文件内 `cloudbase.init(` 出现次数 = 1（`grep -c` 输出 `fetch-tushare-data/index.js:1`），且位于单例体内；调用点 5 处（185、265、290、551、661 行，grep 输出原文见 A8 文档）。✅ 通过（详见 A8）。

### 2.3 requestHttps（39-76 行）

Promise 包装 `https.request`：43-52 行组装 `hostname/path/method/headers`；54-64 行响应回调累积 body 并 `JSON.parse` 后 resolve，解析失败 reject（61 行只带 `body.length` 不带内容）；66 行 `req.on('error', reject)`；67-69 行 `req.setTimeout(options.timeout || 15000, () => req.destroy(new Error('Request timeout')))`；71-74 行写 body 后 `req.end()`。验证点：**超时链路闭环**——`req.destroy(error)` 会触发 `error` 事件，被 66 行捕获并 reject，Promise 必然落定，无悬挂。✅ 通过（语义细节见 A9/A10）。

### 2.4 requestHttpsRetry（78-92 行）

`for (let attempt = 0; attempt <= maxRetries; attempt++)` 包裹 `await requestHttps`，失败则 `500 * 2^attempt` 毫秒退避（88 行日志明确 500ms/1000ms），最后一次失败原样抛出（86 行 `if (attempt === maxRetries) throw e;`）。验证点：循环边界 `<=` 使总尝试为 maxRetries+1=3 次；await 链无泄漏。✅ 通过。

### 2.5 fetchEastMoneyMarket（94-129 行）

按市场 `fs` 串行分页（99 行 `page <= 20`），每页经 `requestHttpsRetry`（102 行），校验 `!data || !data.data || !data.data.diff`（103 行）、空页退出（105 行）、字段缺失跳过（110 行）、`tsCode` 后缀按 6/0,3/8,4 规则生成（112-116 行）、`stocks.length < 100` 提前收尾（121 行）、单页异常 break 该市场（122-125 行）。✅ 结构通过；数据格式校验缺口另见 security.md 第三节（不改判定本节语法完整性）。

### 2.6 缓存变量（131-139 行）

`cachedTradeDate`/`cachedTradeDateTs`（TTL 1 小时）、`cachedNameMap`/`cachedNameMapTs`（TTL 24 小时）四个模块级变量。验证点：均为容器级缓存，函数实例存活期内有效，语义与注释一致。✅ 通过。

### 2.7 callTushare（141-165 行）

组包 `api_name/token/params/fields`（145-150 行）→ `requestHttps POST timeout:15000`（152-157 行）→ 159 行 `data.code !== 0` 校验 → 161 行 token 脱敏 → 164 行返回 `data.data`。✅ 通过。

### 2.8 getStockNameMap（167-324 行）——含本次验证的核心发现

设计降级链六级：内存缓存（178-181）→ CloudBase 存储新鲜缓存（184-209）→ 东财并行刷新（216-283，经 `Promise.all` 调四个 `fetchEastMoneyMarket`，224-233 行合并结果）→ 过期存储缓存兜底（289-306）→ 硬编码映射（308-319，`require('./hardcoded-names')`，文件存在已验证）→ 空 Map（321-323）。前半段与后半段各自语法完好。

**但 234-256 行是编辑残片**，详见第三节。除残片外本段逻辑 ✅。

### 2.9 getLatestTradeDate（326-391 行）

缓存命中（332-335）→ 计算 30 天窗口起止（338-351）→ `callTushare('trade_cal', ...)` 限制 `start_date/end_date/limit:'1'`（353-362）→ 取 `items[0][0]`（365 行）→ 失败回退本地推算（374-390：周日减二、周六减一、工作日取当天）。验证点：365 行 `tradeCal.items[0][0]` 依赖 Tushare `fields:'cal_date'` 单列返回，与 353-362 行的 fields 参数匹配。✅ 通过。

### 2.10 getDailyMovers（393-441 行）

398 行取交易日 → 402-410 行 `Promise.all` 并行拉 daily 与名称映射，daily 失败 `.catch` 返回 null（405-408）→ 412 行校验 `items` 非空 → 415-419 行 fields 映射 → 421-426 行名称补全 → 428-431 行按 `THRESHOLD` 过滤 → 433-436 行日志统计。✅ 通过。

### 2.11 checkCompliance（443-488 行）

无 Key 跳过（457-460）→ `requestHttps POST timeout:10000`（463-474）→ 476 行 `safeType` 兜底 `'Unknown'` → 480 行 Safe/ConditionallySafe 判定 → 484-487 行检查失败跳过不阻塞。✅ 通过。

### 2.12 createAlertItems（490-543 行）

方向判定（497 行）、信号阈值（498 行 `absPct = Math.abs(pctChg).toFixed(2)`、503 行 `absPct >= 8.0`）。验证点：503 行是**字符串与数值的关系比较**，JavaScript 规范将字符串 ToNumber 后比较（`"8.00" >= 8.0` 为 true），行为正确但建议改为先数值化以消歧义。alertId 规则 `symbol_now`（529 行）、signalNote 仅涨/跌两态（505-511 行）、文案为白话固定句式（515-521 行）——与适老化与三禁红线一致。✅ 通过。

### 2.13 saveAlertsToDB（545-610 行）

下载现有 alerts.json（557-559）→ 并发写保护：现有 `serverTs > 当前最新 ts` 则跳过（572-576）→ alertId 去重合并（579-587）→ 按 ts 降序保留 500 条（590-592）→ 上传（601-604）→ 全程 try/catch（549-609）。✅ 通过。

### 2.14 exports.main（612-735 行）

见第四节逻辑闭环。结构本身：try/catch 完整，735 行 `};` 收尾。✅。

## 三、截断检测——结论是"编辑残片"，不是截断

### 3.1 证据一：括号不配平且方向为"多闭合"

词法扫描输出 `{}: open=134 close=136`——多 2 个闭合括号。若是网络传输截断，特征应为"少闭合"（文件中途截断必然欠闭合）且文件尾缺失；本文件 `last line: };`、`ends with newline: True`，文件尾完好。**排除截断**。

### 3.2 证据二：非法 break 与残片定位

循环深度分析器输出（实际运行结果）：

```
final brace depth (should be 0): 0
issues found:
  line 235: keyword 'break' outside any loop
  line 253: keyword 'break' outside any loop
  line 284: EXTRA closing brace at depth 0
  line 324: EXTRA closing brace at depth 0
total issues: 4
```

人工比对源码：234-256 行是旧版内联东财循环的残体——

```js
234:        const stocks = data.data.diff;      // data/fs/page 在此作用域均未定义
235:        if (stocks.length === 0) break;     // break 不在任何循环内 → V8: Illegal break statement
...
252:        console.log(`EastMoney: fs=${fs}, page=${page}, ...`);  // fs/page 已随旧循环删除
253:        if (stocks.length < 100) break;     // 第二处非法 break
254:        page++;
255:      }                                     // 多余闭括号①
256:    }                                       // 多余闭括号②
```

（分析器报 284/324 行多余闭括号，是因为 255/256 两枚残片括号提前闭合了 try 块，使解析器在 284 行 `} catch` 处才探测到深度异常——同一根因的两种表象。）

### 3.3 判定与后果

**判定：当前 735 行版本语法损坏，云函数无法加载部署**。Node 18 V8 解析到 235 行即抛 `SyntaxError: Illegal break statement`（早于花括号错误暴露）。这也意味着 08:19:27 的并发编辑引入的是阻断级回归——本批次任何"已修复"的表述都必须以删除残片为前提才成立。

### 3.4 修复补丁（由代码席位执行，写手席位不改源码）

删除 234-256 行整块（23 行），使 233 行合并循环的 `}` 直接衔接 258 行 `console.log(\`EastMoney total: ...\`)`。修后行数 735-23=712，花括号恢复 134/134 配平，两处非法 break 一并消除。修后必须复跑：

```bash
node --check cloudfunctions/functions/fetch-tushare-data/index.js   # 应无输出
md5sum cloudfunctions/functions/fetch-tushare-data/index.js          # 锚定新快照
```

## 四、逻辑闭环确认

### 4.1 exports.main 四条返回路径全覆盖

| 路径 | 行号 | 条件 | 返回形状 |
| --- | --- | --- | --- |
| ①快速失败 | 618-625 | `TUSHARE_TOKEN` 未配置 | `{success:false, error:'TUSHARE_TOKEN not configured', items:[], serverTs}` |
| ②空异动 | 631-638 | movers 为空 | `{success:true, items:[], serverTs, message}` |
| ③正常成功 | 720-725 | 全链路完成 | `{success:true, items, serverTs, count}` |
| ④异常兜底 | 726-734 | 任意抛错 | `{success:false, error:e.message, items:[], serverTs}` |

四条路径都携带 `serverTs` 与 `items`，与端侧 `AlertFeed` 契约（`entry/src/main/ets/model/AlertItem.ets`）字段闭合；`exports.main` 全文唯一（扫描输出 `exports.main count: 1`）。✅ 闭环。

### 4.2 降级链闭环

- 交易日：trade_cal 失败 → 本地推算最近工作日（374-390），永不抛出到 main 之外。
- 名称映射：六级降级（2.8 节）终点是空 Map，`createAlertItems` 用 `mover.name || mover.ts_code`（499 行）兜底显示代码。
- daily 主数据失败：`.catch` 返回 null → `getDailyMovers` 返回 `[]` → 走路径②而非④，语义为"今日无异动"而非"系统故障"，符合"首屏永不空白、服务未连通显示演示卡"的端侧约束。
- TTS/合规批量：`Promise.allSettled`（654、663 行）保证单项失败不影响整体，结果逐项落 `complianceStatus`/`audioUrl`；`audioUrl` 失败留空由端侧按需调 `generate-tts`，与已知问题口径一致。

### 4.3 异步与资源闭环

`requestHttps` 的三种落定（resolve/reject/超时经 destroy 转 error）在 2.3 节已验证；`requestHttpsRetry` 有限次尝试必返回；`Promise.all` 中两翼（daily 的 catch 与 getStockNameMap 的六级兜底）都不会 reject，外层 try/catch 兜住剩余异常。无悬挂 Promise、无未 await 的调用点（除 549 行 `saveAlertsToDB` 在 718 行被 await，且其内部自吞异常——设计为"存储失败不阻塞返回"）。✅。

## 五、复验命令清单与并发编辑流程建议

```bash
cd cloudfunctions/functions
wc -l fetch-tushare-data/index.js                      # 修后应为 712
md5sum fetch-tushare-data/index.js                      # 锚定快照
node --check fetch-tushare-data/index.js                # 语法闸门（本机不可用时在CI/部署机执行）
grep -n "break" fetch-tushare-data/index.js             # 每处 break 应都在 for/while 行区间内
```

流程建议：本批次存在多席位并发修改同一工作副本的情况（六个云函数 08:19-08:27 连续变更）。建议 (1) 任何席位落盘修复前先 `md5sum` 锚定，(2) 修复粒度以"整块替换"代替"就地插入"，(3) 每次改动后必须过 `node --check` 闸门再宣告完成——本次 735 行回归正是缺这道闸门的直接后果。

## 六、附录A：首测快照（683 行）与当前快照（735 行）差异分析

完整性验证必须回答"变的是什么、变的范围是否与声明的修复一致"。本会话恰好握有两个快照：首测 683 行版（本会话开始时读取全文）与当前 735 行版（md5 `fbf3afdd…`）。逐段比对后差异清单如下：

| 区域 | 683 行版 | 735 行版 | 判定 |
| --- | --- | --- | --- |
| 1-76 行（常量、单例、requestHttps） | 完全一致 | 一致 | 无改动 |
| 78-92 行 | 不存在 | 新增 `requestHttpsRetry` | 并发编辑新增（重试封装） |
| 94-129 行 | 不存在 | 新增 `fetchEastMoneyMarket` | 并发编辑新增（按市场分页函数） |
| 131-165 行（缓存变量、callTushare） | 原行号 78-112，内容一致 | 一致（行号平移） | 仅位置变化 |
| getStockNameMap 东财拉取段 | 内联双层循环（原 169-204 行） | 改为调 `fetchEastMoneyMarket` 并 `Promise.all` 四市场并行（216-233 行） | 重构：串行改并行 |
| 234-256 行 | 不存在 | **旧循环体残片** | 编辑事故（第三节） |
| 258 行以后至文件尾 | 内容一致 | 一致（行号整体平移 +52） | 无改动 |

差异净额核算：新增两个函数约 52 行 + 残片 23 行 − 删除的旧内联循环约 30 行 ≈ +45~52 行，与 683→735 的 +52 吻合。结论：除残片外，两快照间的全部变化集中于"东财名称拉取的重构"，与任务口径中 A10（统一封装）、超时重试的修复方向一致；**没有任何一处变化触及 exports.main 的四条返回路径与降级链结构**——即逻辑闭环的结论对两个快照均成立，损坏仅是语法层。

## 七、附录B：全链路调用图（文本版，行号锚定 735 行快照）

```
exports.main (615)
├─ 守卫：TUSHARE_TOKEN 空 → 返回路径① (618-625)
├─ getDailyMovers (397)
│   ├─ getLatestTradeDate (330)
│   │   ├─ 命中内存缓存 (332-335)
│   │   ├─ callTushare('trade_cal') (355) ─→ requestHttps (152) ─→ 超时15s (67-69)
│   │   └─ 失败 → 本地推算最近工作日 (374-390)
│   └─ Promise.all (402)
│       ├─ callTushare('daily') (403) ─→ .catch 降 null (405-408)
│       └─ getStockNameMap (176)
│           ├─ 内存缓存 (178) / CloudBase 存储缓存 (184-209)
│           ├─ 东财刷新：Promise.all × 4 市场 (224)
│           │   └─ fetchEastMoneyMarket (97) × [页面1-20 串行]
│           │       └─ requestHttpsRetry (81) ─→ requestHttps ─→ 退避 500/1000ms (87)
│           ├─ 过期缓存兜底 (289-306) → 硬编码映射 (308-319) → 空 Map (321-323)
│           └─ 成功 → 上传名称缓存 (265-274)
├─ movers 空 → 返回路径② (631-638)
├─ createAlertItems (493) → alerts（含 signal/fact 分型 503、白话文案 515-521）
├─ signalAlerts = filter(signal).slice(0,10) (647)
│   └─ Promise.all (653)
│       ├─ allSettled × checkCompliance (654-658 → 456)
│       │   └─ requestHttps(DKnowC) (463) ─→ 超时10s ─→ 失败跳过放行 (484-487)
│       └─ allSettled × app.callFunction('generate-tts') (663-672)
│           └─ 逐项落 complianceStatus (684-697) / audioUrl (702-715)
├─ saveAlertsToDB (718 → 549)
│   ├─ 下载 alerts.json (557) → 并发写保护 (572-576) → 去重合并 (579-587)
│   ├─ 保留最新500条 (590-592) → 上传 (601-604)
│   └─ 全程 try/catch，存储失败不阻塞返回 (549-609)
└─ 返回路径③ (720-725)；任何未捕获异常 → 路径④ (726-734)
```

图中每个叶子节点都能回溯到本会话逐行读过的源码行号，无凭记忆推断的边。值得强调的三处结构性质：其一，名称映射的六级降级链与 daily 的 catch 降级相互独立，二者不串联——名称失败不会拖垮主数据；其二，合规检查与 TTS 生成被放进同一个 `Promise.all`（653 行），两翼内部又各自 allSettled，形成"外层并行、内层隔离"的双层容错；其三，`saveAlertsToDB` 在所有信号处理之后才执行（718 行），即使它整体失败也只影响持久化不影响本次返回——这个顺序保证了调用方总能先拿到当轮异动列表。

## 八、附录C：十四段验证结论一览

| 段 | 行区间 | 内容 | 语法 | 逻辑 |
| --- | --- | --- | --- | --- |
| 1 | 1-25 | 头注释与常量 | ✅ | ✅ 密钥全环境变量 |
| 2 | 27-37 | CloudBase 单例 | ✅ | ✅ init 仅 1 处 |
| 3 | 39-76 | requestHttps | ✅ | ✅ 超时闭环 |
| 4 | 78-92 | requestHttpsRetry | ✅ | ✅ 有限次退避 |
| 5 | 94-129 | fetchEastMoneyMarket | ✅ | ✅（格式校验缺口另见 security.md） |
| 6 | 131-139 | 缓存变量 | ✅ | ✅ TTL 语义正确 |
| 7 | 141-165 | callTushare | ✅ | ✅ 含 token 脱敏 |
| 8 | 167-324 | getStockNameMap | ⚠️ 含 234-256 残片 | ✅ 六级降级完整 |
| 9 | 326-391 | getLatestTradeDate | ✅ | ✅ 窗口限定+本地兜底 |
| 10 | 393-441 | getDailyMovers | ✅ | ✅ 并行+catch 降级 |
| 11 | 443-488 | checkCompliance | ✅ | ✅ 失败放行不阻塞 |
| 12 | 490-543 | createAlertItems | ✅ | ✅（503 行字符串比较建议数值化） |
| 13 | 545-610 | saveAlertsToDB | ✅ | ✅ 并发保护+去重+限量 |
| 14 | 612-735 | exports.main | ✅ | ✅ 四路径闭环 |

十四段中十三段全绿，唯一红点集中在第 8 段的残片区间——修复动作是整块删除而非重写，改动半径被压缩到最小。

## 九、附录D：完整性检查方法选型

本会话因环境缺 Node 被迫自建 Python 词法扫描，顺势比较了各方法的效力与成本，沉淀为后续批次的选型参考。`wc -l` 只能锚定行数，对"残片型"损坏（总量增加）不敏感，本案若只看行数会得出"文件变长、大概没事"的错误结论。`md5sum` 是快照锚定的唯一可靠手段，本会话正是靠"5 秒两次 md5 一致"才确认了快照稳定，它的正确用法是变更前后各取一次形成对照。`node --check` 是语法闸门金标准，能直接抛出 `Illegal break statement` 定位到 235 行，代价是需要 Node 环境——建议接进部署流水线而非依赖个人机器。括号配平统计（本会话 Python 脚本）是零依赖的粗筛，对"多闭括号"型的编辑残片特别有效，但对方括号/圆括号配平而语义破坏的场景无感。循环深度分析（break/continue 归属）是本案的定位利器：残片的本质特征就是"控制流语句失去了宿主循环"，两个非法 break 恰好把残片钉死在 235/253 行。五者分工：md5 锚定、node --check 定性、括号统计粗筛、循环分析定位、wc -l 仅作记录。任何单一手段都不足以下结论，组合使用才有交叉证实力。

## 十、附录E：结论使用方式与后续动作

### 10.1 结论的正确解读边界

本文的核心判定是语法层与结构层的，必须防止被误读为功能层结论。语法损坏的判定是强结论：只要 235 行的非法 break 还在，任何 Node 18 运行时都无法加载该模块，这与运行环境、部署区域、配置参数无关，属于"不修必炸"的确定性缺陷。逻辑闭环的判定则是中强结论：四条返回路径、六级降级链、双层容错结构都经逐行核对成立，但"闭环存在"不等于"每条路径的行为都符合预期"——例如 503 行字符串与数值的比较虽行为正确，风格上仍建议数值化；又如空异动路径对用户呈现"今日无异动"，而上游接口整体超时时用户其实分不清"真的没有异动"与"数据没取到"，这属于产品语义选择而非缺陷，端侧演示卡契约已兜住底线。因此下游引用本文时应表述为："结构完整性与降级设计经静态验证成立，语法层存在一处阻断性残片，修复后需复跑语法闸门"，而不应简化成"验证通过"四个字——后者会掩盖残片的存在，重演本次回归的成因。

### 10.2 后续动作与责任划分

修复责任在代码席位：删除 234-256 行残片、复跑 node --check、以新 md5 锚定快照并同步更新本文行号表。写手席位（本席位）到产出本文为止，不改源码——这不是能力限制而是批次分工，且并发编辑的工作副本上再叠加第三个修改者只会放大冲突窗口。复核责任在批次主控：本文第三、四节的判定与 9.1 节流程建议（md5 锚定、整块替换、语法闸门前置）合并验收，确认修复后的行数（预期 712）与括号配平（预期 134/134）。归档动作：本文与同批 security.md、A8/A9/A10 四份互为印证——security.md 引用了本文的扫描脚本结论，A8 的五处调用点与本文附录B调用图同源，引用关系已在各文注明，归档时应作为一组存放，避免单篇被抽走后行号口径失去锚点。

### 10.3 复现成本与材料归档

本文全部结论可在十分钟内复现：wc 与 md5sum 两条命令共需数秒；词法扫描与循环分析两个脚本已随批次归档于工作区（`_tmp_integrity_check.py`、`_tmp_break_check.py`），对任意 index.js 改一下脚本头部的路径常量即可重跑；唯一依赖外部条件的是 node --check，需在有 Node 18 的机器或流水线上执行。建议把这两个脚本收编进仓库 `tools/` 目录并在流水线里串行执行——它们的存在本身就是对"语法闸门缺失导致本次回归"这堂课的制度化回应，成本近零而收益随每次合并累积。

## 十一、验证状态汇总

| 检查项 | 状态 | 证据 |
| --- | --- | --- |
| 735 行全文逐段审读（14 段） | 已执行 | 第二节，行号锚定 md5 fbf3afdd… |
| 括号配平统计 | 已执行 | `{134/136` 不配平 |
| 非法 break/多余闭括号定位 | 已执行 | 235/253/284/324 四项输出 |
| 文件尾与截断特征检查 | 已执行 | `};` 收尾、带末换行、排除截断 |
| 函数定义/调用点计数 | 已执行 | 十函数全对齐（第一节输出） |
| 依赖存在性（hardcoded-names.js、@cloudbase/node-sdk） | 已执行 | 均 True |
| node --check | **未运行** | 本机无 node（`node: command not found`） |
| 云函数实际加载/部署验证 | **未运行** | 本会话未部署任何云函数 |

### 自我评估
- 正确性：4分——核心结论（735行快照因234-256行编辑残片语法损坏、非截断）由括号配平+循环深度两项独立静态检查与逐行人工比对交叉证实；但最终语法判定依赖未运行的 node --check，静态扫描器不能完全等价于语法树解析，故不自评满分。
- 完整性：4分——覆盖任务三要素（逐段验证/截断检测/逻辑闭环）并额外回答了"685行口径与实测不符"的偏差；运行时验证未做，已如实标注并给出复验命令。
- 可复用性：5分——结构图谱、四路径表、补丁定位、复验命令与并发编辑流程建议均可直接迁移到其他批次与函数。
- 字数：约4400字（正文汉字实测4364）
- 使用模型：GLM-5.3-Flash
