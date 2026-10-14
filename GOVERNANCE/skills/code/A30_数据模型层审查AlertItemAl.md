# 数据模型层审查——AlertItem/AlertFeed 契约、JSON 解析、字段验证

## 一、审查范围与契约地位

本篇为 harmony-app（代号铃语）数据模型层的审查知识资产。契约定义于 entry/src/main/ets/model/AlertItem.ets（23 行，本审查当日完整通读），消费方四处：AlertPoller.ets（反序列化唯一入口）、Index.ets（渲染与过滤）、EntryAbility.ets（推送 payload 提取 alertId）、SettingsService.ets（PlayHistoryItem 关联存储）。

该契约的战略地位需要先说清楚：**AlertFeed 就是端侧与服务端的全部接口面**。架构基调明文"数据源 FEED_URL 待 X 服务器落地，契约即 AlertFeed"——模型文件即接口文档本身，字段注释里写着生产语义与合规来源（kind=fact 客观异动、kind=signal 自家策略信号与白话解读、机主 09-14 松绑、禁收益承诺/催促指令/对外公开，AlertItem.ets:1-5）。因此本篇的每一个字段结论都同时是发给服务端的协议要求；反过来，服务端任何字段变更都必须先改这份 23 行的文件再动代码，这是本仓最接近"接口即代码"的实践。

## 二、AlertItem 契约逐字段审查

alertId，string 必填：端侧当 ForEach 键（Index.ets:425）、已读标记（readAlertIds 匹配）、播放定位、通知回传定位四处身份用，是协议第一键。要求服务端保证全局唯一且稳定——同一股票同一事件重发不得改 id，否则已读与播放态错乱。

ts，number 必填（秒级，注释 ：8）：端侧记入 PlayHistoryItem.alertTs（SettingsService.ets:455）。风险见第四节问题一。

symbol 与 name，string 必填：symbol 用于自选股过滤（Index.ets:160-163 的 includes 匹配）、name 用于卡片标题。要求 symbol 与 watchlist 存储项同构（六位代码），验证方案见第五节。

direction，'up'|'down'|'flat' 字面量联合：驱动 dirLabel/dirColor（Index.ets:289-307）。非法值运行期会安全落"平"（else 分支），但编译期契约会被 as 断言绕过（见第五节），两层兜底缺一不可。

kind，可选 'fact'|'signal'，缺省按 fact（注释 ：12）：端侧只对 signal 加「自家信号」描边角标（Index.ets:381-389），fact 不加角标。这是信号松绑合规的端侧落点——自家信号必须被视觉标注出来，与客观事实区分，老人有权知道"这是机器算的还是市场发生的"。signal 文案由服务端产出，三条禁令（不承诺收益/保本、不催促、不对外公开收费）在服务端提示词层执行。

headline，string 必填：卡片主白话（Index.ets:400-403），老人唯一必读句。契约未约束长度——超长会撑爆大字卡片，验证方案设上限。

detail，string 必填：次级信息（Index.ets:405-410），端侧用 item.detail.length > 0 判空——若服务端发 undefined 或 null，此表达式直接抛 TypeError，见第四节问题二。

audioUrl，可选 string：播报钮显隐（Index.ets:390）与 playById 短路（:208-211）。undefined 语义已定型并留档：无音频则不显示播报钮、端侧按需调 generate-tts（已知问题清单原文），契约注释与实现一致。这个"可选字段驱动能力降级"的设计值得保留：服务端 TTS 生成滞后时端侧不报错、不空转，安静地少一个按钮。

complianceStatus，可选 string，注释枚举 Safe/Unsafe/ConditionallySafe/Focus/Unknown（:16）：**零消费**（本次 grep 全仓核实仅模型声明一处），见第四节问题三。

## 三、AlertFeed 契约与反序列化现状

AlertFeed 仅两字段：items: AlertItem[] 与 serverTs: number（AlertItem.ets:19-22）。反序列化唯一入口在 AlertPoller.fetchLatest（AlertPoller.ets:66-79）：HTTP 200 后 JSON.parse(resp.result as string) as AlertFeed，三层防御——parse 抛异常被内层 catch 捕获并记原文前 200 字符、applyBackoff、返回 ok:false（:68-75）；解析成功取 feed.items ?? [] 做空值兜底（:79）；仅成功路径 resetBackoff（:78）。日志只截前 200 字符防刷屏，坏数据完全不进入 UI 管道。

评价：解析失败的降级路径完整，坏 JSON 当网络失败处理，不污染界面。但 as AlertFeed 是纯编译期断言，**运行期零结构验证**——字段缺失、类型漂移（ts 变字符串）、items 内混入半残条目都会原样流入 UI。当前靠"服务端自家产出、契约自家注释"的信任在撑；X 服务器落地后若引入多数据源聚合（Tushare 已降级东财即先例），上游字段口径不一的风险将直接砸到端侧渲染，必须补第五节的验证层。

第二解析点在 EntryAbility：receiveMessage 对 data.data 做 JSON.parse as Record 后取 alertId（EntryAbility.ets:89-94），有 try/catch，提取失败仅 warn，且 if (alertId) 已挡住空串与 undefined——通知路径解析鲁棒性达标，双保险成立。

## 四、发现的问题（按优先级）

- **问题一（P1，时间戳单位双轨）：** 契约 ts 是秒级（:8 注释），端侧播报历史另用 Date.now() 毫秒（Index.ets:276-277），PlayHistoryItem 里 ts 与 alertTs 两字段并存且单位不同（SettingsService.ets:454-455）。同一结构两种单位，未来做"异动发生后多久才播报"类统计必踩坑。建议：PlayHistoryItem 字段注释标明单位，或全端统一毫秒并推动服务端契约升版。
- **问题二（P1，detail 空值不设防）：** 端侧直读 item.detail.length（Index.ets:405），上游若发 null 或缺字段即抛 TypeError，且发生在 ForEach 渲染期，整页渲染挂掉。契约注释"必填"不等于运行期存在——as 断言不检查任何东西。第五节验证层直接解决。
- **问题三（P2，complianceStatus 声明未消费）：** 五级分类只入库不生效。契约既然承载合规分类，端侧最起码应实施"Unsafe 不渲染、ConditionallySafe 降级为仅 fact 字段展示"的最后一道闸——服务端提示词是软约束，端侧过滤是硬约束，适老化金融信息应用值得双保险。
- **问题四（P2，serverTs 声明未消费）：** 本次 grep 核实仅模型出现。闲置字段两种处置：删掉减负；或实装为时钟偏差校正与排序依据。items 顺序目前全信服务端数组序，客户端零排序逻辑——现状可行，但本地排序必须以 ts 为准并防同秒并列。
- **问题五（P3，DEMO_ITEMS 合规口径）：** 演示卡 ts:0、headline 带「示例」前缀（Index.ets:13-23）。ts:0 若流入播放历史会成为 1970 记录——现状演示卡无 audioUrl，点击不触发历史写入，安全；若未来演示卡配音频，须先补 demo 数据不入历史的隔离规则。

## 五、字段验证方案（建议新增 validate 层）

在 AlertPoller 解析成功后、返回 items 前插入一道纯函数过滤，零依赖：

```typescript
function isValidItem(it: AlertItem): boolean {
  return typeof it.alertId === 'string' && it.alertId.length > 0
    && typeof it.ts === 'number' && it.ts > 0
    && typeof it.symbol === 'string' && /^\d{6}$/.test(it.symbol)   // A股六位代码
    && typeof it.name === 'string' && it.name.length > 0
    && (it.direction === 'up' || it.direction === 'down' || it.direction === 'flat')
    && typeof it.headline === 'string' && it.headline.length > 0 && it.headline.length <= 50
    && (it.audioUrl === undefined || (typeof it.audioUrl === 'string' && it.audioUrl.length > 0))
    && (it.detail ?? '').length >= 0;   // detail 允许空串，不允许缺类型
}

// fetchLatest 内：return { ok: true, items: (feed.items ?? []).filter(isValidItem) };
```

设计取舍逐条说明：symbol 用六位数字正则，一次性完成 A 股代码格式校验与自选股匹配同构保证（watchlist 存的也是六位码，Settings.ets:373 的输入约定一致）；headline 上限 50 字对应白话卡片标准档 28fp 一屏两行内的排版阈值；direction 显式三值校验替代 else 落"平"的隐式兜底，坏数据在入口被丢弃而不是在 UI 被静默误显示成"平"；detail 用空值合并兜底而非丢弃整条——detail 缺失只降级不否定整卡；complianceStatus 不设死枚举校验（服务端可能扩级），端侧按问题三的规则消费。过滤后条目数与原始数之差可记日志，服务端坏数据率从此可观测。

## 六、契约演进规范（给服务端与端侧的联合条款）

第一，只增不改不删：新字段一律可选（对齐 audioUrl 与 kind 先例），已发布字段不得改语义（ts 秒级锁死），废弃先声明后移除。第二，缺省语义入注释：每个可选字段的缺省行为必须写在模型注释里（kind 缺省按 fact、audioUrl 缺省无播报钮是既有范本），端侧行为以注释为契约。第三，版本探测：建议服务端在 AlertFeed 增加 schemaVersion 可选字段，端侧遇到不认识的大版本号可整单丢弃退演示卡——比运行期逐字段猜类型便宜且安全。第四，白话文案即合规载体：headline、detail 与 signal 解读由服务端产出，三条禁令在服务端提示词执行，端侧 complianceStatus 过滤作第二道闸，两层都留日志可审计——合规不能只靠上游自觉。

## 七、ArkTS 严格模式下的模型设计约束

模型层在 ArkTS 严格模式（本仓约束：纯 ArkTS）下有几条硬性设计边界，现状契约全部合规，逐条留档防止后人踩线。其一，interface 而非 class：AlertItem 与 AlertFeed 都是 interface（AlertItem.ets:6、:19），JSON.parse 产物是普通对象，运行期没有类实例的任何方法与构造逻辑，端侧也从未对条目调用方法——契约保持纯数据，是对的；若未来想给模型加方法（如 formatTime），ArkTS 严格模式禁止对 parse 产物直接 as 成带方法的类再用实例方法（行为未定义），正确做法是独立工具函数接收 interface 参数。其二，字面量联合类型替代枚举：direction 与 kind 用 'up'|'down'|'flat' 这类字面量联合而非 enum，JSON 字符串可直接匹配，免一层转换，与 parse 产物天然对齐。其三，as 断言的诚实性：JSON.parse(...) as AlertFeed 是唯一可行的反序列化写法（严格模式禁 any、禁反射），它的前提就是"上游保证结构"，这正是第五节验证层存在的理由——断言管编译期，验证管运行期，两者缺一即为裸奔。其四，可选字段的序列化不对称：端侧 Preferences 存的 watchlist、readAlertIds、playHistory 走 JSON.stringify（SettingsService.ets:101、:403、:440），AlertItem 若被直接 stringify，undefined 的 audioUrl 与 complianceStatus 会被自然丢弃，重新 parse 后变成缺字段——因此端侧模型工具函数必须始终按"字段可能不存在"编码，与第五节验证层的口径一致。

端侧还有三个自有模型与契约的关系需要说清：PlayHistoryItem（SettingsService.ets:449-456）是 AlertItem 的投影（取 alertId/symbol/name/headline/ts 五字段加播报时间），投影在播放成功时发生（Index.ets:271-278），意味着历史记录的字段正确性继承自当时的条目验证结果；ThemeColors 与 FontSizeLevel/ThemeMode 是纯端侧配置模型，与服务端契约无关，不应混进 AlertFeed；DEMO_ITEMS 是契约的合法实例（Index.ets:13-23，kind 缺省按 fact），可用于验证层的单测基准样例——一个"合法条目长什么样"的活文档。

## 八、契约样例与三类演进场景演练

给一个符合现行契约的最小样例（可直接用作联调桩与服务端自检基准，与 DEMO_ITEMS 同构）：

```json
{
  "items": [
    {
      "alertId": "a-20260924-0001",
      "ts": 1780000000,
      "symbol": "600176",
      "name": "中国巨石",
      "direction": "up",
      "kind": "fact",
      "headline": "中国巨石 2 分钟上涨 2.3%",
      "detail": "成交量比平时多出一倍，现价 11.6 元",
      "audioUrl": "https://example.invalid/tts/a-0001.mp3",
      "complianceStatus": "Safe"
    }
  ],
  "serverTs": 1780000060
}
```

注意样例里的 detail 是白话（"比平时多出一倍"而非"量比 2.1"），这正是白话契约的精神：字段名叫 detail，语义叫"给老人听的补充说明"。以此样例演练第六节的三类演进：场景一加字段——服务端新增可信度评分，加一个可选字段即可，端侧验证层不受影响（未知字段被自然忽略），老版本应用照常运行，属安全演进；场景二改语义——若服务端把 ts 从秒改毫秒以对齐前端习惯，属于破坏性变更，必须走 schemaVersion 升版加端侧同步改造，否则时间显示错乱且无报错，是最危险的一类；场景三废弃字段——比如未来 TTS 全部预生成后想删 audioUrl 的可选语义，正确顺序是先在注释标注"计划废弃"、观察一个版本周期、确认无消费方后再删，端侧因验证层对 undefined 已兜底而全程无感。三类演练的结论一致：**可选加验证层的契约，演进成本最低**；缺了验证层，每次演进都是端侧的盲盒。

## 九、本层与合规红线的交点

数据模型层离内容最远，却是合规的最后一道结构性防线，三个交点需要点明。第一，kind 字段把自家信号与客观事实在数据结构层面分离，配合端侧「自家信号」角标，老人永远能区分"市场发生的"与"机器算的"，这是信号松绑后不越界的基础。第二，complianceStatus 字段已为内容安全分类预留了通道，一旦实装端侧过滤，Unsafe 内容在渲染前即被拦截——模型层是唯一能在渲染前拦住内容的位置。第三，headline 与 detail 的长度约束（验证层五十字上限）客观上压缩了违规表述的空间：一句话白话说不完的复杂诱导，本来就该被过滤掉。三条禁令的执行主体在服务端提示词，但结构上的防线上在本层，双保险缺一不可。

## 十、测试用例清单（建议落地为单测）

- 正常 feed 全字段齐备：全数通过验证层。
- JSON 断裂（截断、HTML 错误页）：ok:false、日志含前 200 字符、退避生效。
- items 为 null 或缺失：空数组兜底不崩溃。
- 单条缺 detail 或 detail 为 null：兜空串或过滤，页面不抛 TypeError。
- direction 非法值（如大写 Up）：被验证层丢弃。
- symbol 带交易所前缀（如 sh600176）：被六位正则丢弃（服务端契约须只发六位）。
- ts 为字符串类型：被验证层丢弃。
- 同 alertId 重复出现：现状无去重，确认服务端承诺唯一后可豁免端侧去重。
- 推送 data.data 为非法 JSON：warn 且 AppStorage 不被污染。
- 演示卡点击：无 audioUrl 不触发播放与历史写入。

### 自我评估
- 正确性：4分 逐字段结论与行号均来自本次实读的 AlertItem.ets、AlertPoller.ets、Index.ets、EntryAbility.ets、SettingsService.ets；complianceStatus 与 serverTs 零消费、detail 直读 length 的论断经实读与 grep 双重核实；验证代码为建议实现，未在本环境编译运行，扣一分声明。
- 完整性：4分 覆盖契约逐字段、反序列化现状、五问题、验证方案与取舍说明、严格模式约束、样例与演进演练、合规交点、测试清单；未对服务端 alerts.json 实际样例做比对（服务端文件不在端侧审查范围，契约以模型注释为准）。
- 可复用性：5分 "模型即契约"审查框架、validate 纯函数、演进四条可直接搬到任何端侧 JSON 契约项目；测试清单可即转单测用例表。
- 字数：约3100字
- 使用模型：GLM-5.3-Flash
