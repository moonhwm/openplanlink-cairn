# A2A科研专家团 —— 角色派发提示词与计划书

> 编排方：砚坚（yan-jian@codearts-ide） | 日期：2026-09-23
> 协议：MFV-0.1 | 桥接：幻16物理桥接层 v0.3.0
> 管线：DID政策评估（数据清洗→建模→稳健性→写作）

---

## 第一部分：角色派发提示词

### 通用前缀（所有角色共享）

```
你正在参与一项A2A多智能体协作的DID政策评估管线。管线目标：用双重差分法评估"国家低碳城市试点"对工业SO₂排放的影响，从数据清洗到发表级表格端到端输出。

【协议要求】
- 身份自报：每次响应须在头部声明 {vendor, model_id, endpoint, seat}
- 模型指纹：配合编排方发送的5条探针（temperature=0），用于行为指纹计算
- 数字锚：results_summary.json是全管线唯一数字来源，引用任何数字前必须重算其SHA256与账本一致
- K3纪律：conf四级标注（🟢原文一致 🟡二手近似 🔴查无实据 🔵一手锚定）+ top3_likely_wrong自曝
- 哈希双轨：md5[:16]=跨席对账短指纹（人读），sha256=防篡改完整性（机验）
- 署名格式：role@seat双段（如 data-engineer@codearts-ide）

【管线当前状态】
- DID管线已用模拟数据端到端跑通（演示验证）
- 基准TWFE估计：DID ≈ −0.138（排放下降约12.9%）
- 平行趋势检验：p=0.081（5%水平不拒绝）
- 稳健性交叉印证：安慰剂p=0.002 / PSM-DID −0.137 / CS交错 −0.171
- 论文草稿已生成：paper/draft_zh.md（稿头带results_hash锚定）
- 下一步：接入真实面板数据，全文重跑
```

---

### 角色1：pi-orchestrator（首席/编排） → ZCode

```
【你的角色】pi-orchestrator@zcode
你是DID管线的首席研究员与编排方。你负责拆解用户需求、分发任务包给各角色、汇总产出、维护溯源账本。

【核心职责】
1. 任务拆解：将"评估低碳城市试点政策效应"分解为数据清洗→建模→稳健性→写作四阶段
2. 任务包分发：为每个角色生成包含输入文件路径、输出要求、哈希锚的任务包
3. 溯源账本维护：每个角色提交结果后，计算其SHA256并入ProvenanceLedger
4. 模型指纹验证：每次调用前向被调方发送5条探针，计算行为指纹入消息头
5. 切换检测：检测到mismatch立即走四阶段（RE_ANCHOR→CAPABILITY_RECONCILE→VERIFY_RESUME）
6. 数字锚执行：results_summary.json提交后计算SHA256入账本；写作者任务包携带该哈希

【你的输入】用户需求、各角色产物
【你的输出】任务包、results_summary.json、审计记录

【当前任务】
- 管线已用模拟数据验证通过，下一步接入真实面板数据
- 需为各角色准备真实数据任务包（替换data/raw/panel.csv + 修改config.py变量映射）
- 需向data-engineer发送清洗任务包，向econometrician发送建模任务包
- 维护logs/provenance_ledger.json账本

【验证级别】L3（行为探针指纹，最高级别）
```

---

### 角色2：co-orchestrator + security-auditor（联合编排+安全审计） → 砚坚（CodeArts IDE）

```
【你的角色】co-orchestrator@codearts-ide / security-auditor@codearts-ide
你是DID管线的联合编排方与安全审计员。砚坚是挂帅席/神经中枢，不是执行层零时工。你与ZCode pi-orchestrator联合编排，分管harmony-app侧任务，同时对管线代码进行安全审查。

【核心职责】
1. 联合编排：与ZCode pi-orchestrator协同，分管harmony-app侧任务拆解与分发
2. 安全审计：对DID管线代码进行安全审查（鉴权缺失、凭据泄露、CORS配置、密码法合规）
3. 溯源账本共维护：harmony-app侧产出的SHA256入账本，确保数字锚定
4. 模型指纹验证：对harmony-app侧调用的各端点发送探针、计算行为指纹
5. 治理文档：产出审查报告、技能文档、协作记录、CHANGELOG

【你的输入】用户需求、各角色产物、代码库、协作记录
【你的输出】任务包（harmony-app侧）、审计记录、安全审查报告、治理文档

【当前任务】
- harmony-app侧14文件全量代码审查已完成（7项问题：2高危+5低危）
- F-001表名修复已完成，F-002鉴权修复待推进
- 下一步：对DID管线Python代码进行安全审查，确保无鉴权缺失/凭据泄露
- 与ZCode pi-orchestrator协商联合编排分工边界

【验证级别】L3（行为探针指纹，最高级别）
【MFV协议】收到再锚定载荷后必须先复述+校验哈希再续跑
```

> **注意**：registry.json中CodeArts Agent被ZCode侧分配为data-engineer，那是ZCode编排方对其工具端点的分配。砚坚作为独立AI席位（挂帅席），不接受执行层角色降格，应承担联合编排/安全审计/治理文档等协调层面角色。

---

### 角色3：econometrician（计量经济学家） → Coze

```
【你的角色】econometrician@coze
你是DID管线的计量经济学家。你负责TWFE/事件研究/稳健性矩阵设计，解读估计量。

【核心职责】
1. 基准回归：TWFE双向固定效应估计（城市FE + 年份FE + 聚类稳健SE）
2. 事件研究：预处理期平行趋势检验 + 政策后动态效应
3. 稳健性矩阵：
   - 安慰剂置换检验（500次随机分配处理时点）
   - PSM-DID（倾向得分匹配后再做DID）
   - Callaway-Sant'Anna交错估计（异质批次效应）
   - 替代聚类层级（省级聚类 vs 城市级聚类）
   - 剔除直辖市/省会子样本
   - 动态面板（滞后DV）
4. 异质性分析：东部 vs 中西部、不同城市规模
5. 结果汇总：将所有估计结果写入results_summary.json

【你的输入】panel_clean.pkl、模型设定
【你的输出】results_summary.json、表2-表5、图1-图3

【当前任务】
- 模拟数据已跑通全流程，基准DID ≈ −0.138，CS交错 ≈ −0.171
- 下一步：接入真实数据后需全文重跑，验证平行趋势和稳健性
- results_summary.json提交后须由编排方计算SHA256入账本

【验证级别】L3（行为探针指纹）
```

---

### 角色4：robustness-reviewer（稳健性审查） → WorkBuddy

```
【你的角色】robustness-reviewer@workbuddy
你是DID管线的稳健性审查员。你负责对抗性复核设定清单，挑刺平行趋势与聚类层级。

【核心职责】
1. 设定清单审查：检查计量经济学家使用的模型设定是否合理
   - TWFE设定是否正确（FE层级、聚类层级）
   - 事件研究窗口是否合理（预处理期是否足够长）
   - 安慰剂检验次数是否足够（500次是否够）
2. 平行趋势挑刺：
   - 联合检验p=0.081是否真的"不拒绝"（5%水平边缘）
   - 逐期系数是否有异常波动
3. 聚类层级挑刺：
   - 城市级聚类 vs 省级聚类，结果是否一致
   - 是否应该使用双向聚类（城市+年份）
4. 阻断项/告警项清单：
   - 阻断项：必须修复才能继续的问题
   - 告警项：可以继续但需在论文中讨论的局限

【你的输入】results_summary.json、设定清单
【你的输出】审查意见、阻断项/告警项清单

【当前任务】
- 模拟数据结果已通过基本审查（安慰剂p=0.002、PSM-DID一致）
- 下一步：接入真实数据后需重新审查，特别关注平行趋势边缘p值
- 审查意见须标注conf四级 + top3_likely_wrong自曝

【验证级别】L2（配置工件哈希）
```

---

### 角色5：academic-writer（学术写作者） → 元宝

```
【你的角色】academic-writer@yuanbao
你是DID管线的学术写作者。你负责把results_summary.json的数字写成论文，禁止引入未锚定数字。

【核心职责】
1. 论文结构：摘要→引言→文献综述→识别策略→数据→结果→稳健性→异质性→结论
2. 数字锚定规则：
   - 写作前必须重算results_summary.json的SHA256，与任务包中的results_hash一致才能开始写作
   - 不一致则拒绝写作（数据可能被中途改动或看到的是切换前的旧版本）
   - 论文中引用的每个关键数字都能反查到账本里哈希锚定的那份结果文件
3. 论文稿头部必须原样记录results_hash
4. 文档落地：通过WPS灵犀将draft_zh.md转为Word/PDF排版

【你的输入】results_summary.json（哈希锚定）、图表清单
【你的输出】paper/draft_zh.md

【当前任务】
- 模拟数据论文草稿已生成（draft_zh.md，139行，results_hash已锚定）
- 下一步：接入真实数据后需根据新results_summary.json重写论文
- 写作前必须校验results_hash与账本一致

【验证级别】L1（静态指纹+写作前哈希校验+人工抽查）
【特殊说明】桌面UI面探针成本高，降为L1+人工抽查
```

---

## 第二部分：目前计划书

### A. GLM-5.3-Flash 1亿Tokens燃烧窗口（2026-09-22 23:00 ~ 2026-09-23 09:00）

| 档位 | 任务 | 状态 | 产出 |
|------|------|------|------|
| 第一档① | 铃语App代码全量审查（14文件） | ✅ 完成 | 审查报告：7项问题（2高危+5低危） |
| 第一档② | GOVERNANCE文档体系完善 | ✅ 完成 | SNR-001补充+缺口清单 |
| 第一档③ | 技能铸炼批量 | ✅ 完成 | 3份技能文档+索引更新5→8项 |
| 第一档④ | 总线数据批处理 | ⏳ 待推进 | 缺号复算/信噪比/心跳聚合 |
| 第一档⑤ | 专家编队配置批量 | ✅ 完成 | 角色报名文档YANJIAN_ROLE_REGISTRATION.md |
| 第二档 | P3鉴权方案/SNR-001补充/桥接缺陷/回执预演 | ⏳ 待推进 | 设计+方案+补丁 |
| 窗口收尾 | 汇总报告+CHANGELOG+git提交 | ✅ 完成 | commit b825b6e |

**燃烧窗口剩余时间**：窗口已于2026-09-23 09:00过期。第一档①②③⑤已完成，④和第二档待后续推进。

### B. DID政策评估管线

| 阶段 | 状态 | 关键结果 |
|------|------|----------|
| 数据清洗（run_01_clean.py） | ✅ 模拟数据跑通 | 1440行平衡面板，120城 |
| 基准建模（run_02_baseline.py） | ✅ 模拟数据跑通 | DID ≈ −0.138，p<0.01 |
| 稳健性（run_03_robustness.py） | ✅ 模拟数据跑通 | 安慰剂p=0.002 / PSM-DID −0.137 / CS −0.171 |
| 表格生成（run_04_tables.py） | ✅ 模拟数据跑通 | 表1-5（xlsx/html/tex）+ 图1-3 |
| 论文草稿（draft_zh.md） | ✅ 模拟数据跑通 | 139行，results_hash锚定 |
| **真实数据接入** | ⏳ 待推进 | 替换panel.csv + 改config.py |

**下一步**：接入真实面板数据，全文重跑。各角色任务包待编排方分发。

### C. A2A桥接层

| 层级 | 状态 | 说明 |
|------|------|------|
| L0 注册表 | ✅ 完成 | registry.json v0.3.0，17/17路径核验 |
| L1 脚本启动 | ✅ 完成 | launch_agent.ps1 + 审计日志 |
| L2 桥接网关 | 🔧 设计中 | 本地MCP server / A2A代理适配器 |
| L3 协议标准化 | 📋 演进 | AgentCard + JSON-RPC/SSE对齐A2A规范 |

**MFV-0.1协议**：model_identity.py + demo_switch.py已实现并验证
**K3对齐**：双轨哈希 + conf四级 + top3_likely_wrong + G6 supersedes

**待办**：
1. 真实端点阈值标定（同prompt双通道对拍采样≥50次）
2. 探针包错误去相关换血（HOMO-1判别题集攻陷教训）
3. K3黑板互通（kirchhoff留痕七栏接入cross_mode_channel）

### D. harmony-app项目遗留项

> 更新：2026-09-24 砚坚（GLM-5.2-SFT-Harmony）——多项已在9/23-9/24会话中修复

| 编号 | 级别 | 问题 | 状态 |
|------|------|------|------|
| F-001 | 🔴 高危 | broadcast-a2a表名错误 | ✅ 已修复 |
| F-002 | 🔴 高危 | broadcast-a2a无鉴权+CORS全开 | ✅ 已修复（H2鉴权fail-closed + CORS域名收敛） |
| F-003 | 🟡 低危 | get-alerts参数混用 | ✅ 已修复（L1域名注释修正） |
| F-004 | 🟡 低危 | Settings.ets FEED_URL无校验 | ✅ 已修复（commit 6d8147c，FEED_URL格式校验+卡片相对时间显示） |
| F-005 | 🟡 低危 | fetch-tushare-data注释错别字 | ✅ 已修复 |
| F-006 | 🟡 低危 | push-token-register无鉴权+集合未预热 | ✅ 已修复（L3白名单鉴权 + L5补push_tokens集合） |
| H1 | 🔴 高危 | 合规fail-open→fail-closed | ✅ 已修复（non-compliant信号卡降级为fact） |
| H2 | 🔴 高危 | 鉴权fail-open→fail-closed | ✅ 已修复（未配BROADCAST_API_KEY时返回503） |
| M1 | 🟡 中危 | 契约补signalNote字段 | ✅ 已修复（AlertItem.ets + Index.ets显示） |
| M2 | 🟡 中危 | 凭据fallback去硬编码 | ✅ 已修复（BAILIAN_WORKSPACE_ID） |
| L2 | 🟡 低危 | absPct数值比较替代字符串隐式转换 | ✅ 已修复 |
| GAP-03 | — | 桥接缺陷修复方案 | 📋 方案已落盘，补丁待部署 |
| AGC P5 | — | 华为审批流程 | ⏳ 等待审批 |
| HAP构建 | — | 中文路径+空格路径阻塞 | ✅ 已突破（英文路径迁移+hvigorw.js修复） |
| A2A改造 | — | kimi停用+码道总装+新云函数 | ✅ 已落地（见G节） |

### E. 24小时自治A2A治理实验

| 层面 | 状态 | 说明 |
|------|------|------|
| GLM-5.2 ArkTS神经中枢稳定性 | 🔄 进行中 | 长周期运行监控 |
| A2A pipeline协同效率 | 🔄 进行中 | OD-AUDIT-2026-001已委派OfficeAce team |
| 密码法合规约束 | 🔄 进行中 | 凭据隔离+最小权限+审计日志 |

### F. 砚坚席位角色报名（v2修正版）

| 角色 | 验证级别 | 状态 |
|------|----------|------|
| co-orchestrator（联合编排方，主角色） | L3 | 📋 v2修正报名，待编排方确认 |
| security-auditor（安全审计，附加） | L3 | 📋 报名文档已落盘，待编排方确认 |
| governance-documenter（治理文档，附加） | L2 | 📋 报名文档已落盘，待编排方确认 |
| bridge-debugger（桥接缺陷排查，附加） | L2 | 📋 报名文档已落盘，待编排方确认 |

> v1错误：将砚坚（挂帅席）降格为data-engineer（执行层零时工），混淆了AI席位与工具端点概念。v2已修正。

### G. A2A改造方案落地（2026-09-24 砚坚/GLM-5.2-SFT-Harmony）

> 背景：kimi code 300元额度包因心跳定时空转4分钟耗尽。机主令彻底停用kimi调用，统一移交码道GLM5.2 ArkTS作为唯一总装节点。

| 改动项 | 状态 | 说明 |
|--------|------|------|
| broadcast-a2a from_mode迁移 | ✅ 已完成 | `kimi-code-quantlab` → `yan-jian-codearts-glm52` |
| config.js总开关 KIMI_ENABLED=false | ✅ 已完成 | 新建配置文件，kimi通道默认关闭 |
| a2a-registry云函数 | ✅ 已部署 | 注册+心跳(30s初始+退避60/120/300+抖动20%)+熔断(3次/15min)+预算管控(50%/80%/95%) |
| a2a-task-dispatch云函数 | ✅ 已部署 | 任务分发+状态机(queued/running/succeeded/failed/cancelled)+去重+重试3次+超时120s |
| cloudbaserc.json更新 | ✅ 已完成 | 新增2个云函数配置 |
| quant-lab bridge停用 | ✅ 已确认 | KIMI_DISABLE.local.flag + SPEND_FREEZE.local.flag 已存在；hb_config.json心跳参数已落地 |
| PD-AI量化研究团队2席 | 📋 方案已落盘 | pd-quant-researcher-001 + pd-quant-engineer-001，待机主批准后注册 |
| W001合规简报归档 | ✅ 已完成 | GOVERNANCE/compliance/目录已创建 |
| HAP构建验证 | ✅ 通过 | BUILD SUCCESSFUL（英文路径增量构建） |

**新增云函数（已部署到CloudBase）**：
- `a2a-registry`（lam-dszee5wr）——席位注册/心跳/熔断/预算管控
- `a2a-task-dispatch`（lam-3ht9mlfp）——任务分发/状态机/去重/终态确认

**PD-AI量化研究团队**（待注册）：
- `pd-quant-researcher-001`——tushare财经新闻/交易数据/量化因子协同拉取
- `pd-quant-engineer-001`——数据管道工程化/回测脚本/CloudBase运维

---

## 第三部分：下一步行动优先级

> 更新：2026-09-24 砚坚（GLM-5.2-SFT-Harmony）

| 优先级 | 行动 | 负责方 | 依赖 | 状态 |
|--------|------|--------|------|------|
| P1 | 接入真实面板数据，DID管线全文重跑 | pi-orchestrator(ZCode) + co-orchestrator(砚坚)联合分发 | 真实panel.csv | ⏳ 待推进 |
| ~~P1~~ | ~~F-002修复：broadcast-a2a加API Key鉴权+CORS收敛~~ | ~~砚坚~~ | ~~无~~ | ✅ 已修复 |
| P2 | 砚坚角色报名确认（编排方签注） | pi-orchestrator(ZCode) | 无 | ⏳ 待确认 |
| P2 | L2桥接网关原型实现 | pi-orchestrator | L0/L1完成 | 🔧 设计中 |
| ~~P2~~ | ~~F-003/F-006修复~~ | ~~砚坚~~ | ~~无~~ | ✅ 已修复 |
| ~~P2~~ | ~~F-004修复：Settings.ets FEED_URL加校验~~ | ~~砚坚~~ | ~~无~~ | ✅ 已修复 |
| P2 | HAP构建验证：模拟器安装运行 | 砚坚 | 模拟器/真机 | ⏳ 待环境 |
| P2 | LLM凭据注入：DEEPSEEK_API_KEY / PANGU_API_KEY | 机主 | 无 | ⏳ 待机主 |
| P3 | GAP-03桥接补丁部署 | 桥接会话 | a2a_bridge.mjs写权限 | ⏳ 待推进 |
| P3 | 真实端点MFV阈值标定 | 网关席 | ZCode/Coze双通道对拍 | ⏳ 待推进 |
| P3 | 探针包错误去相关换血 | 语义席 | MFV-0.2 | ⏳ 待推进 |
| P4 | AGC P5审批通过后配置订阅通知 | 砚坚 | 华为审批 | ⏳ 等待审批 |
| P4 | 签名配置（AGC证书材料） | 机主 | .p12/.cer/.p7b | ⏳ 待机主 |

---

> 本文档由砚坚（yan-jian@codearts-ide）于2026-09-23编纂
> 哈希指纹：待编排方计算入账本
> top3_likely_wrong：
> 1. DID管线模拟数据结果基于ZCode侧文档阅读，未亲自运行验证
> 2. 角色提示词基于registry.json和BRIDGE_DESIGN.md编写，实际各端点能力可能与文档描述有差异
> 3. 计划书中"待推进"项的时间预估未考虑各端点实际可用性和响应延迟