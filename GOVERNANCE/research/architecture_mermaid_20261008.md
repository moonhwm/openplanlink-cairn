# 全链路可视化溯源与调度架构图

> 档号：DF-ARCH-MERMAID-2026-1008-YANJIAN-01
> 拟稿席：砚坚（挂帅席/神经中枢）
> 日期：2026-10-08T10:25 CST
> 体例：党组学术技术成员视角
> 依据：GOVERNANCE/proposals/context_compress_migration_20261007.md

## 一、上下文压缩迁移操作集——全链路架构图

```mermaid
graph TB
    subgraph 输入层
        CTX[当前上下文<br/>完整会话/文档]
        DOC[原始文档<br/>Markdown/JSON/Text]
    end

    subgraph 操作集核心
        CP[context-pruner<br/>上下文裁剪<br/>重复指令/已过期事项/冗余引用]
        UC[ultra-compress-ops<br/>极致压缩<br/>结构识别→关键提取→500字摘要]
        LB[link-bridge-ops<br/>链路桥接<br/>SHA3-512签名→摘要→原文映射]
        LS[ls-bus-format-ops<br/>总线格式化<br/>统一格式→跨席位交换]
    end

    subgraph 存储节点
        WPS[WPS云文档<br/>长期归档+跨端协同<br/>OTL格式]
        NEON[Neon<br/>向量索引+结构化数据<br/>PostgreSQL]
        SUPA[Supabase<br/>实时检索+API服务<br/>REST/GraphQL]
        IMA[ima-skill<br/>知识库沉淀<br/>技能文档]
        BDU[百度云盘<br/>冷归档备份<br/>完整会话记录]
    end

    subgraph 记忆分层架构
        HOT[热数据层<br/>会话级缓存<br/>当前活跃上下文]
        WARM[温数据层<br/>经验级索引<br/>桥接索引+摘要]
        COLD[冷数据层<br/>归档级存储<br/>完整原文+历史记录]
    end

    subgraph A2A总线传输
        BUS[A2A消息总线<br/>JSON-RPC 2.0<br/>kind: experience]
    end

    subgraph 席位消费
        YJ[砚坚席<br/>挂帅席/神经中枢]
        GQ[顾权席<br/>数据策略]
        MOON[Moon席<br/>研究探索]
        KIMI[Kimi席<br/>基础设施]
    end

    %% 输入→操作集
    CTX --> CP
    DOC --> CP
    CP --> UC
    UC --> LB
    LB --> LS

    %% 操作集→存储
    CP -.->|裁剪日志| WARM
    UC -.->|压缩摘要| WARM
    LB -.->|桥接索引| WARM
    LS -.->|总线格式| HOT

    %% 存储→记忆分层映射
    HOT --> SUPA
    WARM --> NEON
    COLD --> BDU
    WPS --> COLD
    IMA --> WARM

    %% 总线传输
    LS --> BUS
    BUS --> YJ
    BUS --> GQ
    BUS --> MOON
    BUS --> KIMI

    %% 追溯链
    LB -.->|追溯验证| DOC
    LS -.->|完整性校验| CTX
```

## 二、操作集内部数据流——详细序列图

```mermaid
sequenceDiagram
    participant U as 用户/席位
    participant CP as context-pruner
    participant UC as ultra-compress-ops
    participant LB as link-bridge-ops
    participant LS as ls-bus-format-ops
    participant S as 存储节点

    U->>CP: 输入完整上下文/文档
    CP->>CP: 扫描标记（重复/过期/冗余）
    CP->>CP: 裁剪移除标记内容
    CP-->>U: 返回裁剪后上下文+裁剪日志

    U->>UC: 输入裁剪后文档
    UC->>UC: 结构识别（标题/列表/表格/代码块）
    UC->>UC: 关键提取（决策/数据/链接/档号）
    UC->>UC: 生成<500字结构化摘要
    UC-->>U: 返回摘要+压缩比报告

    U->>LB: 输入摘要+原文路径
    LB->>LB: 计算SHA3-512签名
    LB->>LB: 建立摘要→原文映射索引
    LB->>LB: 完整性验证（hash比对）
    LB-->>U: 返回桥接索引+验证结果

    U->>LS: 输入文档/摘要
    LS->>LS: 检测来源类型（md/json/skill/changelog）
    LS->>LS: 提取元数据（档号/标题/作者/时间）
    LS->>LS: 结构化分段解析
    LS->>LS: 生成标准总线格式记录
    LS-->>U: 返回总线格式记录+完整性验证

    LS->>S: 迁移至存储节点
    S-->>U: 确认存储完成
```

## 三、记忆分层架构——数据生命周期

```mermaid
graph LR
    subgraph 热数据层
        H1[当前会话上下文]
        H2[活跃任务状态]
        H3[实时轮询数据]
        H4[总线格式记录]
    end

    subgraph 温数据层
        W1[压缩摘要库]
        W2[桥接索引表]
        W3[经验向量索引]
        W4[技能文档引用]
    end

    subgraph 冷数据层
        C1[完整原文归档]
        C2[历史会话记录]
        C3[审计日志]
        C4[变更历史]
    end

    %% 生命周期流转
    H1 -.->|会话结束→归档| W1
    H2 -.->|任务完成→索引| W2
    H3 -.->|过期→冷归档| C2
    H4 -.->|格式化→索引| W3

    W1 -.->|长期→冷归档| C1
    W2 -.->|长期→冷归档| C3
    W3 -.->|长期→冷归档| C4
    W4 -.->|技能更新→归档| C1

    %% 访问频次标注
    H1 -->|高频访问| FA[访问频次: 每轮]
    W1 -->|中频访问| MA[访问频次: 每日]
    C1 -->|低频访问| LA[访问频次: 每周/月]

    %% 延迟敏感度
    H2 -->|毫秒级| MS[延迟敏感: 毫秒]
    W2 -->|秒级| SS[延迟敏感: 秒]
    C2 -->|分钟级| MNS[延迟敏感: 分钟]
```

## 四、A2A网络节点拓扑——当前状态

```mermaid
graph TB
    subgraph 幻16物理桥接层
        HS[serve-handshake.mjs<br/>端口4173<br/>systemd管理]
        NR[node_registry.mjs<br/>端口4174<br/>30s心跳超时]
    end

    subgraph Supabase函数层
        SF[Supabase Edge Function<br/>/functions/v1/app<br/>HTTP 200]
    end

    subgraph 本地席位
        YJ[砚坚席<br/>GLM-5.2 ArkTS<br/>神经中枢]
        GQ[顾权席<br/>Kimi Code<br/>数据策略]
    end

    subgraph 远程席位
        MOON[Moon席<br/>研究探索]
        KIMI[Kimi席<br/>基础设施]
    end

    subgraph GitHub正本
        GH[GitHub仓库<br/>moonhwm/openplanlink-mirror<br/>技能唯一正本]
    end

    %% 通信链路
    YJ -->|HTTP| SF
    SF -->|转发| HS
    HS -->|注册| NR
    NR -->|心跳检测| HS

    YJ -->|git push/pull| GH
    GQ -->|git push/pull| GH
    MOON -->|git push/pull| GH
    KIMI -->|git push/pull| GH

    YJ -.->|A2A消息| SF
    SF -.->|A2A消息| GQ
    SF -.->|A2A消息| MOON

    %% 状态标注
    HS -->|运行中| ST1[状态: active]
    NR -->|运行中| ST2[状态: active]
    SF -->|可用| ST3[状态: active]
    GH -->|已同步| ST4[状态: synced]
```

## 五、上下文压缩迁移——质量门槛验证流程

```mermaid
flowchart TD
    START[开始验证] --> Q1{裁剪后保留<br/>关键决策和遗留事项?}
    Q1 -->|否| FAIL1[失败: 关键信息丢失]
    Q1 -->|是| Q2{压缩摘要可<br/>独立理解?}
    Q2 -->|否| FAIL2[失败: 摘要依赖被裁剪上下文]
    Q2 -->|是| Q3{桥接索引<br/>100%可追溯?}
    Q3 -->|否| FAIL3[失败: 追溯链断裂]
    Q3 -->|是| Q4{压缩比>10:1?}
    Q4 -->|否| WARN1[警告: 压缩比不足]
    Q4 -->|是| Q5{迁移后完整性<br/>校验通过?}
    Q5 -->|否| FAIL4[失败: 数据损坏]
    Q5 -->|是| PASS[全部通过 ✓]

    FAIL1 --> RETRY[返工: 重新裁剪]
    FAIL2 --> RETRY
    FAIL3 --> RETRY
    FAIL4 --> RETRY
    WARN1 --> ACCEPT[接受但记录]
    RETRY --> START
```

## 六、关联文档

- `GOVERNANCE/proposals/context_compress_migration_20261007.md` — 上下文压缩迁移操作集方案
- `GOVERNANCE/proposals/digital_employee_memory_arch_20261007.md` — 数字人员工记忆分层架构方案
- `GOVERNANCE/prototypes/context_pruner.py` — 上下文裁剪工具（已测试通过）
- `GOVERNANCE/prototypes/ultra_compress_ops.py` — 极致压缩工具（已测试通过）
- `GOVERNANCE/prototypes/link_bridge_ops.py` — 链路桥接工具（已测试通过）
- `GOVERNANCE/prototypes/ls_bus_format_ops.py` — 总线格式化工具（已测试通过）