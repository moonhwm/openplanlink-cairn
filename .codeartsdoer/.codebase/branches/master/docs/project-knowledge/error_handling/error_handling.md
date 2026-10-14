---
name: 异常处理
description: try-catch降级模式、静默降级策略、错误回调机制
type: project-knowledge
category: error_handling
---

# 异常处理

## 异常处理模式

项目采用"静默降级"为核心异常处理策略——非致命异常不抛出、不阻塞主流程，仅记日志并降级处理。

## 降级策略

| 场景 | 降级行为 | 代码位置 |
|------|---------|---------|
| Push初始化失败 | 静默降级为轮询模式 | EntryAbility.onCreate |
| Settings初始化失败 | 静默降级，getter返回默认值 | EntryAbility.onCreate |
| 网络请求失败 | 退避策略，保留旧数据 | AlertPoller.fetchLatest |
| 429限流 | 静默跳过，不计入连接中断 | AlertPoller.fetchLatest |
| JSON解析失败 | 记原文前200字符，ok=false | AlertPoller.fetchLatest |
| 音频prepare/play失败 | 清理半初始化player，onError回调 | AudioPlayer.play |
| Preferences读写失败 | 返回默认值/静默忽略 | SettingsService所有方法 |
| Push Token获取失败 | 按错误码判断重试(最多3次) | PushService.handleTokenRetry |
| TTS生成失败 | 返回undefined，不阻塞异动生成 | feed-server generateTTS |
| HRTF后处理失败 | 回退为单声道WAV | feed-server postProcessAudio |

## 错误回调机制

`AudioPlayer.play(url, onDone?, onError?)`提供双回调模式：
- `onDone`：播放完成（completed/idle状态）
- `onError`：播放出错（AVPlayer error事件或prepare/play reject）

Index.ets中`togglePlay`使用try-catch + onDone/onError三重错误处理：
- try-catch：prepare/play reject
- onError：AVPlayer运行时错误
- onDone：正常播放完成

## 关键设计原则

- **首屏永不空白**：服务未连通时显示带"示例"字样的演示卡
- **旧数据保留**：网络失败时保留当前items不覆盖
- **资源清理**：prepare/play失败时release半初始化的player
- **幂等性**：stop()的catch忽略重复释放错误