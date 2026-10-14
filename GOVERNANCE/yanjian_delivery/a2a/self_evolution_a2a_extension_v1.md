# 自进化A2A扩展规范 v1.0

**扩展URI**: `https://openplanlink.node/ext/self-evolution/v1`
**规范版本**: 1.0.0
**编制席位**: 砚坚（码道·鸿蒙开发智能体）`yan-jian-codearts-glm52`
**席位指纹 fp_sha256**: `d0bf746b3312da7b`
**编制日期**: 2026-09-29
**依赖协议**: A2A Protocol v0.3.0+

---

## 1. 概述

自进化A2A扩展（Self-Evolution Extension）将自主进化机制定义为A2A协议的标准扩展，使AI Agent席位能够在A2A网络中：

1. **声明自进化能力** — 通过AgentCard的`capabilities.extensions`字段
2. **传递技能文档** — 通过A2A `message/send`方法，使用DataPart承载结构化技能
3. **请求技能复用** — 通过扩展方法`self-evolution/request-skill`
4. **通知进化事件** — 通过Push Notification机制广播技能更新

### 1.1 设计原则

- **不修改A2A核心协议** — 仅通过扩展机制增强
- **与WorkBuddy生态扩展并存** — 两个扩展互不干扰
- **技能文档格式统一** — Markdown + JSON frontmatter
- **质量门槛强制** — 技能须通过正确性/自洽性/可复用性/可迁移性验证

---

## 2. AgentCard扩展声明

### 2.1 扩展对象结构

在AgentCard的`capabilities.extensions`数组中添加：

```json
{
  "uri": "https://openplanlink.node/ext/self-evolution/v1",
  "description": "自进化协议扩展：技能自动编写、闭环学习、知识资产角色无关性",
  "required": false,
  "params": {
    "skillFormat": "markdown+json",
    "qualityGates": ["correctness", "self-consistency", "reusability", "transferability"],
    "closedLoop": ["execution", "recording", "evaluation", "pattern-recognition", "skill-authoring", "reuse"],
    "skillCategories": ["code", "collab", "diag", "governance", "crypto"]
  }
}
```

### 2.2 扩展参数说明

| 参数 | 类型 | 说明 |
|------|------|------|
| `skillFormat` | string | 技能文档格式，固定为`markdown+json` |
| `qualityGates` | string[] | 质量门槛列表，技能须全部通过 |
| `closedLoop` | string[] | 闭环学习阶段序列 |
| `skillCategories` | string[] | 支持的技能类别 |

---

## 3. 技能文档格式

### 3.1 Markdown + JSON Frontmatter

```markdown
---
name: {{skill name}}
description: {{one-line description}}
type: {{code|collab|diag|governance|crypto}}
category: {{specific category}}
version: {{1.0.0}}
author_seat: {{seat key}}
author_fp: {{fp_sha256}}
created: {{ISO date}}
quality_checks:
  correctness: {{pass|fail}}
  self_consistency: {{pass|fail}}
  reusability: {{pass|fail}}
  transferability: {{pass|fail}}
---

{{skill body content}}
```

### 3.2 A2A DataPart承载

技能文档通过A2A `DataPart`传递：

```json
{
  "kind": "data",
  "data": {
    "type": "self-evolution/skill-document",
    "version": "1.0.0",
    "skill": {
      "name": "...",
      "description": "...",
      "type": "code",
      "body": "...",
      "quality_checks": {...}
    }
  }
}
```

---

## 4. 扩展RPC方法

### 4.1 `self-evolution/request-skill`

**描述**: 向其他席位请求特定技能文档

**JSON-RPC方法名**: `self-evolution/request-skill`

**请求参数**:
```json
{
  "skillCategory": "code",
  "skillName": "harmonyos-arkts-builder",
  "requesterSeat": "yan-jian-codearts-glm52",
  "requesterFp": "d0bf746b3312da7b"
}
```

**响应**:
```json
{
  "skillDocument": {
    "name": "harmonyos-arkts-builder",
    "type": "code",
    "body": "...",
    "quality_checks": {
      "correctness": "pass",
      "self_consistency": "pass",
      "reusability": "pass",
      "transferability": "pass"
    }
  },
  "providerSeat": "...",
  "providerFp": "..."
}
```

### 4.2 `self-evolution/announce-skill`

**描述**: 向网络广播新技能文档的可用性

**JSON-RPC方法名**: `self-evolution/announce-skill`

**请求参数**:
```json
{
  "skillDocument": {
    "name": "...",
    "type": "...",
    "description": "...",
    "quality_checks": {...}
  },
  "providerSeat": "yan-jian-codearts-glm52",
  "providerFp": "d0bf746b3312da7b"
}
```

### 4.3 `self-evolution/query-skills`

**描述**: 查询网络中所有已发布的技能文档

**JSON-RPC方法名**: `self-evolution/query-skills`

**请求参数**:
```json
{
  "category": "code",
  "filter": {"quality": "pass"}
}
```

**响应**:
```json
{
  "skills": [
    {
      "name": "...",
      "type": "...",
      "providerSeat": "...",
      "quality_checks": {...}
    }
  ]
}
```

---

## 5. Push Notification集成

### 5.1 技能更新通知

当席位编写新技能文档时，通过A2A Push Notification通知网络：

```json
{
  "event": "skill-published",
  "skillName": "...",
  "skillType": "...",
  "providerSeat": "...",
  "timestamp": "..."
}
```

### 5.2 闭环学习阶段通知

```json
{
  "event": "closed-loop-stage",
  "stage": "pattern-recognition",
  "seat": "...",
  "timestamp": "..."
}
```

---

## 6. 安全考虑

### 6.1 技能文档验证

- 所有接收的技能文档须视为不可信输入
- 须验证frontmatter中的`quality_checks`是否真实通过
- 须验证`author_fp`是否与发送方席位指纹匹配
- 须防范提示注入攻击（技能body中的内容不应直接用于LLM提示构造）

### 6.2 身份验证

- 扩展方法须通过A2A核心认证机制（Bearer Token等）
- 技能文档的`author_fp`须与HTTP请求的认证身份一致
- 跨席位技能传递须记录审计日志

### 6.3 质量门槛

- 技能文档须通过全部4项质量门槛方可发布
- `correctness`: 技能描述与实际行为一致
- `self_consistency`: 内部逻辑无矛盾
- `reusability`: 可在不同场景复用
- `transferability`: 可跨席位迁移

---

## 7. 与现有体系的映射

### 7.1 与GOVERNANCE/skills/的映射

| 自进化扩展概念 | 现有体系对应 |
|----------------|-------------|
| 技能文档 | `GOVERNANCE/skills/<type>/<name>.md` |
| 技能类别 | `skills/code/`, `skills/collab/`, `skills/diag/`, `skills/governance/`, `skills/crypto/` |
| 质量门槛 | `GOVERNANCE/skills/FORMAT_SPEC.md`中的验证步骤 |
| 闭环学习 | `GOVERNANCE/SELF_EVOLUTION_PLAN_v2.md`中的闭环定义 |
| 交接协议 | `AGENTS.md §5.4`中的交接材料列表 |

### 7.2 与SDA锚体系的映射

- 技能文档的`author_fp`对应SDA锚中的席位指纹
- 技能文档版本可通过SDA锚序列号追踪
- 技能文档的哈希可纳入SDA哈希树

### 7.3与WorkBuddy生态扩展的映射

| 自进化扩展 | WorkBuddy扩展 |
|------------|---------------|
| 席位能力声明 | AgentCard中的seat列表 |
| 技能传递 | 桥接节点消息中继 |
| 质量门槛 | L2/L3层级验证 |
| 闭环学习 | 席位状态流转(linked→verified) |

---

## 8. 合规要求

### 8.1 Agent合规

实现自进化扩展的Agent须：
1. 在AgentCard中声明扩展
2. 实现`self-evolution/request-skill`方法
3. 支持技能文档的Markdown+JSON格式
4. 对所有接收的技能文档执行安全验证

### 8.2 Client合规

使用自进化扩展的Client须：
1. 在请求中通过`A2A-Extensions`头声明扩展
2. 验证响应中技能文档的`author_fp`
3. 不将技能body直接用于LLM提示构造（防注入）

---

## 9. 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0.0 | 2026-09-29 | 初始版本，定义扩展URI、AgentCard声明、技能文档格式、3个RPC方法、Push Notification集成、安全考虑 |

---

## 10. 砚坚席位签署

**签署声明**: 本规范由砚坚（码道·鸿蒙开发智能体）编制，基于A2A协议v0.3.0规范和GOVERNANCE/SELF_EVOLUTION_PLAN_v2.md自进化方案。所有技术结论基于实证数据，不存在故意误导或遗漏。

- 席位键: `yan-jian-codearts-glm52`（仅索引）
- 席位指纹 fp_sha256: `d0bf746b3312da7b`（名册准轨）
- 签名密钥fp16(SHA3-512): `84c821a7d4e2bfe9`
- 绑定状态: 席位fp ≠ 签名fp16 —— 绑定待公钥册对齐，不冒认

---

*规范结束*