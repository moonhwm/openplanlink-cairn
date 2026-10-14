---
name: hash-algorithm-upgrade
type: crypto
created: 2026-09-23
updated: 2026-09-23
version: 1.0.0
trigger: 需要审查哈希算法使用、升级弱哈希或实施哈希策略时
source_files: [GOVERNANCE/research/CRYPTO_HARDENING_HIFI_REPORT.md]
---

# 哈希算法升级技能

## 概述
审查和升级哈希算法使用的技能，确保项目中不使用弱哈希算法（MD5、SHA-1），统一使用SHA-256或更强的哈希算法。哈希算法升级是密码学加固的基础步骤。

## 适用场景
- 代码审查中发现MD5或SHA-1的使用
- 数据完整性校验的哈希算法选择
- 密码存储的哈希算法审查（应使用bcrypt/scrypt/argon2）
- 文件指纹生成（应使用SHA-256）
- A2A总线消息签名（应使用ed25519）

## 执行步骤
1. **扫描弱哈希**：grep搜索`md5`、`sha1`、`MD5`、`SHA1`、`createHash('md5')`、`createHash('sha1')`等关键词
2. **分类评估**：对每个使用点评估：
   - 数据完整性校验 → 升级为SHA-256
   - 密码存储 → 升级为bcrypt/scrypt/argon2（不能直接用哈希）
   - 文件指纹 → 升级为SHA-256
   - 兼容性需求 → 如必须支持旧格式，保留MD5但新增SHA-256并行
3. **实施升级**：替换弱哈希为强哈希，确保调用方适配
4. **验证升级**：确认升级后功能正常，哈希输出长度和格式正确
5. **记录变更**：在CHANGELOG中记录哈希算法升级

## 质量门槛
- 生产代码零处MD5使用（除非有明确的兼容性需求并标注）
- 生产代码零处SHA-1使用（除非有明确的兼容性需求并标注）
- 密码存储不使用直接哈希（须使用bcrypt/scrypt/argon2）
- 文件指纹使用SHA-256或更强
- 任何弱哈希保留须有注释说明兼容性理由

## 经验记录
- MD5在数据完整性校验中仍常见——虽然碰撞风险低但不应使用
- 密码存储直接用SHA-256也不够——须使用bcrypt/scrypt/argon2等慢哈希
- 哈希升级可能影响数据库索引——如果哈希值作为索引键，长度变化需适配
- A2A总线消息签名使用ed25519而非哈希——签名和哈希是不同的密码学原语

## 关联文档
- GOVERNANCE/research/CRYPTO_HARDENING_HIFI_REPORT.md（密码学加固报告——S3/S4修复）
- GOVERNANCE/skills/crypto/密码学分析加固.md（密码学分析与加固总技能）