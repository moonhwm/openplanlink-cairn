---
name: 百炼CosyVoice TTS
description: 阿里云百炼CosyVoice语音合成服务，WebSocket协议
type: project-knowledge
category: external_dependency
---

# 百炼CosyVoice TTS

## 用途

服务端（feed-server）调用阿里云百炼CosyVoice语音合成服务，将异动白话标题和详情合成为WAV音频流，供端侧App点按播报。

## 版本与配置

- **模型**：cosyvoice-v3-flash
- **音色**：longxiaochun_v3
- **协议**：WebSocket（wss://...maas.aliyuncs.com/api-ws/v1/inference）
- **工作空间**：ws-ay6o8osb22o9dc3t

## 适老化TTS参数

| 参数 | 值 | 说明 |
|------|-----|------|
| format | wav | 无损格式（Phase 2 Hi-Fi升级） |
| sample_rate | 48000 | 专业品质采样率（Phase 2 Hi-Fi升级） |
| volume | 65 | 适老化响度提升（50→65） |
| rate | 0.9 | 适老化语速放缓（1.0→0.9） |
| pitch | 0.95 | 音色暖化（1.0→0.95） |

## WebSocket交互流程

1. 建立WebSocket连接（Bearer Token认证）
2. 发送run-task事件（设置模型、音色、格式等参数）
3. 等待task-started事件
4. 发送continue-task事件（待合成文本）+ finish-task事件
5. 接收result-generated事件 + binary音频帧
6. 接收task-finished事件
7. 关闭连接

## 凭据管理

- API Key从环境变量`DASHSCOPE_API_KEY`读取
- 或从金库文件读取（支持AES-256-GCM加密版本`.enc`）
- 凭据隔离三铁律：凭据本体永不进总线/聊天/日志，只登记位置与指纹

## 缓存策略

- TTS音频缓存到`feed-server/data/tts-cache/{alertId}.wav`
- 同一alertId的音频只生成一次，后续直接返回缓存URL
- 缓存URL格式：`http(s)://127.0.0.1:8000/audio/{alertId}.wav`

## 后处理

TTS生成的单声道WAV经过audio-postprocess.mjs的HRTF后处理升级为双声道立体声（EQ滤波+动态压缩+HRTF渲染+微量混响）。FFmpeg不可用时回退为单声道。