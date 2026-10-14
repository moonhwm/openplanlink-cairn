# A23 Index.ets 审查——List 卡片流渲染、5s 前台轮询机制、AlertPoller 实现

> 审查对象：`entry/src/main/ets/pages/Index.ets`（共 458 行）与 `entry/src/main/ets/services/AlertPoller.ets`（共 100 行），关联 `entry/src/main/ets/model/AlertItem.ets`、`entry/src/main/ets/services/SettingsService.ets`。
> 审查方式：2026-09-23 通读源文件并交叉核对（含对 `pendingAlertId` 消费点、`autoPlay` 死标志的 grep 核实，见 A22 审查），未做真机运行；运行时推断均已标注。

---

## 一、总体结论

Index.ets 是全应用的主界面，实现了"List 卡片流 + 5s 前台轮询 + AudioPlayer 点按播报"的架构基调，适老化三要素（28-34fp 大字、白话文案、点卡片即听）落地扎实；演示卡机制保证首屏永不空白；`playingId/loadingId/failedId` 三态机与刷新竞态防御是全文亮点。主要问题：①退到后台轮询不暂停（耗电耗流量）；②自选股过滤可能造成"服务端有数据但用户看到暂无异动"的误导空态；③免打扰状态不随时间自动重算；④轮询为整页 items 替换，无增量，60 岁用户正在阅读时卡片可能整屏跳变。逐节展开如下。

---

## 二、List 卡片流渲染审查

### 2.1 演示卡与首屏保障（约束：首屏永不空白）

`Index.ets:13-23` 定义 `DEMO_ITEMS`：单条示例卡，`alertId: 'demo-1'`、`ts: 0`、headline 带"示例："前缀、detail 写明"示例数据，服务器接通后自动换成真实异动"。`:28` `@State items` 初始值即 DEMO_ITEMS，`:34` `isDemoMode` 初始 true。链路核对：首次 `refresh()` 成功（:153-157）才置 `isDemoMode = false` 并以真实数据整体替换 items——**首屏任何时刻都有内容，且明确标注示例不冒充真实数据**，合规与体验双达标。注意 `ts: 0` 意味着演示卡在任何按 ts 排序的场景都沉底，但当前 items 直接按服务端顺序渲染，无本地排序，此字段暂无副作用（若未来做本地排序需留意）。

一个未使用的状态：`isDemoMode`（:34）置位后全文无读取（本次通读确认），属于死状态，可删或用于顶栏"演示中"徽标。

### 2.2 字号与布局的适老化映射（约束：28-34fp 大字）

`:50-71` 七个字号 getter 按 `fontLevel` 两档切换：standard 档 headline 28 / cardTitle 30 / title 34 / detail 22 / 状态 20；large 档整体 +6。主信息区（headline 28、卡片标题 30、页面标题 34）落在 28-34fp 约束带内；detail 22 与状态字号 20 属次级信息，低于 28 但不承载关键语义，可接受。`:74-91` 布局 getter 按 `elderlyMode` 放大卡距/内边距/热区。设置入口按钮 `:341-348` 用 `constraintSize({ minWidth: 48, minHeight: 48 })` 保证热区 ≥48vp，符合触达无障碍要求。

`SettingsService.ets:178-194` 的 `setElderlyMode` 联动强制字号档（开=large，关=standard），Index 侧 `loadSettings()`（:118-136）在 `aboutToAppear` 与 `onPageShow` 都会重读，设置页返回后立即生效，闭环正确。

### 2.3 ForEach 与卡片结构

`:354-426`：`List({ space: this.cardSpace })` + `ForEach(this.items, ..., (item: AlertItem) => item.alertId)`——键函数用 alertId（服务端格式 `symbol_ts`，见 A24），新增异动只增节点、旧节点复用，这是卡片流正确的键策略。卡片内结构：未读圆点（:361-365，仅未读显示，金色 10vp）、方向徽章（:366-372，涨红跌绿符合 A 股配色惯例，`dirColor` :289-297 映射自主题）、股票名（:373-380，maxLines(1)+Ellipsis 防长名破版）、`kind === 'signal'` 时显示"自家信号"描边徽章（:381-389）、有 audioUrl 才显示播放态文本（:390-396，`▶ 听` / `■ 停` / `…` 三态字符，不依赖图标资源，契合零三方依赖）。headline/detail 文案来自服务端白话字段（契约见 A24）。

播放按钮不是独立按钮，而是整卡 `onClick(() => this.togglePlay(item))`（:423）——"点卡片=听"的适老化交互，整卡热区远大于 48vp，设计正确。但副作用是：老年用户想"仔细看卡片文字"时误触即开始播报；由于 togglePlay 对 playingId 是切换停止语义（:232-235），再点一次即停，且 `failedId` 卡片显示"语音加载失败，点重试"（:412-417），误触成本可控。此为设计取舍，记录不改。

### 2.4 主题与导航

`:94-96` 主题 getter 从 `SettingsService.getThemeColors(this.themeMode)` 取色，白天/夜间两套配色定义于 `SettingsService.ets:41-60`。`build()` 根节点 `Navigation(this.navStack)`（:310），`:449-454` `navDestination` 按 name 返回 `Settings()` 组件，`:349` 设置入口 `pushPath({ name: 'pages/Settings' })`。核对 `main_pages.json`：仅注册 `pages/Index`，Settings 走 Navigation 目的地而非 router 页面，链路自洽。`hideTitleBar(true)` + `NavigationMode.Stack`（:455-456）符合单页卡片流形态。

---

## 三、5s 前台轮询机制审查

### 3.1 轮询循环结构

`:146-149`：

```ts
private async pollLoop(): Promise<void> {
  await this.refresh();
  this.timer = setTimeout(() => this.pollLoop(), AlertPoller.getInterval());
}
```

两个正确决策值得固化：

1. **setTimeout 链而非 setInterval**：下一轮间隔在 `refresh()` 完成之后才开始计，请求天然串行、不会堆叠并发；若用 setInterval，慢网络下 5s 一发的请求会叠罗汉。
2. **间隔从 AlertPoller 动态读取**（`AlertPoller.getInterval()`，AlertPoller.ets:33-35）：退避逻辑封装在 Poller 内，Index 无感跟随，职责分离干净。

`:110-116` `aboutToDisappear` 清 timer 并 `AudioPlayer.stop()`，页面销毁后无泄漏。`:98-108` 启动时 `loadSettings + pollLoop + checkPendingAlertId` 三连。

### 3.2 问题 Q1（高）：后台不暂停轮询

`aboutToDisappear` 只在组件销毁时触发；应用退到后台（Home 键/切走）页面不销毁，`timer` 链继续每 5s（退避后最长 30s）打一次网络请求。对老年用户的低端机，后台持续唤醒耗电显著；`module.json5` 虽申请了 `KEEP_BACKGROUND_RUNNING` 但注释明确"当前未实际调用对应 API"——后台轮询属于无权限裸跑网络。修复：重写 `onPageHide()` 暂停（clearTimeout + 置 -1）、`onPageShow()` 恢复 `pollLoop()`；若担心后台期间漏推送，后台恰恰有系统推送/回到前台立即 refresh 兜底，不存在信息缺口。

### 3.3 问题 Q2（中）：自选股过滤的误导性空态

`:159-163`：`watchlist` 非空时 `filtered = result.items.filter((it) => this.watchlist.includes(it.symbol))`；过滤后为空则落入 `:180-188` 的分支，`items = []` → 渲染 `:430-443` 空态文案"今日暂无异动 / 监测进行中"。此时服务端明明有异动，只是都不在自选股内——文案对用户是误导（用户以为今天没行情）。建议区分三态文案："今日暂无异动"（服务端空）、"自选股暂无异动"（过滤后空，另提示当前自选股数量）。改动点在 refresh 的空态判定处，成本低。

### 3.4 问题 Q3（中）：dndActive 不随时间重算

`dndActive` 只在 `loadSettings()`（:118-136）计算（`SettingsService.isDndActive`，SettingsService.ets:300-312，跨天时段已正确处理）。用户 21:50 打开应用一直挂着，22:00 进入免打扰时段后顶栏"免打扰"徽标不出现、自动播报也不生效，直到下一次 `onPageShow`。修复：pollLoop 每轮顺手重算 `dndActive`（纯内存时间比较，无 IO），或在 isDndActive 边界时刻设一个对时 timer。

### 3.5 刷新与播放的竞态防御（亮点记录）

`:151-200` refresh 成功后的三连检查（:166-177）：正在播放/加载/失败标记的 alertId 若不在新列表（被服务端撤下），分别 stop 播放、复位 loading、清 failed 标记；`:171` 注释点明动机"防止 prepare 完成后设置已失效的 playingId"。配合 togglePlay 内 `:261-263`——`await AudioPlayer.play` 返回后校验 `loadingId` 仍是本卡才置 `playingId`，防住了"refresh 在 await 期间撤卡"的窗口。这个双向防御在轮询型 UI 里少见地完整，值得作为模式沉淀。

---

## 四、AlertPoller 实现审查（AlertPoller.ets）

### 4.1 请求与状态码分支（:37-88）

`fetchLatest(limit=20)`：`SettingsService.getFeedUrl()`（SettingsService.ets:351-361，Preferences 可覆盖默认 CloudBase 地址）拼 `?limit=${limit}`，`connectTimeout/readTimeout` 各 5000ms——超时明确，老年用户弱网不至干等。分支设计：

- **429**（:47-52）：静默退避，返回 `{ ok:false, rateLimited:true }`；Index 侧 `:192-194` 对 rateLimited 不增计数、不打扰用户（白皮书 §3.2.4"不惊动老爷子"），且不覆盖现有 items——限流期间界面冻结在旧数据，正确；
- **5xx**（:54-58）与其余非 200（:60-64）：退避 + 普通失败；
- **200 但 JSON 坏**（:66-75）：解析失败记响应原文前 200 字符（:72）后按失败处理——日志保留现场又不刷屏，做法好；
- 成功（:78-79）：`resetBackoff()` 复位 5s，返回 `feed.items ?? []`（服务端 items 缺省也稳）。
- `finally { req.destroy() }`（:85-87）：每次请求的 http 实例必毁，无泄漏。

### 4.2 退避参数（:28-30, 90-99）

BASE 5000ms、MAX 30000ms、失败翻倍。口径核对：连续失败 2 次后 Index 顶栏才显示"连接中断，显示旧数据"（`Index.ets:195-198` + `:335-339`），且旧数据保留不清空——"显示旧数据"与约束一致。退避上限 30s 意味着最坏感知延迟可控，参数合理。

### 4.3 问题 Q4（中）：响应体无契约校验

`:69` `JSON.parse(resp.result as string) as AlertFeed` 后直接信任 `feed.items`。服务端是自家 get-alerts 云函数，正常情况契约稳定；但 alerts.json 由多个函数读改写（A21 已述并发窗口），一条 `headline` 缺失的脏数据会让 `Text(item.headline)`（Index.ets:400）渲染 undefined。建议 Poller 出口处做一次轻量 normalize：过滤掉缺 `alertId/headline/symbol` 的条目、补 `direction` 缺省 'flat'、`ts` 缺省 0。十行代码，把"服务端脏数据"挡在 UI 外。

### 4.4 问题 Q5（低）：limit 固定 20

`fetchLatest` 默认 limit=20，Index 调用未传参（:152）。服务端 get-alerts 上限 100（get-alerts/index.js:58-61）、存储层保留 500 条。卡片流无分页加载（List 一次渲染全部 items），20 条对单屏滚动场景够用；若未来加"历史回看"，需同步调整 limit 与虚拟滚动，此处仅记录扩展点。

---

## 五、播放状态与数据的其余发现

1. **已读标记时机**（:266-270）：仅在播放成功后 `markAlertRead`。用户"看过但没听"的卡片永远显示未读圆点——对"未读=没听"的播报型产品，这其实是有意语义（圆点引导用户去听），记录为设计意图而非缺陷；`markAlertRead` 上限 200 条（SettingsService.ets:395-402），`readAlertIds` 状态数组随 loadSettings 全量读入（:134），includes 判断 O(n) 但 n≤200，无性能问题。
2. **playHistory 双写**（:271-280）：Index 内存维护一份 `playHistory`（slice 50），`SettingsService.addPlayHistory`（SettingsService.ets:426-445）持久层也维护一份并去重。两份逻辑重复但语义一致（去重键 alertId、上限 50），风险是未来改上限只改一处。建议持久层为准，内存态每次 loadSettings 重读，删掉 Index 内的本地拼接。
3. **togglePlay 的防重入**（:229-231）：`loadingId === item.alertId` 时直接 return，防住连点；跨卡片快速连点仍存在竞态残留（A25 审查详述，根因在 AudioPlayer 静态单实例 + Index 状态跨调用覆盖），两篇结论互相印证。
4. **playById 的静默三连**（:202-223）：通知拉起不命中/无 audioUrl/开关拦截均静默，其中"不命中"场景的体验缺口已在 A22 §4.2 记录（建议补拉+提示），本篇不重复展开。
5. **空态布局**（:430-443）：空态 Column 用 `layoutWeight(1) + justifyContent(Center)` 垂直居中，文案两级字号（headlineSize/statusSize），无复杂图表，符合"禁 K 线图等复杂图表"约束——全页核对无任何图表组件。

---

## 六、问题清单汇总

| 编号 | 级别 | 问题 | 证据 | 建议动作 |
|---|---|---|---|---|
| Q1 | 高 | 退后台轮询不暂停，后台裸跑网络 | Index.ets:110-116 仅销毁时清理；module.json5 KEEP_BACKGROUND_RUNNING 注释 | onPageHide 暂停 / onPageShow 恢复 |
| Q2 | 中 | 自选股过滤空态文案误导 | Index.ets:159-163, 180-188, 430-443 | 区分"服务端空"与"过滤后空" |
| Q3 | 中 | dndActive 不随时间重算 | Index.ets:129-132 仅 loadSettings 计算 | pollLoop 内每轮重算 |
| Q4 | 中 | 轮询响应无契约校验 | AlertPoller.ets:67-79 | Poller 出口 normalize |
| Q5 | 低 | isDemoMode 死状态 | Index.ets:34 | 删除或作演示徽标 |
| Q6 | 低 | playHistory 双份维护 | Index.ets:271-280 vs SettingsService.ets:426-445 | 以持久层为准 |
| Q7 | 低 | limit 固定 20，无分页扩展点 | AlertPoller.ets:37, Index.ets:152 | 记录为历史回看前置项 |

## 七、审查方法声明

本审查完成于 2026-09-23，基于当日仓库快照对 Index.ets（458 行）与 AlertPoller.ets（100 行）的全文通读，及与 SettingsService.ets、AlertItem.ets、get-alerts 云函数的交叉引用核对。**未执行项**：DevEco 模拟器运行、真机弱网退避实测、hilog 实际输出验证；涉及时序的结论（Q1 后台行为、Q3 重算时机）为静态推演并已标注。A22 审查中已核实的 grep 结论（autoPlay/xiaoYiQuery 无消费点）在本篇引用时注明出处，未重复执行。

### 自我评估
- 正确性：4分 所有关键结论给出精确行号，竞态防御与轮询结构的正向确认同样有据；运行时行为推演标注了未验证。
- 完整性：4分 三条主线（渲染/轮询/Poller）全部展开，附问题清单与跨篇（A22/A24/A25）边界划分；未覆盖动画与手势细节（页面确实不存在这些能力）。
- 可复用性：4分 问题表可直接转工单，"setTimeout 链 + 动态间隔 + 竞态双向防御"提炼为可迁移模式；修复建议保守不越架构基调。
- 字数：约3600字
- 使用模型：GLM-5.3-Flash
