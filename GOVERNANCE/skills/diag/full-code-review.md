---
name: full-code-review
type: diag
created: 2026-09-22
updated: 2026-09-23
version: 1.1.0
trigger: 对鸿蒙端侧或云函数做全量代码审查、合规走查、契约一致性检查
source_files: [entry/src/main/ets/, cloudfunctions/functions/, docs/audit/2026-09-23-full-review.md]
---

# 鸿蒙全量代码审查技能

## 概述
对 HarmonyOS 端侧（ArkTS）与 CloudBase 云函数（Node.js）做批量、可复现的全量审查。以工程硬约束（适老化/信号松绑/占位封装/首屏兜底/串行纪律）为准绳，输出分级发现清单与修复建议。

## 适用场景
- 新增功能合并前的全量合规走查
- 云函数/端侧契约不一致排查
- 对抗性审查（AR类）的代码侧输入
- 批量燃烧模型额度的高价值任务载体

## 执行步骤
1. glob 列出端侧 `.ets` 与云函数 `**/index.js` 全部文件，登记行数
2. 逐文件通读，对照工程硬约束逐项核验（适老化无K线、信号三禁、PushService占位、DEMO兜底、冷启动/后台拉起）
3. 云函数重点核：表名/存储路径/API端点是否与实测一致、鉴权、并发写保护、错误降级
4. 发现按 高/中/低 分级归入表格，标注 文件:行号
5. 输出审查报告到 `GOVERNANCE/review/`，含修复优先级（P1/P2/P3）
6. 高优先发现立即修复并记录

## 质量门槛
- 端侧+云函数 100% 文件覆盖（无遗漏）
- 每项发现带 文件:行号 证据
- 硬约束条目逐条核验并显式标注 通过/发现
- 修复后重新走查受影响函数

## 经验记录
- Supabase 表名必须实测确认：代码里写 `a2a_messages`，实际表是 `cross_mode_channel`，一次误写导致广播静默失败 404
- `downloadFile` 的 `fileID` 与 `cloudPath` 两种参数在不同 SDK 版本行为可能不一致，应统一
- ArkTS 端侧硬约束核验可用 "无 K线/图表组件 + 字号范围 + 状态机完整性" 三查法快速通过
- 注释错别字类低级问题单独清点，修复成本近乎为零
- **fail-open 是云函数最高危模式**：合规检查"只贴标签不拦截"等于没有合规检查；鉴权"未配Key时允许访问"等于没有鉴权。接入 LLM 后风险放大。修复必须 fail-closed：不达标降级、未配Key拒绝
- **合规降级必须联动 TTS 跳过**：signal 卡被降级为 fact 后，TTS 循环必须跳过该卡（不设置 audioUrl），否则降级卡仍会播报白话解读，合规闸门形同虚设
- **端侧场景鉴权用 bundleName 白名单优于 API Key**：API Key 需在端侧硬编码（不安全），bundleName 白名单由系统签名保证不可伪造，更适合 Push token 注册等端侧发起的请求
- **契约字段必须端侧+服务端双向同步**：服务端新增 signalNote 字段但端侧 AlertItem.ets 未声明，会导致端侧 JSON 解析时该字段被丢弃。审查时必须对照端侧 interface 与服务端返回 JSON 逐字段核验
- **域名迁移后必须全局搜索旧域名**：从 service.tcloudbase.com 迁移到 app.tcloudbase.com 后，注释、CORS allowedOrigins 中仍残留旧域名，需全局搜索彻底清理
- **AGENTS.md 约束条件需结合当前状态判断**：PushService.ets 标记为"占位封装"约束，但约束原文是"AGC 未配置前不得展开实装"——AGC 已配置后实装即合理。审查时不能只看约束字面，需结合约束的触发条件判断

## 关联文档
- AGENTS.md（工程硬约束）
- GOVERNANCE/AUDIT_REPORT.md（对抗性审查基线）
- docs/audit/2026-09-23-full-review.md（2026-09-23 全量审查报告：2P0+2P1+5P2）