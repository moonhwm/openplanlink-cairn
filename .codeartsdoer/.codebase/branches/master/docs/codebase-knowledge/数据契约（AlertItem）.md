---
name: 数据契约（AlertItem）
description: AlertItem与AlertFeed接口定义，fact/signal区分
type: codebase-module
module: model/alertitem
source_files:
  - entry/src/main/ets/model/AlertItem.ets
---

# 数据契约（AlertItem）

## 概述

提供异动条目与数据流的接口契约定义。AlertItem描述单条异动（客观事实或自家策略信号），AlertFeed描述服务端返回的异动列表。此契约为端侧App与服务端（X服务器/feed-server）之间的数据交换格式，是跨仓协作的接口边界。

## 架构设计

`AlertItem`接口字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| alertId | string | 唯一ID，通知点击回传定位用 |
| ts | number | 秒级时间戳 |
| symbol | string | 股票代码（如600176） |
| name | string | 股票名称（如中国巨石） |
| direction | 'up'\|'down'\|'flat' | 涨跌方向 |
| kind | 'fact'\|'signal' | 缺省按fact处理 |
| headline | string | 一句话白话结论 |
| detail | string | 补充事实（量能、价位） |
| audioUrl | string | 云端TTS音频流地址，无则不显示播报钮 |

`AlertFeed`接口字段：`items: AlertItem[]` + `serverTs: number`。

`kind`字段语义：
- `fact`：客观异动事实（涨跌幅/量能/价格穿越），由服务端westock-data数据驱动
- `signal`：自家策略信号与白话解读，须带`kind: "signal"`标记，UI上加"自家信号"角标

信号松绑约束（AGENTS.md §二.2）：允许输出自家策略信号，但禁止三条：①承诺收益/保本等绝对化措辞；②催促性强指令；③任何对外公开/收费形态。

## 技术栈

- ArkTS interface（纯类型定义，无运行时代码）

## 编码规范

- `kind`字段可选，缺省按`fact`处理（向后兼容）
- `audioUrl`可选，无则不显示播报钮
- `direction`三值枚举：up/down/flat
- 此文件为跨仓接口边界，修改须先在CHANGELOG.md写明意图并停机主确认

## 配置与命令

- 无可配置参数，纯接口定义

## 关系

- 被依赖 ← Index.ets（items类型）、AlertPoller（PollResult.items类型）、Settings.ets（无直接依赖但间接通过Index）
- 被依赖 ← feed-server/server.mjs（服务端生成AlertItem JSON）
- 接口边界 → AGENTS.md定义的分区主权边界