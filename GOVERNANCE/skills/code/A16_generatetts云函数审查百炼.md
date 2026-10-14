# A16｜generate-tts 云函数审查——百炼 TTS WebSocket 调用方式修复、连接管理、音频流处理

> 项目：harmony-app（铃语，鸿蒙适老化股票异动播报）。本篇为 Moon 席位知识资产，自包含成文，依据本仓库实际代码与 2026-09-23 当日核实的阿里云官方文档写成，引用一律给文件路径与行号，可直接照单施工。

## 一、审查范围与方法

审查对象：`cloudfunctions/functions/generate-tts/index.js`（403 行）与 `cloudfunctions/functions/generate-tts/package.json`。参照物：`cloudfunctions/cloudbaserc.json`（部署配置）、`cloudfunctions/functions/fetch-tushare-data/index.js`（上游调用方）、`entry/src/main/ets/services/AudioPlayer.ets`（端侧播放契约）。

核实手段：通读上述源码全文；用 WebFetch 抓取阿里云百炼官方文档《CosyVoice 语音合成 WebSocket API》（https://help.aliyun.com/zh/model-studio/cosyvoice-websocket-api ，2026-09-23 取回）核对端点、请求头与任务时序；用 grep 确认 callFunction 调用点（仅 `fetch-tushare-data/index.js:613`）。未运行云端实测（本地无 DASHSCOPE_API_KEY，无法发起真实合成），凡未实测处均在文中注明。

## 二、云函数现状画像

职责：接收 `alertId + text`，经阿里百炼 CosyVoice 合成播报音频，上传 CloudBase 云存储，写 tts-cache 缓存文件，回写 `alerts/alerts.json` 中对应条目的 audioUrl。依赖：`ws ^8.16.0`（package.json 第 4 行）与 `@cloudbase/node-sdk ^3.0.0`。环境变量：`DASHSCOPE_API_KEY`（必需）、`BAILIAN_WORKSPACE_ID`、`TCB_ENV`（cloudbaserc.json 中 generate-tts 段，timeout 60 秒）。

关键常量（index.js:19-25）：模型 `cosyvoice-v3-flash`，音色 `longxiaochun_v3`，WSS 地址 `wss://${BAILIAN_WORKSPACE_ID}.cn-beijing.maas.aliyuncs.com/api-ws/v1/inference`。已知问题背景：百炼 TTS 只支持 WebSocket（HTTP 无该能力），alerts.json 中 audioUrl 常为 undefined，端侧需按需调用本函数补齐。

## 三、WebSocket 调用方式审查与修复

### 3.1 端点核实结论（重要澄清）

官方文档核实结果：CosyVoice WebSocket 支持两类地址。其一是通用地址 `wss://dashscope.aliyuncs.com/api-ws/v1/inference`；其二是**业务空间专属地址**，华北2（北京）格式恰为 `wss://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api-ws/v1/inference`。因此 `index.js:23` 拼出的地址属于官方支持的第二类形式，**端点本身不是缺陷**，无需"改成 dashscope 域名"。但有一处稳健性建议：workspace 专属地址把 `BAILIAN_WORKSPACE_ID` 的默认值硬编码在代码里（index.js:19 的 `'ws-ay6o8osb22o9dc3t'`），环境变量未注入时会静默用错空间的额度；应改为缺失即报错退出，或同时携带 `X-DashScope-WorkSpace` 头（文档列其为可选头）双保险：

```js
// 修复：缺配置快速失败，而不是落到硬编码默认值
const BAILIAN_WORKSPACE_ID = process.env.BAILIAN_WORKSPACE_ID;
if (!BAILIAN_WORKSPACE_ID) throw new Error('BAILIAN_WORKSPACE_ID not configured');
const TTS_WSS_URL = `wss://${BAILIAN_WORKSPACE_ID}.cn-beijing.maas.aliyuncs.com/api-ws/v1/inference`;
// ws 建连头中追加（可选但建议）：
// 'X-DashScope-WorkSpace': BAILIAN_WORKSPACE_ID
```

### 3.2 握手与鉴权

`index.js:189-193` 用 `new WebSocket(TTS_WSS_URL, { headers: { Authorization: 'Bearer ' + BAILIAN_API_KEY } })`，与文档要求的握手头 `Authorization: Bearer <api-key>` 一致，鉴权方式正确。鉴权失败会在握手期返回 401/403 并触发 `error`/`close` 事件，现有 error 监听（index.js:283-287）只记 `event.message`，ws 库对握手失败给出的信息很贫瘠，建议在 close 事件里带上状态码区分"鉴权失败"与"网络失败"：

```js
ws.addEventListener('close', (event) => {
  // ws 库的 CloseEvent 携带 code/reason；1002/1006 多为握手失败
  console.error(`ws closed code=${event.code} reason=${event.reason || 'n/a'}`);
});
```

### 3.3 任务协议时序对照

文档规定的时序：建连 → 发 `run-task`（客户端生成 UUID 作 task_id）→ 收 `task-started` → 发一或多个 `continue-task` 提交文本（服务端自动分句）→ 经 binary 通道收音频流 → 发 `finish-task`（强制合成缓存内容，**不可省略**）→ 收 `task-finished` → 关连接。同一任务内三个指令必须用同一 task_id。

逐项对照现有实现：run-task 在 open 后发送（index.js:203-228），payload 中 `task_group:'audio'、task:'tts'、function:'SpeechSynthesizer'`，字段与文档骨架一致；收到 task-started 后连发 continue-task 与 finish-task（index.js:241-260），task_id 全程复用 `crypto.randomUUID()`（index.js:181），三处一致——**时序正确**。二进制音频帧经 `event.data instanceof ArrayBuffer` 分流收集（index.js:230-234），`ws.binaryType='arraybuffer'`（index.js:195）设置正确。

两个细节修复点：其一，`error` 消息里若 header.error_code 存在（task-failed 之外的错误形态），现有 JSON.parse 分支只处理了四种事件，`result-generated` 与未知事件被静默吞掉（index.js:278-280 的 catch 注释"非 JSON 消息忽略"），建议对 `msg.header.error_code` 做统一日志，便于对账百炼错误码；其二，超时 30 秒（index.js:197-201）对单段短文本够用，但 finish-task 后若音频较长（10 条信号卡并发时百炼限流排队）30 秒可能截断，建议超时改为"距最后一次收到数据帧 20 秒无新帧"的空转计时，而非全程总闸。

### 3.4 调用方式结论

"调用方式修复"的实际工作不在端点与协议——这两处经核实是对的——而在下面的连接管理、输入约束与回写安全，这三项才是当前 audioUrl 长期为 undefined 的可疑根因所在（额度统计失真导致静默放弃生成，见 6.3）。

## 四、连接管理审查

### 4.1 现状：每任务新建连接，无复用无心跳

`generateTTSAudio` 每次调用都 `new WebSocket(...)`（index.js:189），任务结束即 close（index.js:269、276）。一次 fetch-tushare-data 批量给 10 条信号卡合成时（fetch-tushare-data/index.js:611-626 的 Promise.allSettled 并发 callFunction），就是 10 条并发 TLS+WSS 握手，每条冷开销 200-500ms，且并发握手可能触发百炼侧连接数限流。官方文档明确建议"复用 WebSocket 连接处理多个任务"。

修复方案（模块级连接 + 串行互斥 + 空闲保活）：

```js
let _ws = null; let _wsReady = false; let _inflight = 0; const MAX_INFLIGHT = 2;
function getSharedWs() {
  if (_ws && _ws.readyState === WebSocket.OPEN) return _ws;
  _ws = new WebSocket(TTS_WSS_URL, { headers: { Authorization: `Bearer ${BAILIAN_API_KEY}` } });
  _ws.on('open', () => { _wsReady = true; });
  _ws.on('close', () => { _wsReady = false; _ws = null; });
  _ws.on('error', () => { _wsReady = false; _ws = null; });
  // 保活：30s 心跳空 ping，防云函数 NAT 空闲断链
  const hb = setInterval(() => { if (_wsReady) _ws.ping(); }, 30000);
  hb.unref?.();
  return _ws;
}
```

互斥策略：同一连接上百炼允许顺序跑多任务，但消息路由要靠 task_id 匹配，现有 on-message 是闭包绑定单任务的（index.js:230），改造时需维护 `Map<task_id, 状态机>`。若不想动消息路由，退而求其次保留每任务一连接、但把批量调用从 10 并发降到 2-3 并发（在上游 callFunction 处分批），同样消除限流风险——这是改动量最小的折中，推荐先做。

### 4.2 CloudBase 实例泄漏（对照性缺陷）

`getCloudBaseApp()` 每次 `cloudbase.init({env})`（index.js:63-66），而它在 checkCache、saveCache、updateAlertAudioUrl、uploadToStorage 四处被各调一次（index.js:74、98、124、312），一次请求至少 init 4 个 SDK 实例。对照 `fetch-tushare-data/index.js:28-37` 已有注释"避免重复 init 导致连接泄漏"并实现单例——generate-tts 没跟上同一纪律。修复：拷贝同款单例模式即可，两行改动。

## 五、音频流处理审查

### 5.1 收流与拼接

收流逻辑（index.js:230-281）：二进制帧 push 进 chunks，task-finished 时 `Buffer.concat(chunks)`（index.js:267）。MP3 16000Hz 采样（index.js:221-222）与端侧 AVPlayer 兼容（AudioPlayer.ets:39 直接 `av.url = url` 由系统 demux）。适老化参数 volume 65 / rate 0.9 / pitch 0.95（index.js:222-224）放慢语速，符合大字慢语的产品基调，保留。

### 5.2 半截音频风险（close 兜底是双刃剑）

`close` 事件里若 chunks 非空就用部分音频兜底（index.js:289-295）——"WebSocket closed with N chunks, using partial audio"。这会产出**尾帧被截断的 MP3**：可能能播但结尾破音，也可能整体时长残缺导致"老爷子听到一半没了"，比不播更伤体验。建议改为：只有当已收到 task-finished 才产出成品；close 兜底的音频必须标记 degraded，上传到 `tts/partial/{cacheKey}.mp3` 且**不写缓存、不回写 alerts.json**，让端侧下次点击重新按需生成。

### 5.3 tempFileURL 过期（最严重的隐患）

`uploadToStorage` 上传后立即 `getTempFileURL` 取**临时链接**返回（index.js:320-326），而这个临时 URL 被写入 tts-cache 缓存文件（saveCache，index.js:96-116）和 alerts.json 的 audioUrl（updateAlertAudioUrl，index.js:122-164）。CloudBase 临时链接带有效期（默认约两小时量级，以平台文档为准），而 alerts.json 是被端侧轮询数小时乃至数天的持久化数据——**过期后端侧点播必然失败**，且失败形态是 AVPlayer error，用户视角是"点了没声音"。修复方向二选一：

```js
// 方案A（推荐）：audioUrl 字段改存 fileID，端侧/服务端按需换临时URL
return result.fileID;                       // 不再 getTempFileURL
// 方案B：音频文件开公开读，拼接永久 CDN 域名
// https://{bucket}.tcloudbaseapp.com/tts/{cacheKey}.mp3
```

方案A改动最小且不改变存储权限面；配套要求 get-alerts 出口或端侧在上播前用一个轻量换链调用。鉴于已知问题"alerts.json 的 audioUrl undefined 端侧按需调 generate-tts"本就要在端侧加按需链路，按需调用返回体里给新换的临时链接正好闭环。

## 六、缓存与额度控制审查

### 6.1 缓存键不含 voice/model

`getCacheKey` = SHA256(text) 前 16 位（index.js:56-58），音色或模型升级（如 v3→v4、换音色）后旧音频仍命中缓存，白话播报永远是旧嗓子。修复：`sha256(`${TTS_MODEL}|${TTS_VOICE}|${text}`)`，成本相同，键空间自动隔离。

### 6.2 用"下载文件"探测缓存的成本

checkCache 用 `app.downloadFile` 读 `tts-cache/{cacheKey}.json`，文件不存在抛异常当 miss（index.js:72-91）。冷缓存路径每次多一次全量下载往返；且异常驱动的控制流在并发下 noisy。tts_cache 数据库集合已在 init-db 清单里（见 A18 篇）却无人使用，把缓存索引迁到集合（`where({cacheKey}).get()`，毫秒级、可加 TTL 字段）是顺势改造，同时能记录 hitCount 供额度复盘。

### 6.3 QUOTA 内存态失真 → 静默放弃生成

额度计数器是纯内存对象（index.js:28-51），云函数实例回收即清零，多实例各自计数；`recordUsage(textLength * 2.5)` 是估算而非回读账单。后果：用量统计**永远偏低**，`shouldStop()` 形同虚设，超额度后请求在百炼侧失败，表现为 task-failed → 返回 TTS generation failed → audioUrl 继续 undefined。这是"audioUrl 长期缺失"的第一嫌疑。修复：用量落库（复用 6.2 的 tts_cache 集合或单独 quota 集合，按日一条 `date/usedTokens` 文档，`_.inc` 原子累加），shouldStop 读库判断；估算系数先用 2.5 但要拿真实账单校准一次。

### 6.4 回写 alerts.json 无并发保护

updateAlertAudioUrl 走"下载整文件→改→整文件覆盖上传"（index.js:127-158），没有并发保护。对照上游 `fetch-tushare-data/index.js:518-524` 专门做了 P2 并发写入保护（existing serverTs 大于本次数据则放弃写入）。竞态场景：fetch-tushare-data 刚合并写入 500 条新异动，generate-tts 手里的旧快照把整个文件覆盖回去——**上游的增量直接丢失**，且丢的是主数据。修复：把同样的 serverTs 比对搬进 updateAlertAudioUrl，若 `data.serverTs` 比下载时更小（说明有人刚写过且更新），重走一遍下载-改-传；更彻底的做法是不回写整文件，改往数据库 alerts 集合 `where({alertId}).update({audioUrl})` 单字段更新，从根上消除覆盖。

## 七、入口鉴权与输入约束

main 入口（index.js:339-354）只校验 text 非空与 API key 已配，无鉴权、无频控、无文本长度上限。按 HTTP 访问服务暴露后，公网可匿名刷 text，一次超长文本即可消耗大量百炼额度（额度是真实金钱）。最小加固：

```js
const MAX_TEXT_LEN = 500; // 适老化播报一句话+补充事实，远用不满
if (typeof text !== 'string' || !text.trim()) return { success:false, error:'text is required' };
if (text.length > MAX_TEXT_LEN) return { success:false, error:`text too long (>${MAX_TEXT_LEN})` };
// 可选：alertId 存在时校验其格式（symbol_ts），非法直接拒
```

配合 cloudbaserc.json 里已为函数配置 60 秒超时，建议再在 HTTP 访问服务侧开限流（端侧 AlertPoller.ets:47-52 已有 429 静默处理逻辑，服务端限流与端侧降级是配套设计）。

## 八、修复优先级清单

| 级别 | 事项 | 位置 | 依据 |
|---|---|---|---|
| P0 | audioUrl 改存 fileID 或公开读永久链接，停存 tempFileURL | index.js:310-334 | 5.3，过期即点播失败 |
| P0 | 额度用量落库持久化，shouldStop 读库 | index.js:28-51 | 6.3，统计失真致静默失败 |
| P1 | 回写 alerts.json 加 serverTs 并发保护或改库单字段更新 | index.js:122-164 | 6.4，可丢上游主数据 |
| P1 | 缓存键混入 model/voice；缓存探测迁数据库集合 | index.js:56-58, 72-91 | 6.1/6.2 |
| P1 | 文本长度上限+格式校验+服务端限流 | index.js:346-350 | 七 |
| P2 | CloudBase SDK 单例化 | index.js:63-66 | 4.2，对照上游已有纪律 |
| P2 | 批量合成降并发至 2-3，或连接复用+task_id 路由 | index.js:189 | 4.1 |
| P2 | close 兜底音频降级隔离，不进缓存不回写 | index.js:289-299 | 5.2 |
| P3 | workspace 缺配置快速失败；close 事件记 code/reason | index.js:19, 283-287 | 3.1/3.2 |

## 九、遗留与未实测项

未做真实链路验证：本地无 DASHSCOPE_API_KEY 与 CloudBase 凭证，"端点可连通、tempFileURL 实际有效期、task-failed 报文样例"三项均未实测，上述判断分别基于官方文档当日取回内容与 CloudBase 通用行为，施工后需用一条真实 alertId 做端到端验收（生成→缓存命中→回写→端侧 AVPlayer 播放完整不破音）。合规面：本函数文本源头上游已经 DKnowC 检查并携带 complianceStatus 元数据（fetch-tushare-data/index.js:601-646），白话文案无催促与收益承诺措辞，本层无需重复审查，保持即可。

## 十、修复项验收标准（与第八节清单一一对应）

验收要可执行，逐项给验收动作与通过判据：

- **P0-audioUrl（5.3）**：验收=同一文本连调 generate-tts 两次，第二次返回 cached:true；若采用 fileID 方案，从 alerts.json 取出 fileID 后经 getTempFileURL 换链返回 200 可播；六小时后重复换链仍成功。若采用公开读方案，需复核存储权限面，确认放开的是 tts/ 路径而非整桶。
- **P0-额度落库（6.3）**：验收=两个不同函数实例各合成一次后，用量文档的 usedTokens 是两次之和而非互相覆盖；人为把阈值调到 1% 再调用，返回体 error 应明确指向 quota 而非笼统的 generation failed。
- **P1-回写保护（6.4）**：验收=在 generate-tts 回写前手工向 alerts.json 注入一条新异动（模拟上游刚写完），回写完成后新异动仍在文件中；若改走数据库单字段更新，验收=该 alertId 文档仅 audioUrl 字段变化。
- **P1-缓存键（6.1）**：验收=同文本换音色后 cacheKey 改变、触发新合成而非命中旧缓存。
- **P1-输入约束（七）**：验收=501 字文本被拒并返回明确错误；HTTP 访问服务限流配置后超限请求拿到 429，端侧日志出现 rate-limited 字样（AlertPoller.ets:49 的既有分支承接）。
- **P2-三项**：单例化=一次请求日志中不再出现多次 SDK 初始化；降并发=上游批量日志按 2-3 条一组分批；partial 隔离=截断场景下 tts/partial/ 有产物而 tts-cache/ 与 alerts.json 无新增。
- **P3-两项**：缺 workspace 环境变量时函数冷启动即失败并返回配置错误；close 日志带 code/reason，能区分握手失败与中途断链。

## 十一、超时预算拆解（60 秒函数超时的分配）

cloudbaserc.json 给 generate-tts 60 秒，链路耗时构成（逐段估算，施工后以日志实测校准）：TLS+WSS 握手 0.3-0.8 秒（首连含 DNS 解析）；run-task 到 task-started 往返 0.2-0.5 秒；CosyVoice 合成时长与音频时长同量级（实时率以实测为准）约 10-16 秒；上传 40-96KB 音频到 CloudBase 0.5-2 秒；checkCache、saveCache、updateAlertAudioUrl 三次存储往返合计 1-3 秒（未做单例改造时更差，见 4.2）。正常单条合计 13-23 秒，60 秒裕量充足。真正吃满超时的形态是同一实例被上游批量灌入 10 条串行执行——按 4.1 的降并发改造后单实例 60 秒内最多完成 3-4 条，其余靠多实例分摊，这正是上游按 10 条截断并用 allSettled 的设计边界（fetch-tushare-data/index.js:595、611-626）。若未来要提量，优先做连接复用而不是加函数超时。

## 十二、成本与容量估算（估算值，供预算参考）

假设前提均为估算：信号卡每交易日 0-10 条（上游截断 10），每条播报文本约 40-60 字；按语速 0.9 折算音频约 10-16 秒，mp3 16000Hz 单声道按 32-48kbps 估体积 40-96KB。日新增音频不超过 10 个文件、月不超过 300 个；采用 fileID 方案后 alerts.json 里只是指针，不受文件数增长影响。百炼计费以控制台账单为准；代码内置的 `totalEstimated: 1000000`（generate-tts/index.js:29）是估算额度，建议与真实配额核对后改由环境变量注入。缓存的省钱效果值得实测：同一文本重复触发（定时器重叠、人工补跑）时第二次起走缓存命中（index.js:359-366），命中率取决于上游触发模式，上线后用第十一节日志字段聚合一周即可得到真实比例，再决定是否上调单条文本上限。

## 十三、与端侧 AudioPlayer 的契约对齐

端侧播放（AudioPlayer.ets:17-53）对 url 的唯一要求是 AVPlayer 能直接 prepare 的网络地址，三点对齐结论：其一，mp3 16000Hz（generate-tts/index.js:221-222）在 AVPlayer 支持面内，无需转码；其二，若按第十节采用 fileID 方案，端侧**不能**直接播 fileID，必须先换临时链接——换链应放在按需调用 generate-tts 的返回体或 get-alerts 出口统一完成，因为端侧在"零三方依赖"约束下引不了云存储 SDK，换链必须在服务端做；其三，端侧 onDone 在 completed/idle 触发、onError 在 error 事件触发（AudioPlayer.ets:29-37），5.2 的半截音频会让 onDone 正常触发而内容残缺——错误形态比报错更隐蔽，这正是 partial 必须隔离出缓存与回写的最终理由。

## 十四、日志排障字典

按"看到什么日志→去查什么"整理，全部对应现有代码路径：`TTS cache hit`（index.js:82）→ 缓存命中，无需排障但可统计命中率；`TTS cache miss`（index.js:88）→ 正常首播路径，异常高频出现说明缓存写入失败，转查 `Cache save error`（index.js:114）；`TTS WebSocket connected, sending run-task`（index.js:204）→ 握手成功，若之后长时间无 task-started，查服务端限流或 task_id 冲突；`TTS task-started, sending text`（index.js:240）→ 协议推进正常；`TTS task-finished, N audio chunks`（index.js:264）→ N 为 0 时音频为空，Buffer.concat 产出零字节文件，上游会把它当成功上传——**建议在 concat 后加 N>0 与总字节数下限校验**，零块成品是比 partial 更早暴露的坑；`TTS task-failed`（index.js:273）→ 附带完整报文，对照百炼错误码文档定位（额度、文本含违禁内容、模型名错误都在这里现形）；`TTS WebSocket timeout`（index.js:198）→ 三十秒总闸到点，结合十一节预算判断是合成慢还是挂死；`WebSocket closed with N chunks, using partial audio`（index.js:292）→ 5.2 的截断场景，出现即说明有用户会听到残音频；`updateAlertAudioUrl: alertId not found`（index.js:150）→ 上游还没把该条写进 alerts.json 就先完成了合成，时序倒挂，属链路竞态的温和形态（见 A20 篇五.4）；`DASHSCOPE_API_KEY not configured`（index.js:353）→ 部署时环境变量漏注，检查 cloudbaserc.json generate-tts 段与控制台实际配置是否一致。

## 十五、回写方案对比（6.4 的展开）

三个候选的取舍：**方案一 serverTs 比对保护**（把上游 fetch-tushare-data/index.js:518-524 的写法搬过来）——改动最小，但仍整文件覆盖，保护只降概率不除根，且每次回写仍下载-上传 200KB 级文件；**方案二 数据库单字段更新**（`db.collection('alerts').where({alertId}).update({audioUrl})`，集合化联动 A17/A20）——从根上消除覆盖语义，代价是 alerts 数据要在文件与集合间选一个事实源，属二期拓扑改造；**方案三 不回写 alerts.json，端侧合并**（generate-tts 只返回 audioUrl，由调用方或端侧自行关联）——最彻底的解耦，但端侧需缓存 alertId→audioUrl 映射、且缓存过期后映射丢失，复杂度转移到端侧，不符合"端侧零依赖轻逻辑"的适老化基调。推荐路径：立即落方案一（两行级改动），二期随集合化迁到方案二，方案三仅作记录不实施。选型原则一句话：**回写这种"支线改主线数据"的动作，保护措施必须与主写入同级，否则宁可不写**。

## 十六、部署配置核对单

部署本函数前逐项核对（依据 cloudbaserc.json generate-tts 段与代码内读取点）：①`DASHSCOPE_API_KEY` 已注入且非空（index.js:20、352 两处依赖）；②`BAILIAN_WORKSPACE_ID` 已注入（3.1 修复后缺失即拒启）；③`TCB_ENV` 与实际环境一致（index.js:24，未注入回落硬编码默认环境）；④timeout 保持 60 秒（十一节预算的前提，误配 10 秒会让长音频必然超时截断）；⑤`installDependency: true` 未被改动（ws 与 node-sdk 两依赖需在线安装）；⑥node_modules 与 package.json 声明一致（ws ^8.16.0 的次版本漂移一般安全，但升级前应跑一遍第十节验收）；⑦HTTP 访问服务路径若暴露了本函数，确认第七节的限流已配——未暴露则纯走 callFunction，鉴权面收窄到云函数网络内，输入约束（第七节）可降为 P2。核对单与第十节验收标准配合使用：核对单管部署前，验收管部署后，中间不留真空。

### 自我评估
- 正确性：4分 端点与协议结论经官方文档当日核实并明确纠正了"端点写错"的先入判断；tempFileURL 过期、额度内存态、回写竞态三项均有行号级证据；未实测项如实标注。
- 完整性：4分 覆盖调用方式、连接管理、音频流、缓存、额度、鉴权六大维度并给出 P0-P3 清单；未展开百炼错误码全表与成本核算。
- 可复用性：4分 修复片段可直接粘贴施工，优先级表可直接当工单；连接复用方案需按 4.1 的 task_id 路由注意事项二次设计。
- 字数：约4300字（正文汉字，实测统计，不含本自评）
- 使用模型：GLM-5.3-Flash
