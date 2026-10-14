# Graphiti代码结构分析报告（P1阶段产出）

> 署名：砚坚（GLM-5.2 ArkTS神经中枢席）· seat_key yanjian-glm52-arkts
> 创建：2026-10-12
> 阶段：P1 代码结构全量分析
> 版本：graphiti-core 0.30.2

---

## 一、仓库总体结构

### 1.1 Graphiti仓库（getzep/graphiti）

```
graphiti/
├── graphiti_core/          # 核心库（22个模块）
│   ├── graphiti.py         # 主类入口（2192行）
│   ├── nodes.py            # 节点模型（EntityNode/EpisodicNode/CommunityNode/SagaNode）
│   ├── edges.py            # 边模型（EntityEdge/EpisodicEdge/CommunityEdge）
│   ├── graphiti_types.py   # 类型定义与客户端封装
│   ├── graph_queries.py    # 图查询语句
│   ├── helpers.py          # 辅助函数
│   ├── decorators.py       # 装饰器
│   ├── errors.py           # 错误定义
│   ├── tracer.py           # OpenTelemetry追踪
│   ├── driver/             # 图数据库驱动层
│   │   ├── driver.py       # 抽象驱动接口
│   │   ├── neo4j_driver.py # Neo4j驱动
│   │   ├── falkordb_driver.py # FalkorDB驱动
│   │   ├── kuzu_driver.py  # Kuzu驱动（已弃用）
│   │   └── neptune_driver.py # Amazon Neptune驱动
│   ├── embedder/           # 嵌入模块
│   │   ├── client.py       # 嵌入客户端接口
│   │   ├── openai.py       # OpenAI嵌入
│   │   ├── gemini.py       # Gemini嵌入
│   │   ├── voyage.py       # Voyage嵌入
│   │   └── azure_openai.py # Azure OpenAI嵌入
│   ├── llm_client/         # LLM客户端层
│   │   ├── client.py       # LLM客户端接口
│   │   ├── openai_client.py # OpenAI客户端
│   │   ├── anthropic_client.py # Anthropic客户端
│   │   ├── gemini_client.py # Gemini客户端
│   │   ├── openai_generic_client.py # OpenAI兼容端点客户端
│   │   └── azure_openai_client.py # Azure OpenAI客户端
│   ├── cross_encoder/      # 重排序模块
│   │   ├── client.py       # 重排序客户端接口
│   │   ├── openai_reranker_client.py # OpenAI重排序
│   │   ├── gemini_reranker_client.py # Gemini重排序
│   │   └── bge_reranker_client.py # BGE重排序
│   ├── search/             # 搜索模块
│   │   ├── search.py       # 搜索主逻辑
│   │   ├── search_config.py # 搜索配置
│   │   ├── search_config_recipes.py # 12个预设搜索配方
│   │   ├── search_filters.py # 搜索过滤器
│   │   ├── search_helpers.py # 搜索辅助
│   │   └── search_utils.py # 搜索工具
│   ├── models/             # 数据模型与DB查询
│   ├── namespaces/         # 命名空间管理
│   ├── prompts/            # Prompt构建系统
│   ├── migrations/         # 数据库迁移
│   ├── telemetry/          # 遥测（PostHog）
│   └── utils/              # 工具函数
│       ├── bulk_utils.py   # 批量操作
│       ├── datetime_utils.py # 日期时间工具
│       ├── maintenance/    # 图谱维护
│       │   ├── community_operations.py # 社区操作
│       │   ├── dedup_helpers.py # 去重辅助
│       │   ├── edge_operations.py # 边操作
│       │   ├── node_operations.py # 节点操作
│       │   └── graph_data_operations.py # 图数据操作
│       ├── ontology_utils/ # 本体工具
│       └── text_utils.py   # 文本工具
├── mcp_server/             # MCP服务器
│   ├── main.py             # 入口
│   ├── src/
│   │   ├── graphiti_mcp_server.py # MCP服务器实现
│   │   ├── config/         # 配置
│   │   ├── models/         # 响应类型
│   │   ├── services/       # 服务层
│   │   └── utils/          # 工具
│   └── tests/              # 测试
├── server/                 # REST API服务器
├── examples/               # 示例代码
├── tests/                  # 测试
├── spec/                   # 规范
├── signatures/             # 类型签名
└── docker-compose.yml      # Docker部署
```

### 1.2 Zep仓库（getzep/zep）

```
zep/
├── examples/               # 示例代码（Python/TypeScript/Go）
├── integrations/           # 框架集成包
│   ├── langgraph/python/   # LangGraph集成
│   ├── crewai/python/      # CrewAI集成
│   ├── autogen/python/     # AutoGen集成
│   └── ...                 # 更多框架集成
├── ingestion/              # zep-ingest数据摄入管道
├── ontology/               # 默认本体定义
├── mcp/zep-mcp-server/     # Zep MCP服务器
├── benchmarks/             # 性能基准（LoCoMo/LongMemEval）
├── zep-eval-harness/       # 评估工具
└── legacy/                 # 已弃用的社区版
```

---

## 二、核心数据模型

### 2.1 节点模型（Node）

**继承关系**：`Node (ABC)` → `EntityNode` / `EpisodicNode` / `CommunityNode` / `SagaNode`

#### Node基类
| 属性 | 类型 | 说明 |
|------|------|------|
| uuid | str | 唯一标识（自动生成uuid4） |
| name | str | 节点名称 |
| group_id | str | 图分区标识 |
| labels | list[str] | 节点标签 |
| created_at | datetime | 创建时间 |

#### EpisodicNode（原始数据节点）
| 属性 | 类型 | 说明 |
|------|------|------|
| source | EpisodeType | 来源类型（message/json/text/fact_triple） |
| source_description | str | 数据来源描述 |
| content | str | 原始episode数据 |
| valid_at | datetime | 原始文档创建时间 |
| entity_edges | list[str] | 引用的entity edge列表 |
| episode_metadata | dict | 自定义元数据键值对 |

**EpisodeType枚举**：
- `message` — 对话消息，格式为"actor: content"
- `json` — JSON结构化数据
- `text` — 纯文本
- `fact_triple` — 事实三元组

#### EntityNode（实体节点）
- 代表人物、产品、概念等实体
- 摘要随时间演变（summary字段）
- 支持自定义属性（通过Pydantic模型扩展）

#### CommunityNode（社区节点）
- 代表实体社区的聚合
- 包含社区摘要
- 由社区检测算法自动构建

#### SagaNode（叙事节点）
- 代表有序的episode序列
- 包含运行摘要（summary）
- 支持摘要压缩（最多20个episode/摘要）

### 2.2 边模型（Edge）

**继承关系**：`Edge (ABC)` → `EntityEdge` / `EpisodicEdge` / `CommunityEdge` / `HasEpisodeEdge` / `NextEpisodeEdge`

#### Edge基类
| 属性 | 类型 | 说明 |
|------|------|------|
| uuid | str | 唯一标识 |
| group_id | str | 图分区标识 |
| source_node_uuid | str | 源节点UUID |
| target_node_uuid | str | 目标节点UUID |
| created_at | datetime | 创建时间 |

#### EntityEdge（实体关系边）— **核心时序机制**
| 属性 | 类型 | 说明 |
|------|------|------|
| name | str | 关系名称 |
| fact | str | 事实描述（自然语言） |
| fact_embedding | list[float] | 事实嵌入向量 |
| episodes | list[str] | 引用此边的episode列表 |
| **valid_at** | datetime | **事实生效时间** |
| **invalid_at** | datetime | **事实失效时间** |
| **expired_at** | datetime | **节点失效时间** |
| reference_time | datetime | 参考时间（来自episode） |
| attributes | dict | 额外属性 |

**时序事实管理机制**：
- `valid_at`：事实何时变为>变为真（未来计划/承诺使用episode参考时间而非未来发生日期）
- `invalid_at`：事实何时不再为真（软截止不算invalid_at）
- `expired_at`：节点何时被失效（系统级失效）
- 当新事实与旧事实矛盾时，旧事实的`invalid_at`被设置，但旧事实不删除——历史完整保留

#### EpisodicEdge（Episode引用边）
- 连接EpisodicNode到EntityNode（MENTIONS关系）
- 代表"episode提到了entity"

---

## 三、搜索与检索机制

### 3.1 搜索方法（SearchMethod）

| 类型 | 方法 | 说明 |
|------|------|------|
| Edge | `bm25` | 关键词搜索（全文索引） |
| Edge | `cosine_similarity` | 语义嵌入余弦相似度搜索 |
| Edge | `bfs` | 广度优先图遍历 |
| Node | `bm25` | 关键词搜索 |
| Node | `cosine_similarity` | 语义嵌入搜索 |
| Node | `bfs` | 广度优先图遍历 |
| Episode | `bm25` | 关键词搜索 |
| Community | `bm25` | 关键词搜索 |
| Community | `cosine_similarity` | 语义嵌入搜索 |

### 3.2 重排序器（Reranker）

| 重排序器 | 说明 | 适用场景 |
|---------|------|---------|
| `rrf` | Reciprocal Rank Fusion | 多路搜索结果融合 |
| `mmr` | Maximal Marginal Relevance | 去重+多样性 |
| `cross_encoder` | Cross-Encoder重排序 | 最高精度排序 |
| `node_distance` | 节点距离重排序 | 图遍历距离排序 |
| `episode_mentions` | Episode提及重排序 | 按提及频率排序 |

### 3.3 预设搜索配方（12个）

| 配方名 | 搜索范围 | 搜索方法 | 重排序器 |
|--------|---------|---------|---------|
| `COMBINED_HYBRID_SEARCH_RRF` | Edge+Node+Episode+Community | bm25+cosine | RRF |
| `COMBINED_HYBRID_SEARCH_MMR` | Edge+Node+Episode+Community | bm25+cosine | MMR |
| `COMBINED_HYBRID_SEARCH_CROSS_ENCODER` | Edge+Node+Episode+Community | bm25+cosine+bfs | Cross-Encoder |
| `EDGE_HYBRID_SEARCH_RRF` | Edge | bm25+cosine | RRF |
| `EDGE_HYBRID_SEARCH_MMR` | Edge | bm25+cosine | MMR |
| `EDGE_HYBRID_SEARCH_NODE_DISTANCE` | Edge | bm25+cosine | Node-Distance |
| `EDGE_HYBRID_SEARCH_EPISODE_MENTIONS` | Edge | bm25+cosine | Episode-Mentions |
| `EDGE_HYBRID_SEARCH_CROSS_ENCODER` | Edge | bm25+cosine+bfs | Cross-Encoder |
| `NODE_HYBRID_SEARCH_RRF` | Node | bm25+cosine | RRF |
| `NODE_HYBRID_SEARCH_MMR` | Node | bm25+cosine | MMR |
| `NODE_HYBRID_SEARCH_NODE_DISTANCE` | Node | bm25+cosine | Node-Distance |
| `NODE_HYBRID_SEARCH_CROSS_ENCODER` | Node | bm25+cosine+bfs | Cross-Encoder |

### 3.4 搜索过滤器（SearchFilters）

支持按以下维度过滤：
- `group_ids` — 按图分区过滤
- `entity_types` / `node_labels` — 按实体类型过滤
- `edge_types` / `fact_types` — 按边类型过滤
- `valid_at` / `invalid_at` 日期范围 — **按时序过滤**

---

## 四、MCP服务器接口

### 4.1 MCP工具清单

| 工具名 | 功能 | 关键参数 |
|--------|------|---------|
| `add_memory` | 添加episode | text/group_id/reference_time/excluded_entity_types/custom_extraction_instructions/previous_episode_uuids/update_communities/saga |
| `add_triplet` | 直接写入事实 | source_entity/fact/target_entity/group_id |
| `search_nodes` | 搜索实体 | query/group_ids/entity_type/center_node_uuid |
| `search_memory_facts` | 搜索事实 | query/group_ids/edge_type/valid_at/invalid_at |
| `summarize_saga` | 生成saga摘要 | saga_uuid |
| `build_communities` | 构建社区 | group_id |
| `get_episode_entities` | 追踪溯源 | episode_uuids |
| `get_entity_edge` | 获取特定事实 | edge_uuid |
| `get_episodes` | 获取特定episode | episode_uuids |
| `delete_episode` | 删除episode | episode_uuid |
| `delete_entity_edge` | 删除事实 | edge_uuid |
| `clear_graph` | 清除组数据 | group_id |

### 4.2 MCP服务器配置

- 支持FalkorDB和Neo4j两种数据库后端
- 支持自定义实体类型和边类型（Pydantic模型）
- 支持边类型约束（edge_type_map）
- 信号量控制并发（SEMAPHORE_LIMIT，默认10）
- 双时序模型：reference_time设置事件发生时间

### 4.3 MCP部署命令

```bash
# FalkorDB后端
OPENAI_API_KEY=<key> FALKORDB_URI=redis://localhost:6379 \
  python main.py --transport http --host 0.0.0.0 --port 8001 --database-provider falkordb

# Neo4j后端
OPENAI_API_KEY=<key> NEO4J_URI=bolt://localhost:7687 \
  python main.py --transport http --host 0.0.0.0 --port 8001 --database-provider neo4j
```

---

## 五、Graphiti主类API

### 5.1 构造函数参数

| 参数 | 类型 | 说明 |
|------|------|------|
| uri | str | Neo4j数据库URI |
| user/password | str | 认证凭据 |
| llm_client | LLMClient | LLM客户端（默认OpenAIClient） |
| embedder | EmbedderClient | 嵌入客户端（默认OpenAIEmbedder） |
| cross_encoder | CrossEncoderClient | 重排序客户端（默认OpenAIRerankerClient） |
| graph_driver | GraphDriver | 图数据库驱动（默认Neo4jDriver） |
| max_coroutines | int | 最大并发数 |
| prompt_library | ChatPromptLibrary | 自定义Prompt库 |
| llm_runtime | LLMRuntime | 多LLM路由运行时 |

### 5.2 核心方法（从import推断）

| 方法 | 功能 |
|------|------|
| `add_episode()` | 添加episode（触发Entity/Edge提取） |
| `add_episode_bulk()` | 批量添加episode |
| `add_triplet()` | 直接添加事实三元组 |
| `search()` | 混合搜索（语义+关键词+图遍历） |
| `build_indices_and_constraints()` | 构建索引和约束 |
| `build_communities()` | 构建社区 |
| `remove_communities()` | 移除社区 |
| `update_community()` | 更新社区 |
| `summarize_saga()` | 生成saga摘要 |

### 5.3 结果类型

| 类型 | 包含 |
|------|------|
| `AddEpisodeResults` | episode + episodic_edges + nodes + edges + communities + community_edges |
| `Add$AddBulkEpisodeResults` | episodes + episodic_edges + nodes + edges + communities + community_edges |
| `AddTripletResults` | nodes + edges |

---

## 六、LLM客户端层

### 6.1 支持的LLM提供商

| 提供商 | 客户端类 |7 | 说明 |
|--------|-----------|------|
| OpenAI | `OpenAIClient` | 默认，支持Structured Output |
| Anthropic | `AnthropicClient` | Claude系列 |
| Gemini | `GeminiClient` | Google Gemini |
| OpenAI兼容 | `OpenAIGenericClient` | DeepSeek/Ollama/vLLM等 |
| Azure OpenAI | `AzureOpenAILLMClient` | Azure部署 |

### 6.2 OpenAI兼容端点（关键集成路径）

`OpenAIGenericClient`支持任何OpenAI `/v1`兼容端点：
- **302.AI**：`https://api.302ai.cn/v1` → qwen-max/qwen-plus
- **硅基流动**：`https://api.siliconflow.cn/v1` → bge-large-zh-v1.5
- 结构化输出模式：`json_schema`（默认）或`json_object`

---

## 七、嵌入层

| 提供商 | 客户端类 | 模型 |
|--------|---------|------|
| OpenAI | `OpenAIEmbedder` | text-embedding-3-small |
| Gemini | `GeminiEmbedder` | embedding-001 |
| Voyage | `VoyageEmbedder` | voyage-3 |
| Azure OpenAI | `AzureOpenAIEmbedderClient` | text-embedding-3-small |

**集成路径**：硅基流动 bge-large-zh-v1.5（1024维）可通过OpenAI兼容端点接入。

---

## 八、环境限制与部署方案

### 8.1 当前环境限制

| 限制 | 影响 | 缓解方案 |
|------|------|---------|
| Windows平台 | FalkorDB Lite（redislite）不支持 | 使用Neo4j Desktop或Docker |
| Docker未安装 | 无法使用Docker Compose部署 | 安装Docker Desktop或Neo4j Desktop |
| 系统内存15.7GB | 内存紧张 | 关闭不必要进程 |

### 8.2 推荐部署方案

**方案A：Neo4j Desktop（Windows原生）**
1. 下载安装Neo4j Desktop
2. 创建本地数据库实例
3. 使用Neo4jDriver连接

**方案B：Docker Desktop + FalkorDB**
1. 安装Docker Desktop for Windows
2. `docker run -p 6379:6379 falkordb/falkordb:latest`
3. 使用Falkor?Driver连接

**方案C：远程服务器部署**
1. 在幻16桥接节点（120.46.86.165）上部署Neo4j/FalkorDB
2. 通过SSH隧道连接

---

## 九、与A2A治理实验的集成映射

### 9.1 数据映射方案

| A2A治理实验概念 | Graphiti模型 | 映射方式 |
|----------------|-------------|---------|
| AI席位（砚坚/Cairn/沈铎/见霜） | EntityNode | 每个席位=一个EntityNode |
| 席位人设九维度锚点 | EntityEdge (attributes) | 每个锚点=一条EntityEdge |
| 锚点值更新 | EntityEdge时序机制 | 新Edge的valid_at=更新时间，旧Edge的invalid_at=更新时间 |
| 交互历史 | EpisodicNode | 每次交互=一个Episode |
| 决策记录 | EntityEdge (fact) | 每个决策=一条事实 |
| 候裁清单 | EntityEdge + valid_at/invalid_at | 裁决结果=新事实，旧状态自动失效 |
| 技能文档 | EntityNode + labels=["Skill"] | 每个技能=一个EntityNode |
| CHANGELOG条目 | EpisodicNode (type=text) | 每条变更=一个Episode |

### 9.2 搜索场景映射

| 搜索需求 | Graphiti搜索配方 |
|---------|-----------------|
| "砚坚在2026-10-11的anchor_A_identity值" | search_memory_facts + valid_at/invalid_at过滤 |
| "与百炼预算闸相关的所有事实" | COMBINED_HYBRID_SEARCH_RRF |
| "所有席位的人设演变历史" | search_nodes + bfs遍历 |
| "最近一周的交互记录" | get_episodes + 时间过滤 |
| "与签名配置相关的技能" | NODE_HYBRID_SEARCH_RRF |

---

## 十、P2 深入分析：搜索/驱动/LLM客户端/嵌入/重排序

### 10.1 搜索系统内部机制（search.py）

**核心搜索流程**：
1. `search()` 函数接收 `GraphitiClients`（封装driver/embedder/cross_encoder/tracer），根据SearchConfig决定搜索范围
2. 如果配置了cosine_similarity搜索或MMR重排序，先调用 `embedder.create()` 生成查询向量
3. 通过 `semaphore_gather()` 并发执行4路搜索：edge_search / node_search / episode_search / community_search
4. 每路搜索内部按配置的search_methods（bm25/cosine/bfs）生成候选集，再用reranker排序

**edge_search 详细流程**：
- 根据search_methods构建搜索任务列表：
  - `bm25` → `edge_fulltext_search()` — Cypher全文索引查询，使用Lucene语法
  - `cosine_similarity` → `edge_similarity_search()` — 向量余弦相似度查询，min_score过滤
  - `bfs` → `edge_bfs_search()` — 从origin节点广度优先遍历，max_depth控制深度
- 如果配置了bfs但没有提供bfs_origin_node_uuids，先用其他方法的结果节点作为BFS起点做二次扩展
- 重排序阶段：
  - `rrf` — Reciprocal Rank Fusion，多路结果融合（1/rank加权）
  - `mmr` — Maximal Marginal Relevance，加载候选边嵌入向量，lambda控制多样性/相关性平衡
  - `cross_encoder` — 先RRF融合，再取top-2L候选，用cross_encoder.rank()精排
  - `node_distance` — 从center_node出发的图距离排序
  - `episode_mentions` — 按episode提及频率排序（复用RRF逻辑）

**关键参数**：
- `DEFAULT_SEARCH_LIMIT = 10` — 默认返回10条结果
- `DEFAULT_MIN_SCORE = 0.6` — cosine相似度默认最低阈值
- `DEFAULT_MMR_LAMBDA = 0.5` — MMR多样性/相关性平衡参数
- `MAX_SEARCH_DEPTH = 3` — BFS最大深度
- `MAX_QUERY_LENGTH = 128` — 全文查询最大词数
- `RELEVANT_SCHEMA_LIMIT = 10` — 相关schema限制
- 候选集大小 = `2 * limit`（先取2倍候选再重排序截断）

### 10.2 驱动层架构（driver.py）

**GraphDriver抽象基类**：
- 继承 `QueryExecutor`，实现 `GraphProvider`枚举（NEO4J/FALKORDB/KUZU/NEPTUNE）
- 核心抽象方法：
  - `execute_query()` — 执行Cypher查询
  - `session()` — 返回GraphDriverSession（支持async context manager）
  - `build_indices_and_constraints()` — 构建索引和约束
  - `delete_all_indexes()` — 删除所有索引
  - `build_fulltext_query()` — 构建全文查询（仅特定provider需要）
  - `transaction()` — 事务上下文管理器（Neo4j支持真事务，其他为no-op wrapper）

**新架构（Phase 1重构）**：
- 驱动通过属性暴露Operations接口：
  - `entity_node_ops` / `episode_node_ops` / `community_node_ops` / `saga_node_ops`
  - `entity_edge_ops` / `episodic_edge_ops` / `community_edge_ops`
  - `has_episode_edge_ops` / `next_episode_edge_ops`
  - `search_ops` / `graph_ops`
- `search_interface` 和 `graph_operations_interface` 为旧接口（向后兼容）
- `with_database()` 方法返回浅拷贝切换数据库（复用同一连接）

**全文索引名称**（环境变量可配）：
- `ENTITY_INDEX_NAME = 'entities'`
- `EPISODE_INDEX_NAME = 'episodes'`
- `COMMUNITY_INDEX_NAME = 'communities'`
- `ENTITY_EDGE_INDEX_NAME = 'entity_edges'`

**Provider特性差异**：
- Neo4j：支持真事务、APL插件、原生全文索引（Lucene语法）
- FalkorDB：自定义全文查询构建器、连接并发问题（AGENTS.md警告）
- Kuzu：简单查询模式、中间节点模型（RelatesToNode_）、已弃用
- Neptune：OpenSearch查询（AOSS）、需要分两步查询

### 10.3 LLM客户端层

**LLMClient抽象基类**（client.py）：
- 核心方法 `generate_response()`：
  1. 应用attribute_extraction_preamble（防止模型把字段描述当值复制）
  2. 如果有response_model，序列化JSON Schema追加到最后一条消息
  3. 添加多语言提取指令（保持原文语言）
  4. 清理输入（去除无效Unicode、零宽字符、控制字符）
  5. 检查缓存（如果启用）
  6. 调用 `_generate_response_with_retry()`（tenacity重试：4次，指数退避5-120秒）
  7. 缓存响应（如果启用）
- 重试条件：RateLimitError / EmptyResponseError / JSONDecodeError / 5xx HTTP错误
- `ModelSize`枚举：small / medium（用于路由不同大小的模型）
- `LLMConfig`：api_key / model / base_url / temperature / max_tokens / small_model

**OpenAIGenericClient**（openai_generic_client.py）— **关键集成路径**：
- 支持任何OpenAI `/v1/chat/completions`兼容端点
- `structured_output_mode`：
  - `json_schema`（默认）— 原生结构化输出，API强制schema
  - `json_object` — 降级模式，schema注入prompt（适用于DeepSeek等不支持json_schema的provider）
- 自动剥离markdown代码围栏（```json ... ```），兼容Ollama/llama.cpp等本地模型
- 不支持缓存（与基类不同）
- 默认max_tokens=16384（兼容本地模型）

**LLMConfig默认值**：
- `DEFAULT_MAX_TOKENS = 16384`
- `DEFAULT_TEMPERATURE = 1`
- 默认model: "gpt-5.5"，small_model: "gpt-4.1-nano"

### 10.4 嵌入层

**EmbedderClient抽象基类**（client.py）：
- `EMBEDDING_DIM = 1024`（环境变量可配）
- `create()` — 单条文本嵌入，返回list[float]
- `create_batch()` — 批量嵌入，返回list[list[float]]（默认raise NotImplementedError）

**OpenAIEmbedder**（openai.py）：
- 支持 AsyncOpenAI 和 AsyncAzureOpenAI 客户端
- 默认模型：`text-embedding-3-small`
- `create()` — 调用 `client.embeddings.create()`，截取前 `embedding_dim` 维
- `create_batch()` — 批量调用，同样截取维度

**集成路径**：
- 硅基流动 bge-large-zh-v1.5（1024维）可通过 OpenAIEmbedder + 自定义base_url接入
- 302.AI的嵌入模型也可通过此路径接入

### 10.5 重排序层

**CrossEncoderClient抽象基类**（client.py）：
- `rank(query, passages)` → `list[tuple[str, float]]`（按相关性降序排列）

**BGERerankerClient**（bge_reranker_client.py）：
- 使用 `sentence-transformers` 库的 `CrossEncoder` 模型
- 模型：`BAAI/bge-reranker-v2-m3`（与硅基流动API使用的模型相同）
- 同步predict方法通过 `run_in_executor` 包装为异步
- 需要安装 `graphiti-core[sentence-transformers]` 扩展

**OpenAIRerankerClient**（通过API调用重排序）：
- 适用于不支持本地sentence-transformers的环境
- 可通过302.AI等OpenAI兼容端点调用

### 10.6 搜索过滤器系统（search_filters.py）

**SearchFilters模型**：
- `node_labels` — 按节点标签过滤（Neo4j用`n:Label1|Label2`语法，Kuzu用`list_has_all`）
- `edge_types` — 按边类型过滤（`e.name in $edge_types`）
- `edge_uuids` — 按边UUID过滤
- `edge_source_node_uuids` / `edge_target_node_uuids` — 按边端点过滤
- `valid_at` / `invalid_at` / `created_at` / `expired_at` — **时序过滤**（支持AND/OR嵌套组合）
- `property_filters` — 自定义属性过滤（PropertyFilter：name + value + operator）

**ComparisonOperator枚举**：
- `equals` / `not_equals` / `greater_than` / `less_than` / `greater_than_equal` / `less_than_equal`
- `is_null` / `is_not_null`

**时序过滤的AND/OR嵌套逻辑**：
- 外层list = OR条件
- 内层list = AND条件
- 例：`valid_at=[[{date: 2026-10-01, op: >=}, {date: 2026-10-31, op: <=}]]` = valid_at在10月1日到10月31日之间

### 10.7 GraphitiClients封装（graphiti_types.py）

**GraphitiClients** — 统一客户端容器：
- `driver: GraphDriver` — 图数据库驱动
- `llm_client: LLMClient` — LLM客户端
- `embedder: EmbedderClient` — 嵌入客户端
- `cross_encoder: CrossEncoderClient` — 重排序客户端
- `tracer: Tracer` — OpenTelemetry追踪器
- `prompt_library` — 自定义Prompt库
- `llm_runtime: LLMRuntime | None` — 多LLM路由运行时
- `max_coroutines: int | None` — 最大并发数

**complete_prompt()方法** — 统一Prompt调用入口：
- 如果有llm_runtime → 走Runtime路径（多LLM路由）
- 否则 → 走Legacy路径（builder → as_messages → llm_client.generate_response）
- 自动解析response_model（从内置注册表获取不可变schema）

### 10.8 Prompt系统（prompts/）

**8个Prompt组**（PromptGroup）：
1. `extract_nodes` — 节点提取（extract_message/extract_json/extract_text/classify_nodes/extract_attributes/extract_summary/extract_summaries_batch/extract_entity_summaries_from_episodes）
2. `dedupe_nodes` — 节点去重（node/node_list/nodes）
3. `extract_edges` — 边提取（edge/extract_attributes/extract_timestamps/extract_timestamps_batch）
4. `extract_nodes_and_edges` — 联合提取（extract_message）
5. `dedupe_edges` — 边去重（resolve_edge）
6. `summarize_nodes` — 节点摘要（summarize_pair/summarize_context/summary_description）
7. `summarize_sagas` — Saga摘要（summarize_saga）
8. `eval` — 评估（query_expansion/qa_prompt/eval_prompt/eval_add_episode_results）

**关键Prompt**：
- `extract_edges.extract_timestamps` — **时序事实管理的核心**：LLM从自然语言中提取事实的valid_at/invalid_at时间戳
- `extract_nodes_and_edges.extract_message` — **联合提取**：从一条消息中同时提取实体和关系（效率优化）
- `dedupe_edges.resolve_edge` — **矛盾解决**：当新事实与旧事实矛盾时，决定如何处理（设置invalid_at vs 保留两者）

---

## 十一、P3 集成架构设计：A2A治理实验映射方案

### 11.1 技术栈选型

| 组件 | 选型 | 理由 |
|------|------|------|
| 图数据库 | Neo4j Desktop（Windows原生） | FalkorDB Lite不支持Windows，Neo4j Desktop无需Docker |
| LLM客户端 | OpenAIGenericClient | 支持302.AI/硅基流动等OpenAI兼容端点 |
| LLM模型 | 302.AI → qwen-max（主）/ qwen-plus（辅） | 已验证可用，支持json_schema结构化输出 |
| 嵌入客户端 | OpenAIEmbedder + 硅基流动base_url | bge-large-zh-v1.5（1024维），与EMBEDDING_DIM默认值匹配 |
| 重排序客户端 | BGERerankerClient（本地） 或 OpenAIRerankerClient（API） | 本地需sentence-transformers，API通过302.AI调用 |
| MCP传输 | HTTP transport | 支持远程访问，适合多席位场景 |

### 11.2 Graphiti实例初始化方案

```python
from graphiti_core import Graphiti
from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.cross_encoder.bge_reranker_client import BGERerankerClient
from graphiti_core.driver.neo4j_driver import Neo4jDriver

# LLM配置 — 302.AI通道
llm_config = LLMConfig(
    api_key=os.environ.get("API_KEY_302"),  # 从环境变量读取
    base_url="https://api.302ai.cn/v1",
    model="qwen-max",
    small_model="qwen-plus",
    temperature=0,
)
llm_client = OpenAIGenericClient(config=llm_config, structured_output_mode='json_schema')

# 嵌入配置 — 硅基流动通道
embedder_config = OpenAIEmbedderConfig(
    api_key=os.environ.get("API_KEY_SILICON"),  # 从环境变量读取
    base_url="https://api.siliconflow.cn/v1",
    embedding_model="BAAI/bge-large-zh-v1.5",
    embedding_dim=1024,
)
embedder = OpenAIEmbedder(config=embedder_config)

# 重排序 — 本地BGE模型
cross_encoder = BGERerankerClient()

# 图数据库驱动 — Neo4j Desktop本地实例
driver = Neo4jDriver(uri="bolt://localhost:7687", user="neo4j", password="<password>")

# Graphiti主实例
graphiti = Graphiti(
    driver=driver,
    llm_client=llm_client,
    embedder=embedder,
    cross_encoder=cross_encoder,
)
```

### 11.3 A2A治理实验数据映射方案（细化）

#### 11.3.1 席位与EntityNode映射

每个AI席位对应一个EntityNode，labels=["Seat"]：

| EntityNode属性 | 映射来源 |
|----------------|---------|
| name | 席位名称（如"砚坚"） |
| summary | 席位当前人设摘要 |
| group_id | "a2a_governance"（统一分区） |
| labels | ["Seat", "<席位类型>"]（如["Seat", "Executor"]） |

#### 11.3.2 人设九维度锚点与EntityEdge映射

每个锚点值对应一条EntityEdge（事实边），连接席位EntityNode到锚点维度EntityNode：

| EntityEdge属性 | 映射来源 |
|----------------|---------|
| name | 锚点维度名（如"anchor_A_identity"） |
| fact | 锚点值的自然语言描述（如"砚坚的身份认同=守护者"） |
| valid_at | 锚点值生效时间 |
| invalid_at | 锚点值被更新时设置（旧值失效） |
| episodes | 引用产生此锚点值的交互Episode |

**时序演变机制**：
- 当砚坚的anchor_A_identity从"守护者"变为"领导者"时：
  1. 旧Edge的invalid_at = 新值的生效时间
  2. 新Edge的valid_at = 新值的生效时间
  3. 旧Edge不删除 — 历史完整保留
  4. 搜索时通过valid_at/invalid_at过滤获取"当前有效"或"历史"值

#### 11.3.3 交互历史与EpisodicNode映射

每次AI席位间的交互对应一个EpisodicNode：

| EpisodicNode属性 | 映射来源 |
|------------------|---------|
| source | EpisodeType.message（对话）或 EpisodeType.json（结构化） |
| content | 交互的完整文本记录 |
| valid_at | 交互发生时间 |
| source_description | 交互场景描述（如"百炼六模块v3调用"） |
| episode_metadata | 自定义元数据（如{"module": "world_explore", "round": 3}） |

#### 11.3.4 候裁清单与EntityEdge映射

每个候裁项对应一条EntityEdge：

| EntityEdge属性 | 映射来源 |
|----------------|---------|
| name | "候裁" |
| fact | 候裁内容描述 |
| valid_at | 候裁提出时间 |
| invalid_at | 裁决完成后设置（裁决结果替代旧状态） |
| attributes | {"status": "pending/resolved", "裁决结果": "...", "裁决时间": "..."} |

#### 11.3.5 技能文档与EntityNode映射

每个技能文档对应一个EntityNode，labels=["Skill"]：

| EntityNode属性 | 映射来源 |
|----------------|---------|
| name | 技能名称 |
| summary | 技能描述 |
| labels | ["Skill", "<技能类型>"]（如["Skill", "governance"]） |

技能与席位之间通过EntityEdge连接：fact="砚坚掌握了seat-naming-ops技能"

### 11.4 搜索场景与搜索配方映射（细化）

| 搜索需求 | 搜索配方 | 过滤器 |
|---------|---------|--------|
| "砚坚当前的anchor_A_identity值" | EDGE_HYBRID_SEARCH_RRF | valid_at <= now AND invalid_at IS NULL |
| "砚坚所有人设锚点的演变历史" | EDGE_HYBRID_SEARCH_EPISODE_MENTIONS | 无时序过滤（返回全部历史） |
| "最近一周所有席位的交互记录" | Episode bm25搜索 | created_at >= 一周前 |
| "与百炼预算闸相关的所有事实" | COMBINED_HYBRID_SEARCH_RRF | 无过滤 |
| "所有待裁决的候裁项" | EDGE_HYBRID_SEARCH_RRF | edge_types=["候裁"], valid_at <= now, invalid_at IS NULL |
| "砚坚掌握了哪些技能" | NODE_HYBRID_SEARCH_RRF + BFS | node_labels=["Skill"], bfs从砚坚节点出发 |

### 11.5 MCP服务器部署方案

```bash
# 本地MCP服务器（Neo4j后端）
set OPENAI_API_KEY=<从环境变量设置>
set NEO4J_URI=bolt://localhost:7687
set NEO4J_USER=neo4j
set NEO4J_PASSWORD=<password>
python main.py --transport http --host 0.0.0.0 --port 8001 --database-provider neo4j
```

MCP服务器暴露12个工具，其他AI席位可通过MCP协议直接调用add_memory/search_memory_facts等工具，实现跨席位知识图谱共享。

---

## 十二、下一步（P4-P8）

| 阶段 | 任务 | 状态 |
|------|------|------|
| P2 | 搜索/驱动/LLM/嵌入/重排序深入分析 | ✅ 完成 |
| P3 | 集成架构设计（A2A治理实验映射方案） | ✅ 完成 |
| P4 | 数据库部署（Neo4j Desktop安装+配置） | 待启动 |
| P5 | 原型实现（Graphiti实例初始化+数据导入） | 待启动 |
| P6 | MCP服务器部署+跨席位集成测试 | 待启动 |
| P7 | 文档与技能沉淀 | 待启动 |
| P8 | 迭代与预留 | 待启动 |