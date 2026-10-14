# AGENTS.md —— 任何 AI 编辑器进入本工程前必读（共治契约 v1.0，2026-09-14）

本工程会被多个 AI 席位编辑（码道 IDE·鸿蒙开发智能体 / Kimi Code / Kimi Work 桌面席）。
为防止不同 AI 的架构风格互相踩踏，**先读完本文件再动手；动手前先看 CHANGELOG.md 最新条目**。

## 一、分区主权（不可越界）

| 目录 | 主权席 | 职责 |
|---|---|---|
| `harmony-app/`（本工程） | 码道 IDE（鸿蒙开发智能体 + ArkTS-SPARK） | 端侧 UI、播报交互、Push 封装 |
| `quant-lab/`（工作区外另一目录） | Kimi Code（顾权席） | 取数、策略、监测、服务端出数 |
| 接口边界 | **本文件 + `entry/src/main/ets/model/AlertItem.ets`** | 服务端产出 AlertFeed JSON 契约 |

越界规则：任何一方要动对方目录或改 AlertItem/AlertFeed 契约，须先在 CHANGELOG.md 写明意图并停机主确认。

## 二、硬约束（改代码不许破坏）

1. **适老化**：主界面=大字白话卡片流（28-34fp 高对比深色底），**禁止引入 K 线图/走势图等复杂图表组件**；点卡=听播报。
2. **信号松绑（机主 2026-09-14 10:57 裁）**：允许输出自家策略信号与白话解读（如「动量策略今日目标」「浮亏扩大，注意」），条目须带 `kind: "signal"` 标记；仍禁三条：①承诺收益/保本等绝对化措辞；②催促性强指令（「立即买入」「满仓」式）；③任何对外公开/收费形态。事实卡 `kind: "fact"` 照旧。信号卡视觉上加「自家信号」角标，与事实卡区分。
3. **平台**：Stage 模型，`compatibleSdkVersion 20` / `targetSdkVersion 26`，纯 ArkTS，零三方依赖。
4. **PushService.ets 保持占位封装**：AGC 未配置前自动降级轮询，不得展开实装（实装步骤在 README「推送实装」）。
5. **首屏永不空白**：服务未连通时必须显示带「示例」字样的演示卡（现有 DEMO_ITEMS 机制）。

## 三、串行纪律

同一时间只允许一个 AI 席位在本工程写代码。开工前：
1. `git status` —— 有未提交改动先读 CHANGELOG 判断是谁的活，未明即提交快照再动手；
2. 读 CHANGELOG.md 最后一条；
3. 干完立即 `git add -A && git commit`，并在 CHANGELOG.md 追加条目（谁/何时/改了什么/为什么/遗留什么）。

## 四、架构基调（已定型，勿推翻）

- EntryAbility：Push 初始化 + onNewWant 带 alertId 拉起定位；
- Index.ets：List 卡片流 + 5s 前台轮询（AlertPoller）兜底；
- AudioPlayer：AVPlayer 播云端 TTS 音频流；
- 数据源：FEED_URL 待 X 服务器落地后替换，契约即 AlertFeed。

改进可以做，推翻须机主批准。
## 五、自主进化与知识沉淀（项目约束，非角色选择）

> 来源：GOVERNANCE/SELF_EVOLUTION_PLAN_v2.md（2026-09-19 砚坚编纂，机主审阅后写入本节）
> 任何 AI 席位进入本工程后，以下进化机制自动生效，不依赖单一角色的选择。

### 5.1 技能自动编写（每次任务完成后）

完成非平凡任务后，须将经验编写为技能文档，保存到 `GOVERNANCE/skills/<类型>/`。技能文档格式见 `GOVERNANCE/skills/FORMAT_SPEC.md`。

| 技能类型 | 目录 | 编写触发 |
|---------|------|---------|
| code | skills/code/ | 完成非平凡代码编写 |
| collab | skills/collab/ | 完成跨席位协作 |
| diag | skills/diag/ | 完成问题诊断 |
| governance | skills/governance/ | 完成治理实验 |
| crypto | skills/crypto/ | 完成密码学分析 |

### 5.2 闭环学习（任务执行→结果记录→质量评估→模式识别→技能编写→下次复用）

每次任务完成后执行闭环学习：
1. 结果记录：CHANGELOG.md追加条目
2. 质量评估：验证步骤V1-V8
3. 模式识别：从个案中提炼共性
4. 技能编写：将模式编写为可复用技能
5. 下次复用：遇到同类任务时引用已有技能

### 5.3 知识资产角色无关性（所有知识资产必须满足）

- 不引用隐含上下文（不用"上次会话中我们讨论了..."）
- 自包含（每条知识资产可独立理解）
- 引用而非记忆（引用文件路径而非依赖记忆）
- 格式规范化（Markdown+JSON，任何角色可解析）

### 5.4 交接协议（替代角色接续时）

替代角色进入本工程后，须阅读以下交接材料：
- AGENTS.md（本文件）→ 项目宪法
- GOVERNANCE/SELF_EVOLUTION_PLAN_v2.md → 自主进化方案
- GOVERNANCE/GOVERNANCE_PLAN.md → 治理方案
- GOVERNANCE/IMPLEMENTATION_ROADMAP.md → 落地路线图
- CHANGELOG.md（最后一条）→ 最近变更
- GOVERNANCE/skills/ → 可复用技能

### 5.5 进化受治理约束

进化不是无约束的——进化本身也受制度规范。技能编写须通过质量门槛（正确性/自洽性/可复用性/可迁移性），治理实验须遵循HY4协议。
