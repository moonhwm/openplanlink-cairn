---
name: 主页面（Index）
description: 大字白话卡片流主界面，点卡即听交互，5s前台轮询，适老化布局，自选股过滤
type: codebase-module
module: pages/index
source_files:
  - entry/src/main/ets/pages/Index.ets
---

# 主页面（Index）

## 概述

提供适老化大字异动卡片流主界面能力。以"点卡即听"为核心交互——用户点击异动卡片即播放云端TTS语音播报。支持自选股过滤、已读标记、播报历史、连接中断提示、空态展示、429限流独立处理。服务未连通时显示带"示例"字样的演示卡保证首屏永不空白。

## 架构设计

`Index`为`@Entry @Component`装饰的页面组件，使用`Navigation`+`NavPathStack`管理页面栈（设置页通过`navStack.pushPath`进入）。

核心状态机：
- `loadingId`/`playingId`/`failedId`三态防连击——加载中显示"…"、播放中显示"■ 停"、失败显示红字"语音加载失败，点重试"
- `isDemoMode`+`items`双轨——示例卡与真实数据互不覆盖
- `consecutiveFailures`≥2触发`connectionBroken`连接中断提示
- `watchlist`非空时自动过滤只显示自选股

轮询采用`setTimeout`递归（非setInterval），支持动态退避间隔——`AlertPoller.getInterval()`在失败时翻倍封顶30s，成功后复位5s。

字体档驱动：`fontLevel='large'`时所有字号增大（标题40fp、卡片标题34fp、正文34fp），适老化模式驱动布局间距增大。

主题颜色通过`SettingsService.getThemeColors(themeMode)`获取，夜间/白天双配色方案。

## 技术栈

- ArkUI声明式组件（@Entry, @Component, @State）
- Navigation + NavPathStack（页面栈管理）
- @kit.PerformanceAnalysisKit（hilog）

## 编码规范

- 日志TAG格式：`StockPulse.Index`，DOMAIN=0x0001
- DEMO_ITEMS明确标注"示例"字样，不产生误导
- 播报开关关闭/免打扰时段时自动播报静默跳过，手动点击不受限
- 刷新后旧alertId被撤下时停止播放并复位（防止播放已失效的音频）
- aboutToDisappear清理timer和AudioPlayer
- 禁止引入K线图/走势图等复杂图表组件（AGENTS.md硬约束）

## 配置与命令

- DEMO_ITEMS为内置示例数据，服务接通后自动替换
- 字体档通过getter动态计算：titleSize/cardTitleSize/headlineSize/detailSize/statusSize/playBtnSize/badgeSize
- 适老化模式通过getter动态计算间距：cardSpace/cardPadding/cardInnerSpace/topBarPadding/listSidePadding

## 关系

- 依赖 → AlertPoller（轮询获取数据）、AudioPlayer（播放音频）、SettingsService（读取配置）、AlertItem（数据模型）
- 依赖 → Settings（设置页面组件，通过Navigation跳转）
- 通信 ← AppStorage（pendingAlertId、xiaoYiQuery、autoPlay）
- 被依赖 ← EntryAbility（通过loadContent加载）