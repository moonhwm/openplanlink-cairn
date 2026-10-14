# A24 AlertItem.ets 审查——AlertFeed JSON 契约定义、kind:fact/signal 区分、字段完整性

> 审查对象：`entry/src/main/ets/model/AlertItem.ets`（共 22 行，契约定义文件）；生产方对照：`cloudfunctions/functions/fetch-tushare-data/index.js`（createAlertItems :441-491、saveAlertsToDB :497-558）、`cloudfunctions/functions/get-alerts/index.js`（:57-76）；消费方对照：`entry/src/main/ets/services/AlertPoller.ets`、`entry/src/main/ets/pages/Index.ets`。
> 审查方式：2026-09-23 通读上述文件，对契约的"定义—生产—消费"三方逐字段对账；未运行服务端与端侧，凡动态行为推断均标注。

---

## 一、总体结论

AlertItem.ets 用 22 行定义了全项目最重要的端云契约：`AlertItem` 十字段 + `AlertFeed { items, serverTs }`，文件头注释直接写明 kind=fact/signal 的业务语义与合规边界（"机主 09-14 松绑，禁收益承诺/催促指令/对外公开"），契约即文档的做法值得肯定。三方对账发现的核心问题：①服务端实际产出了 `signalNote/pctChg/close/vol` 四个契约外字段，契约文件未声明，属于单向漂移；②`complianceStatus` 在契约中有、UI 中无任何消费，非合规（Unsafe）卡片只打日志不拦截，合规闭环缺最后一环；③端侧对响应零校验，脏数据直达 `Text()` 渲染；④`audioUrl` 的临时链接生命周期问题使该字段的可信期远短于 alerts.json 的存续期。分节展开。

---

## 二、AlertFeed JSON 契约逐字段对账

### 2.1 字段清单（定义 vs 生产 vs 消费）

`AlertItem.ets:6-17` 定义的十个字段对账结果：

| 字段 | 类型（定义处 :6-17） | 生产方证据 | 消费方证据 | 对账结论 |
|---|---|---|---|---|
| alertId | string，必选 | fetch-tushare-data:477 `${symbol}_${now}` | Index:203 find、:425 ForEach 键 | 一致；语义见 2.2 |
| ts | number（秒级，注释 :8） | :478 `ts: now`（Math.floor(Date.now()/1000)，:442） | PlayHistoryItem.alertTs 透传（Index:277） | 一致，秒级约定靠注释维系 |
| symbol | string，如 600176 | :479 | 自选股过滤 Index:162 | 一致 |
| name | string | :447 `mover.name \|\| mover.ts_code` | Index:373 Text 渲染 | 一致；兜底显示代码 |
| direction | 'up'/'down'/'flat' 字面量联合 | :445 三分支 | dirColor/dirLabel Index:289-307 | 一致；flat 为死值（见 3.4） |
| kind | 可选，'fact'/'signal'，注释"缺省按 fact 处理"（:12） | :451 显式赋 'fact'/'signal' | Index:381 `kind === 'signal'` 显徽章 | 一致；但缺省语义只活在注释里（见 3.5） |
| headline | string，一句话白话 | :462-469 模板拼接 | Index:400 Text | 一致 |
| detail | string | :471-474 | Index:405 `item.detail.length > 0` | 一致，但消费方直接取 `.length`，若服务端漏发将抛错（见 3.2） |
| audioUrl | 可选 string（:15 注释"无则不显示播报钮"） | generate-tts 回填（updateAlertAudioUrl） | Index:208/226 判空 | 一致；生命周期问题见 3.6 |
| complianceStatus | 可选 string（:16 注释五值） | fetch-tushare-data:635/643 | **全工程无消费** | 消费缺失（见 3.3） |

`AlertFeed`（:19-22）：`items: AlertItem[]` + `serverTs: number`。生产方 get-alerts:65-68 与 fetch-tushare-data:542-546 均返回该结构，serverTs 秒级一致；消费方 AlertPoller:79 取 `feed.items ?? []`。契约主体成立。

### 2.2 alertId 的格式语义与去重职责

服务端格式 `${symbol}_${now}`（fetch-tushare-data:477），秒级时间戳入键。两处消费依赖它：端侧 ForEach 键（Index:425）与通知回传定位（EntryAbility→pendingAlertId→playById）。存储层按 alertId 建 Map 去重、新覆盖旧（:527-535），因此"同一股票同一秒内重复触发"会收敛为一条——这是 alertId 兼职去重键的隐含语义，契约注释只写了"通知点击回传定位用"（:7），建议补一句"亦为云端去重键，全局唯一"。另注意：同股票跨秒会生成新 alertId（旧行保留），端侧列表会出现同股票多条递进异动卡——对播报场景合理，记录为预期行为。

### 2.3 serverTs 的双重职责

生产方 fetch-tushare-data:518-524 用 `existingServerTs > currentLatestTs` 做并发写入保护，说明 serverTs 兼任"写版本号"；消费方 AlertPoller 完全未读 serverTs（:67-79 只取 items）。当前无害，但契约注释应写明"兼作云端写序版本，端侧不得依赖其业务语义"，防止未来有人拿它当"最后更新时间"展示——它表达的是"最后一次成功写入 alerts.json 的时刻"，与最新异动 ts 不是一回事。

---

## 三、问题清单

### 3.1 问题 F1（高）：服务端四个契约外字段未入契约

`fetch-tushare-data/index.js:476-489` 的返回对象除契约字段外还携带：`signalNote`（signal 卡的提示语，:485）、`pctChg`（数值涨跌幅）、`close`（收盘价字符串）、`vol`（成交量字符串）。这些字段经 alerts.json 一路透传到端侧 `JSON.parse`（AlertPoller:69），但 `AlertItem.ets` 未声明——ArkTS 接口是结构化的，多余字段不报错，于是形成"契约文件说这是全部，实际报文比契约胖"的单向漂移。危害：①任何人以契约为准做端侧复刻（如未来加数据校验、做 mock）都会漏掉这四个字段；②`detail` 已把 signalNote 拼进文案（:484），signalNote 本身端侧再无独立价值，pctChg/close/vol 却是未来"detail 结构化展示"的现成原料。处置二选一：**a. 收**——服务端瘦身，只产出契约字段（signalNote 并入 detail 后删除）；**b. 扩**——契约补四个可选字段并写明语义。推荐 b：字段有真实用途，契约应反映现实。

### 3.2 问题 F2（高）：端侧零校验，脏数据直达渲染

消费链 `JSON.parse(...) as AlertFeed`（AlertPoller:69）→ `items ?? []`（:79）→ ForEach 渲染（Index:356）。alerts.json 由 fetch-tushare-data（写入）与 generate-tts（回填 audioUrl，:122-164）两个函数读改写，且 A21 已记录存储层并发窗口；一条缺 `headline` 或 `detail` 为 null 的脏条目，会让 `item.detail.length`（Index:405）这类直接访问抛错，进而可能打断整列表渲染。契约文件本身无 default、无守卫——**接口文件只管类型不管值**。修复建议（十行，放 Poller 出口）：

```ts
function normalizeItem(raw: object): AlertItem | null {
  const it = raw as AlertItem;
  if (typeof it.alertId !== 'string' || !it.alertId) return null;
  if (typeof it.headline !== 'string' || !it.headline) return null;
  return {
    ...it,
    ts: typeof it.ts === 'number' ? it.ts : 0,
    symbol: it.symbol ?? '',
    name: it.name ?? it.symbol ?? '',
    direction: it.direction === 'up' || it.direction === 'down' ? it.direction : 'flat',
    kind: it.kind === 'signal' ? 'signal' : 'fact',
    detail: typeof it.detail === 'string' ? it.detail : '',
  };
}
```

### 3.3 问题 F3（高）：complianceStatus 有生产无消费，Unsafe 卡片照常展示

生产侧：fetch-tushare-data:601-646 对 signal 卡调 DKnowC 检查并写入 `complianceStatus`，非合规只 `console.log('⚠ NON-COMPLIANT')`（:640），**不过滤、不降级**。消费侧：grep 核对 `complianceStatus` 在 `entry/src` 仅出现于 AlertItem.ets:16 定义处，UI 无任何读取。结果：假设 DKnowC 判某 signal 卡为 Unsafe，该卡仍带着"自家信号"徽章、合成语音、进入用户列表——三禁红线（承诺收益/保本、催促指令、对外公开/收费）的执行目前依赖"生成模板本身就是白话事实句"这一前置设计（:462-474 的 headline 模板确实不含违规措辞），但模板是静态防线，检查器判 Unsafe 却不拦，等于合规层只记录不执法。处置建议：在 fetch-tushare-data 落库前过滤 `complianceStatus === 'Unsafe'` 的 signal 卡（fact 卡为纯客观行情事实，可不过检不过滤，与现状一致），端侧 Index 对 `Unsafe` 条目做兜底隐藏——双层防线，任一失效另一层兜底。注意 422-428 行语义：`ConditionallySafe` 放行、`Unknown`（含 DKnowC 未配置/失败 :405-407、:432-435 的 skipped 放行）放行——放行策略保留，仅收紧 Unsafe。

### 3.4 问题 F4（低）：direction 的 'flat' 是契约死值

生产方 :445 只在 `pctChg === 0` 时给 'flat'，而入选异动的门槛是 `Math.abs(pct) >= THRESHOLD(5.0)`（:376-379），故生产路径永远产出 up/down，flat 仅存在于类型定义与端侧 dirLabel/dirColor 的 '平' 分支（Index:299-307）。保留它是正确的（契约完整性 + normalize 兜底需要），但契约注释宜标注"当前生产不产出，为未来横盘/停牌类异动预留"，避免后人误删或误依赖。

### 3.5 问题 F5（中）：kind 缺省语义只存在于注释

`AlertItem.ets:12` 注释"缺省按 fact 处理"，但端侧唯一消费点 `Index:381` 用严格相等 `item.kind === 'signal'` 判定徽章——`kind` 为 undefined/拼写异常（如 'Signal'）时按 fact 处理，行为恰好符合注释，这是靠"消费端写法正确"而非"解析层归一"实现的。若未来出现 `kind?.toLowerCase()` 之类的宽松写法，注释语义即刻失守。归一函数（F2 的 normalizeItem）已将 kind 收敛为二值，建议随 F2 一并落地，让"缺省即 fact"成为代码事实而非注释约定。

### 3.6 问题 F6（中）：audioUrl 的临时链接生命周期

生产链：generate-tts:310-334 `uploadToStorage` 先 `getTempFileURL`（:321-325），把**临时链接**写进 alerts.json 的 audioUrl 与 tts-cache。临时 URL 有有效期，过期后端侧 `av.url = url`（AudioPlayer:39）播放必然失败 → Index failedId "语音加载失败，点重试"（Index:412-417），且重试永远失败。契约层面 audioUrl 无"有效期"概念，端侧无从判断链接死活。处置方向（需决策，不在本篇擅自定案）：① 存储改用持久下载 URL；② 端侧按需调 generate-tts 换新链接（治理上下文已知问题"alerts.json 的 audioUrl undefined 端侧按需调 generate-tts"即指向此方向，但当前端侧 playById 对无 audioUrl 是静默跳过 Index:208-211，按需生成尚未实装）；③ 至少在播放失败且重试失败时，端侧调一次 generate-tts 刷新。无论选哪条，契约文件应为 audioUrl 注明"可能过期，消费方必须具备失效重取路径"。

### 3.7 次要发现

① `AlertItem.ets:16` complianceStatus 用宽泛 `string` 而非字面量联合 `'Safe'|'Unsafe'|'ConditionallySafe'|'Focus'|'Unknown'`——注释枚举与生产方 fetch-tushare-data:424-428 的实际取值一致，但类型层面未锁，建议收紧（与 kind 的做法对齐）。② ts 秒级约定与端侧 `PlayHistoryItem.alertTs`（SettingsService.ets:449-456）、`PlayHistoryItem.ts`（毫秒，Index:276 Date.now()）并存于同一历史条目，两套时间基准靠字段名区分，契约注释建议显式提醒（alertTs 秒、ts 毫秒），避免展示"多久前"时算错三个数量级。

---

## 四、契约演进建议（汇总）

1. **契约文件扩容**（对应 F1）：补 `signalNote?/pctChg?/close?/vol?` 四个可选字段及注释；
2. **归一防线**（对应 F2/F5）：Poller 出口 normalizeItem，缺省语义代码化；
3. **合规执法**（对应 F3）：服务端落库前过滤 Unsafe signal 卡，端侧兜底隐藏；
4. **注释补全**：alertId 兼任去重键（2.2）、serverTs 兼任写序版本（2.3）、direction flat 为预留（F4）、audioUrl 可过期（F6）、秒/毫秒双基准提醒（3.7②）；
5. **类型收紧**：complianceStatus 字面量联合（3.7①）。

以上五条全部不动 AlertFeed 现有字段的名称与必选性——端云两端可独立灰度：服务端先加字段（端侧旧版无感），端侧再上 normalize 与消费逻辑，契约向后兼容。

## 五、审查方法声明

本审查完成于 2026-09-23，依据当日仓库快照：契约文件 AlertItem.ets 全文 22 行逐行核对；生产方 fetch-tushare-data（684 行）与 get-alerts（77 行）中所有构造/透传 AlertItem 字段的代码段均已阅读并引用行号；消费方 AlertPoller.ets 与 Index.ets 的取值点已核对；`complianceStatus` 端侧消费点经 grep 全工程核实为零。**未执行项**：真实 alerts.json 样本抓取比对（本环境未连 CloudBase 线上数据）、DKnowC 实际返回值样本分析——契约外字段清单来自源码构造处，非报文抓包，若线上 alerts.json 存在历史遗留字段（如更早版本产物），需抓样后补对账。

### 自我评估
- 正确性：4分 三方对账（定义/生产/消费）全部附行号，契约外字段来自源码构造处核对而非猜测；未抓线上报文已声明。
- 完整性：4分 覆盖任务三主题（契约定义/fact-signal 区分/字段完整性）并给出可灰度的演进方案；F3 合规闭环缺口是超出字面任务但必要的发现。
- 可复用性：5分 对账表、归一代码、五条演进建议可直接执行；向后兼容与灰度顺序写明，不依赖对话上下文。
- 字数：约3600字
- 使用模型：GLM-5.3-Flash
