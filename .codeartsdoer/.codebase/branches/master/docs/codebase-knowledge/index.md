# 铃语（StockPulse）模块树导航

> 代码仓内容知识 — 按模块树组织，描述每个模块提供什么能力及如何组织。

## 模块树

```
harmony-app/
├── 入口能力（EntryAbility）         — 应用入口、Push/Settings初始化、通知拉起、小艺A2A
├── 主页面（Index）                  — 大字异动卡片流、点卡即听、轮询兜底
├── 设置页面（Settings）             — 自选股/播报开关/字体档/显示模式/免打扰
├── 轮询服务（AlertPoller）          — 前台5s轮询、退避策略、429限流处理
├── 音频播放服务（AudioPlayer）      — AVPlayer云端TTS音频流播放
├── 推送服务（PushService）          — Push Kit封装、AGC降级、Token上报
├── 设置服务（SettingsService）      — Preferences持久化、全量设置项管理
├── 数据契约（AlertItem）            — AlertItem/AlertFeed接口定义
├── 数据管道服务器（feed-server）    — 异动检测、TTS生成、HTTP服务
├── 音频后处理模块（audio-postprocess） — HRTF渲染、EQ滤波、动态压缩
```

## 模块文档列表

| 模块 | 文档 | 核心职责 |
|------|------|---------|
| 入口能力 | [入口能力（EntryAbility）.md](入口能力（EntryAbility）.md) | 应用生命周期入口，Push Kit与Settings初始化，通知点击带alertId拉起定位，小艺A2A语音助手接入 |
| 主页面 | [主页面（Index）.md](主页面（Index）.md) | 大字白话卡片流主界面，点卡即听交互，5s前台轮询，适老化布局，自选股过滤 |
| 设置页面 | [设置页面（Settings）.md](设置页面（Settings）.md) | 设置页UI——自选股增删、播报开关、字体档、显示模式、免打扰时段、数据源地址 |
| 轮询服务 | [轮询服务（AlertPoller）.md](轮询服务（AlertPoller）.md) | 前台轮询兜底，退避策略（失败翻倍封顶30s），429限流静默跳过 |
| 音频播放 | [音频播放服务（AudioPlayer）.md](音频播放服务（AudioPlayer）.md) | AVPlayer播放云端TTS音频流，prepare/play错误回调与清理 |
| 推送服务 | [推送服务（PushService）.md](推送服务（PushService）.md) | Push Kit集成封装，AGC未配置时自动降级轮询，Token获取与上报 |
| 设置服务 | [设置服务（SettingsService）.md](设置服务（SettingsService）.md) | Preferences持久化封装，管理自选股/播报/字体/主题/免打扰/已读/历史 |
| 数据契约 | [数据契约（AlertItem）.md](数据契约（AlertItem）.md) | AlertItem与AlertFeed接口定义，fact/signal区分 |
| 数据管道 | [数据管道服务器（feed-server）.md](数据管道服务器（feed-server）.md) | Node.js HTTP服务，westock-data数据获取，异动检测，百炼TTS生成 |
| 音频后处理 | [音频后处理模块（audio-postprocess）.md](音频后处理模块（audio-postprocess）.md) | FFmpeg音频后处理：EQ滤波+动态压缩+HRTF渲染+微量混响→双声道WAV |