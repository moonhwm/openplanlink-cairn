---
name: 设置页面（Settings）
description: 设置页UI——自选股增删、播报开关、字体档、显示模式、免打扰时段、数据源地址
type: codebase-module
module: pages/settings
source_files:
  - entry/src/main/ets/pages/Settings.ets
---

# 设置页面（Settings）

## 概述

提供应用全量设置项的UI交互能力。包括自选股管理（添加/删除）、播报开关、适老化模式切换、字体大小切换、显示模式（夜间/白天/自动）、免打扰时段配置、数据源地址配置。所有设置项通过SettingsService持久化，杀进程重启后恢复。

## 架构设计

`Settings`为`@Component`装饰的组件，作为NavDestination呈现（通过Index的Navigation pushPath进入）。

设置项分6个卡片区块：
1. **显示模式**：自动/夜间/白天三按钮切换，自动模式按系统时间6:00-18:00白天/18:00-6:00夜间
2. **适老化模式**：Toggle开关，开启时自动锁定特大字体
3. **免打扰**：Toggle开关+开始/结束时段调整（0-23小时加减按钮）
4. **自选股管理**：TextInput+添加按钮+列表+删除操作
5. **播报开关**：Toggle开关，关闭时主界面显示"播报关"红字提示
6. **数据源地址**：TextInput+保存按钮（默认http://127.0.0.1:8000/api/alerts/latest）

手动选择夜间/白天时自动关闭自动主题切换；开启自动主题时按系统时间计算当前模式。

## 技术栈

- ArkUI声明式组件（@Component, @State）
- NavDestination（Navigation子页面）
- @kit.PerformanceAnalysisKit（hilog）

## 编码规范

- 日志TAG格式：`StockPulse.Settings`，DOMAIN=0x0001
- 所有交互元素热区≥48vp（constraintSize minWidth/minHeight=48）
- 字体档驱动字号（与Index保持一致的计算方式）
- 主题颜色通过SettingsService.getThemeColors获取
- 返回按钮通过navStack.pop()（非router.back()）

## 配置与命令

- 默认值：播报=true、适老化=true、字体=standard、主题=night、自动主题=true、免打扰=false(22-8)、数据源=127.0.0.1:8000
- 适老化模式开启时自动设为特大字体，关闭时恢复标准字体

## 关系

- 依赖 → SettingsService（读写所有设置项）
- 被依赖 ← Index.ets（通过Navigation pushPath进入）
- 通信 → NavPathStack（页面栈pop返回）