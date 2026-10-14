---
name: HarmonyOS Kits
description: @kit.PushKit、@kit.MediaKit、@kit.NetworkKit等官方Kit使用说明
type: project-knowledge
category: external_dependency
---

# HarmonyOS Kits

项目端侧代码仅使用HarmonyOS官方Kits，不引入任何第三方依赖。

## Kit使用详情

### @kit.AbilityKit
- **用途**：应用生命周期管理（UIAbility）、Want参数传递、AbilityContext
- **核心API**：UIAbility, AbilityConstant, Want, common.UIAbilityContext
- **使用模块**：EntryAbility（UIAbility继承）、PushService（common.UIAbilityContext）、SettingsService（common.UIAbilityContext）

### @kit.ArkUI
- **用途**：声明式UI框架、窗口管理
- **核心API**：window.WindowStage, @Entry, @Component, @State, Navigation, NavPathStack, List, Text, Button, Toggle等
- **使用模块**：EntryAbility（windowStage）、Index（全部UI）、Settings（全部UI）

### @kit.ArkData
- **用途**：Preferences轻量级数据持久化
- **核心API**：preferences.getPreferences, preferences.Preferences
- **使用模块**：SettingsService（全量设置项持久化）

### @kit.NetworkKit
- **用途**：HTTP网络请求
- **核心API**：http.createHttp, http.RequestMethod.GET/POST
- **使用模块**：AlertPoller（轮询获取异动数据）、PushService（上报Push Token）

### @kit.MediaKit
- **用途**：音频播放
- **核心API**：media.createAVPlayer, media.AVPlayer
- **使用模块**：AudioPlayer（云端TTS音频流播放）

### @kit.PushKit
- **用途**：Push推送服务
- **核心API**：pushService.getToken, pushService.receiveMessage, pushCommon.PushPayload
- **使用模块**：EntryAbility（场景化消息接收器）、PushService（Token获取与上报）

### @kit.BasicServicesKit
- **用途**：基础服务错误类型
- **核心API**：BusinessError
- **使用模块**：EntryAbility、PushService（错误码处理）

### @kit.PerformanceAnalysisKit
- **用途**：日志输出
- **核心API**：hilog.info/warn/error
- **使用模块**：全部模块（统一日志框架）