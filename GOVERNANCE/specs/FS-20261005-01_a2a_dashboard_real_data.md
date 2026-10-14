# 功能规范：A2A看板接入真实事件总线数据

## 元数据
- 档号：FS-20261005-01
- 版本：v1.0.0
- 责任席：砚坚（挂帅席/神经中枢）
- 状态：draft
- 日期：2026-10-05

## 功能描述

将A2A IM GUI看板页面（A2ADashboard.ets）从当前模拟数据（MOCK_SEATS/MOCK_EVENTS/MOCK_AUDITS）切换为真实事件总线ICRF数据源，实现席位状态、事件日志和审计轨迹的实时展示。

## 用户故事

作为A2A治理实验的参与者，我希望在看板页面看到各席位的真实运行状态和事件流，以便实时了解网络拓扑健康状况和协作动态。

## 验收条件（EARS格式）

1. WHEN 事件总线发布新事件 THEN 看板事件日志Tab实时更新，新事件出现在列表顶部
2. WHILE 看板页面处于活跃状态 THEN 系统每5秒向事件总线拉取最新数据
3. IF 事件总线端点不可达 THEN 看板显示"连接中断"状态指示，保留最后成功获取的数据
4. WHEN 用户点击刷新按钮 THEN 系统立即向事件总线发起拉取请求
5. WHILE 席位状态Tab活跃 THEN 各席位卡片显示最新状态（idle/thinking/acting/syncing/error）
6. WHEN 席位状态发生变化 THEN 对应席位卡片的状态指示灯颜色实时更新
7. IF 拉取数据为空 THEN 看板显示"暂无事件"提示，不显示模拟数据

## 约束

- 技术约束：纯ArkTS、零三方依赖、Stage模型、compatibleSdkVersion 20
- 适老化约束：28-34fp高对比深色底、大字白话
- 数据约束：事件总线端点 http://120.46.86.165/functions/v1/app（A2A JSON-RPC 2.0）
- 安全约束：不暴露API密钥，不显示敏感事件载荷
- 性能约束：5秒轮询间隔，单次拉取不超过50条事件

## 依赖

- 前置功能：A2ADashboard.ets页面（已完成，含NavDestination路由接入）
- 数据源：事件0总线ICRF（scripts/event_bus.py，已部署在幻16）
- 协议：A2A 0.3.0（JSON-RPC 2.0）

## 数据契约

### 事件总线拉取请求

```json
{
  "jsonrpc": "2.0",
  "id": "<uuid>",
  "method": "events/query",
  "params": {
    "limit": 50,
    "since": "<timestamp>"
  }
}
```

### 事件总线拉取响应

```json
{
  "jsonrpc": "2.0",
  "id": "<uuid>",
  "result": {
    "events": [
      {
        "eventId": "<string>",
        "timestamp": "<ISO8601>",
        "seatName": "<string>",
        "eventType": "hb.|biz.|esc.*",
        "priority": "low|normal|high|critical",
        "summary": "</string>"
      }
    ],
    "seats": [
      {
        "name": "<string>",
        "role": "<string>",
        "state": "idle|thinking|acting|syncing|error",
        "lastActive": "<ISO8601>",
        "tasksCompleted": <number>,
        "tasksInProgress": <number>
      }
    ]
  }
}
```

## 测试用例

| 用例ID | 条件 | 预期结果 | 验证方式 |
|---|---|---|---|
| TC-001 | 看板页面加载，事件总线可达 | 显示真实席位状态和事件列表 | 设备截图+日志 |
| TC-002 | 事件总线发布新事件 | 看板事件日志Tab更新 | 设备截图+事件对比 |
| TC-003 | 事件总线端点不可达 | 显示"连接中断"指示 | 断网测试+截图 |
| TC-0048 | 点击刷新按钮 | 立即发起拉取请求 | 日志验证请求发出 |
| TC-005 | 5秒轮询间隔 | 定时拉取请求 | 日志验证时间间隔 |
| TC-006 | 拉取数据为空 | 显示"暂无事件"提示 | 设备截图 |
| TC-007 | 席位状态变化 | 状态指示灯颜色更新 | 设备截图+状态对比 |

## 实现路径

1. 在A2ADashboard.ets中替换MOCK数据为@State动态数据
2. 添加EventBusService.ets服务类，封装事件总线拉取逻辑
3. 在aboutToAppear中启动5秒轮询定时器
4. 在aboutToDisappear中停止定时器
5. 添加连接状态指示器（连接中断/正常）
6. 添加"暂无事件"空状态提示

## 风险

1. **事件总线端点可能不支持events/query方法** — 需要确认幻16事件总线的API接口
2. **跨域请求限制** — HarmonyOS应用可能需要配置网络权限
3. **数据量过大** — 需要限制单次拉取数量和前端渲染数量