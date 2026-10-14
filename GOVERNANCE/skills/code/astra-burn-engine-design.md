---
name: ChatGPT-6Astra额度燃烧引擎设计
description: 在OpenAI小时限制(RPM/TPM)约束下自适应节流消耗额度，模型分3档(旗舰/主力/填缝)，429熔断+降速，金融线数据禁入
type: code
---

# ChatGPT-6Astra 额度燃烧引擎设计

## 适用场景

当 OpenAI 额度充值后，需要在小时限制（RPM/TPM）约束下平稳消耗额度，优先完成高价值公开信息类总装任务。

## 核心架构

### 1. 模型分档

| 档位 | 模型 | 并发 | RPM目标 | 用途 |
|---|---|---|---|---|
| 旗舰 | gpt-6-astra/luna/sol | 1 | 10 | 少量高价值总装任务 |
| 主力 | gpt-5~5.6 | 4 | 30 | 燃烧ChatGPT5×额度 |
| 填缝 | gpt-5-nano/4o-mini | 8 | 60 | 打磨/通译/去重 |

### 2. 自适应令牌桶

- 成功 → RPM +2（升速）
- 429 → RPM -5（降速，降幅更大）
- 连续3次429 → 熔断暂停60s → 重启从MIN_RPM=5开始
- RPM范围：5~60

### 3. 429 vs 402 区分

OpenAI 的 429 可能是限流也可能是余额不足（insufficient_quota/credit_balance_exhausted）。必须检查 body 内容区分：
- body含"no credits"/"insufficient_quota"/"credit_balance" → 402_no_credits（停止燃烧）
- 否则 → 429_rate_limit（降速继续）

**关键细节**：body截断200字符可能丢失关键词，需检查"no credits"（出现在message字段前200字符内）。

### 4. 红线

- 金融线数据禁入请求（行情/持仓/策略信号）
- 仅OpenAI官方端点（api.openai.com），中转站=红线零容忍
- 凭据只从金库读，不回显、不落日志
- ChatGPT-6Astra仅为外脑，不代权、不代签、不命名

## 当前状态

余额0（credit_balance_exhausted），126模型可用但无法调用。脚本已就绪，等充值后即可运行。

## 工具文件

- `astra_burn_engine.py` — 额度燃烧引擎（自适应令牌桶+熔断+3档模型）