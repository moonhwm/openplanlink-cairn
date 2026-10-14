# A38: a2a-judge 判官自动化云函数开发经验

**技能类型**: code  
**编写时间**: 2026-09-25  
**编写者**: 砚坚（码道·鸿蒙开发智能体/GLM-5.2-SFT-Harmony）  
**关联文件**: `cloudfunctions/functions/a2a-judge/index.js`, `GOVERNANCE/A2A_COMMONWEALTH_CHARTER.md` §14.6

## 情境

机主令"调用外池云服务器判官常态化矫正"——需要将判官机制从手动执行升级为云函数自动化执行，实现每日定时四路判官矫正。

## 方法论

### 1. 设计阶段：从规划书到代码

规划书第十四章已定义a2a-judge的设计参数（触发方式、四路判官、输出位置、矫正通知）。开发时需将设计转化为可运行的云函数代码。

**关键设计决策**：
- 判官检查方式从"本地grep扫描"改为"Supabase总线查询"——因为云函数运行时无法访问本地文件系统
- 四路判官并行执行（`Promise.allSettled`）而非串行——提高执行效率
- 判官报告写入Supabase总线 + 本地归档——实现远程实时推送和本地持久化双重保障

### 2. 开发阶段：适配云函数环境

**第一次实现的问题**：
- 判官2和判官4通过HTTP端点ping其他云函数——但云函数未配置HTTP访问路径，全部返回404
- 环境变量数量阈值设为20——CloudBase运行时本身有65+系统环境变量，导致误报WARN

**修复方案**：
- 判官2改为通过Supabase总线查询活动记录（`cross_mode_channel`表）
- 判官4改为通过Supabase总线查询A2A注册和心跳消息
- 环境变量阈值调整为100

### 3. 验证阶段：部署+调用

```bash
tcb fn deploy a2a-judge --env-id <envId> --force
tcb fn invoke a2a-judge --env-id <envId> --data '{"action":"run_all"}'
```

首次调用结果：总体FAIL（a2a-registry HTTP 404）
修复后调用结果：总体WARN（冷启动预期状态），0 critical items

### 4. 归档阶段：报告持久化

- 云函数自动将报告写入Supabase总线（`kind=judge_report`）
- 本地手动归档到 `GOVERNANCE/a2a/judge-reports/` 目录
- 严重项自动触发 `kind=judge_alert` 总线消息

## 经验教训

### 教训1：云函数间通信不能依赖HTTP端点

CloudBase云函数默认不配置HTTP访问路径，通过 `https://{envId}.service.tcloudbase.com/{fnName}` 访问会返回404。

**解决方案**：通过共享数据层（Supabase总线）间接验证云函数活跃度，而非直接HTTP ping。

### 教训2：云函数运行时环境变量远多于预期

CloudBase Node.js 18.15运行时环境有65+系统环境变量（`TCB_*`, `NODE_*`等），自定义环境变量数量阈值需设为100而非20。

### 教训3：冷启动状态的WARN是预期行为

A2A网络冷启动时，总线中无注册消息、无心跳消息、无任务分发消息——这些都是预期行为，不应判为FAIL。判官逻辑需区分"冷启动预期WARN"和"真正故障FAIL"。

### 教训4：Promise.allSettled 比 Promise.all 更适合判官场景

四路判官独立执行，某一路判官异常不应影响其他判官。`Promise.allSettled`确保所有判官都能完成，异常的判官标记为FAIL但不中断其他判官。

### 教训5：判官报告需双重持久化

- Supabase总线：远程实时推送，其他席位可即时读取
- 本地文件归档：持久化记录，便于历史追溯

仅依赖总线不够——总线数据可能被清理；仅依赖本地不够——本地文件无法远程访问。

## 可复用模式

### 模式1：云函数判官架构

```
入口（exports.main）
  → action路由（run_all / judge_xxx）
  → Promise.allSettled 并行执行四路判官
  → aggregateReport 汇总
  → writeBusMessage 写入总线
  → 严重项 → writeBusMessage kind=judge_alert
  → 返回JSON汇总
```

### 模式2：通过Supabase总线验证云函数活跃度

```javascript
const recentMessages = await queryBusMessages({ limit: 100 });
const modeActivity = {};
for (const msg of recentMessages) {
  if (!modeActivity[msg.from_mode]) {
    modeActivity[msg.from_mode] = new Date(msg.created_at).getTime();
  }
}
// 检查各 from_mode 的最近活动时间是否在24小时内
```

### 模式3：判官报告文本生成

判官报告需同时输出机器可读JSON和人类可读Markdown文本，便于总线传输和本地归档。