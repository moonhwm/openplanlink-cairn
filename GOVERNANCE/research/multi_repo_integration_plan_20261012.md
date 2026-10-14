# 多仓库整合实施计划

| 项 | 值 |
|---|---|
| 档号 | DF-PLAN-20261012-YANJIAN-01 |
| 署名 | 砚坚（GLM-5.2 ArkTS神经中枢席） |
| 席位 | `a2a-node-local`（harmony-app 主权工程） |
| 时点 | 2026-10-12 22:30+08:00 |
| 状态 | 候主权人裁定 |
| 前置档 | DF-PLAN-20261011-WORKBUDDY-01（沈铎P1-P6框架）；DF-OPS-20261011-HY4-05（预算阻断定谳） |

> 口径声明：本件为**执行席位实施计划**，非裁定文书。零凭据——全文无任何键值明文。

---

## 一、当前状态总览

### 1.1 百炼预算阻断（裁五未落定）

| 模块 | 模型 | 百炼状态 | 替代通道状态 |
|---|---|---|---|
| 向量编码 | text-embedding-v4 | **403 insufficient_quota** | ✅ 302.AI（3072维）/ ✅ 硅基流动 bge-large-zh-v1.5（1024维） |
| 重排序 | qwen3-rerank / gte-rerank-v2 | **429** | ✅ 硅基流动 bge-reranker-v2-m3 |
| 决策模型 | decision-model-preview | **429 BudgetLimitExceeded** | ✅ 302.AI（qwen-max等）可做LLM决策 |
| 世界模型 | happyoyster-1.0-adventure | 只读面200（10世界ready）；写路径未测 | 无替代（百炼专属） |
| 实时导演/角色演绎 | happyoyster-1.0-directing/acting | **403**（须账户侧开通） | 无替代 |

**结论**：百炼预算阻断是账号级的，唯一解法是主权人在控制台调高Budget Management预算（裁五）。在裁五落定前，向量编码与重排序模块**使用302.AI和硅基流动作为替代通道**继续推进。

### 1.2 六仓库现状

| 仓 | 本地状态 | 与三模块的关系 |
|---|---|---|
| `getzep/zep` | 已浅克隆到 `GOVERNANCE/external/zep/` | 记忆平台——时序事实管理、混合检索、MCP服务器 |
| `getzep/graphiti` | 已浅克隆到 `GOVERNANCE/external/graphiti/` | 时序知识图谱——EntityEdge三重时序窗口、12搜索配方、5种重排序器 |
| `openplanlink-cairn` | GitHub MCP验活✅；本地归档在WorkBuddy | 正本仓：tools/350件、skills/3件、bus/bus.jsonl、worlds_manifest |
| `openplanlink-mirror` | GitHub MCP验活✅；本地归档在WorkBuddy | 镜像仓：deliverables/119件、attest.json+HMAC-SHA3树 |
| `qoder-skills-hub` | GitHub MCP验活✅；本地归档在WorkBuddy | 技能总库：world-model-ops/night-playground-ops/persona-modeling-kit/unified-decision-suite |
| `sleepless-flower-under-sealevel` | GitHub MCP验活✅；本地归档在WorkBuddy | 决策模型基座：nn_deep.py（16→8→1，spearman 0.912） |

### 1.3 已完成的前置工作

| 工作 | 产出 | 状态 |
|---|---|---|
| Graphiti代码分析P1-P3 | `graphiti_code_analysis_20261012.md` | ✅ 完成 |
| Graphiti 1亿token规划 | `graphiti_100m_token_plan_20261012.md` | ✅ 完成 |
| 火山引擎ImageTo3D测试 | 3D模型ZIP（27MB，含GLB+PBR纹理） | ✅ 成功 |
| 百炼六模块v3调用 | 6个JSON结果文件 | ✅ 完成 |
| v3结构化档案 | `night_playground_v3_20261012.md` | ✅ 完成 |
| 替代通道验证 | 302.AI embedding ✅ / 硅基流动 embedding+rerank ✅ | ✅ 完成 |
| 全局声明重读 | 20261011 CAIRN版正文副本 | ✅ 完成 |
| 沈铎P1-P6框架重读 | DF-PLAN-20261011-WORKBUDDY-01 | ✅ 完成 |
| 预算阻断定谳重读 | DF-OPS-20261011-HY4-05 | ✅ 完成 |
| 世界模型作业总册v3重读 | DF-AI-20261009-CAIRN-50 | ✅ 完成 |
| 3D资产Unity规范重读 | DF-SPEC-20261009-HY4-07 | ✅ 完成 |

---

## 二、实施计划 Q1-Q6

### Q1 替代通道向量+重排接入（立即可执行，不依赖裁五）

**目标**：在百炼预算阻断期间，使用302.AI和硅基流动替代通道完成向量编码与重排序模块的接入。

**具体步骤**：

1. **向量编码服务层**（`GOVERNANCE/prototypes/embedding_service.py`）：
   - 主通道：百炼 `text-embedding-v4`（1024维）——待裁五解阻后启用
   - 替代通道A：302.AI `text-embedding-3-large`（3072维）——已验证可用
   - 替代通道B：硅基流动 `BAAI/bge-large-zh-v1.5`（1024维）——已验证可用
   - 降级链：百炼→302.AI→硅基流动，自动故障转移
   - 输出契约：`{embedding: float[], dim: int, model: str, provider: str, latency_ms: int}`

2. **重排序服务层**（`GOVERNANCE/prototypes/rerank_service.py`）：
   - 主通道：百炼 `gte-rerank-v2`——待裁五解阻后启用
   - 替代通道：硅基流动 `BAAI/bge-reranker-v2-m3`——已验证可用
   - 降级链：百炼→硅基流动，自动故障转移
   - 输出契约：`{results: [{index: int, relevance_score: float}], model: str, provider: str}`

3. **节级检索闭环**（承沈铎P2）：
   - 现状：`section_search.py` 3126节纯BM25，零向量零重排
   - 改造：BM25 top50 → 向量化 → 重排 → top5
   - 先有界试点200节（含凭据形态之32件**不入向量库**——承脱敏工单门禁）
   - **评测判据（能失败）**：P@1 / P@5 / MRR 对 BM25基线；消融组（仅BM25 / 仅向量 / 向量+重排）三组对照

**验收判据**：
- 向量编码服务层：输入文本→输出float数组，维度与provider字段正确，降级链自动切换
- 重排序服务层：输入query+documents→输出排序结果，relevance_score单调递减
- 节级检索：向量+重排组P@5优于BM25基线，或如实报负结果

**预计用量**：200节×~500 token ≈ 10万token + 重排200次 ≈ <0.5元/轮（承裁十）

---

### Q2 Graphiti时序知识图谱集成（立即可执行，不依赖裁五）

**目标**：将Graphiti时序知识图谱集成到A2A网络，为多席位协作提供记忆持久化和时序事实管理。

**架构设计**（基于P1-P3代码分析）：

```
┌─────────────────────────────────────────────────────────────┐
│                    Graphiti集成架构                          │
│                                                              │
│  ┌──────────┐   ┌──────────────┐   ┌───────────────────┐   │
│  │ Neo4j    │◄──│ Graphiti     │◄──│ LLM Client        │   │
│  │ Desktop  │   │ Core         │   │ (302.AI→qwen-max) │   │
│  │ (图DB)   │   │ (时序事实)   │   │                   │   │
│  └──────────┘   └──────────────┘   └───────────────────┘   │
│                        │                                     │
│                        ▼                                     │
│  ┌──────────┐   ┌──────────────┐   ┌───────────────────┐   │
│  │ Embedder │◄──│ Search       │◄──│ Reranker          │   │
│  │ (硅基流动│   │ (12配方)     │   │ (硅基流动         │   │
│  │ bge-large│   │ (bm25+cos+   │   │ bge-reranker-v2)  │   │
│  │ -zh)     │   │  bfs三路)    │   │                   │   │
│  └──────────┘   └──────────────┘   └───────────────────┘   │
│                        │                                     │
│                        ▼                                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ MCP Server (12工具: add_memory/search_memory_facts   │   │
│  │ /get_episodes/search/etc.)                           │   │
│  │ HTTP transport → A2A网络可调用                       │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**具体步骤**：

1. **Neo4j Desktop安装**（需主权人授权）：
   - 下载Neo4j Desktop（免费本地版）
   - 创建本地图数据库实例
   - 配置连接：`bolt://localhost:7687`

2. **Graphiti配置**（`GOVERNANCE/prototypes/graphiti_config.py`）：
   - LLM Provider：302.AI（`https://api.302ai.cn/v1`，model=qwen-max）
   - Embedder：硅基流动（`BAAI/bge-large-zh-v1.5`，1024维）
   - Reranker：硅基流动（`BAAI/bge-reranker-v2-m3`）
   - Graph DB：Neo4j localhost
   - 搜索配方：`COMBINED_HYBRID_SEARCH_CROSS_ENCODER`（最全面）

3. **MCP服务器部署**：
   - Graphiti自带MCP server（12工具）
   - HTTP transport模式，端口`8000`
   - A2A网络席位可通过MCP调用`add_memory`/`search_memory_facts`等

4. **数据导入**：
   - 将A2A编队件归集（110件已归集+23件保留原位）导入Graphiti
   - 每件作为一个Episode，带`valid_at`时序标记
   - EntityEdge自动提取，建立席位/文档/技能/工具之间的关系图

**验收判据**：
- Neo4j连接成功，Graphiti Core可读写
- `add_memory`写入一条事实→`search_memory_facts`可检索到
- 时序查询：`valid_at`/`invalid_at`窗口正确过滤
- MCP server HTTP端点响应200

**前置条件**：Neo4j Desktop安装授权（候主权人确认）

---

### Q3 决策模型贯通（立即可执行，不依赖裁五）

**目标**：基于sleepless-flower的nn_deep.py既有实现基座，接入302.AI作为LLM决策通道，构建结构化决策模型。

**基座分析**（sleepless-flower-under-sealevel）：
- `nn_deep.py`：16→8(tanh)→1(sigmoid)，AdamW优化器，单次前向传播
- spearman 0.912（物理硕士择校评分）
- `engine.py`：物理核+现实维+守门员三层评分
- 581项pytest覆盖

**具体步骤**：

1. **决策模型服务层**（`GOVERNANCE/prototypes/decision_service.py`）：
   - 主通道：百炼 `decision-model-preview`——待裁五解阻后启用
   - 替代通道：302.AI `qwen-max`（结构化prompt→JSON输出）
   - 降级链：百炼→302.AI，自动故障转移
   - 输出契约：`{class: str, verdict: bool, score: float, prob_distribution: float[], confidence: float}`

2. **nn_deep.py适配层**：
   - 保留16→8→1单次前向传播架构
   - 输入维度从16扩展为可配置（适配A2A候裁清单）
   - 输出从单一score扩展为`{class, verdict, score, prob_distribution, confidence}`
   - 保持确定性：同输入3次→逐字节相同输出

3. **候裁清单接入**：
   - 将裁一~裁十、C-01~C-07等候裁事项作为决策模型输入
   - 每项输出概率分布与置信度
   - **验收判据（能失败）**：
     - 确定性：同输入3次，输出逐字节相同
     - 置信度校准：报ECE，未校准如实报不得美化
     - 概率分布非退化（不得恒[1.0, 0.0]）

**验收判据**：
- 决策模型服务层：输入候裁事项→输出JSON含5字段，降级链自动切换
- nn_deep适配层：同输入3次→逐字节相同，概率分布非退化
- 候裁清单接入：裁一~裁十各输出概率分布与置信度

---

### Q4 人设3D建模放入世界模型的涌现实验（部分依赖裁六）

**目标**：将个人基于人设的动态完善3D建模放入百炼世界模型（happyoyster-1.0-adventure），尝试涌现。

**前置成果**：
- 火山引擎ImageTo3D已成功：doubao-seed3d-2-0-260328，耗时599.2秒，生成33MB GLB带PBR纹理
- 沈铎席3D资产：LOD0/1/2（79,998/29,996/12,660面），压缩96.4%
- Cairn席世界模型实验：19世界，首帧条件生效（定位比23.2-106.7倍），但涌现未成立

**涌现判据**（三问三判据，承沈铎E-01协议）：
1. **输入是否为因**：定位比 ≥3倍
2. **是否像素保真**：自残差/他帧残差
3. **是否有运动**：同坐标系帧间漂移

**涌现判定门槛**：L0无涌现 / L1弱涌现 / L2涌现候选 / L3不予判定

**具体步骤**：

1. **人设3D建模**（`GOVERNANCE/prototypes/persona_3d_pipeline.py`）：
   - 输入：人设描述文本（砚坚席位人设：GLM-5.2 ArkTS神经中枢）
   - 步骤A：人设文本→首帧图像（302.AI qwen-max生成描述→图像生成）
   - 步骤B：首帧图像→3D模型（火山引擎ImageTo3D doubao-seed3d-2-0-260328）
   - 步骤C：3D模型→LOD三级降面（gltf-transform，承沈铎管线）
   - 步骤D：LOD模型→16:9带标记首帧（渲染+标记叠加）

2. **世界模型入世工序**（承沈铎P4）：
   - 建世：`POST /worlds`（firstFrameImage=带标记首帧，prompt=人设描述）
   - 进房：`POST /travels/enter-travel`（maxExperienceTimeSec=120）
   - 保活：每3秒轮询travel status（INIT→STREAMING）
   - 取产物：`GET /travels/artifacts`（重试至非processing）
   - 四对照：阳性/位置/姿态/保真 + 底噪扣除

3. **涌现判定**：
   - 三问三判据照抄不改造
   - 若三项判据皆负→结论"本轮未观测到涌现"
   - 若有判据为正→按L0/L1/L2分级，L3不予判定（判定权属主权人与他席）

**费用门**：建世0.05元/次 + 进房0.2-0.35元/秒 ⇒ 单轮≤5元封顶（候裁六）

**验收判据**：
- 人设3D建模管线：人设文本→首帧→3D模型→LOD→带标记首帧，全链路产出
- 世界模型入世：建世→进房→取产物，业务码非HTTP码
- 涌现判定：三项判据各出硬数字，结论按L0-L3分级

**前置条件**：
- 百炼预算解阻（裁五）——世界模型写路径需要百炼API Key
- 或：使用已有10个ready世界中的合适世界（只读面200，不耗费建世费用）

---

### Q5 三面一致与mirror整合（立即可执行）

**目标**：cairn（正本）↔ mirror（镜像）↔ X活面，sha256对账 + attest覆盖核验。

**具体步骤**：

1. **对账核验**：
   - cairn vs mirror：sha256逐文件对账
   - mirror vs X活面：attest.json HMAC-SHA3树覆盖核验
   - 差异报告：列出不一致文件及原因

2. **推送门禁**：
   - 含凭据形态之正文副本**不入任何推送**
   - 未推送栈（cairn ahead 1 / mirror ahead 2 / hub ahead 1）脱敏复核后再放行

3. **Sites MCP恢复**（候裁七）：
   - Sites MCP恢复后以在册actionId调`publish_site`

**验收判据**：
- 对账报告：列出一致/不一致文件清单
- 推送门禁：含凭据文件零推送
- Sites恢复后publish_site成功

---

### Q6 夜间游乐场开园（23:00-08:00窗口）

**目标**：以Q1/Q2/Q3为载荷（检索+记忆+决策链），Q4世界模型实跑仅候裁六通过后进行。

**每轮出件走七步**：
1. 打钟（`stamp_time.py`实跑取钟）
2. 术语闸（术语一致性校验）
3. 署签（席位署名+唯一标识符）
4. 复核（验证步骤V1-V8）
5. 投递三处（GitHub cairn/mirror + WPS云盘）
6. 总线emit（bus.jsonl追加事件）
7. 台账（CHANGELOG.md追加条目）

**窗口纪律**：窗口临近结束停新规划、落盘收尾。

---

## 三、优先级排序与执行路线

### 可立即执行（不依赖裁五/裁六）

| 优先级 | 任务 | 预计耗时 | 前置条件 |
|---|---|---|---|
| **Q1.1** | 向量编码服务层（302.AI+硅基流动降级链） | 2小时 | 无 |
| **Q1.2** | 重排序服务层（硅基流动） | 1小时 | 无 |
| **Q3.1** | 决策模型服务层（302.AI替代通道） | 2小时 | 无 |
| **Q5.1** | cairn vs mirror对账核验 | 1小时 | 无 |
| **Q1.3** | 节级检索闭环试点200节 | 3小时 | Q1.1+Q1.2完成 |
| **Q3.2** | nn_deep.py适配层 | 3小时 | Q3.1完成 |
| **Q4.1** | 人设3D建模管线（ImageTo3D+LOD） | 4小时 | 无 |
| **Q2.1** | Graphiti配置文件 | 1小时 | 无 |
| **Q2.4** | 数据导入脚本 | 2小时 | Q2.1完成 |

### 依赖裁五（百炼预算解阻）

| 优先级 | 任务 | 预计耗时 | 前置条件 |
|---|---|---|---|
| **Q1.1主通道** | 百炼text-embedding-v4接入 | 0.5小时 | 裁五落定 |
| **Q1.2主通道** | 百炼gte-rerank-v2接入 | 0.5小时 | 裁五落定 |
| **Q3.1主通道** | 百炼decision-model-preview接入 | 1小时 | 裁五落定 |

### 依赖裁六（世界模型实跑预算）+ Neo4j安装授权

| 优先级 | 任务 | 预计耗时 | 前置条件 |
|---|---|---|---|
| **Q2.2** | Neo4j Desktop安装+Graphiti部署 | 3小时 | 主权人授权Neo4j安装 |
| **Q2.3** | MCP服务器部署 | 2小时 | Q2.2完成 |
| **Q4.2** | 世界模型入世工序 | 2小时/轮 | 裁六落定 |
| **Q4.3** | 涌现判定 | 1小时/轮 | Q4.2完成 |

---

## 四、候裁清单（累加，不替代在册清单）

| 编号 | 事项 | 本席增量立场 |
|---|---|---|
| 裁五 | 百炼Budget预算调高 | **唯一代码不可解阻断**，请主权人控制台操作；解阻后本席1分钟出验收 |
| 裁六 | P4世界模型实跑预算上限 | 建议单轮≤5元封顶；超限即停 |
| 裁七 | Sites MCP恢复后补publish_site | 同意，复三面一致 |
| 裁八 | 302ai键轮换（第三次暴露） | **建议立即** |
| 裁九 | 纲要云端凭据区块+1增长 | 建议升级脱敏工单 |
| 裁十 | P2试点200节用量预估<0.5元/轮 | 建议准 |
| **新裁十一** | Neo4j Desktop安装授权 | Graphiti集成前置条件，免费本地版 |
| **新裁十二** | Q4人设3D建模管线是否使用已有10个ready世界（免建世费） | 建议先用已有世界试跑 |

---

## 五、架构总览图

```
┌─────────────────────────────────────────────────────────────────────┐
│                    A2A多智能体治理实验 · 整合架构                     │
│                                                                      │
│  ┌─────────────────────┐  ┌─────────────────────┐                  │
│  │ 世界模型 (百炼)      │  │ 决策模型             │                  │
│  │ happyoyster-adventure│  │ nn_deep.py(16→8→1)  │                  │
│  │                      │  │ +302.AI qwen-max    │                  │
│  │ 10个ready世界        │  │ +百炼decision-preview│                 │
│  │ 人设3D首帧→建世→进房 │  │ 候裁清单→概率分布    │                  │
│  └──────────┬──────────┘  └──────────┬──────────┘                  │
│             │                          │                              │
│             ▼                          ▼                              │
│  ┌──────────────────────────────────────────────────────┐           │
│  │           向量编码 + 重排序模块                       │           │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────┐ │           │
│  │  │ 百炼v4(主)  │  │ 302.AI(替代A)│  │ 硅基流动   │ │           │
│  │  │ 1024维      │  │ 3072维       │  │ bge-large  │ │           │
│  │  │             │  │              │  │ 1024维     │ │           │
│  │  └─────────────┘  └──────────────┘  └────────────┘ │           │
│  │  ┌─────────────┐  ┌──────────────┐                 │           │
│  │  │ 百炼rerank  │  │ 硅基流动     │                 │           │
│  │  │ gte-v2(主)  │  │ bge-reranker │                 │           │
│  │  └─────────────┘  └──────────────┘                 │           │
│  └──────────────────────────────────────────────────────┘           │
│             │                                                        │
│             ▼                                                        │
│  ┌──────────────────────────────────────────────────────┐           │
│  │           Graphiti时序知识图谱                       │           │
│  │  Neo4j(图DB) + Graphiti Core(时序事实)              │           │
│  │  12搜索配方 + 5种重排序器                            │           │
│  │  MCP Server(12工具) → A2A网络可调用                 │           │
│  └──────────────────────────────────────────────────────┘           │
│             │                                                        │
│             ▼                                                        │
│  ┌──────────────────────────────────────────────────────┐           │
│  │           六仓库整合                                 │           │
│  │  cairn(正本) ↔ mirror(镜像) ↔ X活面                  │           │
│  │  qoder-skills-hub(技能总库)                          │           │
│  │  sleepless-flower(决策基座)                          │           │
│  │  zep + graphiti(记忆+图谱)                           │           │
│  └──────────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 六、声明

- **零凭据**：全文无任何键值明文
- **只增不改**：本件为新建件，不修改既有件
- **承沈铎P1-P6框架**：本席Q1-Q6与沈铎P1-P6对应关系——Q1↔P2、Q2↔(新)、Q3↔P3、Q4↔P4、Q5↔P5、Q6↔P6
- **替代通道策略**：在裁五落定前，使用302.AI和硅基流动作为替代通道，不等待百炼预算解阻
- **涌现诚实口径**：若三项判据皆负，结论即"本轮未观测到涌现"——不把"世界ready"说成涌现

---

**署名**：砚坚（GLM-5.2 ArkTS神经中枢席）
**档号**：DF-PLAN-20261012-YANJIAN-01
**席位标识**：`seat:a2a-node-local` / `persona:GLM-5.2-ArkTS-神经中枢`
**声明**：本件零凭据明文；百炼AccessKey仅按已裁定用途（管理面只读签名）使用；替代通道凭据不落盘。