# PD-AI 量化研究团队席位注册方案

> 立件：砚坚（yan-jian-codearts-glm52 · 华为云CodeArts · GLM-5.2-SFT-Harmony）
> 日期：2026-09-24
> 协议：A2A MFV-0.1
> 状态：待机主批准后执行注册

---

## 一、注册席位

| 席位 | 席位键 | 模式 | 能力标签 | 租约TTL |
|---|---|---|---|---|
| 量化研究员 | `pd-quant-researcher-001` | 量化研究 | `["quant-data","tushare","factor-research","eastmoney","backtest"]` | 300s |
| 量化工程师 | `pd-quant-engineer-001` | 代码开发 | `["quant-engineering","data-pipeline","backtest-script","python","cloudbase"]` | 300s |

## 二、职责划分

### pd-quant-researcher-001（量化研究员席）
- tushare 财经新闻/交易数据/量化因子的协同拉取策略制定
- 量化因子研究与筛选（动量、波动率、换手率等）
- 地区经济学前沿论文复现的量化方法论设计
- 异动判定阈值与筛选逻辑优化
- **合规约束**：只产出客观数据/异动监测/量化指标呈现，禁止投资建议/走势预测/买卖时机建议7建议（与 AGENTS.md §二.2 信号松绑三禁一致）

### pd-quant-engineer-001（量化工程师席）
- 数据管道工程化（fetch-tushare-data 云函数维护与优化）
- 回测脚本编写与验证
- 量化因子计算代码实现
- CloudBase 云函数部署与运维
- 与端侧 AlertPoller 的数据契约对接

## 三、注册命令

```bash
# 量化研究员席注册
tcb fn invoke a2a-registry --data '{
  "action": "register",
  "node_id": "pd-quant-researcher-001",
  "capability_tags": ["quant-data","tushare","factor-research","eastmoney","backtest"],
  "lease_ttl": 300,
  "renew_method": "heartbeat"
}'

# 量化工程师席注册
tcb fn invoke a2a-registry --data '{
  "action": "register",
  "node_id": "pd-quant-engineer-001",
  "capability_tags": ["quant-engineering","data-pipeline","backtest-script","python","cloudbase"],
  "lease_ttl": 300,
  "renew_method": "heartbeat"
}'
```

## 四、与 fetch-tushare-data 的协同

```
pd-quant-researcher-001 → A2A总线 → 砚坚(总装节点) → 调度 fetch-tushare-data 云函数
                                                    ↓
pd-quant-engineer-001 ← A2A总线 ← 砚坚 ← 数据结果回传
```

- 砚坚作为总装节点负责任务分发与结果回传
- 两个PD-AI席位通过 A2A 总线与砚坚协调
- fetch-tushare-data 的定时触发器（cron `0 * * * * * *`）保持不变
- PD-AI席位可按需请求额外数据拉取（通过 a2a-task-dispatch 创建任务）

## 五、与设计引擎团/fbsir席位的关系

| 席位 | 席位键 | 模式 | 与PD-AI的关系 |
|---|---|---|---|
| 设计引擎团 | `design-engine-001` | 设计创意 | 为PD-AI产出设计数据可视化方案 |
| fbsir超级伙伴 | `fbsir-super-partner-001` | 日常办公 | 执行PD-AI下达的确定性数据操作动作 |
| PD-AI研究员 | `pd-quant-researcher-001` | 量化研究 | 核心数据研究席 |
| PD-AI工程师 | `pd-quant-engineer-001` | 代码开发 | 核心数据工程席 |

## 六、验收规程

1. 注册成功：`tcb fn invoke a2a-registry --data '{"action":"status","node_id":"pd-quant-researcher-001"}'` → 返回 `status: "active"`
2. 心跳维持：30s间隔发送心跳，连续3次成功 → 席位状态保持 active
3. 首个真任务：通过 a2a-task-dispatch 创建数据拉取任务 → 产物落该席隔离目录
4. 砚坚独立复算哈希 → 三态验收 → 入 audit 链 + registry 置 active

---

*砚坚 · 字司契 · 2026-09-24 21:00*