---
name: 设置服务（SettingsService）
description: Preferences持久化封装，管理自选股/播报/字体/主题/免打扰/已读/历史
type: codebase-module
module: services/settingsservice
source_files:
  - entry/src/main/ets/services/SettingsService.ets
---

# 设置服务（SettingsService）

## 概述

提供全量设置项的Preferences持久化封装能力。管理自选股列表、播报开关、字体档、适老化模式、显示模式（夜间/白天）、自动主题切换、免打扰时段、数据源地址、已读异动标记、播报历史。所有设置项通过HarmonyOS Preferences持久化，杀进程重启后恢复。

## 架构设计

`SettingsService`为纯静态类，持有单个`preferences.Preferences`实例。通过`init(context)`初始化，所有getter/setter均为异步方法。

设置项分10个维度：

| 维度 | 键名 | 类型 | 默认值 |
|------|------|------|--------|
| 自选股列表 | watchlist | JSON string[] | [] |
| 播报开关 | broadcast | boolean | true |
| 字体档 | font_level | 'standard'\|'large' | standard |
| 适老化模式 | elderly_mode | boolean | true |
| 显示模式 | theme_mode | 'night'\|'day' | night |
| 自动主题 | auto_theme | boolean | true |
| 免打扰开关 | dnd_enabled | boolean | false |
| 免打扰开始 | dnd_start | number | 22 |
| 免打扰结束 | dnd_end | number | 8 |
| 数据源地址 | feed_url | string | http://127.0.0.1:8000/api/alerts/latest |
| 已读异动 | read_alerts | JSON string[] | [] |
| 播报历史 | play_history | JSON Array | [] |

适老化模式联动字体档：开启适老化自动设为large，关闭恢复standard。

主题颜色方案：`NIGHT_COLORS`（深色底#0d1117）和`DAY_COLORS`（浅色底#f5f7fa），通过`getThemeColors(mode)`获取。

自动主题计算：`computeAutoThemeMode()`按系统时间6:00-18:00白天/18:00-6:00夜间。

免打扰判断：`isDndActive()`支持跨天时段（如22:00-8:00）和同天时段（如9:00-18:00）。

已读标记最多保留200条，播报历史最多保留50条（同一alertId只保留最新一条）。

## 技术栈

- @kit.ArkData（preferences）
- @kit.AbilityKit（common）
- @kit.PerformanceAnalysisKit（hilog）

## 编码规范

- 日志TAG格式：`StockPulse.SettingsService`，DOMAIN=0x0001
- 所有getter在pref为null时返回默认值（不抛异常）
- 所有setter在pref为null时静默返回（不抛异常）
- JSON序列化/反序列化包裹在try-catch中
- 每次put后调用flush()确保持久化

## 配置与命令

- PREF_NAME='stockpulse_settings'
- 已读标记上限200条，播报历史上限50条
- 夜间配色：pageBackground=#0d1117, cardBackground=#1c2433, textPrimary=#e8edf5, accentGold=#f0b232
- 白天配色：pageBackground=#f5f7fa, cardBackground=#ffffff, textPrimary=#1d2129, accentGold=#d4951a

## 关系

- 被依赖 ← EntryAbility（init初始化）、Index.ets（loadSettings读取）、Settings.ets（loadSettings读取+setter写入）、AlertPoller（getFeedUrl）
- 依赖 → @kit.ArkData（preferences）