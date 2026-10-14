# code技能：ArkTS音频播放——AVPlayer使用规范与TTS音频流状态管理

> 编写时间：2026-09-23
> 编写席位：Moon席位批次写手-B组-1号（GLM-5.3-Flash）
> 适用范围：harmony-app（铃语）端侧 `entry/src/main/ets/services/AudioPlayer.ets` 及一切基于 AVPlayer 的播报功能
> 事实来源：现网 `entry/src/main/ets/services/AudioPlayer.ets`（全文 64 行）、`entry/src/main/ets/pages/Index.ets:225-287`（联动逻辑）、`entry/src/main/ets/model/AlertItem.ets:15`（audioUrl 契约）、`cloudfunctions/functions/generate-tts/index.js`（云端生成）。未在现网实现、属建议的内容均标注「规划」。

## 0. 音频链路全景（自包含背景）

铃语的核心交互是「点卡片=听播报」。完整链路：

```
云端：generate-tts 云函数经 WebSocket 调阿里百炼 TTS 合成音频
  → 存为可 HTTP 访问的音频文件 → 写入 alerts.json 的 audioUrl 字段
端侧：Index.ets 拉取 AlertFeed → 卡片上有 audioUrl 才显示播报钮
  → 点击 → AudioPlayer.play(url) → AVPlayer 播放 http(s) 音频流
```

三个已知事实决定设计：① 百炼 TTS 只支持 WebSocket（`generate-tts/index.js:6,16,193`），但那是**云侧**的事，端侧永远只面对一个普通 HTTP 音频 URL，不碰 WebSocket；② `alerts.json` 里 `audioUrl` 可能为 undefined，此时卡片不显示播报钮（`AlertItem.ets:15` 注释、`Index.ets:390`），并规划由端侧按需调 `generate-tts` 补齐后重取；③ 适老化要求无进度条、无复杂控制，播放控制只有「点一下听、再点一下停」。

## 1. AVPlayer 状态机规范

`media.AVPlayer`（`@kit.MediaKit`）是严格状态机，非法迁移直接抛错。与本场景相关的迁移：

```
idle ──(url= 赋值)──> initialized ──(prepare())──> prepared
prepared ──(play())──> playing ──(自然播完)──> completed
playing/prepared/completed ──(stop())──> stopped ──(release())──> released
任意状态 ──(error 事件)──> error ──(release())──> released
```

四条铁规：

1. **必须先赋 `url` 再 `prepare()`**——idle 态直接 prepare 会抛错；url 赋值触发 idle→initialized（`AudioPlayer.ets:39-41` 的顺序即规范）；
2. **`release()` 是唯一终态出口**。error 后、换曲前、页面销毁前都必须 release，否则底层解码资源泄漏，累积后新实例创建失败；
3. **completed ≠ released**：播完进入 completed，实例仍占资源；要么 seek 回去重播，要么 release。本项目选择播完即留给下次 `play()` 前的 `stop()` 链路回收（见 2.1）；
4. **回调注册要赶在动作前**：`on('stateChange')`/`on('error')` 必须在 `prepare()` 之前挂好（`AudioPlayer.ets:29-37` 在 41 行 prepare 之前），否则早到的状态变化漏接。

## 2. 单例封装规范（现网范式逐条讲）

### 2.1 为什么是静态单例

```typescript
export class AudioPlayer {
  private static player: media.AVPlayer | null = null;   // AudioPlayer.ets:9
```

产品语义是**全局同一时刻只播一条**：老年用户不应被两条播报叠音。静态单例从机制上保证「新播必先停旧」（`AudioPlayer.ets:18` 的 `await AudioPlayer.stop()` 打头）。这不是省内存的优化，是交互正确性约束。

### 2.2 play 流程六步（`AudioPlayer.ets:17-53`）

```typescript
static async play(url, onDone?, onError?): Promise<void> {
  await AudioPlayer.stop();                    // ① 先停旧实例（含 release）
  let av: media.AVPlayer;
  try { av = await media.createAVPlayer(); }   // ② 创建（失败即回调并抛出）
  catch (e) { onError?.(); throw new Error(...); }
  AudioPlayer.player = av;
  av.on('stateChange', (state) => {            // ③ 挂状态回调
    if (state === 'completed' || state === 'idle') onDone?.();
  });
  av.on('error', (err) => { onError?.(); });   // ④ 挂错误回调
  av.url = url;                                // ⑤ 赋 url（idle→initialized）
  try {
    await av.prepare();                        // ⑥ prepared
    await av.play();                           //    playing，Promise 方 resolve
  } catch (e) {
    try { await av.release(); } catch (_) {}   // 半初始化实例必须回收
    AudioPlayer.player = null;
    onError?.();
    throw new Error((e as Error).message);
  }
}
```

规范要点：

- **双通道完成通知**：`await play()` resolve 只代表「开始播放」，**播放结束**只能靠 `stateChange` 到 `completed`/`idle` 的回调通知（30-32 行）。把 await 当播完是 AVPlayer 最常见误用，会导致 UI 提前摘掉播放态；
- **失败路径三件套**：release 残骸 → 置空静态引用 → 触发 onError（44-51 行）。少任何一件都会留下"僵尸实例"：下次 play 的 `stop()` 会对已失效实例操作，或 createAVPlayer 因资源未释放而失败；
- **release 包 try-catch**：重复 release 会抛错，忽略即可（47-48、59-60 行注释「忽略重复释放」）；
- **stop 幂等**：`player` 为 null 直接返回（55-63 行），任何地方可放心调 `AudioPlayer.stop()`。

### 2.3 stop 的语义（`AudioPlayer.ets:55-63`）

stop = `stop()` + `release()` + 置 null。注意对已 completed 的实例直接 stop 可能抛错，被外层 catch 吞掉——这是可接受的：目标只是"资源归零"。**页面销毁必调**：`Index.aboutToDisappear` 里 `AudioPlayer.stop()`（`Index.ets:115`），防止退页后声音继续。

## 3. 与 UI 的三态联动规范

播报状态用三个标量 @State 表达（`Index.ets:29-31`），不塞进条目对象：

- `loadingId`：prepare+play 进行中，按钮显「…」；
- `playingId`：播放中，按钮显「■ 停」；
- `failedId`：失败，卡片尾部显「语音加载失败，点重试」（`Index.ets:412-416`）。

### 3.1 togglePlay 状态机（`Index.ets:225-287`）

```typescript
if (this.loadingId === item.alertId) return;      // 加载中重复点击：忽略
if (this.playingId === item.alertId) {            // 播放中再点：停止
  this.playingId = ''; AudioPlayer.stop(); return;
}
if (this.playingId) { AudioPlayer.stop(); ... }   // 别的卡片在播：先停它
this.loadingId = item.alertId;                    // 进入加载态
try {
  await AudioPlayer.play(item.audioUrl,
    () => { this.playingId = ''; },               // onDone：自然播完
    () => { this.loadingId=''; this.playingId='';
            this.failedId = item.alertId; });     // onError：失败态
  if (this.loadingId !== item.alertId) return;    // ★ await 竞态校验
  this.loadingId = ''; this.playingId = item.alertId;
} catch (e) { this.loadingId=''; this.failedId = item.alertId; }
```

★ 处是全篇最重要的一行（`Index.ets:260-265`）：`await` 期间 5 秒轮询可能已把该卡片撤下并清了 `loadingId`（见 3.2），不校验就会给一张已消失的卡片挂上"播放中"。**凡 await 后再写状态，必须先验证前置态仍成立**。

### 3.2 轮询与播放的交叉规则（`Index.ets:165-187`）

每次刷新后检查三个 ID 是否还在新列表：`playingId` 对应卡片被撤 → `AudioPlayer.stop()` + 清态；`loadingId` 对应卡片被撤 → 同样 stop（防 prepare 完成后把失效 ID 播出去）；`failedId` 被撤 → 清。空态（服务端连通但无条目）也停止播放——没内容就别出声。

### 3.3 播放副作用：已读与历史

play 成功启动后记已读并落播报历史（`Index.ets:267-280`）：`markAlertRead` 持久化、`readAlertIds` 前端镜像去重追加、`playHistory` 新旧条去重后**截 50 条**。历史按最新在前。规则：**副作用只在确认开始播放后触发**，加载失败不计历史。

### 3.4 自动播报的三道闸（`Index.ets:202-223`）

通知/小艺拉起的 `playById` 自动播报依次检查：卡片存在于当前列表 → 有 audioUrl → 播报开关开（关则静默跳过）→ 不在免打扰时段（DND 中只拦自动播、用户手点仍可播）。任何一道不过都**静默**返回并记日志——不打扰是默认礼貌。

## 4. TTS 音频流的端侧边界

- **URL 可空**：`audioUrl` 为 undefined 的卡片不渲染播报钮（`Index.ets:390`），点击卡片也不触发（`togglePlay` 首行守卫，226-228 行）；
- **按需生成（规划）**：`alerts.json` 的 audioUrl undefined 时，端侧可先调 `generate-tts` 云函数补齐音频、再行播放；该路径需加"生成中"独立态防重复触发，当前现网未实现，属规划项；
- **云端兜底已内建**：百炼 WebSocket 超时或异常时，若已收到部分音频分片则用部分音频返回（`generate-tts/index.js:296`），端侧无需感知"音频是否完整"；
- **不追求精确时长**：播完即回调，无进度条、无 seek 需求（适老化简化）。

## 5. 已知限制与改进项（如实列出，现网未实装）

1. **音频焦点/打断未处理**：未监听 `interrupt` 事件，来电话或其它应用抢占时不会自动暂停，恢复策略缺失。接入建议：`av.on('interrupt', ...)` 按暂停/停止语义处理，恢复播放需用户重点；
2. **回调未 off**：实例 release 前未 `off('stateChange')/off('error')`，靠整体释放兜底，存在极小概率的释放后回调竞态；
3. **无音量/倍速控制**：刻意省略（适老化），音量遵循系统；
4. **单实例串行**：不支持 A/B 混音或预加载下一条，属产品选择非缺陷。

## 6. 审查清单

- [ ] url 赋值在 prepare 之前；回调注册在动作之前；
- [ ] 失败路径：release + 置空引用 + onError 三件套齐全；
- [ ] await play() 后写状态前有竞态校验（loadingId 比对）；
- [ ] 刷新/空态时对 playingId、loadingId 的撤卡停止逻辑在位；
- [ ] 页面销毁调 `AudioPlayer.stop()`；stop 保持幂等；
- [ ] 自动播报过三道闸（存在/audioUrl/开关+免打扰），静默失败；
- [ ] 历史截 50 条、已读去重；无 audioUrl 不显钮不触发。

## 7. 资源生命周期全景

AudioPlayer 是静态单例，生命周期横跨页面与拉起路径：

```
EntryAbility.onCreate / onNewWant（通知或小艺拉起：alertId 入 AppStorage 信箱）
  → Index.aboutToAppear → pollLoop 首轮拉取填充 items
  → checkPendingAlertId → playById 三道闸 → togglePlay → AudioPlayer.play
  → Index.aboutToDisappear → AudioPlayer.stop()（Index.ets:115）
```

三条纪律：① **每次 play 前先 stop**（`AudioPlayer.ets:18`），跨场景残留的实例由此清场；② 页面销毁是唯一强制回收点——跳设置页是 Navigation 压栈、主页面不销毁（Stack 模式，`Index.ets:456`），播报不中断属预期行为；③ 杀进程随进程回收，无需应用级退出钩子——不为"保存播放进度"这类产品不需要的能力加复杂度。

## 8. 常见故障与排查表

| 症状 | 高概率原因 | 排查与修复方向 |
| --- | --- | --- |
| createAVPlayer 抛错 | 上一实例未 release，解码资源耗尽 | 核对失败路径三件套（2.2 节）；stop 幂等兜底 |
| prepare 抛错 | url 不可达、格式不支持或赋值顺序错 | 先浏览器直开 url 验证；再查 url 赋值是否在 prepare 前 |
| 界面显"播放中"但无声 | 系统静音、音量为零或音频流为空文件 | 云端核对 TTS 产物长度；检查部分音频兜底是否退化为空 |
| completed 不回调 | 回调注册晚于状态迁移 | on('stateChange') 必须在 prepare 前挂好（第 1 节铁规 4） |
| 点卡片无反应 | audioUrl 为 undefined | 契约如此：无钮不触发（`Index.ets:226-228,390`）；按需生成属规划项 |
| 播完界面仍显"■ 停" | onDone 回调未触发或竞态覆盖 | 核对 stateChange 是否同时监听 completed 与 idle |

## 9. 后台播放与音频会话（规划项，如实说明）

`entry/src/main/module.json5` 已在 `requestPermissions` 预留 `ohos.permission.KEEP_BACKGROUND_RUNNING`，配置注释明示"为 R3 推送播报预留：当前未实际调用对应 API"——即**当前版本应用退后台后播报会被系统挂起**，这是已知边界而非缺陷，文档不夸大当前能力。R3 实装方向：申请长时任务保活加 AVSession 媒体会话注册（避免与音乐类应用抢占音频焦点冲突，来电时让路）。本轮不实现，也不提前引入半吊子的后台逻辑。

## 10. 音频格式与弱网行为

- 云端产物为可 HTTP 直读的音频文件，AVPlayer 内建流式缓冲，端侧**无需手动分片下载**，也不要先下载整文件再播（增加首响延迟）；
- 格式建议通用封装（mp3/aac 类），由云侧转存环节保证；端侧只认 url、不感知合成格式细节；
- 弱网下 prepare 阶段即开始缓冲，卡顿属系统行为；端侧职责是把失败转为 failedId 与「语音加载失败，点重试」提示（`Index.ets:412-416`），重试即重点卡片；
- 重复点击防抖：loadingId 守卫（`Index.ets:229-231`）保证同一卡片加载中再点无效，切卡片则先停旧再启新。

### 自我评估
- 正确性：4分 核心流程逐行对齐 `AudioPlayer.ets` 与 `Index.ets` 现网代码并标行号；状态机迁移依据 AVPlayer 公开语义转述，未在本环境真机验证（无鸿蒙设备/模拟器，未运行任何播放检查）。
- 完整性：4分 覆盖状态机、单例封装、三态联动、竞态、TTS 链路与清单；interrupt 等改进项如实标注未实装。
- 可复用性：5分 六步 play 模板与三态联动范式可直接移植到任何"点卡片听音频"场景；审查清单可直接进 CR。
- 字数：约3050字
- 使用模型：GLM-5.3-Flash
