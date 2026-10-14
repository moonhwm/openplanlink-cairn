# 密码学加固总报告（熔铸整合版）

> 编纂：砚坚（码道·GLM-5.2/华为云CodeArts）
> 日期：2026-09-23
> 依据：RHEL10_PQC_A2A_REPORT.md + CRYPTO_HARDENING_HIFI_REPORT.md（两份报告熔铸整合）
> 机主指令：熔铸 RHEL 10 PQC SSH 到密码学中，通知各方重新审视回环

---

## 一、当前系统密码学问题诊断

### 1.1 严重问题（立即修复）

| # | 问题 | 位置 | 风险等级 | 具体描述 |
|---|------|------|----------|----------|
| S1 | **TLS 证书验证禁用** | `yan_jian_bridge.mjs` 运行时 `NODE_TLS_REJECT_UNAUTHORIZED=0` | 🔴 致命 | 允许中间人攻击截获所有 A2A 总线通信 |
| S2 | **凭据金库明文存储** | `GOVERNANCE/credentials/*.json`（18个文件） | 🔴 致命 | 所有 API Key/SSH 口令/Token 明文 JSON 存储 |
| S3 | **MD5 用于消息哈希** | `yan_jian_bridge.mjs:47` | 🟠 高危 | MD5 碰撞攻击可伪造消息哈希绕过去重 |
| S4 | **MD5 用于 alertId 生成** | `server.mjs:165` | 🟡 中危 | MD5 碰撞可能导致异动通知重复或遗漏 |

### 1.2 中等问题（计划修复）

| # | 问题 | 位置 | 风险等级 |
|---|------|------|----------|
| M1 | HTTP 服务器无 TLS | `server.mjs` 端口 8000 | 🟠 高危 |
| M2 | 无密钥轮换机制 | 所有凭据文件 | 🟡 中危 |
| M3 | WebSocket Bearer token 在 header | `server.mjs` TTS 连接 | 🟡 中危 |
| M4 | Paramiko padding 非常数时间 | Paramiko `pkey.py:67-79` | 🟡 中危 |

### 1.3 低风险问题（监控即可）

| # | 问题 | 风险等级 |
|---|------|----------|
| L1 | 3DES-CBC 仍在 Paramiko 偏好列表 | 🟢 低危（仅向后兼容） |
| L2 | HMAC-SHA1/MD5 仍在 Paramiko 偏好列表 | 🟢 低危（同上） |

---

## 二、Paramiko 密码学机制分析

### 2.1 密钥交换协议（KEX）

| 优先级 | 算法 | 安全强度 | 后量子准备 |
|--------|------|----------|------------|
| 1 | `curve25519-sha256@libssh.org` | ★★★★★ 最强经典 | 量子攻击下破解（Shor算法） |
| 2-4 | `ecdh-sha2-nistp256/384/521` | ★★★★ | NIST曲线量子攻击下破解 |
| 5-7 | DH-group16/14/gex | ★★★-★★★★ | 量子攻击下完全破解 |

**关键安全特性**：常数时间比较（`constant_time.bytes_eq`）、零密钥检测、原始字节序列化。

### 2.2 加密算法

| 优先级 | 算法 | 安全评级 | 备注 |
|--------|------|----------|------|
| 1-3 | AES-128/192/256-CTR | ★★★★ | 安全，非 AEAD |
| 4-6 | AES-128/192/256-CBC | ★★★ | padding oracle 风险 |
| 7 | 3DES-CBC | ★ 弱 | NIST 已废弃 |
| 8-9 | aes128/256-gcm@openssh.com | ★★★★★ | **推荐**：AEAD 认证加密 |

### 2.3 消息认证码（MAC）

| 优先级 | 算法 | 安全评级 | 备注 |
|--------|------|----------|------|
| 1-2 | hmac-sha2-256/512 | ★★★★ | 安全 |
| 3-4 | hmac-sha2-256/512-etm@openssh.com | ★★★★★ | **Encrypt-then-MAC**：最安全 |
| 5-8 | hmac-sha1/md5(-96) | ★ 弱 | 已破解，仅向后兼容 |

### 2.4 主机密钥与认证

| 优先级 | 密钥类型 | 安全评级 | 后量子准备 |
|--------|----------|----------|------------|
| 1 | ssh-ed25519 | ★★★★★ | 量子攻击下破解，需 PQC 签名替代 |
| 2-4 | ecdsa-sha2-nistp256/384/521 | ★★★★ | 量子攻击下破解 |
| 5-6 | rsa-sha2-512/256 | ★★★ | 量子攻击下完全破解 |

---

## 三、RHEL 10 后量子 SSH：生态信号

### 3.1 里程碑意义

Red Hat Enterprise Linux 10 **默认开启后量子 SSH**，使用 `mlkem768x25519-sha256` 混合密钥交换——企业级 Linux 发行版首次将 PQC 作为默认配置。

| 维度 | 影响 |
|------|------|
| 部署规模 | RHEL 覆盖全球数百万台服务器，默认开启 = 瞬间获得抗量子能力 |
| 供应链效应 | CentOS Stream / Rocky Linux / AlmaLinux 等下游继承此默认 |
| 合规驱动 | 政府/金融/医疗等需长期保密领域，开箱即用的合规基础 |
| 生态信号 | Ubuntu、Debian、SUSE 将面临跟进压力 |

### 3.2 混合 KEX 工作原理

```
客户端                          服务端
  |                               |
  |--- ML-KEM-768 公钥 + X25519 公钥 --->|
  |                               |
  |<-- ML-KEM-768 密文 + X25519 公钥 ----|
  |                               |
  |  ss_pq = ML-KEM 解封装        |  ss_pq = ML-KEM 解封装
  |  ss_classic = X25519 ECDH     |  ss_classic = X25519 ECDH
  |                               |
  |  session_key = SHA256(ss_pq || ss_classic)
  |                               |
  |  只要任意一路未被攻破 → 安全   |
```

### 3.3 三个混合算法变体

| 方法名 | 经典 KEX | 后量子 KEM | NIST 安全等级 | 适用场景 |
|--------|----------|-----------|--------------|----------|
| `mlkem768x25519-sha256` | X25519 | ML-KEM-768 | Level 1 (128-bit) | **基准组合，RHEL 10 默认** |
| `mlkem1024nistp384-sha384` | NIST P-384 | ML-KEM-1024 | Level 5 (256-bit) | 最高安全等级，政府/军事 |
| `mlkem768nistp256-sha256` | NIST P-256 | ML-KEM-768 | Level 1/3 混合 | 兼容 NIST 曲线体系 |

### 3.4 SSH 连接四阶段（PQC 视角）

| 阶段 | 内容 | 加密状态 | PQC 介入点 |
|------|------|----------|-----------|
| 一 | TCP 连接 + 版本协商 | 明文 | 无 |
| 二 | 算法协商（KEXINIT） | 明文 | 双方广告 `mlkem768x25519-sha256` |
| 三 | 密钥交换（核心） | 明文→密文 | **ML-KEM-768 + X25519 + SHA256 合成** |
| 四 | 加密通道 + 认证 | 密文 | AEAD 加密 |

---

## 四、A2A 协议 PQC 加固方案

### 4.1 当前 A2A 架构

```
砚坚桥接 → Supabase REST API → 总线 → 其他席位桥接
         (HTTPS/TLS)          (RLS)   (HTTPS/TLS)
```

### 4.2 三层加固方案

| 层级 | 方案 | 时间 | 说明 |
|------|------|------|------|
| **层级一：SSH 运维通道** | 所有 SSH 连接升级到混合 KEX | 立即 | OpenSSH 9.0+ 手动启用，10.0+ 默认 |
| **层级二：A2A 总线传输层** | SSH 隧道为 A2A 总线提供 PQC 保护 | 2026 Q4 | TLS PQC 尚未默认，用 SSH 隧道过渡 |
| **层级三：应用层混合 KEX** | A2A 应用层实现 ML-KEM-768 + X25519 | 2027 Q2+ | 需 liboqs-node，创新方案 |

### 4.3 "回环"验证方案

- **近端回环**：席位内部消息回环测试（发送→接收→验证哈希一致性）
- **远端回环**：席位间回环测试（A发送→B接收→B回复→A验证）

PQC 回环验证：
```
席位A → 发送 PQC 混合 KEX 发起消息 → 席位B
席位B → 回环：PQC 混合 KEX 响应 → 席位A
席位A → 验证：ss_pq 一致 + ss_classic 一致 + session_key 一致 → 回环通过
```

### 4.4 "还差什么"五个缺口

| 缺口 | A2A 中的表现 | 解决方案 |
|------|-------------|----------|
| 统一互操作标准 | 不同 SSH 实现的 PQC 算法命名不一致 | 跟随 IETF draft-ietf-sshm-mlkem-hybrid-kex 标准化 |
| MTU 分片优化 | ML-KEM-768 公钥 1184 bytes vs X25519 公钥 32 bytes | SSH 协议已有分片机制（RFC 4253 §6.1） |
| 大规模部署验证 | 多席位同时握手可能导致 CPU 峰值 | ML-KEM-768 封装/解封装 ~0.1ms，可接受 |
| 动态密钥管理 | PQC 密钥的生成、存储、轮换 | 借鉴 Paramiko 的 bcrypt KDF + AES-CBC 私钥保护 |
| 撤销方案 | 席位退出时需撤销其密钥 | A2A 总线增加密钥撤销列表（CRL）机制 |

---

## 五、Paramiko PQC 升级路径

### 5.1 当前差距

| 组件 | Paramiko 5.0.0 | OpenSSH 10.x | 差距 |
|------|----------------|--------------|------|
| KEX | Curve25519（最强经典） | mlkem768x25519-sha256（混合 PQC） | **缺 PQC 路** |
| 加密 | AES-256-GCM（AEAD） | ChaCha20-Poly1305 / AES-256-GCM | 已对齐 |
| MAC | HMAC-SHA2-512-ETM | implicit（AEAD） | 已对齐 |
| 签名 | Ed25519 | Ed25519（PQC 签名实验性） | PQC 签名全行业缺失 |
| 常数时间 | constant_time.bytes_eq | 同 | 已对齐 |

### 5.2 升级概念

```python
# Paramiko 混合 KEX 扩展
class Transport:
    _preferred_kex = (
        "mlkem768x25519-sha256",        # 新增：混合 PQC（最高优先级）
        "curve25519-sha256@libssh.org",  # 现有：经典最强
        "ecdh-sha2-nistp256",
        ...
    )
```

**实施依赖**：`liboqs-python`、`cryptography` 库 ML-KEM 支持（预计 2027）、SSH PQC KEX RFC（draft-ietf-sshm-mlkem-hybrid-kex-10 即将发布）。

---

## 六、Hi-Fi 音频与密码学加固协同

### 6.1 Hi-Fi 路线

| 维度 | 当前 | Hi-Fi 目标 |
|------|------|-----------|
| 格式 | MP3（有损） | PCM/WAV（无损）或 FLAC（无损压缩） |
| 采样率 | 22050 Hz | 44100 Hz（CD）或 48000 Hz（专业） |
| 位深度 | 16-bit | 24-bit |
| 文件大小 | 120-150 KB/条 | 2-5 MB/条（PCM）或 1-2 MB/条（FLAC） |

### 6.2 协同关系

| 维度 | Hi-Fi 影响 | 密码学需求 | 协同方案 |
|------|-----------|-----------|----------|
| 数据量 | 文件增大 10-30x | 大文件更需加密 | HTTPS/TLS 确保传输机密性 |
| 完整性 | 无损格式对比特错误零容忍 | AEAD 加密 | AES-GCM 端到端认证加密 |
| 缓存安全 | 大文件缓存更易成攻击目标 | 加密+权限控制 | AES-256-GCM 加密缓存 |
| 带宽效率 | PCM 占用大量带宽 | 压缩+加密顺序 | 先 FLAC 压缩再 TLS 加密（ETM） |
| 实时性 | Hi-Fi 编码耗时更长 | 低延迟算法 | AES-GCM 硬件加速 |
| 端侧播放 | AVPlayer 需支持 PCM/WAV | 端侧音频解密 | HarmonyOS 内置 AES-NI |

### 6.3 架构不冲突证明

1. Hi-Fi 在应用层，密码学在传输层——互不影响
2. AEAD 兼容无损音频——AES-GCM 对任意二进制数据透明加密
3. FLAC 压缩 + TLS 加密 = ETM 模式——先压缩再加密
4. 端侧解密不影响播放——AVPlayer 可直接播放解密后的 PCM 流

---

## 七、加固方案与实施路径

### 7.1 立即修复（S1-S4）

| # | 修复方案 | 关键步骤 |
|---|---------|---------|
| S1 | 恢复 TLS 验证 | 删除 `NODE_TLS_REJECT_UNAUTHORIZED=0`，改用 `NODE_EXTRA_CA_CERTS` |
| S2 | 凭据金库 AES-256-GCM 加密 | 主密钥从环境变量读取，加密格式 `{ iv, data, tag }` |
| S3 | MD5→SHA-256 消息哈希 | `createHash('sha256')` 替代 `createHash('md5')`，需所有席位同步 |
| S4 | MD5→SHA-256 alertId | 同 S3，`createHash('sha256')` 替代 |

### 7.2 计划修复（M1-M4）

| # | 修复方案 | 关键步骤 |
|---|---------|---------|
| M1 | HTTP→HTTPS | Node.js 内置 TLS，`minVersion: 'TLSv1.2'`，仅 AEAD cipher |
| M2 | 密钥轮换机制 | 凭据增加 `expires_at` + `rotation_reminder_days` |
| M3 | API Key 传输优化 | 改为 URL query parameter（WSS 加密保护）或短期 Token 交换 |
| M4 | Paramiko padding 常数时间化 | 向上游提交 PR，常数时间验证 padding 字节 |

### 7.3 PQC 行动计划

| 优先级 | 行动 | 时间 | 依赖 |
|--------|------|------|------|
| 🔴 立即 | Linux 服务器 SSH 升级到混合 KEX | 1周 | OpenSSH 9.0+ |
| 🔴 立即 | A2A 桥接 MD5→SHA-256（S3/S4） | 立即 | 无 |
| 🟠 短期 | 凭据金库 AES-256-GCM 加密（S2） | 2周 | VAULT_MASTER_KEY |
| 🟡 中期 | A2A 应用层混合 KEX 原型验证 | 1月 | liboqs-node |
| 🟡 中期 | Paramiko PQC KEX 扩展开发 | 1月 | liboqs-python |
| 🟢 长期 | A2A 总线 TLS PQC 迁移 | 待 OpenSSL | OpenSSL 3.5+ |
| 🟢 长期 | 密钥撤销列表（CRL）机制 | 3月 | AGConnect |

### 7.4 PQC 时间线修订

| 阶段 | 原计划 | **修订时间** | 行动 |
|------|--------|-------------|------|
| ~~监控~~ → **采纳** | ~~2026-2027~~ | **立即** | SSH 升级到混合 KEX |
| ~~评估~~ → **试点** | ~~2027~~ | **2026 Q4** | A2A 席位间测试 SSH 混合 KEX 隧道 |
| ~~试点~~ → **部署** | ~~2028~~ | **2027 Q1** | 生产环境启用 PQC 混合 KEX |
| ~~部署~~ → **创新** | ~~2029+~~ | **2027 Q2+** | A2A 应用层混合 KEX 原型 |

---

## 八、WorkBuddy HY4 协同建议

1. **源码学习任务分发**：将 Paramiko 6 个核心密码学文件分发给全体成员学习
2. **HY4 长上下文优势**：利用 1M 上下文窗口一次性加载 Paramiko 全部源码深度分析
3. **密码学审计**：请 HY4 对当前系统进行密码学审计，识别本报告可能遗漏的安全问题
4. **Hi-Fi 音频质量评估**：请 HY4 评估 PCM 48kHz/24bit 与 FLAC 的音质差异和带宽权衡

---

*本报告熔铸整合自 RHEL10_PQC_A2A_REPORT.md（2026-09-18）和 CRYPTO_HARDENING_HIFI_REPORT.md（2026-09-18），消除重复内容，保持逻辑连贯。原始报告保留作为溯源参考。*