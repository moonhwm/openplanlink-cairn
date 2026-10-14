# MFA / Git Hook / AV1-H265 引入方案与协议补充论证

> 编纂：砚坚（码道·GLM-5.2/华为云CodeArts），挂帅席/神经中枢
> 日期：2026-10-03
> 版本：v1.0
> 依据：机主指令（2026-10-03）——"拟系统引入MFA、Git、Hook及AV1/H265编码，同步更新开源协议补充论证中认证流程章节"
> 关联：AGPL-3.0+SSPL分层组合协议、HMAC-SHA3-512 attest v2、幻16桥接节点serve-handshake.mjs

---

## 一、现状审计

### 1.1 已有认证基础设施

| 组件 | 状态 | 位置 |
|------|------|------|
| HMAC-SHA3-512 Merkle树 | ✅ 已实装 | `/root/handshake/hmac_sha3_512_attest.py` → `attest_v2.json` |
| TOTP双因子认证 | ✅ 已实装（serve-handshake.mjs） | `verifyTwoFactor()` + `totpCode()` + `base32Decode()` |
| Ed25519 SSH密钥 | ✅ 已用于SSH连接 | `C:\Users\欧阳宏俊\.ssh\id_ed25519` |
| SHA3-512哈希链审计 | ✅ 已实装 | serve-handshake.mjs 审计层 |
| 速率限制 + Tor拒绝 | ✅ 已实装 | serve-handshake.mjs 安全层 |

**关键发现**：TOTP双因子认证已在 `serve-handshake.mjs` 中实装（`verifyTwoFactor` 函数），但尚未正式纳入协议补充论证文档，也未与HMAC-SHA3-512认证方案整合为统一的多因素认证框架。

### 1.2 已有Git基础设施

| 组件 | 状态 |
|------|------|
| Git仓库 | ✅ harmony-app（本地） + openplanlink-mirror（幻16） |
| Git Hook | ❌ 未配置 |
| 凭据扫描 | ✅ 有cred_health_check.mjs但未集成到提交流程 |
| SPDX标识 | ✅ 182源文件已添加 |
| 签名提交 | ❌ 未配置 |

### 1.3 编码技术现状

| 编码 | 状态 | 说明 |
|------|------|------|
| AV1 | ❌ 未引入 | 开源免版税，与AGPL兼容 |
| H265/HEVC | ❌ 未引入 | 专利许可问题需声明 |
| 截图传输 | 现有PNG | UI对齐截图等未压缩 |

---

## 二、MFA多因素认证框架设计

### 2.1 三因子认证架构

```
┌─────────────────────────────────────────────────────────┐
│              A2A节点多因素认证框架                         │
│                                                          │
│  因子1（知识因子）：HMAC-SHA3-512 共享密钥                │
│    ↓ 验证：tag = HMAC(key, JCS(envelope))               │
│                                                          │
│  因子2（时间因子）：TOTP-30s 时间窗口                     │
│    ↓ 验证：X-OpenPlanLink-TOTP ±1窗口容忍               │
│                                                          │
│  因子3（持有因子）：Ed25519 签名验证                      │
│    ↓ 验证：signature = Ed25519(private_key, message)     │
│                                                          │
│  → 三因子全部通过 = 认证成功                              │
│  → 任一因子缺失/失败 = fail-closed（拒绝）               │
└─────────────────────────────────────────────────────────┘
```

### 2.2 因子详细设计

#### 因子1：HMAC-SHA3-512（已有，保持）

- **协议标识**：`a2a-hmac-sha3-512/v1`
- **密钥**：64字节随机密钥，仅本地存储
- **key_id**：`f1326c5338743db1`（非秘密轮换标识）
- **验证**：检查版本、接收方、时间窗(300秒)、nonce唯一性、正文摘要、HMAC

#### 因子2：TOTP（已有，扩展）

- **算法**：HMAC-SHA1（RFC 6238），30秒时间窗口
- **容忍**：±1窗口（共90秒有效窗口）
- **密钥**：Base32编码种子，存储在 `OPENPLANLINK_TOTP_SECRET` 环境变量
- **传输**：HTTP头 `X-OpenPlanLink-TOTP`
- **扩展**：升级为HMAC-SHA3-512变体（TOTP-SHA3-512），与因子1算法统一

#### 因子3：Ed25519签名（新增）

- **算法**：Ed25519（RFC 8032）
- **密钥对**：每个A2A节点持有独立Ed25519密钥对
- **签名内容**：`Ed25519(private_key, SHA3-512(envelope))`
- **传输**：HTTP头 `X-OpenPlanLink-Sig` + `X-OpenPlanLink-Sig-KeyId`
- **验证**：接收方用发送方公钥验证签名
- **公钥注册**：节点Agent Card中声明 `publicKeyEd25519` 字段

### 2.3 认证级别

| 级别 | 因子组合 | 适用场景 |
|------|----------|----------|
| L1基础 | 因子1（HMAC） | 常规A2A消息 |
| L2增强 | 因子1 + 因子2（TOTP） | 跨生态握手、关键决议 |
| L3最高 | 因子1 + 因子2 + 因子3（Ed25519） | 协议变更、密钥轮换、审计签名 |

### 2.4 fail-closed原则

- 任何因子配置缺失 → 认证恒false，拒绝请求
- 任何因子验证失败 → 立即拒绝，不降级
- 时间窗口外 → 拒绝，不延长窗口
- nonce重复 → 拒绝，记录审计日志

---

## 三、Git Hook方案设计

### 3.1 Hook清单

| Hook | 触发时机 | 功能 |
|------|----------|------|
| `pre-commit` | git commit前 | 凭据扫描 + SPDX标识检查 + 敏感文件拦截 |
| `commit-msg` | 提交消息编写后 | 消息格式验证（遵循CHANGELOG约定） |
| `pre-push` | git push前 | HMAC-SHA3-512 attest验证 + 签名检查 |

### 3.2 pre-commit详细设计

```bash
#!/usr/bin/env bash
# pre-commit: 凭据扫描 + SPDX标识检查 + 敏感文件拦截
set -euo pipefail

# 1. 凭据扫描——检查暂存文件中是否有疑似密钥/令牌
#    规则：AK/SK模式、Bearer token、私钥文件、.env文件
# 2. SPDX标识检查——源文件(.ts/.mjs/.py/.ets)须含SPDX-License-Identifier
# 3. 敏感文件拦截——禁止提交 *.key, *.pem, *.p12, .env, secrets/
```

### 3.3 commit-msg详细设计

```bash
#!/usr/bin/env bash
# commit-msg: 提交消息格式验证
# 规则：须以 R1:/R2:/docs:/fix:/feat:/chore: 之一开头
# 例外：merge commit、revert commit
```

### 3.4 pre-push详细设计

```bash
#!/usr/bin/env bash
# pre-push: attest验证
# 1. 检查 attest_v2.json 是否存在且与当前文件树一致
# 2. 检查 LICENSE 和 NOTICE_SSPL.md 是否存在
# 3. 检查关键文件SPDX标识覆盖率
```

---

## 四、AV1/H265编码引入方案

### 4.1 编码选择论证

| 编码 | 专利状态 | 开源兼容性 | 压缩效率 | 决策 |
|------|----------|------------|----------|------|
| AV1 | ✅ 免版税（AOMedia） | ✅ 与AGPL完全兼容 | ~30%优于H265 | **首选** |
| H265/HEVC | ⚠️ 需MPEG LA专利许可 | ⚠️ 与AGPL有潜在冲突 | 基准 | **仅限内部测试** |
| VP9 | ✅ 免版税（Google） | ✅ 与AGPL兼容 | 略逊于AV1 | 备选 |

**决策**：AV1作为A2A网络多媒体传输的首选编码，H265仅限内部测试不对外分发。

### 4.2 应用场景

1. **UI对齐截图传输**：当前PNG截图体积大，AV1编码可大幅压缩
2. **桌面录屏/操作回放**：A2A协作中的操作可视化
3. **审计证据归档**：屏幕录像作为审计证据的压缩存储
4. **自举工作区演示**：WPS云盘中的交互演示页面视频

### 4.3 实装路径

- **编码工具**：`ffmpeg -c:v libaom-av1`（开源AV1编码器）
- **解码工具**：浏览器原生AV1解码支持（Chrome 70+/Firefox 67+）
- **容器格式**：IVF（简单）或 WebM（广泛支持）
- **分辨率策略**：截图1080p → AV1 CRF 30；录屏720p → AV1 CRF 35

### 4.4 H265专利许可声明

如内部测试使用H265，须在协议补充论证中声明：
- H265编码仅用于内部测试，不对外分发
- 不触发MPEG LA专利许可条款（内部使用豁免）
- 任何对外分发的内容必须转为AV1编码

---

## 五、协议补充论证更新

### 5.1 新增章节：认证流程

在《ima与A2A约束下开源协议补充论证》中新增"认证流程"章节：

```
## 认证流程

### 多因素认证（MFA）

A2A网络节点采用三因子认证框架：

1. **知识因子（HMAC-SHA3-512）**：共享密钥 + JCS规范化 + 300秒时间窗
2. **时间因子（TOTP）**：30秒窗口 + ±1容忍 + HMAC-SHA3-512变体
3. **持有因子（Ed25519）**：非对称签名 + 公钥注册 + 签名验证

认证级别：
- L1基础（因子1）：常规A2A消息
- L2增强（因子1+2）：跨生态握手、关键决议
- L3最高（因子1+2+3）：协议变更、密钥轮换、审计签名

fail-closed原则：任一因子缺失/失败即拒绝，不降级。

### Git Hook

代码提交执行三重自动化检查：
- pre-commit：凭据扫描 + SPDX标识检查 + 敏感文件拦截
- commit-msg：提交消息格式验证
- pre-push：HMAC-SHA3-512 attest验证 + 协议合规检查
```

### 5.2 新增章节：编码技术

```
## 编码技术

### AV1（首选）

A2A网络多媒体内容传输采用AV1编码（AOMedia免版税）：
- 与AGPL-3.0+SSPL协议完全兼容
- 压缩效率优于H265约30%
- 浏览器原生支持（Chrome 70+/Firefox 67+）

### H265/HEVC（仅限内部测试）

H265编码仅用于内部测试，不对外分发：
- 不触发MPEG LA专利许可条款（内部使用豁免）
- 任何对外分发的内容必须转为AV1编码
- 协议补充论证中明确声明此限制
```

### 5.3 NOTICE_SSPL.md更新

在现有NOTICE_SSPL.md中追加：

```
## 认证与编码技术声明

### 多因素认证（MFA）
本项目采用三因子认证框架（HMAC-SHA3-512 + TOTP + Ed25519），
认证流程详见协议补充论证文档。

### AV1编码
本项目多媒体内容采用AV1编码（AOMedia免版税），与AGPL-3.0+SSPL协议兼容。

### H265/HEVC限制
H265编码仅限内部测试，不对外分发。对外分发内容须转为AV1编码。

### Git Hook
本项目配置三重Git Hook（pre-commit/commit-msg/pre-push），
确保凭据安全、协议合规、attest完整性。
```

---

## 六、实装计划

| 步骤 | 内容 | 优先级 | 状态 |
|------|------|--------|------|
| 1 | 编写MFA认证框架文档 | 高 | ✅ 本文档 |
| 2 | 创建Git Hook脚本 | 高 | 待实装 |
| 3 | 更新NOTICE_SSPL.md | 高 | 待实装 |
| 4 | 扩展serve-handshake.mjs（因子3 Ed25519） | 中 | 待实装 |
| 5 | 创建AV1编码工具脚本 | 中 | 待实装 |
| 6 | 更新金山文档协议补充论证 | 中 | 需机主登录 |
| 7 | 魔搭社区同步 | 低 | 待执行 |

---

## 七、验证清单

- [ ] V1：MFA三因子框架文档自洽（因子定义/级别划分/fail-closed逻辑）
- [ ] V2：Git Hook脚本可执行（pre-commit/commit-msg/pre-push）
- [ ] V3：NOTICE_SSPL.md更新包含认证/编码/Hook声明
- [ ] V4：AV1编码工具脚本可执行
- [ ] V5：协议补充论证新增章节与金山文档对齐（待机主确认）
- [ ] V6：所有新增文件含SPDX-License-Identifier
- [ ] V7：无凭据明文泄漏
- [ ] V8：CHANGELOG追加条目

---

**文档版本**: v1.0
**生效日期**: 2026-10-03
**编纂席位**: 砚坚（码道·GLM-5.2/华为云CodeArts）
**依据**: 机主指令 + AGPL-3.0+SSPL分层组合协议 + HMAC-SHA3-512 attest v2