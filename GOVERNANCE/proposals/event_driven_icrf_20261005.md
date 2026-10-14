# 事件驱动架构——信息等幂消费共振场方案设计

> 档号：OTL-20261005-05
> 编纂：砚坚席（码道·GLM-5.2/华为云CodeArts）
> 日期：2026-10-05
> 状态：设计稿（待机主审批后实装）

## 一、背景与问题陈述

### 1.1 当前架构的局限

当前A2A多智能体治理实验采用**轮询模式**：

- 砚坚席每5秒前台轮询AlertPoller获取数据
- 各席位间通过HTTP POST同步通信（幻16 A2A端点）
- 每日外呼配额8次，硅基流动API扩展后有所缓解但仍有限
- 信息流向是**拉取式**而非**推送式**

这种模式存在三个核心问题：

| 问题 | 表现 | 影响 |
|---|---|---|
| **延迟** | 轮询间隔5秒，关键事件可能延迟感知 | 告警/协商响应不及时 |
| **冗余** | 无事件时仍空转轮询，浪费资源 | token消耗增加 |
| **不等幂** | 同一信息可能被多个席位重复消费 | 决策冲突/状态不一致 |

### 1.2 目标

设计**信息等幂消费共振场**（Idempotent Consumption Resonance Field, ICRF），实现：

1. **事件驱动**：从轮询模式升级为事件推送模式，席位仅在事件发生时被唤醒
2. **等幂消费**：同一事件无论被消费多少次，结果一致——通过事件ID+消费日志实现
3. **共振发散**：一个事件可触发多个席位的并行响应，类似黏菌的多路探索
4. **收敛聚合**：多席位响应通过共识机制收敛为单一决策

### 1.3 设计灵感

- **黏菌混合策略**：机主指令中提到"最可以同步类似黏菌混合策略聚合发散检索"——黏菌（Physarum）通过多路探索+信息素反馈实现最优路径发现
- **事件溯源（Event Sourcing）**：所有状态变更以事件序列记录，可重放、可审计
- **CRDT（Conflict-free Replicated Data Types）**：分布式环境下的无冲突数据结构，保证最终一致性
- **Actor模型**：每个席位作为独立Actor，通过消息传递通信，不共享状态

## 二、架构设计

### 2.1 共振场拓扑

```
                    ┌─────────────┐
                    │  事件总线    │
                    │ (Event Bus) │
                    └──────┬──────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
    ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
    │  砚坚席     │ │  Qoder席    │ │  Kimi席     │
    │ (神经中枢)  │ │             │ │             │
    └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
           │               │               │
           └───────────────┼───────────────┘
                           │
                    ┌──────▼──────┐
                    │  共识聚合器  │
                    │ (Consensus)  │
                    └─────────────┘
```

### 2.2 事件总线（Event Bus）

事件总线是共振场的核心组件，负责：

1. **事件注册**：席位将状态变更/决策/请求注册为事件
2. **事件路由**：根据事件类型和订阅关系路由到相关席位
3. **等幂保证**：通过事件ID+消费日志确保等幂性
4. **事件持久化**：所有事件持久化存储，支持重放和审计

**事件结构**：
```json
{
  "event_id": "evt_20261005_001",       // 全局唯一，等幂键
  "event_type": "negotiation_request",   // 事件类型
  "source_seat": "yanjian",              // 发起席位
  "target_seats": ["qoder", "kimi"],     // 目标席位（空=广播）
  "timestamp": "2026-10-05T22:30:00+08:00",
  "payload": {                           // 事件负载
    "topic": "K1_eid_registry",
    "proposal": "..."
  },
  "ttl": 3600,                           // 事件有效期（秒）
  "priority": "HIGH"                     // 优先级
}
```

**事件类型体系**：

| 类型 | 描述 | 触发席位 | 目标 |
|---|---|---|---|
| `negotiation_request` | 协商请求 | 任意 | 指定席位 |
| `negotiation_response` | 协商响应 | 任意 | 发起方 |
| `state_change` | 状态变更 | 任意 | 广播 |
| `alert_critical` | 关键告警 | 任意 | 砚坚席+机主 |
| `task_complete` | 任务完成 | 任意 | 砚坚席 |
| `heartbeat` | 心跳 | 任意 | 砚坚席 |
| `consensus_request` | 共识请求 | 砚坚席 | 全体 |
| `consensus_result` | 共识结果 | 共识聚合器 | 全体 |

### 2.3 等幂消费机制

**等幂保证三要素**：

1. **事件ID**：每个事件有全局唯一ID（`evt_{date}_{seq}`）
2. **消费日志**：每个席位维护消费日志，记录已处理的事件ID
3. **幂等操作**：事件处理操作必须是幂等的——同一事件处理多次与一次效果相同

**消费流程**：
```
席位收到事件 → 检查消费日志
  ├─ 已消费 → 跳过（等幂保证）
  └─ 未消费 → 处理事件 → 写入消费日志 → 返回结果
```

**消费日志结构**：
```json
{
  "seat": "yanjian",
  "consumed_events": [
    {
      "event_id": "evt_20261005_001",
      "consumed_at": "2026-10-05T22:30:05+08:00",
      "result": "accepted",
      "action_taken": "..."
    }
  ]
}
```

### 2.4 共振发散与收敛聚合

**发散阶段**（Resonance Divergence）：
- 一个事件触发多个席位的并行响应
- 每个席位独立分析事件，产生自己的响应
- 类似黏菌的多路探索——不同席位可能从不同角度分析

**收敛阶段**（Convergence Aggregation）：
- 共识聚合器收集所有席位的响应
- 根据共识规则（圆桌/MoA/陪审团）收敛为单一决策
- 决策结果作为新事件广播给全体席位

**共识规则映射**：
| 协作模式 | 收敛规则 | 适用场景 |
|---|---|---|
| 圆桌 | 全体一致同意 | 高风险决策（改契约/改架构） |
| MoA | 多数同意 | 常规决策（补充规程/审计排程） |
| 陪审团 | 评委投票裁决 | 争议解决（跨席位冲突） |

### 2.5 事件持久化与重放

所有事件持久化到幻16上的事件存储：

```
/root/incoming/openplanlink-mirror/GOVERNANCE/event_store/
  ├── 2026-10-05/
  │   ├── evt_20261005_001.json
  │   ├── evt_20261005_002.json
  │   └── ...
  ├── consumption_logs/
  │   ├── yanjian.json
  │   ├── qoder.json
  │   └── kimi.json
  └── consensus_results/
      ├── consensus_001.json
      └── ...
```

**重放能力**：从任意时间点重放事件序列，可重建系统状态——这是审计的核心需求。

## 三、实装方案

### 3.1 事件总线实装（event_bus.py）

```python
#!/usr/bin/env python3
"""事件总线——信息等幂消费共振场核心组件"""

import os
import json
import time
import uuid
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))
EVENT_STORE_ROOT = "/root/incoming/openplanlink-mirror/GOVERNANCE/event_store"

def publish(event_type, source_seat, payload, target_seats=None, priority="NORMAL", ttl=3600):
    """
    发布事件到事件总线
    
    返回：event_id
    """
    now = datetime.now(CST)
    date_str = now.strftime("%Y-%m-%d")
    seq = int(time.time() * 1000) % 1000000
    event_id = f"evt_{now.strftime('%Y%m%d')}_{seq:06d}"
    
    event = {
        "event_id": event_id,
        "event_type": event_type,
        "source_seat": source_seat,
        "target_seats": target_seats or [],
        "timestamp": now.isoformat(),
        "payload": payload,
        "ttl": ttl,
        "priority": priority
    }
    
    # 持久化
    store_dir = os.path.join(EVENT_STORE_ROOT, date_str)
    os.makedirs(store_dir, exist_ok=True)
    event_file = os.path.join(store_dir, f"{event_id}.json")
    with open(event_file, "w", encoding="utf-8") as f:
        json.dump(event, f, ensure_ascii=False, indent=2)
    
    return event_id

def consume(event_id, seat):
    """
    消费事件（等幂保证）
    
    返回：(should_process: bool, event: dict)
    """
    # 检查消费日志
    log_file = os.path.join(EVENT_STORE_ROOT, "consumption_logs", f"{seat}.json")
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            log = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        log = {"seat": seat, "consumed_events": []}
    
    consumed_ids = {e["event_id"] for e in log["consumed_events"]}
    if event_id in consumed_ids:
        return False, None  # 已消费，等幂跳过
    
    # 读取事件
    date_str = event_id.split("_")[1]
    date_formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    event_file = os.path.join(EVENT_STORE_ROOT, date_formatted, f"{event_id}.json")
    
    try:
        with open(event_file, "r", encoding="utf-8") as f:
            event = json.load(f)
    except FileNotFoundError:
        return False, None  # 事件不存在
    
    # 标记为已消费
    log["consumed_events"].append({
        "event_id": event_id,
        "consumed_at": datetime.now(CST).isoformat(),
        "result": "processing"
    })
    
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    
    return True, event

def get_pending_events(seat):
    """
    获取席位待消费的事件列表
    
    返回：[event_id, ...]
    """
    # 读取消费日志
    log_file = os.path.join(EVENT_STORE_ROOT, "consumption_logs", f"{seat}.json")
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            log = json.load(f)
        consumed_ids = {e["event_id"] for e in log["consumed_events"]}
    except (FileNotFoundError, json.JSONDecodeError):
        consumed_ids = set()
    
    # 扫描事件存储
    pending = []
    today = datetime.now(CST).strftime("%Y-%m-%d")
    today_dir = os.path.join(EVENT_STORE_ROOT, today)
    
    if os.path.exists(today_dir):
        for fname in os.listdir(today_dir):
            if not fname.endswith(".json"):
                continue
            event_id = fname.replace(".json", "")
            if event_id in consumed_ids:
                continue
            
            # 检查目标席位
            event_file = os.path.join(today_dir, fname)
            with open(event_file, "r", encoding="utf-8") as f:
                event = json.load(f)
            
            targets = event.get("target_seats", [])
            if not targets or seat in targets:
                pending.append(event_id)
    
    return pending
```

### 3.2 共识聚合器实装（consensus_aggregator.py）

```python
#!/usr/bin/env python3
"""共识聚合器——共振场收敛组件"""

import json
import os
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))
EVENT_STORE_ROOT = "/root/incoming/openplanlink-mirror/GOVERNANCE/event_store"

def aggregate(consensus_id, mode, responses, threshold=None):
    """
    聚合多席位响应，收敛为单一决策
    
    mode: roundtable (全体一致) / moa (多数同意) / jury (评委投票)
    responses: {seat: response_dict}
    threshold: jury模式下的通过阈值
    """
    if mode == "roundtable":
        # 全体一致同意
        all_accept = all(r.get("decision") == "accept" for r in responses.values())
        result = {
            "consensus_id": consensus_id,
            "mode": "roundtable",
            "decision": "accepted" if all_accept else "rejected",
            "responses": responses,
            "timestamp": datetime.now(CST).isoformat()
        }
    elif mode == "moa":
        # 多数同意
        accept_count = sum(1 for r in responses.values() if r.get("decision") == "accept")
        total = len(responses)
        result = {
            "consensus_id": consensus_id,
            "mode": "moa",
            "decision": "accepted" if accept_count > total / 2 else "rejected",
            "vote_count": {"accept": accept_count, "reject": total - accept_count},
            "responses": responses,
            "timestamp": datetime.now(CST).isoformat()
        }
    elif mode == "jury":
        # 评委投票
        accept_count = sum(1 for r in responses.values() if r.get("decision") == "accept")
        passed = accept_count >= (threshold or len(responses) * 0.6)
        result = {
            "consensus_id": consensus_id,
            "mode": "jury",
            "decision": "accepted" if passed else "rejected",
            "threshold": threshold,
            "vote_count": {"accept": accept_count, "reject": len(responses) - accept_count},
            "responses": responses,
            "timestamp": datetime.now(CST).isoformat()
        }
    
    # 持久化共识结果
    result_dir = os.path.join(EVENT_STORE_ROOT, "consensus_results")
    os.makedirs(result_dir, exist_ok=True)
    result_file = os.path.join(result_dir, f"{consensus_id}.json")
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    return result
```

### 3.3 与现有架构的整合

| 现有组件 | 整合方式 |
|---|---|
| AlertPoller（5s轮询） | 保留作为降级兜底；事件总线就绪后改为事件驱动+轮询兜底 |
| 幻16 A2A端点 | 作为事件总线的传输层之一 |
| 硅基流动API | 作为事件总线的传输层之一（突破配额限制） |
| Server酱通道 | 告警事件通过Server酱推送给机主 |
| CHANGELOG | 状态变更事件自动追加CHANGELOG条目 |
| K4审计排程 | 审计事件自动触发K4脚本 |

### 3.4 黏菌混合策略映射

机主指令中提到"最可以同步类似黏菌混合策略聚合发散检索"，映射到共振场：

| 黏菌机制 | 共振场对应 |
|---|---|
| 多路探索（plasmodium branching） | 一个事件触发多席位并行响应 |
| 信息素反馈（pheromone trail） | 事件优先级+消费日志形成反馈回路 |
| 路径强化（path reinforcement） | 高频事件类型自动提升优先级 |
| 路径衰减（path decay） | TTL过期事件自动清理 |
| 最优路径涌现 | 共识聚合器收敛出最优决策 |

## 四、部署路线图

| 阶段 | 内容 | 依赖 | 预计时间 |
|---|---|---|---|
| Phase 1 | 事件总线核心（publish/consume/get_pending） | 幻16存储目录 | 1天 |
| Phase 2 | 砚坚席接入事件总线 | Phase 1 | 1天 |
| Phase 3 | 共识聚合器实装 | Phase 1 | 1天 |
| Phase 4 | Server酱告警事件接入 | Phase 1 + Server酱方案 | 0.5天 |
| Phase 5 | 轮询降级为兜底模式 | Phase 2验证稳定 | 1天 |
| Phase 6 | 黏菌策略增强（优先级自适应） | Phase 2-5稳定运行 | 2天 |

## 五、验证标准

| 编号 | 验证项 | 方法 |
|---|---|---|
| V1 | 事件发布后可被目标席位消费 | publish → consume → 检查返回 |
| V2 | 同一事件被同一席位消费两次，第二次跳过 | consume → consume → 第二次返回False |
| V3 | 事件持久化可重放 | 读取事件文件 → 验证内容完整 |
| V4 | 共识聚合器正确收敛 | 发起3席位投票 → 检查收敛结果 |
| V5 | TTL过期事件不被消费 | 发布TTL=1事件 → 等待2秒 → consume返回False |
| V6 | 黏菌策略优先级自适应 | 连续发布同类事件 → 检查优先级提升 |

## 六、遗留事项

1. 事件总线部署位置：幻16 vs 本地 vs 分布式——须与A2A网络协商
2. 事件存储的清理策略：TTL过期后自动清理 vs 归档保留
3. 跨席位消费日志的同步机制：各席位独立维护 vs 集中维护
4. 与HarmonyOS 7 A2A IM GUI的集成方式：事件总线作为IM GUI的数据源
5. 安全性：事件总线访问控制、事件签名验证