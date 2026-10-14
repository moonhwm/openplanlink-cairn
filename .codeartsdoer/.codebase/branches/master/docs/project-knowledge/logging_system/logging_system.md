---
name: 日志系统
description: hilog统一日志框架、TAG/DOMAIN约定
type: project-knowledge
category: logging_system
---

# 日志系统

## 日志框架

项目统一使用HarmonyOS官方`hilog`日志框架（@kit.PerformanceAnalysisKit），无第三方日志库。

## TAG/DOMAIN约定

所有模块使用统一的DOMAIN和模块化TAG：

| 模块 | TAG | DOMAIN |
|------|-----|--------|
| EntryAbility | StockPulse.EntryAbility | 0x0001 |
| Index | StockPulse.Index | 0x0001 |
| Settings | StockPulse.Settings | 0x0001 |
| AlertPoller | StockPulse.AlertPoller | 0x0001 |
| AudioPlayer | StockPulse.AudioPlayer | 0x0001 |
| PushService | StockPulse.PushService | 0x0001 |
| SettingsService | StockPulse.SettingsService | 0x0001 |

**约定**：
- TAG格式：`StockPulse.<ModuleName>`
- DOMAIN统一为0x0001
- 所有模块在文件顶部定义`const TAG`和`const DOMAIN`

## 日志级别使用

- `hilog.info` — 正常流程节点（初始化成功、数据刷新等）
- `hilog.warn` — 非致命异常（网络失败、降级、重试等）
- `hilog.error` — 致命错误（loadContent失败等）

## feed-server日志

feed-server使用`console.log/warn/error`（Node.js标准输出），前缀格式`[feed-server]`或`[audio-postprocess]`。