---
name: 音频播放服务（AudioPlayer）
description: AVPlayer播放云端TTS音频流，prepare/play错误回调与清理
type: codebase-module
module: services/audioplayer
source_files:
  - entry/src/main/ets/services/AudioPlayer.ets
---

# 音频播放服务（AudioPlayer）

## 概述

提供云端TTS音频流点按播报能力。适老化核心交互——点卡片即听。使用AVPlayer播放远程音频URL，支持播放完成回调(onDone)和播放出错回调(onError)，prepare/play失败时清理半初始化的player防止资源泄漏。

## 架构设计

`AudioPlayer`为纯静态类，持有单个`media.AVPlayer`实例（单例模式，同时只播放一个音频）。

`play(url, onDone?, onError?)`流程：
1. 先调用`stop()`清理上一个player
2. `media.createAVPlayer()`创建新player
3. 注册`stateChange`事件监听（completed/idle状态触发onDone）
4. 注册`error`事件监听（触发onError）
5. 设置`av.url = url`
6. `prepare()` + `play()`（任一失败则清理+onError+rethrow）

`stop()`流程：stop + release + player=null，catch忽略重复释放错误。

关键设计：prepare/play失败时先`release()`清理半初始化的player，再置null，再调onError，再throw——确保不会留下不可控的player实例。

## 技术栈

- @kit.MediaKit（media.AVPlayer）
- @kit.PerformanceAnalysisKit（hilog）

## 编码规范

- 日志TAG格式：`StockPulse.AudioPlayer`，DOMAIN=0x0001
- 单例player：同时只播放一个音频，新播放自动停止旧播放
- 错误清理：prepare/play reject时release+null+onError+rethrow
- stop()的catch块忽略重复释放错误（幂等）

## 配置与命令

- 无可配置参数，纯行为类
- 音频URL由AlertItem.audioUrl提供（服务端TTS生成）

## 关系

- 被依赖 ← Index.ets（togglePlay调用play/stop）
- 依赖 → @kit.MediaKit（AVPlayer）