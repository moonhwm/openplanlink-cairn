---
name: 音频后处理模块（audio-postprocess）
description: FFmpeg音频后处理：EQ滤波+动态压缩+HRTF渲染+微量混响→双声道WAV
type: codebase-module
module: feed-server/audio-postprocess
source_files:
  - feed-server/audio-postprocess.mjs
---

# 音频后处理模块（audio-postprocess）

## 概述

提供单声道TTS音频升级为KU100级别双耳立体声的后处理能力。通过FFmpeg滤镜链实现EQ滤波（模拟Neumann KU100频率响应）、动态压缩（适老化响度均匀化）、HRTF渲染（单声道→双声道，模拟人头双耳效应）、微量混响（ASMR亲密感），最终输出双声道24-bit 48kHz WAV。

## 架构设计

完整处理链：`EQ滤波 → 动态压缩 → HRTF渲染 → 微量混响 → 格式输出`

各环节参数：

**EQ滤波**（模拟KU100频率响应）：
- 50Hz: -2dB（低频轻微衰减，人头遮挡效应）
- 1000Hz: 0dB（中频平坦，语音核心频段）
- 3000Hz: +2dB（高频轻微提升，耳廓共振，ASMR关键频段）
- 8000Hz: +1dB（高频细节）
- 16000Hz: -3dB（极高频自然衰减）

**动态压缩**（适老化响度均匀化）：
- threshold=-20dB, ratio=3, attack=5ms, release=50ms, makeup=+6dB

**HRTF渲染**（单声道→双声道）：
- 基于ITD（双耳时间差）和ILD（双耳强度差）计算
- 人头半径8.75cm，声速343m/s，最大ITD≈0.51ms
- azimuth=0（正前方声源），stereoWidth=0.8（80%立体声宽度）
- FFmpeg滤镜链：asplit → 左路直接通过 → 右路adelay+volume → amerge

**微量混响**（ASMR亲密感）：
- reverbAmount=0.05（5%），reverbDecay=0.3s
- aecho滤镜实现

**输出格式**：双声道，48kHz，24-bit s24le

核心函数：
- `postProcessAudio(inputPath, outputPath)` — 完整后处理
- `checkFFmpeg()` — 检测FFmpeg可用性
- `buildHRTFFilter()` — 构建HRTF FFmpeg滤镜链
- `buildEQFilter()` — 构建EQ滤波链
- `buildCompressorFilter()` — 构建动态压缩滤镜
- `buildReverbFilter()` — 构建微量混响滤镜

## 技术栈

- Node.js（ESM模块）
- FFmpeg（服务端工具，非端侧三方依赖）
- MIT KEMAR HRTF数据集（公开免费，当前未集成，使用参数化近似）

## 编码规范

- FFmpeg路径可通过`FFMPEG_PATH`环境变量配置，默认'ffmpeg'
- 后处理失败时回退为单声道（不阻塞TTS流程）
- 自测入口：`node audio-postprocess.mjs --self-test`
- 所有滤镜参数以配置常量定义（EQ_BANDS, COMPRESSOR, SPATIAL, OUTPUT_FORMAT）

## 配置与命令

- FFMPEG_PATH=process.env.FFMPEG_PATH || 'ffmpeg'
- 输出：双声道，48kHz，24-bit
- HRTF方位角=0（正前方），立体声宽度=80%
- 混响量=5%，混响衰减=0.3s
- 自测：`node feed-server/audio-postprocess.mjs --self-test`

## 关系

- 被依赖 ← feed-server/server.mjs（TTS生成后调用postProcessAudio）
- 依赖 → FFmpeg（外部工具）
- 数据源 → MIT KEMAR HRTF数据集（待集成，当前使用参数化近似）