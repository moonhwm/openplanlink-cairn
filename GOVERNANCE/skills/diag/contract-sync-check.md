---
name: contract-sync-check
type: diag
created: 2026-09-23
updated: 2026-09-23
version: 1.0.0
trigger: 端侧 ArkTS interface 与服务端 JSON 返回格式的一致性检查、契约字段同步审查
source_files: [entry/src/main/ets/model/AlertItem.ets, cloudfunctions/functions/fetch-tushare-data/index.js, cloudfunctions/functions/get-alerts/index.js]
---

# 契约同步检查技能

## 概述
检查端侧 ArkTS interface（AlertItem/AlertFeed）与服务端云函数 JSON 返回格式的字段一致性。契约不同步会导致端侧 JSON 解析时丢失字段、显示异常或功能缺失。本技能提供系统化的双向对照方法。

## 适用场景
- 服务端新增字段后检查端侧是否同步声明
- 端侧 interface 修改后检查服务端是否同步产出
- 接入 LLM 生成新字段（如 signalNote）前的契约对齐
- 跨席位协作中契约变更的同步验证

## 执行步骤
1. **列出端侧 interface 全部字段**：读取 `AlertItem.ets`，逐字段记录名称、类型、可选性
2. **列出服务端 JSON 返回的全部字段**：读取云函数 `createAlertItems` / `saveAlertsToDB` 等产出逻辑，逐字段记录名称、类型
3. **双向对照**：
   - 端侧有、服务端无 → 端侧声明了但服务端不产出（死字段）
   - 服务端有、端侧无 → 服务端产出了但端侧不接收（丢失字段）
   - 两边都有但类型不同 → 类型不匹配（解析风险）
4. **修复缺失**：端侧补声明 / 服务端补产出 / 类型对齐
5. **验证**：`node -c` 语法验证 + 重新部署云函数 + 端侧构建验证

## 质量门槛
- 端侧 interface 与服务端 JSON 返回字段 100% 对照（无遗漏）
- 每个字段标注：端侧声明 / 服务端产出 / 类型 / 可选性
- 可选字段（`?:`）必须确认服务端在缺失时的行为（不返回 vs 返回 null vs 返回空串）
- 新增字段必须同时修改端侧 interface 和服务端产出逻辑

## 经验记录
- **服务端新增字段但端侧未声明 = 静默丢失**：JSON 解析时未声明的字段会被丢弃，不会报错但功能缺失。signalNote 字段就是典型案例——服务端产出但端侧 AlertItem.ets 未声明，导致白话解读无法独立显示
- **端侧显示逻辑必须与契约同步**：仅在 interface 中声明字段不够，还必须在 UI 组件（如 Index.ets 卡片流）中添加渲染逻辑。signalNote 声明后还需在卡片中添加 `if (item.kind === 'signal' && item.signalNote)` 条件渲染
- **契约变更须通报跨席位协作方**：AGENTS.md §一规定 AlertItem/AlertFeed 是接口边界，任何变更须在 CHANGELOG.md 写明意图并停机主确认

## 关联文档
- entry/src/main/ets/model/AlertItem.ets（端侧契约核心）
- cloudfunctions/functions/fetch-tushare-data/index.js（服务端产出逻辑）
- AGENTS.md §一（分区主权——接口边界）
- docs/audit/2026-09-23-full-review.md（M1 契约不同步发现）