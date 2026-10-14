# code技能：ArkTS状态管理最佳实践——V1装饰器与V2体系使用规范

> 编写时间：2026-09-23
> 编写席位：Moon席位批次写手-B组-1号（GLM-5.3-Flash）
> 适用范围：harmony-app（铃语）端侧全部 ArkTS 页面与组件的状态声明、变更与跨层传递
> 事实来源：现网代码以 `entry/src/main/ets/pages/Index.ets`、`entry/src/main/ets/entryability/EntryAbility.ets`、`entry/src/main/ets/model/AlertItem.ets` 为准，引用处标行号；V2 部分为面向 compatibleSdkVersion 20 / targetSdk 26 约束下的规范指引，属升级建议而非现网现状，文中显式区分。

## 0. 状态分层模型（先分层，再选装饰器）

铃语端侧状态天然分三层，动手前先归类：

1. **页面私有 UI 态**：只在 `Index` 组件内消费，如 `playingId`/`loadingId`/`failedId`/`connectionBroken`（`Index.ets:29-33`）。用 `@State`（V1）或 `@Local`（V2）。
2. **持久化用户配置态**：字体档、适老化模式、播报开关、免打扰、自选股等，经 `SettingsService` 落 Preferences（`entry/src/main/ets/services/SettingsService.ets:8-22` 的键定义），页面每次 `aboutToAppear`/`onPageShow` 拉回镜像为 `@State`（`Index.ets:118-136`）。
3. **进程级通信态**：EntryAbility 与页面之间的一次性信号，如通知点击带来的 `alertId`，经 `AppStorage.setOrCreate('pendingAlertId', ...)` 投递（`EntryAbility.ets:25-28,45-48`），页面 `checkPendingAlertId()` 取出即删（`Index.ets:138-144`）。

分层结论：**不引入全局响应式大杂烩**。配置态以 Preferences 为唯一真源、页面态为镜像；进程级信号用 AppStorage 做"信箱"而非"状态库"。

## 1. V1 装饰器使用规范（现网基线）

### 1.1 @State：观察深度只有一层

`@State` 观察的是变量本身赋值与**第一层**属性变化。两条推论决定本项目的写法：

- `items: AlertItem[]` 里某个元素的属性变了（比如给 `item.audioUrl` 赋值），**不会**触发刷新——因为 `AlertItem` 是 interface（`AlertItem.ets:6-17`），元素是普通对象，不在观察范围内；
- 所以现网一律**整体重赋值**：`this.items = filtered`（`Index.ets:178`）、`this.readAlertIds = [...this.readAlertIds, item.alertId]`（269 行）、`this.playHistory = [historyItem, ...].slice(0, 50)`（280 行）。展开/拼接生成新数组再赋值，是 V1 下最可靠的刷新手段。

规范：**凡数组/对象内容更新，必须产出新引用赋回原变量**；禁止 `this.items[0].headline = 'x'`、`this.items.push(y)` 之后期待界面变化。@State 必须本地初始化（`Index.ets:28` 的 `= DEMO_ITEMS` 同时兜住"首屏永不空白"约束）。

### 1.2 @Prop：父到子单向值拷贝

子组件需要一份"快照"时用 `@Prop`，父变则子同步，子变不回传。典型场景：把异动卡片拆成子组件后，`playingId`、`loadingId` 作为 `@Prop playingId: string` 传入，父层三态变化自动下推，子组件只读渲染。注意 @Prop 是深拷贝，**不要传大对象**；卡片场景传字符串 ID 与少量标量即可。

### 1.3 @Link：双向同步引用

需要子改父时用 `@Link`，父端调用处写 `Child({ value: this.value })` 之外还要 `$` 前缀（`Child({ value: $value })` 或 `this.value` 的双向语法）。适用：Settings 页里开关型控件与页面状态的直接互写。纪律：**@Link 变量必须在父层也是状态变量**；一个变量最多被一处 @Link，避免多写者打架。铃语当前 Settings 页通过回调式交互后统一走 `SettingsService` 持久化再刷新，比散布 @Link 更可控。

### 1.4 @Watch：副作用钩子而非数据通道

`@Watch('cb')` 在被装饰变量变化时回调，签名 `cb(propName: string)`。规范：

- 回调里只做**轻量同步**动作（清派生值、发一条日志）；异步重活放 `setTimeout` 或专门方法，避免阻塞渲染管线；
- 不要用 @Watch 传递业务数据，它是变更通知，不是事件总线；
- 回调触发于变更之后，读取的已是新值；
- 典型合法用法：`@Watch('onFontLevel') @State fontLevel` 变化时重算派生尺寸。现网用 getter 派生（`Index.ets:51-71` 的 `titleSize` 等）规避了显式 Watch——**派生优先用 getter/计算属性，跨多变量联动才上 @Watch**。

### 1.5 @Observed + @ObjectLink：嵌套对象观察

`@Observed` 装饰 class，配合子组件 `@ObjectLink`，可观察该类实例的**第一层属性**赋值。两个硬限制：

1. **只对 class 生效**。本项目 `AlertItem` 是 interface（`AlertItem.ets:6`），挂 @Observed 无意义。若要嵌套观察，须先改写为 `@Observed class AlertItem {...}`；
2. @ObjectLink 变量不许本地初始化，必须由父组件传入，且父传的是该 class 实例。

当前不迁移的理由：卡片逐项字段基本只读（服务端产出、端侧不改写），动态部分全部外置为标量 @State（playingId 三态），interface + 整体重赋值的组合已经够用、序列化也省事。**触发迁移的条件**：出现"端侧就地修改条目字段并要求局部刷新"的真实需求时，再改 class 并拆卡片子组件。

### 1.6 跨级与持久：@Provide/@Consume、AppStorage

- `@Provide`/`@Consume` 用于跨多层级共享（如主题色 `theme` 若下沉到深层控件），免去逐层透传；命名即绑定，慎防撞名；
- AppStorage 本项目只做单次投递信箱：`EntryAbility` 的 `onCreate`/`onNewWant`/Push 消息回调写入（`EntryAbility.ets:27,47,59,66,93`），`Index` 侧取出后 `AppStorage.delete` 清信箱（`Index.ets:141`）。**不把 AppStorage 当长期响应式存储**——页面销毁后残留键会造成幽灵状态。

## 2. V2 体系使用规范（升级指引）

状态管理 V2（`@ComponentV2` 家族）在 compatibleSdkVersion 20 / targetSdk 26 下可用，特性是**属性级精确观察**。规范要点：

### 2.1 装饰器对照

| 能力 | V1 | V2 |
| --- | --- | --- |
| 组件声明 | `@Component` | `@ComponentV2` |
| 本地状态 | `@State` | `@Local` |
| 父到子只读 | `@Prop` | `@Param`（配 `@Once` 则仅初始化一次） |
| 子回调父 | 直接调 lambda | `@Event` 显式声明 |
| 变更监听 | `@Watch` | `@Monitor`（可取变更前后值，可监多路径） |
| 派生值 | 无（手写 getter） | `@Computed` |
| 深观察 | `@Observed`+`@ObjectLink` | `@ObservedV2`+`@Trace`（到属性粒度） |
| 跨级共享 | `@Provide`/`@Consume` | `@Provider`/`@Consumer` |
| 进程级 | AppStorage | AppStorageV2 / PersistenceV2 |

### 2.2 关键差异与迁移判据

- `@Local` 取代 @State 的本地态语义，且**不允许外部初始化**——比 V1 更严格地防"父层意外注水"；
- `@ObservedV2 class AlertItemV2 { @Trace headline: string; ... }` 后，改 `item.headline` 即精确刷新绑定处，不必整表重赋值。这是 V2 对本项目最大的收益点；
- `@Monitor('fontLevel')` 能拿到变更前后值并支持数组/嵌套路径监听，比 @Watch 表达力强；
- `@Computed` 让 `titleSize` 这类派生（`Index.ets:51-71`）从 getter 变成可观察计算属性。

**混用规则**：V1 与 V2 组件**可以互相嵌套**（V1 父含 V2 子、反之皆可），但**同一个组件内两套装饰器不可混用**；`@Component` 里不能写 `@Param/@Local`，`@ComponentV2` 里不能写 `@State/@Prop/@Link`。迁移策略：新页面直接 V2 起步；`Index.ets` 这类存量大页面在"卡片子组件化"重构时顺路切换，不做无收益的空转重写。

### 2.3 V2 下的本项目形态（示意）

```typescript
@ObservedV2
export class AlertItemV2 {
  alertId: string = '';
  @Trace headline: string = '';      // 需要就地刷新的字段才标 @Trace
  @Trace audioUrl?: string;
  ts: number = 0;                    // 只读字段不必 @Trace，省观察开销
}

@ComponentV2
struct AlertCard {
  @Param alertId: string = '';
  @Param playingId: string = '';     // 父层三态下推
  @Event onStop: () => void = () => {};  // 子回调父
  @Monitor('playingId') onPlayState(pre: string, cur: string) { /* 轻量联动 */ }
}
```

纪律：@Trace 只标真正会变的字段（音频地址、播报态），只读字段不标，控制观察开销；@Param 默认本地可改但改动不回传，需要强只读语义时配合冻结或约定。

## 3. 本项目现网范式复盘（可作为模板）

1. **变更闭环**：用户点卡片 → `togglePlay` 改 `loadingId`/`playingId`/`failedId` 三个标量 @State（`Index.ets:225-287`）→ ForEach 键为 `alertId`（425 行）只重渲染受影响卡片。**每卡片动态状态外置为标量、而非塞进条目对象**，是 V1 下兼顾刷新精度与数据纯净的关键一手；
2. **异步竞态防悬挂**：`await AudioPlayer.play(...)` 返回后先校验 `this.loadingId !== item.alertId` 再设 `playingId`（`Index.ets:260-265`）——await 期间轮询可能已清态，不校验会出现"幽灵播放中"；
3. **生命周期配对**：`aboutToAppear` 启动轮询与设置加载，`aboutToDisappear` 里 `clearTimeout(this.timer)` 并 `AudioPlayer.stop()`（`Index.ets:110-116`）。**每个 @State 驱动的循环资源必须有对称回收**；
4. **配置镜像刷新时机**：`aboutToAppear` 与 `onPageShow` 双入口 `loadSettings()`（`Index.ets:98-108`），保证从 Settings 返回后字体档/主题即时生效，无需引入跨页双向绑定。

## 4. 反模式清单（审查即否决）

- [ ] 深层/索引赋值期待刷新：`this.items[i].x = v`、`push/splice` 后不重赋值；
- [ ] interface 上挂 @Observed（无效装饰，静默不观察）；
- [ ] @Watch 回调里做网络请求等重异步（应转方法调用）；
- [ ] AppStorage 当长期状态库、键不清理（幽灵 pendingAlertId 会导致误自动播报）；
- [ ] 同一组件混用 V1/V2 装饰器；
- [ ] @State 不初始化（首屏空白风险，违反"永不空白"约束）；
- [ ] 定时器/播放器等资源在 aboutToDisappear 不回收；
- [ ] @Link 多处绑定同一父变量造成多写者。

## 2.4 迁移步骤清单（V1→V2）

按风险从小到大五步走，每步独立合入独立验证，禁止一把梭：

1. **叶子组件先行**：把纯展示子组件（如未来的 AlertCard）切 `@ComponentV2`，入参用 `@Param`、回调用 `@Event`——叶子无下游风险；
2. **派生值升级**：getter 派生（如 titleSize）改 `@Computed`，行为不变、表达力更强；
3. **数据类升级**：interface 改 `@ObservedV2 class`，会变的字段标 `@Trace`；字段名与 feed 契约保持一致，`AlertFeed` 解析不受影响；
4. **页面态升级**：页面级 `@State` 改 `@Local`；跨页配置仍走 Preferences 镜像，不动；
5. **信箱最后动**：AppStorage 投递语义保持"写入-取走-删除"三拍不变，V2 下可换 AppStorageV2 但不强制。

## 5. 状态与渲染配合：ForEach 键规则

- 键函数必须返回**稳定且唯一**的业务 ID：主列表用 `item.alertId`（`Index.ets:425`），自选股列表用股票代码（`Settings.ets:410`）；**禁止用数组索引当键**——删除或插入时索引键引发错位重绘，甚至把 A 卡的状态绑到 B 卡上；
- 键相同的条目在整体重赋值后**不重建子组件**、只更新绑定——"新引用赋值 + 稳定键"的组合让刷新成本收敛到内容真正变化的卡片；
- 当前列表上限 20 条（`AlertPoller.fetchLatest` 默认 limit=20，`AlertPoller.ets:34`），ForEach 足够；未来若放开到数百条，再换 LazyForEach 配 IDataSource 按屏构建，不提前优化。

## 6. Settings 页的双向同步范式（现网样板）

设置页是"镜像状态 + 即时持久化"的标准实现（`Settings.ets:84-150`），每个开关 handler 三拍：先改本地 @State 让界面立即反馈，再 await SettingsService 持久化，最后 hilog 记一条。四条细则：

1. **先镜像后持久化**：老人按下开关的瞬间必须看到变化；持久化失败也不回滚视觉，下一轮 loadSettings 会自我纠正；
2. **联动读回而非推导**：适老化开关联带改字体档，handler 持久化后**重新读回** fontLevel（`Settings.ets:99`），不在两处重复推导——真源只从存储读，杜绝双处计算漂移；
3. **关联状态原子修改**：手动选主题必须连带关自动主题，`toggleThemeMode` 在同一 handler 里双写（`Settings.ets:103-110`），不留"手动夜间+自动开"的矛盾中间态；
4. **输入暂存不落库**：自选股代码 TextInput 的 onChange 只写 `newStockInput` 暂存（`Settings.ets:379-381`），点「添加」才 trim、去重、展开新数组并持久化（64-76 行）——显式提交优于自动保存，误输可弃。

## 7. 状态测试要点

- 竞态类逻辑（await 后校验前置态）是测试重点：模拟"await 期间列表被刷新清态"，断言不会写入失效的 playingId；
- 契约类断言：`AlertFeed.items ?? []` 兜底、`feed.items` 缺字段时 UI 收到空数组而非 undefined；
- 生命周期断言：aboutToDisappear 后定时器不再排期（检查 timer 已清）、AudioPlayer.stop 被调用；
- Preferences 镜像测试：写入后读回应一致；适老化开关与字体档的联动（`SettingsService.ets:190-195`）单向锁定成立。

### 自我评估
- 正确性：4分 V1 部分全部对齐现网源码并标行号（Index/EntryAbility/AlertItem/SettingsService）；V2 部分为官方语义的规范转述，未在本环境编译验证，属指引性内容且已显式标注"非现网现状"。
- 完整性：4分 覆盖任务点名的全部六个装饰器/体系，含对照表、迁移判据、现网复盘与反模式清单；@Provide/@Consume 与 AppStorageV2 只点到为止。
- 可复用性：4分 三层分层法与"标量外置三态"范式可直接复用于新页面；审查清单可直接进 CR 流程。
- 字数：约3050字
- 使用模型：GLM-5.3-Flash
