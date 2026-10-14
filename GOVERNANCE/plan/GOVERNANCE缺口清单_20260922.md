# GOVERNANCE 文档体系缺口清单（2026-09-23 更新）

> 编纂：砚坚（码道·GLM-5.2/华为云CodeArts）
> 日期：2026-09-22 初版 / 2026-09-23 更新
> 用途：盘点治理体系文档缺口，作为批量补档的作业清单

---

## 一、已存在且完整的文档

| 文档 | 状态 |
|------|------|
| AGENTS.md（共治契约v1.0） | ✅ 完整 |
| CHANGELOG.md（交接簿） | ✅ 持续追加 |
| GOVERNANCE_PLAN.md（治理方案v1.0） | ✅ 完整 |
| IMPLEMENTATION_ROADMAP.md（落地路线图v1.0） | ✅ 完整 |
| AUDIT_REPORT.md（审计报告v1.0） | ✅ 完整 |
| SELF_EVOLUTION_PLAN.md / v2（自主进化方案） | ✅ 完整 |
| REVIEW_CHECKLIST.md（审查清单） | ✅ 完整 |
| DECISION_LEDGER_POINTER.md（决策台账指针） | ✅ 完整 |
| compute_resource_registry.md（算力资源登记册） | ✅ 完整 |
| proposals/SNR-001_heartbeat_aggregation.md | ✅ 已补充 |
| 协作记录与最终状态汇总_v1.0.md | ✅ 完整 |
| review/GLM-53-code-review-20260922.md | ✅ 完整 |
| plan/GLM-53-1e8-burn-plan.md | ✅ 完整 |
| research/CRYPTO_HARDENING_INTEGRATED.md | ✅ 新增（2026-09-23，熔铸整合版） |
| a2a/A2A_AUTONOMY_EXPERIMENT_SUMMARY.md | ✅ 新增（2026-09-23） |
| a2a/A2A_DISPATCH_AND_PLAN.md | ✅ 完整 |
| a2a/YANJIAN_ROLE_REGISTRATION.md | ✅ 完整 |

## 二、缺口清单（待补/可补）

### 高优先

| 编号 | 缺失文档 | 用途 | 状态 | 建议动作 |
|------|---------|------|------|---------|
| GAP-01 | 席位冒充检测规程 | 总线安全（AR-001 S-2 延伸） | ✅ 已补（2026-09-23） | 见 GOVERNANCE/proposals/SEAT_IMPERSONATION_DETECTION.md |
| GAP-02 | F-001/F-002 修复记录+部署记录 | broadcast-a2a 修复留痕 | ✅ 已完成 | F-001表名修复+F-002鉴权修复，CHANGELOG已追加 |
| GAP-08 | 密码学修复实施方案（S1-S4） | TLS验证恢复+MD5→SHA-256+凭据加密 | 📋 方案已设计 | 见 CRYPTO_HARDENING_INTEGRATED.md §七 |

### 中优先

| 编号 | 缺失文档 | 用途 | 状态 | 建议动作 |
|------|---------|------|------|---------|
| GAP-03 | 桥接缺陷修复方案（F-8A + 别名匹配） | a2a_bridge.mjs 修复 | 📋 方案已落盘 | 补丁待部署 |
| GAP-04 | push-token-register 鉴权方案 | P3 待办设计文档 | 📋 待设计 | 成文方案 |
| GAP-05 | 回执模板库 | 高频回执复用 | 📋 待沉淀 | 3类回执模板 |
| GAP-09 | README+API文档+部署文档 | 项目文档完善 | 📋 待编写 | H6任务 |

### 低优先

| 编号 | 缺失文档 | 用途 | 状态 | 建议动作 |
|------|---------|------|------|---------|
| GAP-06 | 真机验证交接清单 | R2遗留三事移交 | 📋 待补 | 补文档待机主执行 |
| GAP-07 | AGC P5 审批状态追踪 | 15日审批进度 | 📋 待登记 | 登记状态表 |

---

## 三、已补档记录

| 时间 | 补充项 | 文件 |
|------|--------|------|
| 2026-09-22 | SNR-001 三项补充 | proposals/SNR-001_heartbeat_aggregation.md |
| 2026-09-22 | 燃烧计划 | plan/GLM-53-1e8-burn-plan.md |
| 2026-09-22 | 代码审查报告 | review/GLM-53-code-review-20260922.md |
| 2026-09-22 | 缺口清单初版 | plan/GOVERNANCE缺口清单_20260922.md |
| 2026-09-23 | GAP-01 席位冒充检测规程 | proposals/SEAT_IMPERSONATION_DETECTION.md |
| 2026-09-23 | GAP-02 F-001/F-002修复完成 | CHANGELOG已追加 |
| 2026-09-23 | 密码学加固熔铸整合报告 | research/CRYPTO_HARDENING_INTEGRATED.md |
| 2026-09-23 | A2A自治实验阶段总结 | a2a/A2A_AUTONOMY_EXPERIMENT_SUMMARY.md |
| 2026-09-23 | 云函数深度审查技能 | skills/code/A35_fetchtusharedata云函数深度审查.md |
| 2026-09-23 | 端侧性能优化审查技能 | skills/code/A36_端侧性能优化审查.md |

---

## 四、执行记录

| 时间 | 完成项 |
|------|--------|
| 2026-09-22 | SNR-001 三项补充完成，缺口清单成文 |
| 2026-09-23 | GAP-01席位冒充检测规程补齐，GAP-02确认完成，缺口清单更新 |