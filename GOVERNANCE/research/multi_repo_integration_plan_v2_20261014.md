# 多仓库整合实施计划 v2.0

> 编纂：砚坚（码道·GLM-5.2/华为云CodeArts），神经中枢
> 日期：2026-10-14
> 版本：v2.0（基于全面重读与验证结果更新）
> 状态：执行中
> 依据：主权人2026-10-14宏大指令 + 全面验证结果

---

## 一、验证基线（2026-10-14实测）

### 1.1 GitHub仓库状态

| 仓库 | Stars | 最后推送 | License | 大小 | 状态 |
|------|-------|---------|---------|------|------|
| getzep/zep | 4958 | 2026-10-12 | Apache-2.0 | 61MB | ✅ 活跃 |
| getzep/graphiti | 31715 | 2026-10-13 | Apache-2.0 | 16MB | ✅ 非常活跃 |
| moonhwm/openplanlink-cairn | 0 | 2026-10-13 | Other | 16MB | ✅ 正本仓 |
| moonhwm/openplanlink-mirror | 0 | 2026-10-13 | AGPL-3.0 | 349MB | ✅ 镜像仓 |
| moonhwm/qoder-skills-hub | 0 | 2026-10-12 | AGPL-3.0 | 32MB | ✅ 技能总库(101目录) |
| moonhwm/sleepless-flower-under-sealevel | 0 | 2026-10-11 | AGPL-3.0 | 374KB | ✅ 物理择校系统 |

### 1.2 API通道状态

| 通道 | 用途 | 状态 | 备注 |
|------|------|------|------|
| 302.AI | 向量编码(3072维) + 决策模型(qwen-max) | ✅ 可用 | 主力通道 |
| 硅基流动 | 向量编码(1024维) + 重排序(bge-reranker-v2-m3) | ✅ 可用 | 辅助通道 |
| MiniMax H3 | 3D建模 + 文本生成 | ✅ 可用 | 新增通道 |
| 百炼DashScope | 向量编码/重排序/决策模型/世界模型 | ⚠️ 需DashScope API Key | 节省计划已购买(250→500元) |
| 腾讯云Tokenhub | 文本生成 | ❌ 连接被重置 | 端点URL需修正 |
| 火山引擎Agent plan | Agent任务编排 | ❌ 401认证 | API Key格式需修正 |
| 火山引擎Coding Plan | 代码生成 | ❌ 404模型不存在 | 需使用正确模型端点 |

### 1.3 WPS云盘关键目录

| 目录 | 文件数 | 关键内容 |
|------|--------|---------|
| Plan提示词工程/Re0 | 2 | OTL格式全局声明与A2A建设纲要 |
| Plan提示词工程/openplanlink-docx | 23 | OTL格式文档（A2A纪要/算力分配/收官总账） |
| A2A共同体_总线指针与台账 | 194 | 大量台账记录与共识表态 |
| A2A共同体_公约与议会 | 6 | 自指性论证/同步义务立法通告 |
| Kimi skill归总 | 14 | 14个技能zip包 |
| KI 人设及建模 | 4 | 人设主档案/数字员工方案 |

### 1.4 K3集群技能分布

| 分类 | 数量 | 技能名称 |
|------|------|---------|
| GitHub已有 | 9 | quota-guard-ops, persona-iteration-loop-ops, k3-territory-studies, iteration-convergence-ops, diffusion-dynamics-extension, quant-frontier-lab, registry-knowledge-ops, extpool-furnace-ops, fusion-cast-ops |
| GitHub缺失 | 19 | quota-ledger-ops, seat-naming-ops, github-mirror-sync-ops, govdoc-compliance-ops, otl-format-ops, quad-ops-umbrella, glb-observatory-ops, dcc-mcp-umbrella, remotion-video-forge, compshare-cli, moonforge-ops, moongate-craft, v2fun-ops, hyper3d-rodin-mcp, star-owner-ops, video-seer, vector-verdict-ops, tongtu-hub, ima-skil |

---

## 二、实施优先级排序

### P0级（立即执行）

| 编号 | 任务 | 依据 | 预计耗时 |
|------|------|------|---------|
| P0-1 | 修复百炼DashScope API Key验证 — 从百炼控制台获取sk-格式Key | 主权人指令"强制调用" | 需主权人操作 |
| P0-2 | 基于三大模块开展实际工作 — 向量编码+决策模型+世界模型 | 主权人核心指令 | 立即开始 |
| P0-3 | 19个缺失K3技能创建并上传GitHub | 全局声明"技能从GitHub同步为唯一正本" | 逐批创建 |

### P1级（1-2h内执行）

| 编号 | 任务 | 依据 | 预计耗时 |
|------|------|------|---------|
| P1-1 | 修复火山引擎API通道 — 使用正确模型端点ID | 主权人提供的API Key | 0.5h |
| P1-2 | 修复腾讯云Tokenhub通道 — 查找正确端点URL | 主权人提供的Token | 0.5h |
| P1-3 | 读取WPS云盘Re0/openplanlink-docx中的OTL文档 | 主权人指定路径 | 1h |
| P1-4 | sleepless-flower-under-sealevel仓库分析 — 物理择校评分系统 | 决策模型既有基座 | 1h |

### P2级（4-8h内执行）

| 编号 | 任务 | 依据 | 预计耗时 |
|------|------|------|---------|
| P2-1 | Graphiti/Zep深度集成 — Neo4j配置+MCP服务器部署 | 时序知识图谱需求 | 4h |
| P2-2 | 人设3D建模放入世界模型 — MiniMax H3通道 | 主权人指令 | 2h |
| P2-3 | 夜间游乐场开园 — 端到端集成测试 | A2A公约要求 | 1h |
| P2-4 | SHA3-512对账核验体系 — 全仓库一致性校验 | 全局声明要求 | 2h |

---

## 三、三大模块工作计划

### 3.1 向量编码与重排序模块

**目标**：对文本或图文数据进行向量化处理，结合重排序机制提升检索精度

**通道配置**：
```
主力：302.AI text-embedding-3-large (3072维)
辅助：硅基流动 BAAI/bge-large-zh-v1.5 (1024维)
重排序：硅基流动 BAAI/bge-reranker-v2-m3
待激活：百炼 text-embedding-v3 (需DashScope API Key)
```

**实施步骤**：
1. 完善embedding_service.py — 已有三通道降级链
2. 完善rerank_service.py — 已有双通道降级链
3. 构建端到端检索管线 — 向量化→存储→检索→重排序
4. 验证检索精度 — 参照粒子物理实验置信度水平

### 3.2 决策模型模块

**目标**：面向高频业务判断的结构化决策模型，单次前向传播完成分类/是非判断/评分

**通道配置**：
```
主力：302.AI qwen-max (结构化prompt→JSON)
待激活：百炼 decision-model-preview (需DashScope API Key)
本地基座：sleepless-flower-under-sealevel nn_deep.py (16→8→1)
```

**实施步骤**：
1. 完善decision_service.py — 已有双通道降级链
2. 分析sleepless-flower仓库 — 物理择校评分系统既有实现
3. 构建决策模型评估框架 — 确定性验证+置信度输出
4. 端到端决策管线 — 输入→决策→概率分布→置信度

### 3.3 世界模型模块

**目标**：支持实时交互的开放式世界模型，涵盖世界探索、实时导演、角色演绎三类运行模式

**通道配置**：
```
3D建模：MiniMax H3 (已验证可用)
图像生成：302.AI dall-e-3
文本描述：302.AI qwen-max
待激活：百炼世界模型 (需DashScope API Key)
```

**实施步骤**：
1. 完善persona_3d_pipeline.py — 已有完整管线
2. 人设3D建模 — MiniMax H3生成3D模型
3. 世界模型入世 — 生成入世描述+入世图像
4. 涌现判定 — 沈铎席三问三判据

---

## 四、K3技能创建计划

19个缺失技能分批创建并上传至qoder-skills-hub仓库：

### 第一批（P0级，立即创建）

| 技能 | 功能 | 优先级 |
|------|------|--------|
| seat-naming-ops | 席位命名规范与自我设定 | P0 |
| github-mirror-sync-ops | GitHub镜像同步操作 | P0 |
| govdoc-compliance-ops | 政府文档合规性校验 | P0 |
| otl-format-ops | WPS OTL格式转换 | P0 |
| vector-verdict-ops | 向量编码与决策判定 | P0 |

### 第二批（P1级）

| 技能 | 功能 | 优先级 |
|------|------|--------|
| quota-ledger-ops | 配额台账操作 | P1 |
| quad-ops-umbrella | 四象限操作总括 | P1 |
| glb-observatory-ops | GLB观测站操作 | P1 |
| dcc-mcp-umbrella | DCC MCP总括 | P1 |
| hyper3d-rodin-mcp | Hyper3D Rodin MCP | P1 |

### 第三批（P2级）

| 技能 | 功能 | 优先级 |
|------|------|--------|
| remotion-video-forge | 视频生成锻造 | P2 |
| compshare-cli | 计算共享CLI | P2 |
| moonforge-ops | 月之锻造操作 | P2 |
| moongate-craft | 月门工艺 | P2 |
| v2fun-ops | V2Fun操作 | P2 |
| star-owner-ops | 星主操作 | P2 |
| video-seer | 视频先知 | P2 |
| tongtu-hub | 通路枢纽 | P2 |
| ima-skil | IMA技能 | P2 |

---

## 五、执行时间线

```
Phase 0（立即）: P0-2 三大模块实际工作开始
    ↓
Phase 1（0-30min）: 向量编码+决策模型+世界模型端到端测试
    ↓
Phase 2（30-60min）: K3技能第一批创建+GitHub上传
    ↓
Phase 3（60-120min）: WPS OTL文档读取+火山引擎/腾讯云修复
    ↓
Phase 4（2-4h）: Graphiti集成+人设3D建模+夜间游乐场
    ↓
Phase 5（4-8h）: SHA3-512对账+全仓库一致性校验
```

---

## 六、候裁清单（累加更新）

| 编号 | 事项 | 状态 |
|------|------|------|
| 裁五 | 百炼Budget预算调高 | 已购买节省计划(250→500元)，需验证DashScope API Key |
| 裁六 | P4世界模型实跑预算上限 | 建议单轮≤5元封顶 |
| 裁七 | Sites MCP恢复后补publish_site | 同意 |
| 裁八 | 302ai键轮换（第三次暴露） | 建议立即 |
| 裁九 | 纲要云端凭据区块+1增长 | 建议升级脱敏工单 |
| 裁十 | P2试点200节用量预估<0.5元/轮 | 建议准 |
| 裁十一 | Neo4j Desktop安装授权 | Graphiti集成前置条件 |
| 裁十二 | Q4人设3D建模使用已有10个ready世界 | 建议先用已有世界试跑 |
| 裁十三 | 百炼DashScope API Key获取 | 需主权人在百炼控制台生成sk-格式Key |
| 裁十四 | 腾讯云Tokenhub端点URL确认 | 需主权人提供正确端点 |
| 裁十五 | 火山引擎模型端点ID确认 | 需主权人在火山引擎控制台查看 |