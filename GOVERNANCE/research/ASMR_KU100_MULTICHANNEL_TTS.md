# ASMR KU100 音质参数与多声道 TTS 升级方案

> 编纂：砚坚（码道·GLM-5.2/华为云CodeArts）
> 日期：2026-09-18
> 依据：Neumann KU100 产品规格、双耳录音（Binaural Recording）技术原理、百炼 CosyVoice TTS API
> 机主指令：双声道甚至多声道化，向 ASMR KU100 音质看齐，深入参数化声音频谱

---

## 一、Neumann KU100 音质参数基准

### 1.1 KU100 产品规格

Neumann KU100 是业界标杆级人头录音（Dummy Head）麦克风，ASMR 社区广泛采用。

| 参数 | KU100 规格 | 铃语当前 | 升级目标 |
|------|-----------|---------|---------|
| **声道数** | 2（立体声/双耳） | 1（单声道） | **2（双声道/立体声）** |
| **麦克风类型** | 电容式（ omnidirectional 全向） | TTS 合成 | TTS 合成 + 双声道渲染 |
| **频率响应** | 20Hz - 20kHz（全频段） | ~20Hz - 20kHz（取决于 TTS） | 20Hz - 20kHz |
| **灵敏度** | 40 mV/Pa（高灵敏度） | N/A | 尽量提高 TTS 输出质量 |
| **动态范围** | >120 dB（专业级） | ~96 dB（MP3 16-bit） | **>110 dB（WAV 24-bit）** |
| **采样率** | 最高 192 kHz | 22050 Hz | **48000 Hz**（已升级） |
| **位深度** | 24-bit | 16-bit（MP3） | **24-bit**（WAV） |
| **信噪比** | >75 dB（A计权） | ~60 dB（MP3） | **>75 dB** |
| **HRTF** | 内置（人头几何+耳廓模拟） | 无 | **模拟 HRTF** |

### 1.2 KU100 的核心价值

KU100 的核心不是"高采样率"，而是**双耳录音（Binaural Recording）**：

```
传统单声道录音：         KU100 双耳录音：
    声源 → 麦克风           声源 → 人头左耳麦克风
                                    ↓
                           （人头遮挡+耳廓反射）
                                    ↓
                           声源 → 人头右耳麦克风
                                    ↓
                           （人头遮挡+耳廓反射）
                                    ↓
                           左右声道 = 3D 空间感知
```

**关键原理**：
- **ITD（双耳时间差）**：声波先到达近侧耳，微秒级延迟被大脑解析为方位
- **ILD（双耳强度差）**：人头遮挡使远侧耳接收到的声音更弱
- **HRTF（头部相关传递函数）**：头和耳廓的形状对声波产生频率依赖的滤波

### 1.3 ASMR 社区为何选择 KU100

| ASMR 需求 | KU100 满足方式 |
|-----------|---------------|
| 亲密感（"在耳边说话"） | 双耳录音创造"声源在头部内部"的错觉 |
| 空间定位 | ITD + ILD + HRTF = 精确3D声场 |
| 低噪音 | 电容麦克风 + 高灵敏度 = 极低底噪 |
| 全频段 | 20Hz-20kHz 无缺失 |
| 耳机回放优化 | 双耳录音天然适配耳机（不是扬声器） |

---

## 二、从单声道 TTS 到双声道/多声道 TTS

### 2.1 当前状态

百炼 CosyVoice TTS 当前输出：
- 格式：WAV（已从 MP3 升级）
- 采样率：48000 Hz（已从 22050 升级）
- 声道：**单声道**（1 channel）
- 位深度：16-bit

### 2.2 双声道升级方案

#### 方案 A：TTS 原生双声道输出（最优）

如果百炼 CosyVoice 支持双声道输出参数：

```javascript
parameters: {
  text_type: 'PlainText',
  voice: TTS_VOICE,
  format: 'wav',
  sample_rate: 48000,
  channels: 2,           // 新增：双声道
  volume: 50,
  rate: 1.0,
  pitch: 1.0,
}
```

**需验证**：百炼 CosyVoice API 是否支持 `channels` 参数。当前 API 文档未明确提及。

#### 方案 B：单声道 → 双声道 HRTF 渲染（推荐）

即使 TTS 输出单声道，我们可以在服务端通过 HRTF 处理将单声道渲染为双耳立体声：

```javascript
// 概念：单声道 TTS → HRTF 渲染 → 双声道 WAV
// 1. TTS 生成单声道 WAV
// 2. 对单声道音频应用 HRTF 滤波（模拟人头遮挡+耳廓反射）
// 3. 输出双声道 WAV，左耳和右耳有不同的频率响应和时间延迟

const hrtfLeft = loadHRTF('left', azimuth=0);   // 正前方声源的左耳 HRTF
const hrtfRight = loadHRTF('right', azimuth=0);  // 正前方声源的右耳 HRTF

// 对单声道;声道音频分别用左右 HRTF 滤波
const leftChannel = applyHRTF(monAudio, hrtfLeft);
const rightChannel = applyHRTF(monAudio, hrtfRight);

// 合成双声道 WAV
const stereoWav = combineStereo(leftChannel, rightChannel);
```

**HRTF 数据来源**：
- MIT KEMAR HRTF 数据集（公开，免费）
- CIPIC HRTF 数据库（UC Davis，公开）
- IRCAM Listen HRTF 数据库

#### 方案 C：空间音频 API（HarmonyOS 7+）

HarmonyOS 7 的空间音频能力可在端侧实时渲染：

```typescript
// AudioPlayer.ets 空间音频扩展
player.setSpatialAudioConfig({
  renderingMode: media.SpatialRenderingMode.BINAURAL,
  headTrackingEnabled: false,  // 适老化：关闭头部追踪
});
```

**限制**：需 `compatibleSdkVersion` 升级到 7.0+。

### 2.3 推荐路径

| 阶段 | 方案 | 时间 | 效果 |
|------|------|------|------|
| **Phase 2a** | 方案 B：服务端 HRTF 渲染 | 立即 | 单声道→双声道，KU100级空间感 |
| **Phase 2b** | 方案 A：TTS 原生双声道 | 需验证 API | 最高质量（无渲染损失） |
| **Phase 3** | 方案 C：端侧空间音频 | SDK 7.0+ | 端侧实时渲染，延迟最低 |

---

## 三、深入参数化声音频谱

### 3.1 TTS 频谱参数详解

百炼 CosyVoice 当前可调参数：

| 参数 | 当前值 | KU100 对标 | 调优方向 |
|------|--------|-----------|----------|
| `voice` | `longxiaochun_v3` | — | 选择更自然、更温暖的音色 |
| `format` | `wav`（已升级） | WAV | ✅ 已达标 |
| `sample_rate` | `48000`（已升级） | 48kHz+ | ✅ 已达标 |
| `volume` | 50 | — | 适老化：提高到 60-70（更响亮） |
| `rate` | 1.0 | — | 适老化：0.9（稍慢，更清晰） |
| `pitch` | 1.0 | — | 微调：0.95（稍低，更温暖） |

### 3.2 频谱参数化方案

机主要求的"深入参数化声音频谱"涉及对 TTS 输出音频的频谱进行精细控制：

#### 3.2.1 频率均衡（EQ）

```javascript
// 概念：对 TTS 输出音频应用 EQ 滤波
// 目标：模拟 KU100 的频率响应特性

// KU100 频率响应特征：
// - 20Hz-100Hz：低频轻微衰减（人头遮挡效应）
// - 100Hz-1kHz：中频平坦（语音核心频段）
// - 1kHz-5kHz：高频轻微提升（耳廓共振，ASMR 关键频段）
// - 5kHz-20kHz：高频自然衰减

const eqBands = [
  { freq: 50, gain: -2 },    // 低频轻微衰减
  { freq: 200, gain: 0 },    // 低中频平坦
  { freq: 1000, gain: 0 },   // 中频平坦（语音核心）
  { freq: 3000, gain: +2 },  // 高频轻微提升（ASMR 关键）
  { freq: 8000, gain: +1 },  // 高频细节
  { freq: 16000, gain: -3 }, // 极高频自然衰减
];
```

#### 3.2.2 动态范围控制

```javascript
// 概念：压缩动态范围，使语音更均匀清晰
// KU100 录音动态范围 >120dB，但 TTS 语音不需要这么宽

const compressor = {
  threshold: -20,    // 压缩阈值（dB）
  ratio: 3,          // 压缩比
  attack: 5,         // 启动时间（ms）
  release: 50,       // 释放时间（ms）
  makeup: +6,        // 补偿增益（dB）——适老化：更响亮
};
```

#### 3.2.3 空间感参数

```javascript
// 概念：模拟 KU100 的空间感
// 关键：HRTF + 微量混响

const spatialParams = {
  hrtfAzimuth: 0,        // 声源方位角（0=正前方）
  hrtfElevation: 0,      // 声源仰角（0=水平面）
  reverbAmount: 0.05,    // 微量混响（5%）——模拟房间感
  reverbDecay: 0.3,      // 混响衰减时间（秒）
  stereoWidth: 0.8,      // 立体声宽度（80%）
};
```

### 3.3 参数化频谱处理流程

```
TTS 单声道 WAV
    ↓
┌─────────────────────────────────┐
│ 1. EQ 滤波（频率均衡）          │
│    → 模拟 KU100 频率响应        │
├─────────────────────────────────┤
│ 2. 动态压缩（响度均匀化）       │
│    → 适老化：更响亮、更清晰     │
├─────────────────────────────────┤
│ 3. HRTF 渲染（单声道→双声道）   │
│    → 模拟 KU100 双耳空间感      │
├─────────────────────────────────┤
│ 4. 微量混响（房间感）           │
│    → ASMR 亲密感                │
├─────────────────────────────────┤
│ 5. 输出双声道 WAV 48kHz/24-bit  │
│    → Hi-Fi 无损品质             │
└─────────────────────────────────┘
```

### 3.4 服务端实现方案

在 `feed-server/server.mjs` 中增加音频后处理模块：

```javascript
// 概念：audio-postprocess.mjs
// 对 TTS 输出的单声道 WAV 进行频谱参数化处理

import { spawn } from 'child_process';

async function postProcessAudio(inputWavPath, outputWavPath) {
  // 使用 FFmpeg 进行音频后处理（如果可用）
  // 或者使用 Node.js 的音频处理库

  // 步骤1：EQ 滤波
  // 步骤2：动态压缩
  // 步骤3：HRTF 渲染（单声道→双声道）
  // 步骤4：微量混响
  // 步骤5：输出双声道 WAV 48kHz/24-bit
}
```

**注意**：纯 ArkTS 零三方依赖的约束仅适用于鸿蒙端侧，服务端可以使用 FFmpeg 等工具。

---

## 四、KU100 对标参数总表

| 维度 | KU100 基准 | 铃语 Phase 2 当前 | 铃语 Phase 2a 目标 | 实现方式 |
|------|-----------|------------------|-------------------|----------|
| 声道 | 2（双耳） | 1（单声道） | **2（HRTF 渲染）** | 服务端 HRTF 处理 |
| 采样率 | 192kHz | 48kHz | 48kHz | 已达标 |
| 位深度 | 24-bit | 16-bit | **24-bit** | TTS 参数调整 |
| 频率响应 | 20Hz-20kHz | ~20Hz-20kHz | 20Hz-20kHz + EQ | EQ 滤波 |
| 动态范围 | >120dB | ~96dB | **>110dB** | 24-bit + 压缩 |
| 空间感 | HRTF（人头+耳廓） | 无 | **HRTF 渲染** | MIT KEMAR 数据集 |
| 信噪比 | >75dB | ~60dB | **>75dB** | 24-bit + 降噪 |
| 音色 | 自然电容麦克风 | TTS 合成 | TTS + EQ 暖化 | pitch 微调 + EQ |
| 响度 | 自然 | volume=50 | **volume=65** | 适老化调高 |
| 语速 | 自然 | rate=1.0 | **rate=0.9** | 适老化调慢 |

---

## 五、实施路线图

| 阶段 | 任务 | 优先级 | 依赖 |
|------|------|--------|------|
| **2a.1** | TTS 位深度升级 16-bit → 24-bit | 🔴 | 验证百炼 API 支持 |
| **2a.2** | 服务端 HRTF 渲染模块（单声道→双声道） | 🔴 | MIT KEMAR HRTF 数据集 |
| **2a.3** | EQ 滤波模块（模拟 KU100 频率响应） | 🟠 | FFmpeg 或 Node.js 音频库 |
| **2a.4** | 动态压缩模块（适老化响度均匀化） | 🟠 | 同上 |
| **2a.5** | 微量混响模块（ASMR 亲密感） | 🟡 | 同上 |
| **2b** | 验证百炼 CosyVoice 双声道原生支持 | 🟡 | API 文档/实测 |
| **3** | 端侧空间音频（HarmonyOS 7+） | 🟢 | SDK 7.0+ |

---

## 六、与 Hi-Fi 路线的协同

| Hi-Fi 维度 | Phase 2 当前 | Phase 2a KU100 对标 | 协同关系 |
|-----------|-------------|---------------------|----------|
| 格式 | WAV | WAV 24-bit | 位深度升级 |
| 采样率 | 48kHz | 48kHz | 已达标 |
| 声道 | 单声道 | 双声道（HRTF） | **新增维度** |
| 频谱 | 未控制 | EQ 参数化 | **新增维度** |
| 空间感 | 无 | HRTF + 混响 | **新增维度** |
| 响度 | volume=50 | volume=65 + 压缩 | 适老化协同 |
| 语速 | rate=1.0 | rate=0.9 | 适老化协同 |

---

*本方案基于 Neumann KU100 产品规格、双耳录音技术原理和百炼 CosyVoice TTS API。KU100 的核心价值不是"高采样率"，而是双耳录音创造的 3D 空间感知——通过 HRTF 渲染，我们可以在服务端将单声道 TTS 升级为 KU100 级别的双耳立体声。*