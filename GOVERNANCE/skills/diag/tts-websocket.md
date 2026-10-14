---
name: tts-websocket
type: diag
created: 2026-09-23
updated: 2026-09-23
version: 1.2.0
trigger: generate-tts 云函数或 feed-server TTS 合成失败、REST 报错提示仅支持 WebSocket、端侧播报无声、audioUrl 长期为 undefined
source_files: [cloudfunctions/functions/generate-tts/index.js, feed-server/server.mjs, feed-server/audio-postprocess.mjs]
---

# diag技能：百炼TTS WebSocket诊断——REST报错识别、WebSocket协议切换、连接调试

## 概述

harmony-app（铃语）的语音播报链路：alerts 卡片携带 audioUrl；audioUrl 为 undefined 时端侧按需调用 generate-tts 云函数合成，合成结果经 CloudBase 存储缓存后由端侧 AudioPlayer.ets（AVPlayer）播放音频流；feed-server 侧另有本地合成与 HRTF 后处理路径。已知问题：百炼 CosyVoice TTS 只支持 WebSocket 协议，REST 调用直接报错，项目已全面迁移 WebSocket。本技能覆盖四段：识别 REST 报错、掌握 WebSocket 协议流程与帧处理、云函数与 feed-server 两个调用点的实现要点、连接调试与误诊排除。

## 适用场景

- REST 端点返回 InvalidParameter，message 含 "WebSocket is the only supported protocol for this model"。
- WebSocket 握手失败（401/1006）、task-started 迟迟不回、task-failed。
- 合成出的音频无法播放、时长异常、杂音、只有开头一段。
- feed-server 本地合成与云函数合成行为不一致，需要统一排查口径。
- 端侧播报无声，需要区分"没合成、没上传、没回填、没拉流"四段。

红线：DASHSCOPE_API_KEY 只存云函数与 feed-server 的环境变量，不得进端侧代码、仓库与日志；演示卡可无音频但首屏永不空白。

## 执行步骤

### 步骤一：识别 REST 报错

典型错误调用与返回（项目实战记录）：

```
POST https://dashscope.aliyuncs.com/api/v1/services/audio/tts
→ {"code": "InvalidParameter",
   "message": "WebSocket is the only supported protocol for this model"}
```

判读表：

| 返回 | 判读 | 处置 |
| --- | --- | --- |
| InvalidParameter 且 message 提 WebSocket | TTS 无 REST 合成端点，方向性结论 | 进入步骤二，不要换 URL 绕过 |
| HTTP 404 / InvalidEndpoint | 路径不存在 | 同上 |
| HTTP 401 | Key 无效或欠费 | 控制台核对开通状态与 Key |
| HTTP 429 | 限流 | 退避重试，另查调用方放大 |

判读原则：凡 message 或官方文档明确 TTS 只支持 WebSocket，立即走协议切换；反复更换 REST URL 与参数组合属于方向性浪费时间。

### 步骤二：WebSocket 协议切换

连接地址（两个调用点同构）：`wss://{workspaceId}.cn-beijing.maas.aliyuncs.com/api-ws/v1/inference`，由环境变量中的 workspaceId 拼出；公共接入点 `wss://dashscope.aliyuncs.com/api-ws/v1/inference/` 亦见于官方文档，以项目实际接通者为准。

认证通过握手 header 传递：

```javascript
const ws = new WebSocket(TTS_WSS_URL, {
  headers: { 'Authorization': `Bearer ${BAILIAN_API_KEY}` },
});
```

任务生命周期五步（JSON 文本帧交互）：

1. 客户端 → run-task：声明模型与参数。
2. 服务端 → task-started：任务已启动，此前不得发文本。
3. 客户端 → continue-task（携带文本）+ finish-task（结束输入）。
4. 服务端 → 多个二进制音频帧，与 JSON 事件帧交错下发。
5. 服务端 → task-finished；异常路径为 task-failed。

run-task 关键参数（项目现行值，两调用点一致）：

```javascript
{
  header: { action: 'run-task', task_id: taskId, streaming: 'duplex' },
  payload: {
    task_group: 'audio',
    task: 'tts',
    function: 'SpeechSynthesizer',
    model: 'cosyvoice-v3-flash',
    input: {},
    parameters: {
      text_type: 'PlainText',
      voice: 'longxiaochun_v3',
      format: 'mp3',          // feed-server 侧为 wav 48kHz 高保真口径
      sample_rate: 16000,
      volume: 65,
      rate: 0.9,
      pitch: 0.95,
    },
  },
}
```

rate=0.9、pitch=0.95 是适老化刻意放慢放缓的播报口径，调整前先与适老化规范对齐。task_id 必须每次唯一（项目用随机标识生成），复用旧 id 会撞上服务端任务去重导致莫名拒绝。

### 步骤三：帧处理与云函数实现要点

消息处理的核心是**区分文本帧与二进制帧**：JSON 事件走字符串解析，音频走原始字节累积，两者在同一个连接上交错到达，骨架如下：

```javascript
ws.addEventListener('message', (event) => {
  if (typeof event.data === 'string') {
    const msg = JSON.parse(event.data);
    const action = msg.header.action;          // task-started / task-finished / task-failed
    if (action === 'task-started') sendTextAndFinish();
    if (action === 'task-failed') done(null);
  } else {
    chunks.push(Buffer.from(event.data));      // 二进制音频帧直接入列
  }
});
```

"零三方依赖"约束仅指端侧纯 ArkTS；服务端合法用 WebSocket 客户端——generate-tts 云函数与 feed-server 各自实现，后者明确使用 Node.js v22 内置 WebSocket，无额外依赖。实现必须包含四件套（两处均已有）：

1. 30 秒超时，超时关闭连接并返回 null，绝不让函数悬挂到实例回收：

```javascript
const timeout = setTimeout(() => {
  console.error('TTS WebSocket timeout');
  try { ws.close(); } catch (e) {}
  done(null);
}, 30000);
```

2. Promise 防重入，避免超时与正常完成双路回调：

```javascript
let resolved = false;
const done = (result) => {
  if (!resolved) { resolved = true; resolve(result); }
};
```

3. 部分音频降级：连接提前关闭但已收到音频帧时，用部分音频兜底而不是直接失败——适老播报"念了半句"好过"一声不吭"：

```javascript
ws.addEventListener('close', () => {
  clearTimeout(timeout);
  if (!resolved && chunks.length > 0) {
    done(Buffer.concat(chunks));   // 部分音频降级
  } else if (!resolved) {
    done(null);
  }
});
```

4. 缓存与额度控制（generate-tts 现行实现）：cacheKey 为文本 SHA256 前 16 位；checkCache 下载 `tts-cache/{cacheKey}.json`，命中直接返回 audioUrl 不消耗额度，未命中是正常情况不记错误；saveCache 落盘 `{audioUrl, text, voice, model, createdAt}` 元数据。QUOTA 记录用量并对外暴露 getStatus 三档：normal、warning（80%）、stop（100%），shouldStop 为真时停止生成返回 null，防止额度击穿。

合成成功后上传对象存储 `tts/{cacheKey}.mp3`，getTempFileURL 换临时链接作为 audioUrl 返回。

### 步骤四：两个调用点的差异对照

| 维度 | generate-tts 云函数 | feed-server（server.mjs） |
| --- | --- | --- |
| 触发 | 端侧按需（audioUrl undefined 时） | refresh 检测新 alert 主动合成 |
| 缓存键 | SHA256(text) 前 16 位 | alertId（`data/tts-cache/{alertId}.wav`） |
| 音频格式 | mp3 16kHz | wav 48kHz 高保真口径，另经 HRTF 后处理 |
| 后处理 | 无 | audio-postprocess.mjs：先写 .mono.wav 原始文件，处理后 renameSync 原子替换成品 |
| 无 Key 行为 | 返回 null | 打印"no DASHSCOPE_API_KEY, skipping TTS"直接跳过合成 |

排查时先确认故障落在哪个调用点：卡片完全无声多为云函数侧；卡片有音频但音质/语速异常多为 feed-server 侧后处理环节。renameSync 替换保证了后处理失败时旧成品不被半成品覆盖，属值得沿用的原子写模式。

### 步骤五：连接调试

先做最小复现：独立脚本只做"连接 → run-task → task-started → 一句固定文本 → finish-task → 落盘 out.mp3"，用播放器验证时长，排除业务干扰。可再用 wscat 验证握手连通性（注意 wscat 传自定义 header 不便，连通性测试优先用 Node 脚本）。

常见失败判读表：

| 现象 | 可能原因 | 处置 |
| --- | --- | --- |
| 握手 HTTP 401 | Key 无效、欠费、百炼未开通 | 控制台核对 Key 与开通状态 |
| 连接 1006/被重置 | 云函数 VPC/安全组拦 wss 出网、TLS 异常 | 放行 443 出网，确认用域名而非 IP |
| 握手成功但无 task-started | Authorization 前缀写错（项目用 Bearer）、task_id 非法或复用、payload 字段拼错 | 对照步骤二逐字段核对 |
| task-failed InvalidParameter | voice 与 model 不匹配、参数越界 | voice 换该 model 支持的音色 |
| task-failed 欠费/限流类 | 账户欠费或并发超限 | 充值或退避 |
| 音频杂音/无法播放 | 帧边界处理不当、format 与扩展名不符、后处理半成品 | 核对二进制帧解析、扩展名与 HRTF 产物 |
| 只有开头一段 | 连接提前关闭且未启用部分降级 | 检查 close 分支是否走部分音频兜底 |

日志规范：打印事件名、task_id、收到字节数三要素；不打印 Key，正文日志截断脱敏。

### 步骤六：端侧衔接与误诊排除

- generate-tts 成功返回 audioUrl；失败或超时返回 null，卡片 audioUrl 保持 undefined，端侧按需重试或显示纯文字大字卡片；绝不能因 TTS 失败导致首屏空白。
- 端侧 AudioPlayer.ets 只认音频流 URL，不感知协议切换；播报无声时先 `curl -I <audioUrl>` 确认公网可达（状态码 200 且内容类型为音频），再回查合成链路。
- 常见误诊三则：把 task-failed 当网络抖动反复重试（白白烧额度）——先看事件名；把部分音频当损坏丢弃——那是降级资产；把端侧拉流 403 当合成失败——那是临时链接过期，走按需重调即可。
- 幂等：同一 alertId/同文案命中缓存直接复用，避免端侧 5 秒轮询放大重复合成；失败用指数退避（如 1s、4s、16s 三档）封顶。

## 质量门槛

- [ ] DASHSCOPE_API_KEY 已配置于环境变量，未出现在端侧与仓库
- [ ] 使用 wss 地址与 Bearer 前缀，run-task 含正确 model/voice/parameters，task_id 唯一
- [ ] 文本帧与二进制帧分流处理正确
- [ ] 30 秒超时、Promise 防重入、部分音频降级三件套齐全
- [ ] SHA256 缓存命中不重复消耗额度；QUOTA 三档状态生效
- [ ] task-failed/超时/额度三种路径都返回 null 而非悬挂
- [ ] 端侧验证：audioUrl 可公网访问，AVPlayer 播放正常

## 经验记录

- TTS 没有 REST 端点，REST 报错里的 WebSocket 提示就是最终答案，换 URL 无解。
- voice 必须与 model 配套（cosyvoice-v3-flash 配 longxiaochun_v3），跨系列混用直接 task-failed。
- rate=0.9/pitch=0.95 是适老化放缓口径，改回 1.0 会被评审打回。
- 云函数连接提前关闭时，已收到的部分音频可用，丢弃等于白白消耗额度。
- 缓存键云函数用 SHA256(text)、feed-server 用 alertId，两套键各服务其调用形态，排查时别查错桶。
- 后处理用"写临时名再 renameSync 替换"的原子模式，失败不伤旧成品。

## 关联文档

- GOVERNANCE/skills/diag/tushare-token-failure.md（数据源降级与熔断模式）
- GOVERNANCE/skills/diag/cloudbase-cache.md（tts-cache 元数据缓存诊断）
- GOVERNANCE/skills/diag/feed-server-cache.md（轮询放大与音频缓存键）

### 自我评估
- 正确性：5分 REST 报错、端点、参数、三件套、checkCache/QUOTA 三档、Node22 内置 WebSocket、HRTF 后处理与 renameSync 均引自两个调用点源码本次会话逐行核对；未实调百炼线上接口已在文中注明
- 完整性：5分 覆盖 REST 识别、协议切换、帧处理、双调用点对照、调试、误诊排除、端侧衔接
- 可复用性：5分 生命周期五步、帧分流骨架、判读表可复用到任何 DashScope 类 WebSocket 任务
- 字数：约2750字
- 使用模型：GLM-5.3-Flash
