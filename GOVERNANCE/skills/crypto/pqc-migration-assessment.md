---
name: pqc-migration-assessment
type: crypto
created: 2026-09-23
updated: 2026-09-23
version: 1.0.0
trigger: 需要评估后量子密码学（PQC）迁移的影响、时间线或兼容性时
source_files: [GOVERNANCE/research/RHEL10_PQC_A2A_REPORT.md]
---

# 后量子密码学迁移评估

## 概述
评估后量子密码学（PQC）迁移的影响、时间线和兼容性的技能，覆盖PQC算法选择、混合方案设计、迁移路径规划和风险评估。PQC迁移是长期安全投资——量子计算威胁虽未到来，但准备须提前。

## 适用场景
- 评估当前密码学体系对量子计算的脆弱性
- PQC算法选择（ML-KEM/ML-DSA/SLH-DSA等NIST标准化算法）
- 混合密码学方案设计（经典+PQC并行）
- RHEL10等操作系统的PQC支持评估
- A2A总线的PQC迁移路径规划

## 执行步骤
1. **现状评估**：盘点当前使用的所有密码学算法（RSA/ECDSA/AES/SHA等）
2. **脆弱性分析**：对照量子计算能力评估每个算法的脆弱性：
   - RSA-2048 → 量子脆弱（Shor算法）
   - ECDSA → 量子脆弱（Shor算法）
   - AES-256 → 量子降低安全性但仍可用（Grover算法，安全性降为128位）
   - SHA-256 → 量子降低抗碰撞但仍可用（Grover算法）
3. **PQC算法选择**：根据NIST标准化进程选择替代算法：
   - 密钥封装 → ML-KEM（Kyber）
   - 数字签名 → ML-DSA（Dilithium）或SLH-DSA（SPHINCS+）
   - 对称加密 → AES-256仍可用
   - 哈希 → SHA-256或SHA-3仍可用
4. **混合方案设计**：设计经典+PQC并行方案，确保迁移期间兼容性
5. **迁移路径规划**：制定分阶段迁移计划（评估→试点→混合→全迁移）
6. **风险评估**：评估迁移风险（性能影响、兼容性、标准化进度）

## 质量门槛
- PQC评估覆盖所有当前使用的密码学算法
- 混合方案确保迁移期间不中断现有功能
- 迁移计划含明确的阶段、时间线和停止条件
- PQC算法选择基于NIST标准化进程（不使用未标准化的算法）
- 性能影响评估含具体基准测试数据或预估

## 经验记录
- PQC迁移不是紧急任务但须提前规划——"先收集后加密"的量子攻击意味着现在截获的数据未来可解密
- RHEL10已开始支持PQC——但生产可用性仍需验证
- 混合方案（经典+PQC）是迁移期间的最优选择——不牺牲当前安全性
- A2A总线的ed25519签名在量子时代需升级为ML-DSA——但ed25519在当前仍是最佳选择
- NIST PQC标准化进程仍在进行——ML-KEM和ML-DSA已标准化，SLH-DSA备选

## 关联文档
- GOVERNANCE/research/RHEL10_PQC_A2A_REPORT.md（RHEL10 PQC报告）
- GOVERNANCE/research/CRYPTO_HARDENING_HIFI_REPORT.md（密码学加固报告）
- GOVERNANCE/skills/crypto/密码学分析加固.md（密码学分析与加固总技能）