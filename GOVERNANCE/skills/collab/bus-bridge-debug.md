---
name: bus-bridge-debug
type: collab
created: 2026-09-22
updated: 2026-09-22
version: 1.0.0
trigger: A2A总线消息未路由、桥接脚本缺陷排查、总线数据核验（缺号/信噪比/心跳）
source_files: [C:/Users/欧阳宏俊/Documents/kimi/router-hub/bridge/a2a_bridge.mjs, GOVERNANCE/协作记录与最终状态汇总_v1.0.md, GOVERNANCE/proposals/GAP-03_bridge_fix_plan.md]
---

# A2A总线桥接缺陷排查技能

## 概述
排查 A2A 总线（Supabase `cross_mode_channel` 表）消息未到达收件面、桥接脚本缺陷、总线数据完整性问题。强调"用 REST 直查实测，不猜表名"。

## 适用场景
- 消息寻址为别名（workbuddy/workbuddy-W/yan-jian-workbuddy）但未落入规范席位键（workbuddy-hy4）
- payload_md 为纯文本（非 JSON）时正文丢失（F-8A 类）
- 缺号分析、信噪比统计、心跳占比核验
- 需要恢复未路由消息正文并处置

## 执行步骤
1. 确认真实表名：查桥接脚本 `bus.select('...')` 用什么表；悲剧教训——代码写 `a2a_messages` 但实际是 `cross_mode_channel`
2. 用 Supabase REST API（anon key + `?id=eq.xx&select=*`）直查目标消息，恢复正文
3. 统计同一收件方所有别名变体：`?to_mode=like.*workbuddy*` 列出全部变体
4. 判断根因：精确匹配缺陷（to_mode 别名不含规范键） vs 空 catch 吞正文（JSON.parse 失败静默）
5. 对已恢复消息逐条处置（归档/登记/复函），写入协作记录
6. 成文修复方案（GAP-xx），含改法示例与部署验证步骤

## 质量门槛
- 每条消息结论基于 REST 实测返回（status=200 + payload 全文），不凭记忆
- 三要素齐备：表名、别名变体清单、缺陷根因分类
- 已恢复消息均有处置去向（不是"恢复了但不管"）

## 经验记录
- 表名错误是静默失败高发点：写库 404（PGRST205）不抛到业务层，日志只留 status
- 收件面精确匹配 + 发送方自由文本 to_mode = 必现路由缺口，短期用 include 匹配，长期加规范字段
- JSON.parse 的空 catch 会吞掉明文消息，catch 里必须保留 raw
- 本文档方法验证过：id=250/3066/6277 三条别名消息全部恢复并处置

## 关联文档
- GOVERNANCE/协作记录与最终状态汇总_v1.0.md（未路由件处置记录）
- GOVERNANCE/proposals/GAP-03_bridge_fix_plan.md（修复方案）
- router-hub/bridge/a2a_bridge.mjs（桥接脚本本体）