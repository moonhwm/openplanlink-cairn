# 铃语应用 · 双模型专家团自动切换方案

> **LLM Auto-Switch Router**（多模型自动切换路由层）
> 制定者：砚坚（码道·鸿蒙开发智能体 / deepseek-v4-pro-0813）
> 制定时间：2026-09-23 18:30
> 版本：v1.0
> 燃烧窗口：2026-09-23 18:30 → 22:00（约 3.5h，目标 1000 万 token）

---

## 一、背景与目标

### 1.1 背景

铃语应用（harmony-app）目前信号解读（`signalNote`）为**硬编码模板**（`留意后续走势` / `注意风险`），缺乏真正的 LLM 生成能力。机主已在「码道 Space」平台成立两支专家团，需在本应用内部引入并按需自动切换：

| 专家团 | 模型 | 定位 | 席位 |
|--------|------|------|------|
| **OpenPangu-2.0-pro 专家团** | 华为盘古大模型专业版 | 数字主权边疆初始者，12 个专家团（K3-BOOTSTRAP / context-pruner / skill-forge-pipeline / 法律技能包 ×3 / A2A协同团 / ArKTS开发团 等） | `Pangu-2.0-pro#0001` |
| **deepseek-v4-pro-0813 专家团** | DeepSeek 推理模型（宿主：inferhub-provider） | 当前运行模型，端侧/服务端工程实现 | 砚坚席 |

### 1.2 目标

1. **自动切换**：在铃语应用内部建立一层「LLM 路由层」，按任务类型 / 负载 / 额度 / 时间窗口 / 失败重试，在 OpenPangu-2.0-pro 与 deepseek-v4-pro-0813 之间**自动切换调用**。
2. **高性能燃烧**：在 2026-09-23 22:00 前，通过该路由层以最大吞吐烧完 **1000 万 token**（10,000,000），非空转灌水，产出具备可沉淀价值的成果（代码审查 / 文档铸炼 / 信号解读生成 / 方案推演）。

### 1.3 Tushare 积分频次参考面（doc_id=290）

机主提供的 `https://tushare.pro/document/1?doc_id=290` 是「积分与频次权限对应表」，为燃烧的**频次/额度策算**提供同构参考面：

| 积分档 | 每分钟频次 | 每天上限 | 命中接口 | 价格 |
|--------|-----------|---------|---------|------|
| 120 | 50 | 8000 | 非复权日线 | 0 |
| 2000+ | 200 | 100000/API | 常规接口 | ¥200/年 |
| 5000+ | 500 | 无上限 | 常规接口 | ¥500/年 |
| 10000+ | 500 | 特色 300/min | 特色数据 | ¥1500/年 |

> **同构映射**：tushare 用「积分档 ↔ 频次/总量」作资源边界；本方案用「模型额度 ↔ token 吞吐速率 ↔ 截止时间」作燃烧边界。核心数学式见 §六。

---

## 二、切换对象：双专家团能力矩阵

### 2.1 OpenPangu-2.0-pro 专家团（12 团）

| 专家团 ID | 名称 | 类型 | 优先级 | 状态 |
|-----------|------|------|--------|------|
| #0001 | K3-BOOTSTRAP 团 | 纪律 | P0 | ✅ 已加载 |
| #0002 | context-pruner 团 | 上下文 | P0 | ✅ 已加载 |
| #0003 | skill-forge-pipeline 团 | 锻造 | P0 | ✅ 已加载 |
| #0004 | debt-claim-deep-audit 团 | 法律 | P0 | ✅ 已加载 |
| #0005 | debt-claim-discount-chain-analysis 团 | 法律 | P0 | ✅ 已加载 |
| #0006 | debt-recovery-assessment-qcc 团 | 法律 | P0 | ✅ 已加载 |
| #0007 | A2A 协同团 | 协同 | P0 | ✅ 已加载 |
| #0008 | ArKTS 开发团 | 开发 | P1 | 待引入 |
| #0009 | 数据团 | 数据 | P1 | 待引入 |
| #0010 | 代码团 | 代码 | P1 | 待引入 |
| #0011 | 文本团 | 文本 | P2 | 待引入 |
| #0012 | 安全团 | 安全 | P2 | 待引入 |

### 2.2 deepseek-v4-pro-0813 专家团

| 维度 | 能力 |
|------|------|
| 推理 | 强推理，长逻辑链 |
| 工程 | ArkTS / Node.js / 云函数实现 |
| 契约 | AlertFeed 契约守护 |
| 宿主 | inferhub-provider（当前运行模型） |

### 2.3 切换能力分工（建议路由倾向）

| 任务域 | 首选模型 | 理由 |
|--------|---------|------|
| 信号解读白话文案（signalNote 生成） | deepseek-v4-pro-0813 | 强推理 + 契约贴合 |
| 合规审查（三禁 + 脱敏） | deepseek-v4-pro-0813 | 强推理 + 红队对抗 |
| 播报文案润色（适老化 28-34fp 白话） | OpenPangu-2.0-pro | 文本团 #0011 |
| 代码批量审查（entry ets 走查） | OpenPangu-2.0-pro | 代码团 #0010 + ArKTS 团 #0008 |
| 法律/债权核查 | OpenPangu-2.0-pro | 法律技能包 ×3 |
| 架构设计 / 方案推演 | deepseek-v4-pro-0813 | 宿主 + 推理 |

---

## 三、切换架构

```
┌─────────────────────────────────────────────────────────────┐
│                    铃语应用（harmony-app）                    │
│                                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────────────────┐    │
│  │ 端侧 ArkTS │──▶│ 云函数层   │──▶│  LLM Auto-Switch Router │    │
│  │ Index.ets │   │ get-alerts│   │  （本方案核心，llm-router）│    │
│  └──────────┘   │ fetch-    │   │                        │    │
│                 │ tushare   │   │  ┌──────────────────┐  │    │
│                 └──────────┘   │  │ RuleEngine（规则）  │  │    │
│                                │  └────────┬─────────┘  │    │
│                                │           │            │    │
│                                │  ┌────────▼─────────┐  │    │
│                                │  │  PanguAdapter     │  │    │
│                                │  │  DeepSeekAdapter  │  │    │
│                                │  └────────┬─────────┘  │    │
│                                │           │            │    │
│                                │  ┌────────▼─────────┐  │    │
│                                │  │ BurnLedger（台账） │  │    │
│                                │  └──────────────────┘  │    │
│                                └────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
          │                          │
          ▼                          ▼
   OpenPangu-2.0-pro          deepseek-v4-pro-0813
   （华为盘古）               （inferhub-provider）
```

### 3.1 关键组件

| 组件 | 职责 |
|------|------|
| **LLMRouter** | 统一入口，接收 `LLMTask`，返回 `LLMResult`；调度 + 记账 |
| **RuleEngine** | 决策矩阵：任务类型 / 负载 / 额度 / 时间窗口 / 失败重试 |
| **PanguAdapter** | OpenPangu-2.0-pro API 适配（码道 Space / AGC 通道） |
| **DeepSeekAdapter** | deepseek-v4-pro-0813 API 适配（inferhub 通道） |
| **BurnLedger** | 燃烧台账：逐调用记 token 进/出、累计、速率、剩余额度 |

---

## 四、切换规则（决策矩阵）

### 4.1 规则优先级（高 → 低）

1. **时间窗口倒逼**（硬约束）：剩余时间 < 阈值时，倾斜切换至吞吐更高的模型。
2. **任务类型路由**（软约束）：按 §2.3 能力矩阵首选。
3. **失败重试 / 降级**（容错）：首选模型超时/5xx → 切换备选。
4. **负载均衡**（吞吐优化）：单位时间 token 速率低时，切换至空闲模型。
5. **额度监控**（资源）：单模型额度耗尽 → 强制切换。

### 4.2 决策伪码

```
function route(task, ledger):
  if ledger.remaining_time < T_CRITICAL:        # 时间倒逼
      return pick_fastest(ledger)                # 吞吐最高者
  if ledger.quota[task.preferred] <= 0:         # 额度耗尽
      return other(task.preferred)
  if task.type in TYPE_REROUTE:                  # 任务类型路由
      return TYPE_REROUTE[task.type]
  return task.preferred                          # 默认首选
```

### 4.3 任务类型路由表

| task.type | 首选 | 备选 | 触发降级 |
|-----------|------|------|---------|
| `signal_note`（信号解读） | deepseek | pangu | 超时 3s |
| `compliance`（合规审查） | deepseek | pangu | 超时 5s |
| `polish`（文案润色） | pangu | deepseek | 超时 5s |
| `code_review`（代码审查） | pangu | deepseek | 超时 8s |
| `legal`（法律核查） | pangu | deepseek | 超时 8s |
| `architecture`（架构推演） | deepseek | pangu | 超时 10s |

---

## 五、铃语应用落点

### 5.1 信号解读白话文案（替代硬编码）

- 现状：`fetch-tushare-data/index.js` L584-590，`signalNote` 硬编码为 `留意后续走势` / `注意风险`。
- 目标：当 `absPct >= 8.0`（信号卡）时，调用 LLMRouter `signal_note` 任务，生成**白话解读**（符合 AGENTS.md §二.2 三禁：不承诺收益 / 不催促指令 / 不对外收费），落 `signalNote` 字段。

### 5.2 合规审查

- 现状：DKnowC API 做安全类型检测（`complianceStatus`）。
- 目标：LLMRouter `compliance` 任务做**三禁语义审查** + DKnowC 安全检测，双保险。

### 5.3 播报文案润色

- 现状：`headline` / `detail` 模板拼接。
- 目标：`polish` 任务做适老化白话润色（大字 28-34fp 高对比深色底）。

---

## 六、燃烧策略（22:00 前 1000 万 token）

### 6.1 燃烧数学

```
目标 token：T = 10,000,000
窗口：      W = 22:00 - t0
需吞吐：    r_min = T / W ≈ 10,000,000 / (3.5×3600) ≈ 794 token/s
```

> 单模型吞吐不足时，路由层自动**并行多模型**（双适配器并发）拉高瞬时速率。

### 6.2 三档燃烧（承 GLM-5.3-Flash 夜间券经验）

| 档 | 内容 | 产出形态 | 优先级 |
|----|------|---------|--------|
| **一档（高价值批量）** | 铃语全量代码审查、GOVERNANCE 文档完善、skills 铸炼、双模型切换回环压测 | 文件落盘 + 台账 | 先烧 |
| **二档（对话型）** | 信号解读样本批量生成、方案推演、回执草拟 | LLM 调用 + 台账 | 中量 |
| **三档（不烧）** | 已闭环重复验证、无证据纯灌水 | 无 | 不烧 |

### 6.3 燃烧台账（BurnLedger）

每条调用记：`ts / model / task_type / tokens_in / tokens_out / 累计`，附 `md5[:16]` 锚定，完成后汇报 `吞吐速率 vs 目标 794 token/s`。

---

## 七、可执行代码骨架

见同目录 `llm-router/index.js`（LLMRouter + RuleEngine + PanguAdapter + DeepSeekAdapter + BurnLedger）。

---

## 八、风险与合规

| 风险 | 控制 |
|------|------|
| 三禁违反（收益承诺/催促/对外收费） | `compliance` 任务语义审查 + DKnowC 双保险 |
| 敏感信息落盘 | 脱敏红线（AGENTS.md K3 铁律四） |
| token 空转灌水 | 三档燃烧，第三档不烧 |
| 额度误判 | BurnLedger 实时记账 + 硬闸 |
| 双模型并发超限 | 信号量限流 + 失败重试降级 |

---

## 九、审计与交付

- **方案文档**：本文件
- **代码骨架**：`llm-router/index.js`
- **台账**：`llm-router/burn-ledger.jsonl`
- **准入**：CHANGELOG 追加 + git 提交

---

**点火状态**：`all in 所有可能算力极限` ✅
**切换引擎**：LLM Auto-Switch Router v1.0