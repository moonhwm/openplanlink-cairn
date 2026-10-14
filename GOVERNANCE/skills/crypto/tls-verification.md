---
name: tls-verification
type: crypto
created: 2026-09-23
updated: 2026-09-23
version: 1.0.0
trigger: 需要恢复、维护或审查TLS证书验证时
source_files: [cloudfunctions/functions/, GOVERNANCE/research/CRYPTO_HARDENING_HIFI_REPORT.md]
---

# TLS验证恢复与维护

## 概述
恢复和维护HTTPS/TLS证书验证的技能，确保所有网络请求使用正确的TLS验证，不因开发便利而禁用证书验证。TLS验证是传输安全的基础——禁用等于明文传输。

## 适用场景
- 发现代码中存在`rejectUnauthorized: false`或等价禁用TLS验证的配置
- 云函数中HTTPS请求的证书验证审查
- 开发环境与生产环境的TLS验证策略区分
- TLS验证降级的临时措施与恢复流程

## 执行步骤
1. **扫描禁用点**：grep搜索`rejectUnauthorized`、`NODE_TLS_REJECT_UNAUTHORIZED`、`process.env.NODE_TLS`等关键词
2. **分类评估**：对每个禁用点评估：
   - 是否有明确的临时降级理由（如自签名证书开发环境）
   - 是否影响生产环境安全
   - 是否有替代方案（如配置CA证书而非禁用验证）
3. **恢复验证**：移除`rejectUnauthorized: false`，确保HTTPS请求使用默认证书验证
4. **开发环境处理**：如开发环境使用自签名证书，配置`NODE_EXTRA_CA_CERTS`环境变量而非禁用验证
5. **验证恢复**：确认所有HTTPS请求在证书验证启用状态下正常工作
6. **记录变更**：在CHANGELOG中记录TLS验证恢复的变更

## 质量门槛
- 生产环境零处`rejectUnauthorized: false`
- 开发环境如需降级，须使用`NODE_EXTRA_CA_CERTS`而非禁用验证
- 任何TLS验证降级须有明确的临时理由和恢复计划
- 降级理由须记录在CHANGELOG中
- 云函数环境不允许任何形式的TLS验证禁用

## 经验记录
- TLS验证禁用是最常见的安全债务——开发时为图方便禁用，上线时忘记恢复
- `NODE_TLS_REJECT_UNAUTHORIZED=0`是全局禁用，影响整个进程——比`rejectUnauthorized: false`更危险
- 云函数环境中TLS验证禁用尤其危险——因为云函数直接面向公网
- 恢复TLS验证后可能出现证书不匹配问题——须确认CA证书链完整

## 关联文档
- GOVERNANCE/research/CRYPTO_HARDENING_HIFI_REPORT.md（密码学加固报告——S1修复）
- GOVERNANCE/skills/code/arkts-network-wrapper.md（网络请求封装技能）
- cloudfunctions/functions/fetch-tushare-data/index.js（requestHttps封装——已使用默认TLS验证）