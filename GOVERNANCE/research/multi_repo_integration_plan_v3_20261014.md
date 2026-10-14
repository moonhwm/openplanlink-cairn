# 多仓库整合实施计划 v3.0

> 编纂：砚坚（码道·GLM-5.2/华为云CodeArts），神经中枢
> 日期：2026-10-14
> 版本：v3.0（基于全面重读与实际状态验证更新）
> 状态：执行中
> 依据：主权人2026-10-14指令"重读所涉及的所有项目与文档再进一步计划实施"
> 前版：v2.0（2026-10-14）

---

## 一、重读验证基线（2026-10-14实测）

### 1.1 GOVERNANCE关键文档状态

| 文档 | 版本 | 行数 | 日期 | 状态 |
|------|------|------|------|------|
| QORDER_GLOBAL_DECLARATION.md | v1.0 | 114 | 2026-09-27 | ✅ 砚坚已签署，待DeepSeek/WorkBuddy签署 |
| IMPLEMENTATION_ROADMAP.md | v1.0 | 137 | 2026-09-19 | ✅ 36任务5Phase，关注治理实验漏洞修复 |
| GOVERNANCE_PLAN.md | v1.0 | 608 | 2026-09-19 | ✅ 5维度穷尽式分析，6维语义学审查 |
| SELF_EVOLUTION_PLAN_v2.md | v2.0 | 768 | 2026-09-19 | ✅ 四层进化架构，Hermes Agent深度对比 |
| CHANGELOG.md | — | 3746 | 最新Q4 | ✅ 最新条目：人设3D建模+世界模型入世 |

### 1.2 GitHub仓库克隆状态

| 仓库 | 本地路径 | 状态 | 关键功能 |
|------|---------|------|---------|
| getzep/zep | GOVERNANCE/external/zep/ | ✅ 已克隆 | Agent记忆平台示例+集成 |
| getzep/graphiti | GOVERNANCE/external/graphiti/ | ✅ 已克隆 | 时序知识图谱框架（31K Stars） |
| moonhwm/qoder-skills-hub | GOVERNANCE/external/qoder-skills-hub/ | ✅ 已克隆 | 技能总库（117目录） |
| moonhwm/openplanlink-cairn | — | ❌ 未克隆 | 正本仓 |
| moonhwm/openplanlink-mirror | — | ❌ 未克隆 | 镜像仓 |
| moonhwm/sleepless-flower-under-sealevel | — | ❌ 未克隆 | 物理择校评分系统 |

### 1.3 API通道状态

| 通道 | 用途 | 状态 | 备注 |
|------|------|------|------|
| 302.AI | 向量编码(3072维)+决策模型(qwen-max)+图像生成(dall-e-3) | ✅ 可用 | 主力通道 |
| 硅基流动 | 向量编码(1024维)+重排序(bge-reranker-v2-m3) | ✅ 可用 | 辅助通道 |
| MiniMax H3 | 3D建模+文本生成(abab6.5s-chat) | ✅ 可用 | 3D建模通道 |
| 百炼DashScope | 全套AI服务 | ⚠️ 需sk-格式API Key | 节省计划已购买(250→500元) |
| 腾讯云Tokenhub | 文本生成 | ❌ 连接被重置 | 端点URL需修正 |
| 火山引擎Coding | 代码生成 | ❌ 404模型不存在 | 需正确模型端点ID |
| 火山引擎Agent | Agent任务编排 | ❌ 401认证 | API Key格式需修正 |

### 1.4 K3技能当前状态（实测）

**P0级（5个）——已完成**：

| 技能 | SKILL.md | scripts/ | 自检 | 状态 |
|------|---------|---------|------|------|
| seat-naming-ops | ✅ | ✅ seat_naming.py | ✅ 6/6通过 | 完整 |
| github-mirror-sync-ops | ✅ | ✅ github_sync.py | ✅ 3/3通过 | 完整 |
| govdoc-compliance-ops | ✅ | ✅ govdoc_compliance.py | ✅ 4/4通过 | 完整 |
| otl-format-ops | ✅ | ✅ otl_format.py | ✅ 5/5通过 | 完整 |
| vector-verdict-ops | ✅ | ✅ vector_verdict.py | ✅ 4/4通过 | 完整 |

**P1级（5个）——目录已创建但内容缺失**：

| 技能 | SKILL.md | scripts/ | 状态 |
|------|---------|---------|------|
| quota-ledger-ops | ❌ 丢失 | ❌ 空 | 需从头创建 |
| quad-ops-umbrella | ❌ 丢失 | ❌ 空 | 需从头创建 |
| glb-observatory-ops | ❌ 丢失 | ❌ 空 | 需从头创建 |
| dcc-mcp-umbrella | ❌ 丢失 | ❌ 空 | 需从头创建 |
| hyper3d-rodin-mcp | ❌ 未创建 | ❌ 空 | 需从头创建 |

**P2级（9个）——尚未创建**：

remotion-video-forge, compshare-cli, moonforge-ops, moongate-craft, v2fun-ops, star-owner-ops, video-seer, tongtu-hub, ima-skil

### 1.5 原型代码状态

GOVERNANCE/prototypes/目录包含44个文件，关键原型：

| 原型 | 功能 | 状态 |
|------|------|------|
| embedding_service.py | 向量编码三通道降级链 | ✅ 已验证 |
| rerank_service.py | 重排序双通道降级链 | ✅ 已验证 |
| decision_service.py | 决策模型双通道降级链 | ✅ 已验证 |
| persona_3d_pipeline.py | 人设3D建模完整管线 | ✅ 已执行(Q4) |
| bailian_service_hub.py | 百炼服务接入 | ⚠️ 待API Key |
| graphiti_config.py | Graphiti集成配置 | ✅ 已创建 |
| batch_vectorize.py | 批量向量化 | ✅ 已创建 |
| world_model_entry_v2.py | 世界模型入世(302.AI通道) | ✅ 已执行 |
| three_modules_e2e_test.py | 三模块端到端测试 | ✅ 已创建 |
| night_playground_opening.py | 夜间游乐场开园 | ✅ 已创建 |
| three_face_reconciliation.py | 三面一致对账 | ✅ 已创建 |

### 1.6 CHANGELOG最新遗留项

| 编号 | 遗留项 | 状态 |
|------|--------|------|
| 1 | 百炼预算解阻（裁五）——世界模型写路径待启用 | 待主权人操作 |
| 2 | 世界模型实跑预算（裁六）——百炼happyoyster实跑后重新涌现判定 | 待裁六落定 |
| 3 | Q5三面一致与mirror整合对账——待执行 | 可立即执行 |
| 4 | Q6夜间游乐场开园执行——待执行 | 可立即执行 |

### 1.7 候裁清单

| 编号 | 事项 | 状态 |
|------|------|------|
| 裁五 | 百炼Budget预算调高 | 已购买节省计划，需验证DashScope API Key |
| 裁六 | P4世界模型实跑预算上限 | 建议单轮≤5元封顶 |
| 裁七 | Sites MCP恢复后补publish_site | 同意 |
| 裁八 | 302ai键轮换（第三次暴露） | 建议立即 |
| 裁九 | 纲要云端凭据区块+1增长 | 建议升级脱敏工单 |
| 裁十 | P2试点200节用量预估<0.5元/轮 | 建议准 |
| 裁十一 | Neo4j Desktop安装授权 | Graphiti集成前置条件 |
| 裁十二 | Q4人设3D建模使用已有10个ready世界 | 建议先用已有世界试跑 |
| 裁十三 | 百炼DashScope API Key获取 | 需主权人在百炼控制台生成 |
| 裁十四 | 腾讯云Tokenhub端点URL确认 | 需主权人提供正确端点 |
| 裁十五 | 火山引擎模型端点ID确认 | 需主权人在火山引擎控制台查看 |

---

## 二、v2.0→v3.0关键调整

### 2.1 调整依据

| 发现 | 影响 | 调整 |
|------|------|------|
| P1级5个技能SKILL.md全部丢失 | 不能假设之前的工作已保存 | P1级技能需从头创建 |
| qoder-skills-hub已有117目录（非107） | 部分P2级技能可能已存在 | 创建前先检查目录是否已存在 |
| prototypes已有大量验证过的原型代码 | 三大模块不是从零开始 | 完善和测试已有原型，而非重新编写 |
| CHANGELOG遗留4项中Q5/Q6可立即执行 | 不需要等待主权人操作 | 优先执行Q5三面一致和Q6夜间游乐场 |
| Graphiti有完整的MCP服务器和REST API | 集成路径已明确 | 通过MCP服务器集成，而非从头编写 |
| 全局声明未包含"三个新逆向开发仓库" | 用户提到的更新版可能在WPS云盘 | 需读取WPS云盘OTL文档确认 |

### 2.2 优先级重排

**v2.0优先级**：P0-1百炼修复 → P0-2三大模块 → P0-3 K3技能
**v3.0优先级**：P0-1 Q5三面一致+Q6夜间游乐场 → P0-2 P1级技能补建 → P0-3三大模块深化

调整理由：
1. Q5/Q6是已有工作的闭环，不需要新资源，应优先完成
2. P1级技能SKILL.md丢失是阻塞性问题，需先修复
3. 三大模块已有原型代码，深化工作可在技能补建后进行

---

## 三、实施计划

### Phase 0：立即执行（0-30min）

| 编号 | 任务 | 依据 | 产出 |
|------|------|------|------|
| P0-1 | Q5三面一致对账执行 | CHANGELOG遗留项3 | three_face_reconciliation结果 |
| P0-2 | Q6夜间游乐场开园执行 | CHANGELOG遗留项4 | night_playground_opening结果 |
| P0-3 | 检查qoder-skills-hub中P2级9个技能目录是否已存在 | 117目录vs之前101目录 | 目录存在性报告 |

### Phase 1：P1级技能补建（30-90min）

| 编号 | 任务 | 依据 | 产出 |
|------|------|------|------|
| P1-1 | quota-ledger-ops SKILL.md+scripts创建+自检 | K3技能缺失 | 完整技能目录 |
| P1-2 | quad-ops-umbrella SKILL.md+scripts创建+自检 | K3技能缺失 | 完整技能目录 |
| P1-3 | glb-observatory-ops SKILL.md+scripts创建+自检 | K3技能缺失 | 完整技能目录 |
| P1-4 | dcc-mcp-umbrella SKILL.md+scripts创建+自检 | K3技能缺失 | 完整技能目录 |
| P1-5 | hyper3d-rodin-mcp SKILL.md+scripts创建+自检 | K3技能缺失 | 完整技能目录 |

### Phase 2：三大模块深化（90-180min）

| 编号 | 任务 | 依据 | 产出 |
|------|------|------|------|
| P2-1 | 向量编码：完善embedding_service.py+批量向量化GOVERNANCE文档 | 3亿token计划§2.1 | 向量索引 |
| P2-2 | 决策模型：完善decision_service.py+治理决策测试 | 3亿token计划§2.2 | 决策JSON输出 |
| P2-3 | 世界模型：利用已有Q4成果+世界探索10个世界 | 3亿token计划§2.3 | 世界设定+图像 |
| P2-4 | 重排序：完善rerank_service.py+跨仓库语义检索 | 3亿token计划§2.1 | 检索管线 |

### Phase 3：P2级技能创建（180-300min）

| 编号 | 任务 | 依据 | 产出 |
|------|------|------|------|
| P3-1 | 检查9个P2级技能目录是否已存在于qoder-skills-hub | 117目录实测 | 存在性报告 |
| P3-2 | 创建缺失的P2级技能（SKILL.md+scripts+自检） | K3技能缺失 | 完整技能目录 |

### Phase 4：Graphiti/Zep集成（300-420min）

| 编号 | 任务 | 依据 | 产出 |
|------|------|------|------|
| P4-1 | Graphiti MCP服务器部署 | Graphiti README | MCP服务 |
| P4-2 | Neo4j配置+Graphiti连接 | Graphiti集成需求 | 知识图谱服务 |
| P4-3 | 混合检索管线（BM25+cosine+BFS） | Graphiti搜索配方 | 检索管线 |
| P4-4 | Zep记忆系统四层架构选型 | Zep README | 选型报告 |

### Phase 5：文档同步与对账（420-480min）

| 编号 | 任务 | 依据 | 产出 |
|------|------|------|------|
| P5-1 | GitHub双通道推送（cairn+mirror） | 全局声明要求 | 双仓库同步 |
| P5-2 | SHA3-512对账核验 | 全局声明第二条 | Merkle树对账报告 |
| P5-3 | WPS OTL文档读取与转换 | 主权人指定路径 | OTL→Markdown |
| P5-4 | CHANGELOG追加+git提交 | AGENTS.md串行纪律 | 审计记录 |

---

## 四、三大模块详细计划

### 4.1 向量编码与重排序模块

**当前状态**：embedding_service.py和rerank_service.py已有完整的三通道降级链，已验证302.AI和硅基流动通道可用。

**下一步**：
1. 批量向量化GOVERNANCE目录下的693个Markdown文档
2. 批量向量化A2A总线194条台账消息
3. 构建端到端检索管线：查询→向量编码→cosine检索→重排序→结果
4. 验证检索精度（参照粒子物理实验置信度水平）

**通道配置**：
```
主力：302.AI text-embedding-3-large (3072维)
辅助：硅基流动 BAAI/bge-large-zh-v1.5 (1024维)
重排序：硅基流动 BAAI/bge-reranker-v2-m3
待激活：百炼 text-embedding-v3 (需DashScope API Key)
```

**关键复用**：
- `GOVERNANCE/prototypes/embedding_service.py` — 三通道降级链
- `GOVERNANCE/prototypes/rerank_service.py` — 双通道降级链
- `GOVERNANCE/prototypes/batch_vectorize.py` — 批量向量化脚本
- `GOVERNANCE/external/qoder-skills-hub/vector-verdict-ops/` — 已创建的P0级技能

### 4.2 决策模型模块

**当前状态**：decision_service.py已有双通道降级链，已验证302.AI qwen-max通道可用。

**下一步**：
1. 治理决策测试——分类/是非/评分三种决策类型
2. 量化交易策略评估——策略评分+概率分布
3. 决策确定性验证——3次同输入对比
4. 决策模型评估框架——置信度校准

**通道配置**：
```
主力：302.AI qwen-max (结构化prompt→JSON)
待激活：百炼 decision-model-preview (需DashScope API Key)
本地基座：sleepless-flower-under-sealevel nn_deep.py (16→8→1)
```

**关键复用**：
- `GOVERNANCE/prototypes/decision_service.py` — 双通道降级链
- `GOVERNANCE/external/qoder-skills-hub/unified-decision-suite/` — 已有技能（四层架构）
- `GOVERNANCE/external/qoder-skills-hub/stat-verdict-ops/` — 已有技能（统计裁决）

### 4.3 世界模型模块

**当前状态**：Q4已完成人设3D建模（MiniMax H3生成3D模型+LOD降面+世界模型入世），涌现判定L3。

**下一步**：
1. 世界探索——生成10个世界描述+图像
2. 实时导演——场景推演+事件生成
3. 角色演绎——砚坚席3D建模已有成果纳入世界模型
4. 涌现判定——三问三判据（待百炼通道激活后重新判定）

**通道配置**：
```
3D建模：MiniMax H3 (已验证可用)
图像生成：302.AI dall-e-3
文本描述：302.AI qwen-max
待激活：百炼世界模型 (需DashScope API Key)
```

**关键复用**：
- `GOVERNANCE/prototypes/persona_3d_pipeline.py` — 完整3D建模管线
- `GOVERNANCE/prototypes/world_model_entry_v2.py` — 世界模型入世(302.AI通道)
- `GOVERNANCE/external/qoder-skills-hub/world-model-ops/` — 已有技能（人设资产生成链+涌现判定）
- `GOVERNANCE/research/persona_3d/` — Q4产出的3D模型和入世图像

---

## 五、K3技能创建计划

### 5.1 P1级技能补建（5个）

| 技能 | 功能 | 关键参考 |
|------|------|---------|
| quota-ledger-ops | 配额台账操作 | quota-guard-ops（已有） |
| quad-ops-umbrella | 四象限操作总括 | unified-decision-suite（已有） |
| glb-observatory-ops | GLB观测站操作 | persona_3d_pipeline.py（原型） |
| dcc-mcp-umbrella | DCC MCP总括 | graphiti/mcp_server（已有） |
| hyper3d-rodin-mcp | Hyper3D Rodin MCP | run_imageto3d.py（原型） |

### 5.2 P2级技能创建（9个，先检查是否已存在）

| 技能 | 功能 | 关键参考 |
|------|------|---------|
| remotion-video-forge | 视频生成锻造 | av-media-ops（已有） |
| compshare-cli | 计算共享CLI | — |
| moonforge-ops | 月之锻造操作 | skill-forge-pipeline（已有） |
| moongate-craft | 月门工艺 | — |
| v2fun-ops | V2Fun操作 | — |
| star-owner-ops | 星主操作 | — |
| video-seer | 视频先知 | av-media-ops（已有） |
| tongtu-hub | 通路枢纽 | — |
| ima-skil | IMA技能 | — |

---

## 六、关键已有技能复用清单

以下技能已在qoder-skills-hub中存在，**不得重复造轮子**，应直接引用：

| 技能 | 功能 | 与三大模块的关系 |
|------|------|----------------|
| world-model-ops | 世界模型作业（人设资产生成链+涌现判定+检索核验三器） | 世界模型模块核心技能 |
| unified-decision-suite | 统一决策套件（四层架构+路由表+五件套立场） | 决策模型模块核心技能 |
| night-playground-ops | 夜间游乐场运维（目标内置化+留眠胶囊） | Q6夜间游乐场核心技能 |
| persona-iteration-loop-ops | 人设迭代循环（中性化引擎+三镜诘问+直述层） | 人设3D建模核心技能 |
| skill-forge-pipeline | 技能锻造管线v2.4.1（N-C-D主链+短链） | K3技能创建核心技能 |
| quota-guard-ops | 额度守护运维（Q0-Q3四档程式） | 配额管理核心技能 |
| portable-sync-ops | 便携件同步总署 | GitHub同步核心技能 |
| stat-verdict-ops | 统计裁决室（六检验+假设前置闸） | 决策验证核心技能 |
| av-media-ops | AV媒体操作 | 视频生成相关技能 |
| diffusion-dynamics-extension | 扩散动力学扩展 | 世界模型相关技能 |

---

## 七、执行时间线

```
Phase 0 (0-30min): Q5三面一致+Q6夜间游乐场+P2技能目录检查
    ↓
Phase 1 (30-90min): P1级5个技能补建（SKILL.md+scripts+自检）
    ↓
Phase 2 (90-180min): 三大模块深化（向量编码+决策模型+世界模型）
    ↓
Phase 3 (180-300min): P2级9个技能创建
    ↓
Phase 4 (300-420min): Graphiti/Zep集成（MCP服务器+Neo4j+混合检索）
    ↓
Phase 5 (420-480min): 文档同步+SHA3-512对账+CHANGELOG追加
```

---

## 八、风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 百炼DashScope API Key未获取 | 高 | 30M token无法使用百炼通道 | 302.AI+硅基流动替代通道已验证可用 |
| P1级技能SKILL.md再次丢失 | 中 | 技能创建工作白费 | 创建后立即git commit+push到GitHub |
| 内存不足（15.7GB仅0.11GB可用） | 高 | 批量处理可能中断 | 分批处理+及时清理内存 |
| GitHub Push Protection | 低 | 推送被阻止 | 排除GLB/ZIP/JSON敏感文件 |
| bash工具输出问题 | 高 | 无法执行shell命令 | 使用read/write/edit工具替代bash |
| 火山引擎API Key格式问题 | 中 | 15M token无法使用火山引擎 | 使用MiniMax H3替代3D建模 |

---

## 九、候裁清单（v3.0累加更新）

| 编号 | 事项 | 状态 | 版本 |
|------|------|------|------|
| 裁五 | 百炼Budget预算调高 | 已购买节省计划，需验证DashScope API Key | v2.0 |
| 裁六 | P4世界模型实跑预算上限 | 建议单轮≤5元封顶 | v2.0 |
| 裁七 | Sites MCP恢复后补publish_site | 同意 | v2.0 |
| 裁八 | 302ai键轮换（第三次暴露） | 建议立即 | v2.0 |
| 裁九 | 纲要云端凭据区块+1增长 | 建议升级脱敏工单 | v2.0 |
| 裁十 | P2试点200节用量预估<0.5元/轮 | 建议准 | v2.0 |
| 裁十一 | Neo4j Desktop安装授权 | Graphiti集成前置条件 | v2.0 |
| 裁十二 | Q4人设3D建模使用已有10个ready世界 | 建议先用已有世界试跑 | v2.0 |
| 裁十三 | 百炼DashScope API Key获取 | 需主权人在百炼控制台生成sk-格式Key | v2.0 |
| 裁十四 | 腾讯云Tokenhub端点URL确认 | 需主权人提供正确端点 | v2.0 |
| 裁十五 | 火山引擎模型端点ID确认 | 需主权人在火山引擎控制台查看 | v2.0 |
| 裁十六 | P1级技能SKILL.md丢失原因调查 | 可能是git pull覆盖了本地创建的文件 | v3.0新增 |

---

> 神经中枢：砚坚（码道·GLM-5.2/华为云CodeArts）
> 计划版本：v3.0
> 依据：全面重读GOVERNANCE关键文档+外部仓库状态+K3技能实测+原型代码盘点
> 核心调整：从"假设状态"转为"实测状态"，从"从头创建"转为"复用已有"，从"等待主权人"转为"先执行可执行项"