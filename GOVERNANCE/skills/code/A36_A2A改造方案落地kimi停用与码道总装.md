---
name: A2A改造方案落地——kimi停用与码道总装
description: 从kimi code额度耗尽事故到A2A网络基础设施（注册/心跳/熔断/预算管控/任务分发）的完整改造经验
type: code
source_files:
  - cloudfunctions/functions/broadcast-a2a/config.js
  - cloudfunctions/functions/a2a-registry/index.js
  - cloudfunctions/functions/a2a-task-dispatch/index.js
  - cloudfunctions/functions/broadcast-a2a/index.js
trigger: 需要停用一个AI服务通道并将职能迁移到另一个通道时；需要建立A2A注册/心跳/熔断基础设施时
---

# A2A改造方案落地——kimi停用与码道总装

## 1. 问题诊断

**事故**：kimi code 300元额度包在2026-09-24 11:00后4分钟内耗尽。
**根因**：quant-lab/bridge/ 的定时巡检（cron `*/17 * * * *`）+ 60s心跳定时器持续空转，每次心跳都触发kimi code API调用，链路损耗累积导致额度快速耗尽。
**关键发现**：根因不在应用代码仓库内，而在工作区外的桥接脚本目录。仓库内仅有1处代码级kimi引用（`broadcast-a2a/index.js:107` 的 `from_mode: 'kimi-code-quantlab'`）。

## 2. 改造方案六节框架

### 第一节：停用与移交
- **总开关常量**：新建 `config.js`，`KIMI_ENABLED = false`，所有kimi相关入口检查此开关
- **来源标识迁移**：`from_mode` 从 `kimi-code-quantlab` 改为 `yan-jian-codearts-glm52`
- **quant-lab侧**：`KIMI_DISABLE.local.flag` 哨兵文件 + `SPEND_FREEZE.local.flag` 支出冻结

### 第二节：注册与心跳
- **注册字段**：node_id, capability_tags, lease_ttl(300s), renew_method(heartbeat)
- **心跳策略**：初始30s → 退避60/120/300s → ±20%抖动 → 60s批量合并
- **熔断**：连续3次失败或5分钟错误率>50% → 熔断15分钟 → 半开探测1次
- **预算管控**：50%告警 / 80%降级为按需拉取 / 95%停服并通知

### 第三节：任务分发与状态回传
- **消息schema**：task_id(UUID), idempotency_key(md5[:16]), status(queued/running/succeeded/failed/cancelled)
- **重试**：上限3次，超时120s
- **去重**：同idempotency_key返回原task_id，DEDUP_TTL=3600s
- **终态确认**：task_receipt回读

### 第四节：回归验证
- 24h零kimi调用（grep代码+SQL查总线）
- 心跳次数下降比例（批量合并+退避）
- 额度消耗速率前后对比

### 第五节：合规边界
- 不再以接口调用kimi，码道GLM5.2作为唯一总装节点
- 所有产出数据归档到自有基础设施（GOVERNANCE目录+CloudBase存储）
- 三层审计：CHANGELOG + git log + A2A总线消息id

### 第六节：架构取舍
- 推荐：HTTP/A2A协议（路线①）为主 + 本地物理桥接（路线③）为辅
- 不推荐：网盘托管（不适合实时通信）、自建超节点（工程量大）

## 3. 落地验证

| 验证项 | 结果 |
|--------|------|
| 代码语法验证（node -c） | ✅ 三个文件全部通过 |
| CloudBase部署 | ✅ a2a-registry + a2a-task-dispatch 均部署成功 |
| HAP构建验证 | ✅ BUILD SUCCESSFUL in 1 min 3s 840ms |
| 代码中kimi引用 | ✅ 零残留（grep验证） |

## 4. 经验提炼

1. **事故根因可能在仓库外**——全面尽调不能只看应用代码，桥接脚本/定时任务/环境变量都需排查
2. **总开关常量优于删除**——保留 `KIMI_ENABLED=false` 而非删除kimi代码，未来如需恢复只需改一个值
3. **心跳参数需要抖动**——±20%抖动防止多个席位心跳同步导致周期性流量尖峰
4. **批量合并上报**——60s窗口内的心跳事件合并为一条，减少总线写入次数（从每30s一次降到每60s一次）
5. **预算管控三档**——50%告警/80%降级/95%停服，避免再次发生额度耗尽事故
6. **幂等去重**——idempotency_key确保重复请求不会创建重复任务，DEDUP_TTL=3600s覆盖1小时窗口

## 5. 复用指引

遇到以下场景时引用本技能：
- 需要停用一个AI服务通道并将职能迁移到另一个通道
- 需要建立A2A注册/心跳/熔断基础设施
- 需要实现任务分发与状态回传机制
- 需要为AI服务调用建立预算管控

---

*砚坚 · 字司契 · 2026-09-24 21:30*