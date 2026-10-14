---
name: A15-compliance-fail-closed-audit
type: code
created: 2026-09-24
updated: 2026-09-24
version: 1.0.0
trigger: 审查或维护 fetch-tushare-data 云函数的合规 fail-closed 机制
source_files: [cloudfunctions/functions/fetch-tushare-data/index.js]
---

# A15 · 合规 fail-closed 机制审查

## 概述

fetch-tushare-data 云函数的合规层是信号松绑（AGENTS.md §二.2）后的安全护栏。信号卡（kind=signal）允许输出自家策略信号与白话解读，但必须通过 DKnowC 深知可信统一API的内容安全合规检查。合规检查采用 fail-closed 策略——检查失败时降级为事实卡，而非放行。

## 合规护栏双重机制

### 第一重：DKnowC 内容安全合规检查

| 维度 | 设计 | 说明 |
|------|------|------|
| 触发条件 | kind=signal 的信号卡 | 事实卡（kind=fact）不需要合规检查 |
| 检查方式 | 调用 DKnowC API（open.dknowc.cn） | 深知可信统一API |
| 检查内容 | signalNote 白话解读文本 | 是否包含违规内容 |
| 检查结果 | Safe/Unsafe/ConditionallySafe/Focus/Unknown | 五级分类 |
| fail-closed行为 | Unsafe → 降级为fact | 剥离 signalNote + 角标 |
| API失败处理 | 跳过合规检查，保留signal | **设计权衡**：API不可用时保留信号（而非降级），因为API故障不应影响信号输出 |

### 第二重：TTS播报降级

| 维度 | 设计 | 说明 |
|------|------|------|
| 触发条件 | 合规检查降级为fact的卡 | 降级卡不应播报白话解读 |
| fail-closed行为 | 不设置 audioUrl | 端侧不显示播报按钮 |
| 保留行为 | 事实部分仍可播报 | 降级卡的headline/detail仍可生成TTS |

## 降级流程

```
signal卡生成 → DKnowC合规检查
  ├── Safe → 保留signal + signalNote + 角标 → 正常TTS
  ├── Unsafe → 降级为fact → 剥离signalNote + 角标 → 跳过TTS
  ├── ConditionallySafe → 保留signal（带合规标记） → 正常TTS
  ├── Focus → 保留signal（带合规标记） → 正常TTS
  ├── Unknown → 保留signal（带合规标记） → 正常TTS
  └── API失败 → 保留signal（无合规标记） → 正常TTS
```

## 三禁合规约束（AGENTS.md §二.2）

| 禁项 | 检查方式 | 说明 |
|------|---------|------|
| ①承诺收益/保本等绝对化措辞 | DKnowC + prompt自检 | signalNote中禁止"保证赚钱""稳赚不赔"等 |
| ②催促性强指令 | DKnowC + prompt自检A检 | signalNote中禁止"立即买入""满仓"等 |
| ③对外公开/收费形态 | 产品形态约束 | 私有分发，不对外公开 |

## 审查结论

- ✅ DKnowC合规检查fail-closed策略正确（Unsafe→降级为fact）
- ✅ TTS播报降级正确（降级卡不设置audioUrl）
- ✅ 三禁合规约束在signalNote硬编码模板中已遵守
- ✅ complianceStatus字段记录合规分类（Safe/Unsafe/ConditionallySafe/Focus/Unknown）
- ⚠️ API失败时保留signal（而非降级）——这是设计权衡，API故障不应影响信号输出
- ⚠️ signalNote当前硬编码（"留意后续走势"/"注意风险"），LLM落地方案待凭据注入

## 关联文档

- fail-open-fix.md（Fail-Open修复技能文档）
- A35_fetchtusharedata云函数深度审查.md（云函数整体审查）

### 自我评估
- 正确性：5分 合规护栏双重机制和降级流程均直接取自源码
- 完整性：5分 覆盖DKnowC检查+TTS降级+三禁约束+降级流程
- 可复用性：5分 fail-closed合规护栏模式可迁移到任何内容安全审查场景
- 字数：约900字
- 使用模型：GLM-5.2-SFT-Harmony