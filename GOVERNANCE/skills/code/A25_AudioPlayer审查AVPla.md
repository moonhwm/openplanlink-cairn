# A25 AudioPlayer 审查——AVPlayer 播云端 TTS 音频流、播放状态管理、错误处理

> 审查对象：`entry/src/main/ets/services/AudioPlayer.ets`（共 64 行）；联动方：`entry/src/main/ets/pages/Index.ets`（togglePlay :225-287、refresh 卡片撤下防护 :151-200）、云端生产方 `cloudfunctions/functions/generate-tts/index.js`（音频参数 :205-227、临时链接 :310-334）。
> 审查方式：2026-09-23 通读源文件；并发行为为静态交错推演（本环境无真机），均已标注"待真机复现"。AVPlayer 状态机语义以鸿蒙媒体模块公开文档的通用状态集（idle/initialized/prepared/playing/paused/completed/stopped/released/error）为参照，个别状态迁移细节以实测为准。

---

## 一、总体结论

AudioPlayer 以 64 行实现了"点卡片=听"的适老化核心交互，结构极简：静态单实例 AVPlayer、`play(url, onDone, onError)`、`stop()` 两个入口，与 Index 的 `playingId/loadingId/failedId` 三态机配合。设计取向（同一时刻只允许一条音频、不提供暂停只提供停止、失败靠卡片重试文案）与产品形态匹配，方向正确。但审查发现两个必须在真机上验证的并发缺陷：**stop() 内重复读取静态字段导致"旧停止调用可释放新播放器"的交错窗口**（§五，A25 最高优先级），以及**error 事件不清理实例造成失败播放器滞留**（§四 P1）。另有无音频焦点处理、`idle` 状态被当作完成信号等中低危问题。逐节展开。

---

## 二、播放链路审查（AVPlayer 播云端音频流）

### 2.1 链路还原

`AudioPlayer.ets:17-53` 的 `play(url, onDone?, onError?)`：

1. `await AudioPlayer.stop()`（:18）——先清场，保证静态单实例语义；
2. `media.createAVPlayer()`（:21），失败则 `onError?.()` + throw（:20-26）；
3. 注册两个事件：`stateChange`（:29-33，`completed` 或 `idle` 时回调 onDone）、`error`（:34-37，回调 onError）；
4. `av.url = url`（:39）赋云端流地址 → 状态 idle→initialized；
5. `await av.prepare(); await av.play()`（:41-42）；
6. 失败路径（:43-52）：release 半初始化实例、`player = null`、onError、throw——**"清理半初始化的 player"注释（:45）表明作者已意识到实例泄漏问题，prepare/play 阶段处理到位**。

链路本身符合 AVPlayer 的标准用法（url 流式播放无需 fdSrc，mp3 网络流可直接喂 url）。`generate-tts` 产出的音频为 mp3、16000Hz、单声道、`rate: 0.9` 慢速、`volume: 65`（generate-tts/index.js:220-224）——语速放慢是云端合成参数而非端侧能力，端侧无需倍速 UI，这个分工对适老化场景是合理的：**慢速由 TTS 直接合成，避免了端侧变速导致的音调失真**。

### 2.2 云端流的地址问题（跨篇引用）

`av.url` 接的是 generate-tts 写进 alerts.json 的 `getTempFileURL` 临时链接（generate-tts/index.js:321-325），过期后 prepare 阶段将报错进入 :43-52 清理路径，UI 表现为"语音加载失败，点重试"且重试必败。该问题的契约与产品决策已在 A24 §3.6（F6）完整记录，本篇只确认端侧表现链路：**temp URL 过期 → prepare reject → onError + throw → Index failedId**，端侧现有错误处理能兜住不崩溃，但无法自愈。治理上下文已知问题"audioUrl undefined 端侧按需调 generate-tts"的对应实装（播放失败时按需重取/重新合成）目前不存在——`Index.playById` 对无 audioUrl 仅静默跳过（Index.ets:208-211）。

---

## 三、播放状态管理审查

### 3.1 与 Index 三态机的联动

状态归属划分清晰：AudioPlayer 管 AVPlayer 实例与事件，Index 管用户可见的三态（`playingId` 播放中 / `loadingId` 加载中 / `failedId` 失败可重试）。回调契约：`onDone` → Index 清 playingId（Index:251-253）；`onError` → 清 loading/playing、置 failedId（:254-258）。`togglePlay` 的四道前置闸：loadingId 相同直接 return（:229-231，防连点）、playingId 相同则停止（:232-235，再点即停）、其他卡在播则先停（:237-240，互斥）、failedId 清除（:242-244）。

`stateChange` 只认 `completed/idle`（AudioPlayer:30）意味着 paused/stopped 状态不通知 Index——用户按系统媒体键或来电打断导致 paused 时，UI 仍显示"■ 停"，再点一次走 :232-235 停止分支，状态最终一致，只是中途 UI 与实际播放态短暂脱节（见 P4 的 audioInterrupt 建议）。

### 3.2 单实例策略与 stop 语义

静态 `player` 字段（:9）+ 每次播放前 stop（:18）保证了"全局最多一个活跃播放器"，与单卡片播报的产品形态匹配。`stop()`（:55-63）stop+release 并吞掉重复释放异常（:60 注释"忽略重复释放"）。不提供 pause：对几句话时长的 TTS 短音频，"再点一次=重听"比"暂停/续播"对老年用户更简单，设计取舍合理；代价是重听需重新 prepare（重新拉流），云端小文件（单条 TTS 数十 KB 量级）可接受。

### 3.3 状态管理亮点（记录）

Index 侧两处防御值得点名：①refresh 撤卡防护（Index:166-177）——轮询发现正在播/加载的卡片被服务端撤下时主动 `AudioPlayer.stop()` 并复位状态；②`togglePlay` 完成后的 ownership 复查（Index:261-263）——`await play` 返回后校验 loadingId 仍是本卡才置 playingId，防住"加载中卡片被撤、prepare 晚到"的错位。这两处与 AudioPlayer 的事件回调共同构成三层防护，主路径是严密的；漏洞集中在下文的多调用交错场景。

---

## 四、错误处理审查

### 4.1 问题 P1（高）：error 事件不清理实例

`av.on('error', ...)`（:34-37）只记日志 + `onError?.()`，**不 release、不置 `AudioPlayer.player = null`**。播放中途网络断流触发 error 事件后：实例进入 error 态滞留在静态字段，直到下一次 play() 的 stop(:18) 或页面销毁的 stop(Index:115) 才被回收。滞留期间：①底层资源（解码器/网络连接）不释放；②若用户点另一张卡，play() 先 stop 旧实例——行为能自愈，但窗口内若 App 退后台，滞留实例无任何清理路径（Index.aboutToDisappear 不触发）。修复：error 回调内做与 :43-52 相同的清理（release + 置 null），注意 error 回调是异步事件，清理需 try/catch 包裹。

### 4.2 问题 P2（中）：onError 双触发与 onDone 的 idle 歧义

- **onError 双触发**：prepare/play reject 时，:50 调 `onError?.()` 且 :51 throw；而 error 事件也可能因同一底层故障先行/随后触发 :36 的 `onError?.()`——Index 的 onError 回调（Index:254-258）是幂等的置状态操作，双调用无实际危害，但依赖调用方幂等，属脆弱契约，建议 AudioPlayer 内部加 `errored` 标志去重。
- **idle 当完成**：`state === 'idle'` 触发 onDone（:30）。AVPlayer 初始即 idle、`reset()` 后回到 idle；本类代码不调 reset，故当前无实际触发路径，但该分支是埋着的雷：未来任何人加 `reset()` 复用实例（性能优化的常见手），onDone 将在回 idle 瞬间误报"播放完成"。建议收紧为仅 `completed`（stopped/released 属主动清理，不应触发完成语义）。

### 4.3 问题 P3（低）：异常消息直出 URL

:25、:51 把底层异常 message 原样 throw，Index :282 记入 hilog。AVPlayer 网络错误的 message 可能携带完整 URL——当前 audioUrl 是带鉴权参数的临时链接（A24 F6），失败日志等于把带 token 的链接写进日志。虽然端侧日志泄露面远小于服务端，仍建议 AudioPlayer 对 message 做"截断到 80 字符 + 剥离 query"处理，与项目"不泄露任何 Token/密钥"红线对齐。

---

## 五、竞态分析：stop() 的交错释放窗口（核心发现，待真机复现）

### 5.1 缺陷代码

`AudioPlayer.ets:55-63`：

```ts
static async stop(): Promise<void> {
  if (AudioPlayer.player) {
    try {
      await AudioPlayer.player.stop();      // :57 首次读取静态字段
      await AudioPlayer.player.release();   // :58 再次读取静态字段 ← 问题所在
    } catch (e) { }
    AudioPlayer.player = null;              // :61 无条件置空
  }
}
```

关键：`:58` 在 `await` 恢复后**重新读取** `AudioPlayer.player`。两个 await 之间是异步间隙，期间静态字段可能已被其他 play()/stop() 改写。

### 5.2 交错场景推演

设当前正在播放 A（player=A），用户点卡片 B 触发 `play(B)`，同时页面某处（如 refresh 撤下 A，Index:167）触发 `stop()`#1：

| 时刻 | stop()#1 | play(B) 内部的 stop()#2 与后续 | 静态字段 |
|---|---|---|---|
| t1 | :57 读到 A，await A.stop() 挂起 | | A |
| t2 | | stop#2：读到 A，A.stop+release，:61 置 null | null |
| t3 | | createAVPlayer→B，:27 player=B，prepare/play 启动 | B |
| t4 | :58 恢复：**重读静态字段，得到 B** → `await B.release()` | | B（被释放） |
| t5 | :61 置 null | B 播放中断（error/stateChange） | null |

后果：**新启动的 B 播放被一个"想停 A"的旧调用杀掉**。反向场景（stop#1 的 t4 落在 play(B) 的 :27 之前）则是 :61 把 play(B) 刚赋的 B 置 null → 下一次 stop() 找不到 B → 若此时又点 C，play(C) 内部 stop() 拿不到 B 直接新建 C → **B 的音频流无人能停，与 C 叠音**。两种交错都真实存在触发路径：Index 有四处 fire-and-forget 的 `AudioPlayer.stop()`（:115、:167、:182、:234、:238），与 togglePlay 的 play 并发窗口随轮询刷新常态出现。

### 5.3 修复建议（局部捕获 + 身份校验 + 代际号）

```ts
static async stop(): Promise<void> {
  const p = AudioPlayer.player;          // 局部捕获，不再二次读静态字段
  if (!p) return;
  AudioPlayer.player = null;             // 先摘引用，后续失败也不影响新实例
  try { await p.stop(); } catch (e) { }
  try { await p.release(); } catch (e) { }
}

static async play(url: string, onDone?: () => void, onError?: () => void): Promise<void> {
  await AudioPlayer.stop();
  const av = await media.createAVPlayer();
  AudioPlayer.player = av;               // 此刻起本实例是"现任"
  // ...事件注册...
  try { av.url = url; await av.prepare(); await av.play(); }
  catch (e) {
    if (AudioPlayer.player === av) {     // 只清理仍是"现任"的自己
      try { await av.release(); } catch (e2) { }
      AudioPlayer.player = null;
    }
    onError?.(); throw new Error((e as Error).message);
  }
}
```

要点：① stop 不再无条件置空静态字段（先摘后清，且只动自己捕获的实例）；② play 失败清理加身份校验，避免误杀继任者；③ 配合 Index 侧把三处状态复位改为按 alertId 认领（Index:283-285 的 `loadingId = ''` 应改为 `if (this.loadingId === item.alertId)`，否则 A 卡失败回调会清掉 B 卡的 loading 态——与 A23 §5.3 结论互为印证）。P1（§4.1）的 error 清理同样应带 `AudioPlayer.player === av` 校验。

---

## 六、问题清单汇总

| 编号 | 级别 | 问题 | 证据 | 建议动作 |
|---|---|---|---|---|
| P0 | 高 | stop() 交错读静态字段：可释放/丢失新播放器，极端时叠音 | AudioPlayer.ets:57-61；交错推演见 §5.2 | 局部捕获+身份校验+代际号 |
| P1 | 高 | error 事件不清理实例，失败播放器滞留 | AudioPlayer.ets:34-37 | error 回调内 release+置空（带校验） |
| P2 | 中 | onError 可双触发；idle 被当完成信号埋雷 | AudioPlayer.ets:30,36,50-51 | errored 去重；onDone 收紧为 completed |
| P3 | 中 | 无音频焦点（audioInterrupt）处理，打断后 UI 脱节 | 全文件无该事件注册 | 注册 audioInterrupt，打断时同步 Index 状态 |
| P4 | 中 | temp URL 过期→播放必败且无法自愈 | generate-tts:321-325 + AudioPlayer:39 | 见 A24 F6，端侧按需重取/重新合成 |
| P5 | 低 | 异常 message 可能带鉴权 URL 入日志 | AudioPlayer.ets:25,51 + Index.ets:282 | 剥离 query、截断 |
| P6 | 低 | err 参数未标类型；paused 态 UI 不感知 | AudioPlayer.ets:34；:29-33 状态白名单 | 标 BusinessError；视需要扩展 paused 同步 |
| P7 | 低 | 跨卡连点时 Index 状态被跨调用覆盖 | Index.ets:283-285 无认领校验 | 复位按 alertId 认领（与 §5.3 ③配套） |

---

## 七、云端音频流配套观察

1. **适老参数已内嵌**：mp3/16kHz/单声道足够语音播报清晰度；`rate: 0.9` 慢速、`volume: 65`、`pitch: 0.95`（generate-tts/index.js:220-224）由合成端固化，端侧无需也不应再加工，符合"白话慢速"的适老化要求；
2. **WebSocket 半包兜底**：generate-tts:289-299 对连接提前关闭但已收音频块的场景采用"部分音频也交付"策略——端侧无感知，属云端韧性设计，不在本篇追责范围；
3. **百炼只支持 WebSocket 的约束**已通过 `ws` 依赖 + run-task/continue-task/finish-task 三段协议落地（generate-tts:16、:205-260），端侧 AudioPlayer 与传输方式解耦，未来 TTS 供应商更换不影响本文件；
4. **播放失败与按需合成的衔接**：产品语义上"无 audioUrl 的卡片点击后调 generate-tts 现场合成"是已知规划，届时 AudioPlayer.play 的调用点将从"仅有 URL 才可点"（Index:226）扩展为"先取 URL 再播"，建议届时在 AudioPlayer 增加 `loading` 中间事件回调，避免 Index 再造一层 loading 态。

## 八、审查方法声明

本审查完成于 2026-09-23，基于当日仓库快照对 AudioPlayer.ets 全文 64 行、Index.ets 播放相关段（:115,151-200,202-287）、generate-tts 音频生产段（:205-334）的通读。**未执行项**：真机/模拟器播放实测、AVPlayer 状态迁移的官方文档逐条比对、P0 竞态的运行时复现——§5.2 的交错表为静态推演，逻辑上自洽（依据 ：57/:58 两次读取静态字段与 await 挂起点），但触发概率与时序落地需按修复建议先写并发单测或真机日志验证。P0/P1 的修复代码为设计稿，未经编译运行。

### 自我评估
- 正确性：4分 链路与状态机结论均有行号依据；核心竞态 P0 给出完整交错推演并如实标注"待真机复现"，未夸大为已证缺陷。
- 完整性：4分 三条主线（播放链路/状态管理/错误处理）全覆盖，另补云端音频参数与 temp URL 的跨篇衔接；未做音频性能与编解码细节分析（文件短小，客观上内容有限）。
- 可复用性：4分 修复代码与问题清单可直接转工单；"局部捕获+身份校验"模式可迁移到其他静态资源管理类；与 A23/A24 的交叉结论已互相注明出处。
- 字数：约3600字
- 使用模型：GLM-5.3-Flash
