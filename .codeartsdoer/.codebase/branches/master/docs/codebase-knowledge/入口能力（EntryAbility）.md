---
name: 入口能力（EntryAbility）
description: 应用生命周期入口，Push Kit与Settings初始化，通知点击带alertId拉起定位，小艺A2A语音助手接入
type: codebase-module
module: entryability
source_files:
  - entry/src/main/ets/entryability/EntryAbility.ets
---

# 入口能力（EntryAbility）

## 概述

提供应用启动与生命周期管理能力。负责在应用启动时初始化Push Kit和Settings持久化服务，处理通知点击拉起（携带alertId定位异动卡片并自动播报），以及小艺语音助手的A2A请求接入。是应用与系统、推送服务、语音助手之间的唯一入口协调点。

## 架构设计

`EntryAbility`继承`UIAbility`，作为Stage模型的入口Ability。核心设计为"三入口模式"：

- **onCreate**（冷启动）：初始化PushService和SettingsService，补检want参数中的alertId（冷启动通知缺口修复），注册Push场景化消息接收器
- **onNewWant**（热启动/通知点击）：处理alertId拉起定位，处理小艺A2A的三种action（QUERY_ALERTS/DETAIL_ALERT/PLAY_AUDIO）
- **onWindowStageCreate**：加载pages/Index作为主页面

alertId通过`AppStorage.setOrCreate('pendingAlertId', alertId)`传递给Index页面，Index在`aboutToAppear`/`onPageShow`时检查并自动播报。

小艺A2A接入通过module.json5的skills声明三个自定义action，onNewWant中根据action类型设置不同的AppStorage标志。

## 技术栈

- HarmonyOS Stage模型（UIAbility）
- @kit.AbilityKit（AbilityConstant, UIAbility, Want）
- @kit.PushKit（pushService, pushCommon）
- @kit.ArkUI（window）
- @kit.PerformanceAnalysisKit（hilog）

## 编码规范

- 日志TAG格式：`StockPulse.EntryAbility`，DOMAIN=0x0001
- Push初始化失败时静默降级（catch + hilog.warn），不阻塞主流程
- Settings初始化失败时同样静默降级
- want参数访问使用可选链`want?.parameters?.alertId`，类型断言`as string | undefined`
- AppStorage作为跨Ability/页面通信通道

## 配置与命令

- module.json5中声明三个skills：系统home、push.listener、小艺A2A自定义action
- KEEP_BACKGROUND_RUNNING权限为R3推送播报预留（当前未实际调用对应API）
- 通知自分类（SUBSCRIPTION）待AGC平台P5审批通过后启用

## 关系

- 依赖 → PushService（Push Kit初始化）、SettingsService（Preferences初始化）
- 被依赖 ← Index.ets（通过AppStorage读取pendingAlertId）
- 通信 → AppStorage（pendingAlertId、xiaoYiQuery、autoPlay标志）
- 配置 ← module.json5（skills声明、权限申请）