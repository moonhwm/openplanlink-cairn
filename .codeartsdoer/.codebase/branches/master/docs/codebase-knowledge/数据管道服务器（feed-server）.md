---
name: 数据管道服务器（feed-server）
description: Node.js HTTP服务，westock-data数据获取，异动检测，百炼TTS生成
type: codebase-module
module: feed-server
source_files:
  - feed-server/server.mjs
---

# 数据管道服务器（feed-server）

## 概述

提供铃语App的数据管道服务能力。从westock-data（腾讯自选股）获取热搜股票数据，筛选涨跌幅≥5%的异动，生成白话标题和详情，调用百炼CosyVoice TTS生成语音音频，以AlertFeed JSON格式通过HTTP接口供App轮询消费。

## 架构设计

Node.js HTTP/HTTPS服务器，端口8000。核心数据链路：

```
westock-data CLI → 热搜股票 → 分时数据 → 异动筛选(≥5%) → 白话标题 → 百炼TTS → AlertItem → AlertFeed JSON
```

主要函数：
- `fetchHotStocks()` — 调用`westock-data-clawhub` CLI获取热搜股票，解析Markdown表格
- `fetchMinuteData(code)` — 获取个股分时数据
- `detectAlerts()` — 筛选异动（涨跌幅≥THRESHOLD），生成AlertItem（含TTS音频URL）
- `generateTTS(headline, detail, alertId)` — 百炼CosyVoice WebSocket TTS生成语音
- `refresh()` — 定时刷新缓存数据（30s间隔）

HTTP端点：
- `GET /api/alerts/latest?limit=N` — 返回AlertFeed JSON
- `GET /health` — 健康检查
- `GET /audio/{alertId}.wav` — TTS音频文件

TTS流程（百炼CosyVoice WebSocket协议）：
1. 建立WebSocket连接（wss://...maas.aliyuncs.com）
2. 发送run-task事件（设置模型cosyvoice-v3-flash、音色longxiaochun_v3、格式wav、采样率48000）
3. 等待task-started事件
4. 发送continue-task事件（待合成文本）+ finish-task事件
5. 接收binary音频帧
6. 接收task-finished事件
7. HRTF后处理（audio-postprocess.mjs）
8. 缓存到data/tts-cache/

凭据管理：百炼API Key从环境变量`DASHSCOPE_API_KEY`或金库文件读取（支持AES-256-GCM加密版本`.enc`）。

HTTPS支持：环境变量`FEED_SERVER_HTTPS=1` + 证书文件存在时启用HTTPS，否则降级HTTP。

## 技术栈

- Node.js v22（内置WebSocket）
- node:http / node:https
- node:crypto（sha256生成alertId，AES-256-GCM解密金库）
- node:child_process（exec westock-data CLI）
- 百炼CosyVoice TTS（WebSocket协议）
- westock-data-clawhub@1.0.4（腾讯自选股数据）

## 编码规范

- alertId使用sha256[:12]（Phase 0加固从md5升级）
- TTS缓存文件格式.wav（Phase 2 Hi-Fi从mp3升级）
- TTS参数：volume=65（适老化响度）、rate=0.9（适老化语速放缓）、pitch=0.95（音色暖化）
- 凭据隔离：API Key不硬编码，从环境变量或加密金库读取
- HTTP响应包含CORS头（允许跨域请求）

## 配置与命令

- PORT=8000
- THRESHOLD=5.0（涨跌幅绝对值阈值%）
- REFRESH_INTERVAL=30000ms
- TTS_MODEL=cosyvoice-v3-flash, TTS_VOICE=longxiaochun_v3
- TTS参数：format=wav, sample_rate=48000, volume=65, rate=0.9, pitch=0.95
- 启动：`node feed-server/server.mjs`
- HTTPS启用：`FEED_SERVER_HTTPS=1 node feed-server/server.mjs`

## 关系

- 依赖 → audio-postprocess.mjs（HRTF后处理）
- 依赖 → westock-data-clawhub（数据源）
- 依赖 → 百炼CosyVoice TTS（语音合成）
- 被依赖 ← AlertPoller（App轮询消费AlertFeed JSON）
- 凭据 → GOVERNANCE/credentials/aliyun_bailian.json（.enc加密版本）