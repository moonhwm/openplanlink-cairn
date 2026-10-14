---
name: 推送服务（PushService）
description: Push Kit集成封装，AGC未配置时自动降级轮询，Token获取与上报
type: codebase-module
module: services/pushservice
source_files:
  - entry/src/main/ets/services/PushService.ets
---

# 推送服务（PushService）

## 概述

提供Push Kit集成封装能力。AGC配置到位时自动获取Push Token并上报X服务器；AGC未配置时（agconnect-services.json缺失）静默降级为仅日志模式，前台轮询（AlertPoller）兜底。Token获取失败时按错误码判断是否重试（最多3次，间隔1s）。

## 架构设计

`PushService`为纯静态类。核心流程：

- `init(context)` → `probeAgcConfig(context)`检测agconnect-services.json是否存在 → 存在则`fetchToken()` → 不存在则静默降级
- `fetchToken()` → `pushService.getToken()` → 成功则`reportToken(token)` → 失败则`handleTokenRetry(errorCode)`
- `handleTokenRetry(errorCode)` → 可重试错误码且未超过3次则setTimeout 1s后重试
- `reportToken(token)` → POST到`/api/push/register`，失败仅记日志不影响主流程

可重试错误码：1000900001, 1000900008, 1000900009, 1000900011（官方文档定义）。

AGC配置探测：通过`context.resourceManager.getRawFileContentSync('agconnect-services.json')`检测文件是否存在且非空。

## 技术栈

- @kit.PushKit（pushService）
- @kit.BasicServicesKit（BusinessError）
- @kit.NetworkKit（http）
- @kit.AbilityKit（common）
- @kit.PerformanceAnalysisKit（hilog）

## 编码规范

- 日志TAG格式：`StockPulse.PushService`，DOMAIN=0x0001
- AGC未配置时静默降级（hilog.info + return），不抛异常
- Token上报失败仅记日志，不影响App主流程
- 重试逻辑：可重试错误码 + retryCount < 3 + setTimeout 1s
- 凭据隔离：API Key从环境变量或金库文件读取，不硬编码

## 配置与命令

- TOKEN_REPORT_URL=http://127.0.0.1:8000/api/push/register（待X服务器落地后替换）
- RETRYABLE_ERROR_CODES=[1000900001, 1000900008, 1000900009, 1000900011]
- MAX_RETRY_COUNT=3, RETRY_INTERVAL=1000ms
- AGC配置文件位置：AppScope/resources/rawfile/agconnect-services.json

## 关系

- 被依赖 ← EntryAbility（onCreate调用init）
- 依赖 → @kit.PushKit（getToken）、@kit.NetworkKit（reportToken）
- 降级链 → AlertPoller（Push未实装时轮询兜底）