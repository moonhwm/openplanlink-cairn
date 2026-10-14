# A22 EntryAbility.ets 审查——Push 初始化流程、onNewWant 处理、alertId 拉起定位逻辑

> 审查对象：`entry/src/main/ets/entryability/EntryAbility.ets`（123 行，快照 2026-09-18 15:54，本轮审查时未再变更）；关联文件 `entry/src/main/ets/services/PushService.ets`（108 行，快照 2026-09-23 09:30）、`entry/src/main/ets/pages/Index.ets`（461 行，快照 2026-09-23 12:42）、`entry/src/main/module.json5`、`build-profile.json5`。
> 审查方式：2026-09-23 通读上述源文件，并以 grep 核对 `pendingAlertId`、`xiaoYiQuery`、`autoPlay` 三个 AppStorage 键在 `entry/src` 的全部读写点；仓库当日高频并发修改，关联文件行号以各自快照时间为准。未做真机运行验证——凡属运行时行为推断均已标注。

---

## 一、总体结论

EntryAbility 的骨架符合架构基调："EntryAbility = Push 初始化 + onNewWant 带 alertId 拉起定位"，冷启动 alertId 补检、AGC 未配置降级轮询两个关键点都已落实，且 09:30 波次把 PushService 的上报地址改为从 `CLOUDBASE_BASE_URL` 拼接（PushService.ets:6、:12），端侧三处 URL 常量已收敛为一处导出（SettingsService.ets:26-28），方向正确。主要问题：①两个写了却没人读的 AppStorage 死标志（`xiaoYiQuery`、`autoPlay`）；②小艺 PLAY_AUDIO 显式播放指令会被播报开关/免打扰静默拦截的链路冲突；③Push 消息接收器直接在 Ability 内注册、绕开了 PushService 封装的分层不一致，且注册时序与 AGC 探测时序脱钩；④alertId 提取逻辑三处重复、无类型校验。以下分节展开，每条结论附行号证据。

---

## 二、Push 初始化流程审查（onCreate 阶段）

### 2.1 流程还原

`EntryAbility.ets:13-31` 的 onCreate 依次做四件事：

1. `PushService.init(this.context)`（:16-18），`.catch` 只打 `push init degraded` 警告——不 await、不阻塞启动；
2. `SettingsService.init(this.context)`（:20-22），同样 fire-and-forget + 降级日志；
3. 冷启动 alertId 补检（:23-28）：`want?.parameters?.alertId` 存在则 `AppStorage.setOrCreate('pendingAlertId', alertId)`，注释援引白皮书 §3.3.2，明确说明这是修"原代码只在 onNewWant 处理 alertId、冷启动点通知会丢失"的缺陷；
4. `registerPushMessageReceiver()`（:30，实现于 :83-105）。

### 2.2 降级设计核对（约束：PushService 保持占位封装、AGC 未配置前降级轮询）

降级链路逐环核对，闭环成立：

- `PushService.ets:100-107` 的 `probeAgcConfig` 用 `resourceManager.getRawFileContentSync('agconnect-services.json')` 探测 AGC 配置文件，异常返回 false；
- `PushService.ets:30-35` 探测失败直接 return 并记日志 'agconnect-services.json absent, push degraded to polling'；
- 前台轮询兜底：Index.aboutToAppear 启动 `pollLoop`（Index.ets:99-103、:148-151），每 5s 拉一次（退避封顶 30s，AlertPoller.ets:25-27）；
- EntryAbility 侧 `.catch`（:16-18）再兜一层，双保险成立。

**AGC 未配置 → init 静默返回 → 轮询兜底**，与治理约束逐字吻合。细节核实：

- `PushService.ets:15-17` 定义可重试错误码 `[1000900001, 1000900008, 1000900009, 1000900011]`、最大 3 次、间隔 1s；`:64-72` 的 `handleTokenRetry` 用 `setTimeout` 重入 `fetchToken`——重试不阻塞 onCreate；
- `PushService.ets:78-98` 的 `reportToken` POST `{token, bundleName}` 到 `${CLOUDBASE_BASE_URL}/push-token-register`（:12），5s 双超时（:83-84），失败仅记日志不影响主流程；`finally req.destroy()`（:96）无泄漏；
- 脱敏核对：`:50` 日志只打 `token length`，不打内容——正确。但注意 Ability 内接收器日志打印了整个 payload（下文 2.4）。

### 2.3 初始化时序问题：接收器注册与 AGC 探测脱钩

`registerPushMessageReceiver()`（:30）在 onCreate 同步调用，而 `PushService.init` 异步执行——"接收器注册"先于"AGC 配置探测完成"。若 AGC 未配置，`pushService.receiveMessage(...)` 可能抛错，try/catch 兜住（:101-104）打 `receiveMessage register failed`，行为安全。但结构上造成：**日志里可能出现 "push message receiver registered"（:100）与 "agconnect absent, push degraded"（PushService.ets:33）并存的矛盾现场**，排查时误导人。建议改为 `PushService.init` 探测通过后再注册接收器，或把注册逻辑整体下沉进 PushService（与 2.4 一并解决）。

### 2.4 分层不一致：接收器绕开了 PushService 封装

`EntryAbility.ets:6` 直接 `import { pushService, pushCommon } from '@kit.PushKit'`，`:83-105` 在 Ability 内调用 `pushService.receiveMessage('DEFAULT', this, callback)`。治理基调是"PushService.ets 保持占位封装"——Push 的端侧细节（getToken、上报、接收）应收敛于 PushService。现状造成：

- Push 逻辑分裂两处：token 生命周期在 PushService.ets:47-72，消息接收在 EntryAbility.ets:83-105；
- `:4` 的 `PushService` 与 `:6` 的裸 `pushService` 两个名字极易混淆的导入并存；
- 接收器内 `JSON.parse(data.data)`（:90）的健壮性逻辑放在了 Ability 层：解析失败有内层 try/catch（:96-98）兜住，但 `parsed['alertId']` 未校验类型即写入 AppStorage（P6 关联点）；
- 接收器日志 `data=${data.data}`（:87）打印完整 payload——payload 含 alertId/symbol/kind/audioUrl（broadcast-a2a/index.js:206-211 的 message.data 构造），audioUrl 是带鉴权参数的临时链接，完整落日志有泄露面（与 A25 P5 同源问题）。

（说明：`pushService.receiveMessage` 的 API 形态本次未做 SDK 文档比对与真机验证，签名与 'DEFAULT' 场景行为以实测为准；本条针对分层归属，不否定 API 用法本身。）

---

## 三、onNewWant 处理审查（:43-69）

### 3.1 四条分支还原

1. **通知拉起**（:45-48）：`want?.parameters?.alertId` → `pendingAlertId`。热启动点通知走这里，与 onCreate 冷启动补检（:25-28）配对——冷/热两条启动路径都已覆盖，白皮书 §3.3.2 缺口修复完整；
2. **小艺 QUERY_ALERTS**（:52-54）：`action === 'com.yehang.stockpulse.QUERY_ALERTS'` → 置 `xiaoYiQuery = true`，注释说"让 Index 页面返回异动摘要"；
3. **小艺 DETAIL_ALERT**（:55-60）：取 `xiaoYiAlertId` → `pendingAlertId`；
4. **小艺 PLAY_AUDIO**（:61-68）：取 `playAlertId` → 同时置 `pendingAlertId` 与 `autoPlay = true`。

三个自定义 action 与 `module.json5` abilities[0].skills 第三组 actions 声明一一对应，清单完整。onNewWant 无返回值、无 await，符合同步回调约束。

### 3.2 问题 P1（高）：`xiaoYiQuery` 与 `autoPlay` 是死标志

grep 对 `entry/src` 全量检索确认：`xiaoYiQuery` 仅出现在 `EntryAbility.ets:54`，`autoPlay` 仅出现在 `:66`——**两个标志没有任何消费点**（Index.ets 全文 461 行无读取）。后果：

- 小艺"查询异动列表"的语音意图被静默吞掉——用户问了，应用没有任何响应路径；
- PLAY_AUDIO 语义是"用户明确要求播放"，但 `autoPlay` 置位后无人理睬，实际播放与否退化为 `pendingAlertId → playById` 的自动播报链路，还受 P2 的开关拦截。

修复方向（任选其一并在 Index 落地）：① 在 `Index.aboutToAppear/onPageShow` 的 `loadSettings()` 后消费 `xiaoYiQuery`——为真时把当前 items 摘要拼成白话短句（仅复述 headline 事实，措辞遵守三禁：不承诺收益、不催促、不涉收费）写回约定 AppStorage 键供小艺读取，随后 `AppStorage.delete` 清标志；② 消费 `autoPlay`：置位时走一条绕过开关的显式播放通道（见 P2），用完即删。当前"只写不读"属于半成品功能上线的典型形态，应在小艺联调前补齐或注释禁用，避免"看起来支持"的假语义。

### 3.3 问题 P2（高）：小艺 PLAY_AUDIO 会被播报开关/免打扰误杀

链路推演（静态）：PLAY_AUDIO → `pendingAlertId` → Index `checkPendingAlertId()`（Index.ets:140-146）→ `playById(id)`（:204-225）。`playById` 内有两道闸门：`if (!this.broadcastEnabled)`（:215-218）与 `if (this.dndActive)`（:220-223），命中即"自动播报静默跳过"。Index.ets:219 的注释写"用户手动点击仍可播放"——但小艺语音指令同样是用户显式意图，却走了自动播报通道被一并拦截。老年用户对小艺说"播放这条异动"，若恰逢免打扰时段或播报开关关闭，得到的是完全无响应。

修复建议：onNewWant 的 PLAY_AUDIO 分支额外置 `explicitPlay` 标志（或直接复用 `autoPlay` 并落地消费），Index 消费时对显式播放跳过 broadcastEnabled/dndActive 两道闸（保留 playingId 互斥处理），并在免打扰被显式穿透时于顶栏短暂提示。此改动不违反合规红线——免打扰是体验设计而非合规要求，显式指令穿透是通用助手惯例。

### 3.4 问题 P3（中）：alertId 提取逻辑三处重复且日志口径不一

`EntryAbility.ets:25-28`（onCreate）、`:45-48`（onNewWant）、`:89-95`（push receiver）三段几乎同构的 `want?.parameters?.alertId → AppStorage.setOrCreate('pendingAlertId', ...)`。重复不直接产生 bug，但已有不一致苗头：receiver 分支打 payload 日志（:87），另两处不打印。建议抽私有静态方法 `stashPendingAlertId(alertId?: string): void` 统一三处，内含 P6 的类型门槛与统一日志口径（alertId 格式为 `symbol_ts`，泄露面小，建议统一只打 id 不打全 payload）。

### 3.5 问题 P4（低）：参数未做类型与格式校验

三处取值都直接 `as string | undefined` 强转。若服务端/小艺传入非字符串（如嵌套对象），`as` 掩盖类型问题，直到 Index 端 `items.find((it) => it.alertId === id)` 匹配失败静默返回（Index.ets:205-209）。建议 stash 方法内加 `typeof alertId === 'string' && alertId.length > 0 && alertId.length < 128` 门槛，超界记 warn 丢弃。

---

## 四、alertId 拉起定位链路审查（Ability → AppStorage → Index）

### 4.1 全链路还原

```
通知/小艺携带 alertId
  ├─ 冷启动：onCreate(:25-28) 写 pendingAlertId
  │     → onWindowStageCreate loadContent('pages/Index')（:33-41）
  │     → Index.aboutToAppear → checkPendingAlertId（Index.ets:99-103, 140-146）
  ├─ 热启动/后台拉起：onNewWant(:45-48) 写 pendingAlertId
  │     → Index.onPageShow → checkPendingAlertId（Index.ets:105-109）
  └─ 前台 DEFAULT 推送：receiver(:83-99) 写 pendingAlertId
        → 下一次 aboutToAppear/onPageShow 消费（页面常驻时无自动触发，见 4.3）
消费侧：checkPendingAlertId 取出即删（AppStorage.delete，Index.ets:143）→ playById
```

取用即删（Index.ets:143）保证标志不重复消费，是正确的幂等设计。三条路径汇入同一 AppStorage 键，解耦了 Ability 与页面生命周期差异，整体干净。

### 4.2 定位失败的静默策略核对

`Index.playById`（Index.ets:204-225）对三种失败均静默：目标不在当前列表（:205-209，含被自选股过滤与被服务端撤下两种原因）、无 audioUrl（:210-213）、播报关闭/免打扰（:214-223）。对"通知点了没反应"的老年用户场景，静默是体验硬伤：用户被通知拉起，列表里却找不到对应卡片时没有任何解释。建议至少做一层：定位失败时补拉一次 feed（调用 `AlertPoller.fetchLatest` 后重试匹配），仍失败则用大字 toast 提示"这条消息已过期"。是否实施属产品决策，本审查先记为缺口。

### 4.3 前台推送路径的时效缺口

前台收 DEFAULT 推送时（receiver :89-95）只写 `pendingAlertId`，而消费点只有 `aboutToAppear`/`onPageShow`（Index.ets:99-109）——页面已展示时这两个钩子不再触发，标志一直躺着，直到用户切去设置页再回来才被消费。此时 alertId 可能已过期，`playById` 静默跳过，行为等于"前台推送不带任何定位效果"。核对语义：前台推送的本意更可能是"新增一条卡片"而非"定位播放"，receiver 或许根本不该写 pendingAlertId。建议明确语义：前台推送若含 alertId 且需要播放，应通过事件机制通知 Index 立即 `checkPendingAlertId()`（AppStorage 键可用 `@StorageLink` 监听变化，或 Ability 持回调注入），而非依赖页面钩子。

### 4.4 onWindowStageCreate 与启动窗口

`:33-41` 的 `loadContent('pages/Index')` 错误分支只打日志不重试不提示——加载失败用户面对空白页，与"首屏永不空白"约束存在理论冲突（实际触发概率极低；`main_pages.json` 中 `pages/Index` 注册在案，演示卡机制在页面加载成功后才生效）。`module.json5` 已配置 `startWindowIcon/startWindowBackground` 启动窗，冷启动观感有兜底。建议失败分支至少二次尝试或提示文案，列低优先级。

### 4.5 生命周期覆盖核对

onCreate（:13-31）、onWindowStageCreate（:33-41）、onNewWant（:43-69）、onForeground（:71-76）四个回调已实现；**onBackground 未重写**。退后台时的行为由页面层决定（Index 无 onPageHide，轮询继续——A23 Q1 详述），Ability 层无兜底。`module.json5` requestPermissions 已预留 `KEEP_BACKGROUND_RUNNING`（注释标明"R3 实装 Push Kit 后启用"），未来 R3 后台播报实装时建议在 onBackground/onForeground 统一调度播放与轮询的暂停恢复。

---

## 五、配置与版本口径核对

1. **SDK 版本口径差异（需治理侧确认）**：治理上下文声明 compatibleSdkVersion 20 / targetSdk 26，但仓库 `build-profile.json5:8-9` 实际为 `"6.0.2(22)"` 两项一致（HarmonyOS 6.0.2 / API 22）。两者不一致影响文档口径而非编译（以仓库为准可编译）。建议在 GOVERNANCE 统一口径或修正 build-profile；
2. **module.json5 skills 三组齐全**：home 主入口、`action.ohos.push.listener`（Push 透传监听）、三个小艺自定义 action——与 onNewWant 分支一一对应（已逐条比对）；
3. **网络权限**：`ohos.permission.INTERNET` 已声明，满足 token 上报与接收器需求；KEEP_BACKGROUND_RUNNING 为预留态。

---

## 六、问题清单汇总与优先级

| 编号 | 级别 | 问题 | 证据 | 建议动作 |
|---|---|---|---|---|
| P1 | 高 | xiaoYiQuery/autoPlay 死标志，小艺意图无响应 | EntryAbility.ets:54、:66；grep 全工程无消费 | Index 消费或注释禁用 |
| P2 | 高 | 小艺显式播放被播报开关/免打扰静默拦截 | Index.ets:214-223 链路推演 | 显式播放通道绕闸 |
| P3 | 中 | 前台推送 pendingAlertId 无消费时机 | Index.ets:99-109 仅页面钩子触发 | 明确前台推送语义并补事件通知 |
| P4 | 中 | 接收器绕开 PushService 封装、注册时序与 AGC 探测脱钩 | EntryAbility.ets:6,30,83-105 | 下沉 PushService，探测通过后注册 |
| P5 | 中 | receiver 日志打印完整 payload（含带鉴权 audioUrl） | EntryAbility.ets:87 | 收敛为只打 alertId |
| P6 | 低 | alertId 无类型/长度校验、三处提取重复 | EntryAbility.ets:25,45,57,63,91 | 抽 stash 方法 + 门槛校验 |
| P7 | 低 | SDK 版本口径与治理文档不一致 | build-profile.json5:8-9 | 治理侧统一口径 |
| P8 | 低 | loadContent 失败无用户可见兜底 | EntryAbility.ets:34-38 | 失败提示或重试 |
| P9 | 低 | onBackground 缺失，后台行为无 Ability 层兜底 | 全文件未重写 | R3 时统一调度 |

## 七、审查方法声明与遗留项

本审查完成于 2026-09-23，依据当日仓库快照：EntryAbility.ets（快照 09-18，123 行）全文逐行阅读；PushService.ets（快照 09:30）全文阅读；Index.ets 消费链路（快照 12:42，:99-109、:140-146、:204-225）核对；module.json5、build-profile.json5、main_pages.json 逐项比对。grep 核实：`pendingAlertId`（9 处写入/消费点）、`xiaoYiQuery`/`autoPlay`（各仅 1 处写入、0 消费）。**未执行项**：真机/模拟器运行验证、Push Kit SDK 签名比对（`pushService.receiveMessage`）、hilog 输出实测——涉及运行时行为的结论（P2 链路推演、P3 时效缺口、2.3 时序矛盾）均基于静态代码路径推演并已标注，实施修复前建议先在模拟器复现 P1/P2。

### 自我评估
- 正确性：4分 全部结论附行号与快照时间，死标志经 grep 全工程核实；运行时推断明确标注未验证。
- 完整性：4分 覆盖三条主线并延伸到时序、分层、生命周期、配置口径；真机验证未做已如实声明。
- 可复用性：4分 问题清单表可直接转工单；链路图与行号引用便于复核；修复建议保留产品决策空间。
- 字数：约3700字
- 使用模型：GLM-5.3-Flash
