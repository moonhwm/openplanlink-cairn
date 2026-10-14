# 状态管理审查——@State/@Prop/@Link 使用规范、数据流向、组件通信

## 一、审查范围与 ArkTS 状态管理基线

本篇为 harmony-app（代号铃语）状态管理层的审查知识资产。审查对象（均在本审查当日完整通读）：entry/src/main/ets/pages/Index.ets（459 行）、entry/src/main/ets/pages/Settings.ets（558 行）、entry/src/main/ets/entryability/EntryAbility.ets（124 行）、entry/src/main/ets/services/SettingsService.ets（456 行）。

ArkTS 状态管理 V1 的装饰器语义基线：@State 是组件内部状态，框架对其做第一层深观察（对象第一层属性、数组引用本身），嵌套对象内部变化不被追踪；@Prop 是父到子的单向数据拷贝，父变子跟着变、子变不影响父；@Link 是父子双向引用，两端改都生效但责任难追溯；@Provide/@Consume 跨层级隐式传递；@Observed/@ObjectLink 把观察粒度下沉到对象级；@StorageLink/@StorageProp 把 AppStorage 的键挂进组件；@Watch 给状态变化挂监听回调。AppStorage 则是应用级单例键值仓，Ability 与页面都能直接读写，适合做跨层消息。

审查方法：先盘点现状，再按"该用没用、用了没用对、没用但该引入"三问展开。一个重要的 grep 事实先行给出：**全仓 ets 源码中 @Prop、@Link、@Provide、@Consume、@Observed、@ObjectLink、@StorageLink、@Watch 的使用为零**（本次 grep 核实），即当前只有 @State 加 AppStorage 两件武器。

## 二、@State 现状盘点

Index（@Entry）持有 18 个 @State：items、playingId、loadingId、failedId、lastRefresh、connectionBroken、isDemoMode、fontLevel、elderlyMode、broadcastEnabled、broadcastOffVisible、themeMode、autoThemeEnabled、dndEnabled、dndActive、watchlist、readAlertIds、playHistory（Index.ets:28-45）；另有刻意非响应式的 private：timer、consecutiveFailures、navStack（:46-48）。Settings（@Component）持有 10 个 @State（Settings.ets:11-22）。合计 28 个 @State，规模可控但已到该立规范的数量级。

**集合变更纪律——做得对的地方：** 所有集合更新一律整体重赋值：this.items = filtered（Index.ets:178）、this.watchlist = [...this.watchlist, code]（Settings.ets:72）、this.readAlertIds = [...this.readAlertIds, item.alertId]（Index.ets:268-270）、this.playHistory = [historyItem, ...this.playHistory.filter(...)].slice(0, 50)（:280）。V1 的 @State 对数组仅观察引用变化，push/splice 就地改不会触发刷新——本仓从未犯此错。ForEach 键函数统一给足（Index.ets:425 以 alertId 为键、Settings.ets:410 以 code 为键），卡片复用身份正确，键函数缺失会让列表在数据更新时按下标错位复用，是 ArkUI 列表最常见的翻车点。

**非响应式取舍做对了：** timer 与 consecutiveFailures（:46-47）是纯逻辑变量，进 @State 只会白渲染，保持 private 正确。navStack 同理。这是很多新手会犯而本仓没犯的坑。

**派生值用 getter 不用冗余状态：** 字号七组、间距五组、主题色一组全部是 getter（Index.ets:51-96），运行时由 fontLevel/elderlyMode/themeMode 三个 @State 推导，不额外存派生结果。派生即函数而非状态，消除了"改了源状态忘了改派生状态"这类脏数据源头。

## 三、播放三态机审查（Index 最精巧的状态设计）

播放相关有三个 @State 协作：playingId（正在播的卡）、loadingId（正在加载音频的卡）、failedId（上次播放失败的卡）。三者以 alertId 为值、互斥为主轴，构成一个显式状态机：

- 空闲到加载：点击卡片进入 togglePlay，若已在加载则直接忽略（:229-231，防重复点击），若在播则先停止旧卡（:237-240），随后 loadingId 设为该卡（:246）。
- 加载到播放：AudioPlayer.play 成功返回后，先核对 loadingId 是否仍是自己（:260-263，注释明示 refresh 可能在 await 期间清掉了 loadingId），确认后才置 playingId、清 loadingId、标记已读并写入播报历史（:265-280）。
- 加载到失败：play 抛错走 catch（:281-286）或 onError 回调，loadingId 清空、failedId 记账，卡片就地显示「语音加载失败，点重试」。
- 播放到结束：AVPlayer completed 事件回调把 playingId 清空（AudioPlayer.ets:29-33 传入的 onDone）。
- 刷新撤卡兜底：refresh 拉到新列表后，检查正在播/加载/失败的 alertId 是否还在新列表里，不在则停止播放并复位对应状态（Index.ets:166-177），防止对已被服务端撤下的异动继续播报或在 prepare 完成后设置已失效的 playingId。

评价：这套设计的价值在于**所有时序陷阱都被点名设防**——await 期间状态被第三方（轮询刷新）修改是异步 UI 最典型的竞态，代码用"恢复后重验前置条件"的模式挡住了它；三状态分离而不是用一个枚举，让一张卡可以同时呈现"加载中"与"上一次失败过"等信息而不互相覆盖。缺点是三状态散在 18 个 @State 里没有成组，后人改动时容易只改其一，建议抽取时收拢为一个播放状态对象或子组件内部状态。

## 四、数据流向审查：单向主干 + 事件回写

**读路径（服务 → 状态 → 视图）：** Preferences 持久化（SettingsService）→ Index.loadSettings()（Index.ets:118-136）批量拉 11 项配置写入 @State → build() 经字号、间距、主题 getter 派生渲染。轮询数据流独立成线：pollLoop → refresh → AlertPoller.fetchLatest → this.items 整体替换（:146-200）。

**写路径（视图 → 状态 → 服务）：** Settings 页每个控件都是同一模式——先改自身 @State，再 await SettingsService.setXxx 落盘（如 toggleBroadcast，Settings.ets:84-88），无一例外。持久化层读写对偶完整（11 组 get/set，SettingsService.ets:83-373），杀进程可恢复。

**设置页与主页的状态同步机制（关键设计点）：** Index 与 Settings 是两个独立 struct，fontLevel/elderlyMode/themeMode 等各自持有**副本 @State**，互不 @Link。同步靠两个时机：Settings 建时 loadSettings 拉最新值（Settings.ets:43-45），返回主页时 Index.onPageShow 再拉一次（Index.ets:104-108，注释自证"设置页返回后刷新配置"）。aboutToAppear 只在首次创建执行，onPageShow 每次页面重现都执行，两者配合覆盖了冷启动与设置返回两条路径。**评价：** 在零三方依赖加两页面的规模下，"副本 + onShow 重拉"比引入 @StorageLink 更简单直给，判定为合理现状；但它是隐式契约——任何新增设置项若忘记加进 Index.loadSettings，就会出现"设置页改了、主页不变"的脏读，且编译期毫无提示。第七节规范条款正是为堵这个。

## 五、@Prop/@Link 缺位评估与抽取示例

当前零子组件、零 @Prop/@Link，卡片、顶栏全部内联在 Index.build() 里。缺位本身不是 bug，但 Index.build 已约 150 行、卡片含未读/播放/加载/失败/信号/普通六种状态组合，继续生长必然要抽 AlertCard 子组件。届时规范如下。

纯展示用 @Prop：卡片需要的 item（AlertItem）、未读、播放态，若纯由父驱动，用 @Prop 单向拷贝最不易错。

```typescript
@Component
struct AlertCard {
  @Prop item: AlertItem;
  @Prop isPlaying: boolean;
  onToggle: (item: AlertItem) => void;   // 回调上抛，父改 @State
  build() { /* … */ }
}
```

需要子改父的场景（点卡播放、停止）走回调而非 @Link：@Link 双向会让"谁改了 playingId"不可追踪，而本应用播放态变更伴随 AudioPlayer 启停副作用，必须留在父层统一调度（现状 togglePlay 已把调度集中在 Index.ets:225-287），子组件只上抛事件。@Prop 对 AlertItem 这类平面对象做深拷贝的代价可忽略；若未来 items 变深层嵌套，才考虑 @Observed/@ObjectLink。本仓"零装饰器 + 回调上抛"的判断框架，比盲目上 @Link 更值得留档为规范。

## 六、跨组件通信审查：AppStorage 信箱模式与死信号

**主信箱 pendingAlertId：** 三处写入（EntryAbility.ets:27 冷启动、:47 热启动、:93 前台推送）加一处读取并 delete（Index.checkPendingAlertId，Index.ets:138-144），消费方在 aboutToAppear 与 onPageShow 双时机兜底。"读后即删"实现一次性消息语义，重复消费被物理排除；双时机兜底覆盖了页面晚于 Ability 就绪的冷启动时序。这是本仓最规范的跨组件通信，可作模板。

**AppStorage 全部键的读写现状：** pendingAlertId 三写一读，健康；autoPlay 一写零读（EntryAbility.ets:66，小艺 PLAY_AUDIO action 设置，全仓无 get——本次 grep 核实）；xiaoYiQuery 一写零读（:54，小艺查询 action 设置，同样无人消费）。后两个是死信号：小艺 E1 能力处于半接线状态，直接播放意图实际靠 pendingAlertId 加默认开着的播报开关"碰巧"成立。处置建议：短期删死信号防误导；实装小艺时在 Index.onPageShow 补消费逻辑（对齐 checkPendingAlertId 模式），并把三个键名收进常量文件，杜绝字符串散落。

## 七、@State 问题清单与沉淀规范

**问题清单：** 其一，isDemoMode 死状态（声明 :34、置 false :156，build 从未读取），演示卡实由 items 初始值承担，应删或实装为徽标。其二，broadcastOffVisible 是 broadcastEnabled 的镜像（:38、:122 仅 loadSettings 赋值一次），运行期若主页内可切播报开关它会静默失真，应删、模板直接用 !this.broadcastEnabled。其三，"副本 + onShow 重拉"缺强制清单，新设置项漏登记两处即脏读。其四，18 个 @State 平铺尚可，再加五个以上应按播放态/设置态/网络态分组成 @Observed 类或拆子组件，防一处变更全页重绘。

**沉淀为本仓状态管理规范（六条）：**

1. 集合只整体重赋值，禁止 push/splice 触发刷新的写法；ForEach 一律给键函数（现有两处即范本）。
2. 纯逻辑变量（timer、计数、navStack）禁止 @State 化；派生值一律 getter，禁止镜像 @State。
3. 父子通信用 @Prop 加回调上抛；仅当父子共享可变配置时才用 @Link；跨页共享配置当前规模下维持"副本 + onShow 重拉"，迁移 @StorageLink 前须先列设置项清单。
4. AppStorage 键名集中常量化；一次性消息必须"读后即 delete"，消费方在 aboutToAppear 与 onPageShow 双时机兜底。
5. EntryAbility 写入的每个 AppStorage 键必须有对应消费方（grep 可验），消灭 autoPlay、xiaoYiQuery 类死信号。
6. await 恢复后必须重验前置状态（三态机的 :260-263 即范本），凡 await 期间可能被轮询或回调改写的状态，恢复后先核对再使用。

## 八、持久化层的写入策略与状态一致性

SettingsService 是所有状态的持久化真相源，写入策略值得单列审查。现状是每个 set 方法都立刻 put 加 flush（如 setBroadcastEnabled，SettingsService.ets:122-132），即"写穿"策略：控件一点，磁盘即落。评估：Preferences 的 flush 在 HarmonyOS 上是轻量异步操作，设置页操作频率极低（一天数次），写穿不构成性能问题，却换来"杀进程零丢失"的强保证——对适老化应用，老人改完设置即杀后台是常态，这个取舍是对的。两个聚合写入的细节处理也审到：markAlertRead 对已读列表限长 200 条（:399-401 防无限增长）、addPlayHistory 去重后限 50 条（:433-439），两个上限都在写入端而非读取端执行，存储不会膨胀，这是很多应用会漏的点。

一致性风险点是"双写顺序"：Settings 页先改 @State 再 await 落盘（如 toggleElderlyMode，Settings.ets:96-101，其中还先写适老化开关再联动写字体档，两次 put 一次 flush）。若 flush 前杀进程，磁盘上的适老化开关与字体档可能出现中间态（开关开了、字体还是标准）。现状 setElderlyMode 把两个 put 放在同一次 flush 前（SettingsService.ets:180-190），中间窗口极小，且下次启动 loadSettings 会读到新开关旧字体——不一致但可自愈（再开关一次即对齐）。建议：把"适老化开关加字体档"合并为单键存储（存一个对象），彻底消灭双写窗口，属低成本高确定性改进。

## 九、状态管理 V2 前瞻与升级判断

ArkTS 状态管理已有 V2 体系（@ObservedV2/@Trace、@Local、@Param、@Monitor 等），提供了自动深观察与更严格的组件输入约束。本仓是否升级的判断：当前 28 个 @State 全部是第一层语义（标量或整体替换的数组），V1 的浅观察完全够用，没有任何一处需要深观察嵌套对象却没得到的真实缺陷；V2 的收益（深观察、更细粒度刷新）要等卡片抽出子组件且 item 需要原地修改时才兑现。结论：**现在不升，抽 AlertCard 子组件时一并评估**。升级时的映射清单预先留档：@State 换 @Local，@Prop 换 @Param，@Watch 换 @Monitor，@Observed/@ObjectLink 换 @ObservedV2/@Trace，AppStorage 用法不变。避免在 V1/V2 混用期无意识混搭装饰器——混用不兼容是 V2 迁移最常见的翻车点。

## 十、AppStorage 与 Preferences 的边界纪律

本仓有两个容易混淆的全局仓，边界必须立清。AppStorage 是内存态、随进程生死，适合做跨组件的一次性消息与瞬时标志——pendingAlertId 是范本：写、读、删三步一气呵成，不留残值；Preferences 是磁盘态、跨启动存活，适合做配置与累积记录——watchlist 与播报历史是范本。判定规则一句话：**丢了要不要紧**。丢了就要紧的（配置、历史）进 Preferences，丢了无所谓的（页面间口信）进 AppStorage。反例警示：若把 pendingAlertId 改存 Preferences，通知点击会在应用未启动时写盘，下次启动读到陈旧口信误触发播报——一次性语义被持久化破坏。正向扩展：未来若加"上次看到的最新 alertId 用于未读计数"，属于丢了要紧的累积状态，应进 Preferences 并设上限，与 readAlertIds 同构管理。另外 AppStorage 不设清理约定会随时间堆积死键，现状只用一个键且读后即删，健康；新增键必须同步在规范第四、五条登记。

## 十一、验证清单

- [ ] grep @Prop/@Link 使用点与设计一致（现为零，引入时按规范第 3 条审）
- [ ] grep 全部 AppStorage 键有读写配对
- [ ] 每个新设置项同时出现在 Settings 写路径与 Index.loadSettings
- [ ] ForEach 键函数覆盖率 100%
- [ ] 无 push/splice 就地改 @State 集合
- [ ] 三态机撤卡兜底：播放中卡片被服务端撤下后自动停播

### 自我评估
- 正确性：4分 全部行号来自本次实读四文件；"零装饰器/死信号/死状态"三个关键论断有本次 grep 输出佐证；三态机流转逐条对照代码；ArkTS V1 装饰器语义为官方文档通行口径，未在本环境编译验证，扣一分声明。
- 完整性：4分 覆盖盘点、三态机专析、流向、缺位评估、通信死信号、问题清单与六条规范；@StorageLink 迁移方案只给决策框架未给迁移代码（当前规模不推荐迁移，故不给）。
- 可复用性：4分 六条规范与验证清单可直接进 GOVERNANCE 技能库；"@Prop 加回调优于 @Link"与"await 后重验前置状态"两条对一切带副作用的 ArkUI 应用通用。
- 字数：约3000字
- 使用模型：GLM-5.3-Flash
