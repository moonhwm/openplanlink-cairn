---
name: 轮询服务（AlertPoller）
description: 前台轮询兜底，退避策略（失败翻倍封顶30s），429限流静默跳过
type: codebase-module
module: services/alertpoller
source_files:
  - entry/src/main/ets/services/AlertPoller.ets
---

# 轮询服务（AlertPoller）

## 概述

提供前台轮询兜底能力。App打开期间定时拉取最新异动数据，作为Push推送的拉齐补偿。具备退避策略（失败后间隔翻倍封顶30s，成功后复位5s）、429限流静默跳过、5xx按普通失败计、JSON解析失败记原文前200字符等容错机制。

## 架构设计

`AlertPoller`为纯静态类，无实例状态。核心接口：

- `fetchLatest(limit=20): Promise<PollResult>` — 拉取最新异动
- `getInterval(): number` — 获取当前轮询间隔（供Index动态调度setTimeout）

`PollResult`接口：`ok`表示网络是否成功、`items`为异动列表、`rateLimited`标识429限流（ok=false但不计入连接中断）。

退避策略：`currentInterval`从5000ms起步，失败时`applyBackoff()`翻倍封顶30000ms，成功时`resetBackoff()`复位5000ms。

HTTP请求：5s连接超时+5s读取超时，finally中`req.destroy()`确保资源释放。

数据源地址通过`SettingsService.getFeedUrl()`获取（支持用户在设置页自定义），默认`http://127.0.0.1:8000/api/alerts/latest`。

## 技术栈

- @kit.NetworkKit（http）
- @kit.PerformanceAnalysisKit（hilog）

## 编码规范

- 日志TAG格式：`StockPulse.AlertPoller`，DOMAIN=0x0001
- 429限流：ok=false + rateLimited=true，不计入连接中断提示
- 5xx：ok=false，按普通失败计入退避
- JSON解析失败：记原文前200字符，ok=false
- 所有异常路径都调用applyBackoff()确保退避生效

## 配置与命令

- BASE_INTERVAL=5000ms（5秒）
- MAX_INTERVAL=30000ms（30秒）
- DEFAULT_FEED_URL=http://127.0.0.1:8000/api/alerts/latest
- connectTimeout=5000, readTimeout=5000

## 关系

- 依赖 → SettingsService（获取FeedUrl）、AlertItem/AlertFeed（数据模型）
- 被依赖 ← Index.ets（pollLoop调用fetchLatest，getInterval驱动setTimeout间隔）