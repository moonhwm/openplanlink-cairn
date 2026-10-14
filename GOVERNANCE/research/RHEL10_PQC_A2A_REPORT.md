# RHEL 10 后量子 SSH 与 A2A 协议密码学加固报告

> 编纂：砚坚（码道·GLM-5.2/华为云CodeArts）
> 日期：2026-09-18
> 依据：cipherhub.cloud PQC迁移报告 + Paramiko 5.0.0 源码 + Red Hat Enterprise Linux 10 发布说明
> 机主指令：熔铸 RHEL 10 PQC SSH 到密码学中，通知各方重新审视回环

---

## 一、RHEL 10 后量子 SSH：生态信号

### 1.1 里程碑意义

Red Hat Enterprise Linux 10 **默认开启后量子 SSH**，使用 `mlkem768x25519-sha256` 混合密钥交换。这是企业级 Linux 发行版首次将 PQC 作为默认配置，意味着：

| 维度 | 影响 |
|------|------|
| **部署规模** | RHEL 覆盖全球数百万台服务器，默认开启 = 瞬间获得抗量子能力 |
| **供应链效应** | CentOS Stream / Rocky Linux / AlmaLinux 等下游发行版将继承此默认 |
| **合规驱动** | 政府/金融/医疗等需长期保密的领域，RHEL 10 提供了开箱即用的合规基础 |
| **生态信号** | 其他发行版（Ubuntu、Debian、SUSE）将面临跟进压力 |

### 1.2 技术实现

RHEL 10 的 PQC SSH 基于 OpenSSH 10.x，核心配置：

```
# /etc/ssh/sshd_config 默认生效
KexAlgorithms mlkem768x25519-sha256,curve25519-sha256@libssh.org,...
HostKeyAlgorithms ssh-ed25519,...
Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,...
```

**混合 KEX 工作原理**（`mlkem768x25519-sha256`）：

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

**三个混合算法变体**：

| 方法名 | 经典 KEX | 后量子 KEM | NIST 安全等级 | 适用场景 |
|--------|----------|-----------|--------------|----------|
| `mlkem768x25519-sha256` | X25519 | ML-KEM-768 | Level 1 (128-bit) | **基准组合，RHEL 10 默认** |
| `mlkem1024nistp384-sha384` | NIST P-384 | ML-KEM-1024 | Level 5 (256-bit) | 最高安全等级，政府/军事 |
| `mlkem768nistp256-sha256` | NIST P-256 | ML-KEM-768 | Level 1/3 混合 | 兼容 NIST 曲线体系 |

### 1.3 SSH 连接四阶段（PQC 视角）

| 阶段 | 内容 | 加密状态 | PQC 介入点 |
|------|------|----------|-----------|
| **一** | TCP 连接 + 版本协商 | 明文 | 无（仅交换版本号） |
| **二** | 算法协商（KEXINIT） | 明文 | 双方广告 `mlkem768x25519-sha256` |
| **三** | 密钥交换（核心） | 明文→密文 | **ML-KEM-768 封装/解封装 + X25519 ECDH + SHA256 合成** |
| **四** | 加密通道 + 认证 | 密文 | AEAD 加密（ChaCha20-Poly1305 / AES-GCM） |

**关键洞察**：阶段一到三都是明文传输，但只交换算法名称和密钥材料，不涉及业务数据。阶段三结束后双方激活密钥，阶段四起所有通信加密。ML-KEM 抗量子攻击，X25519 抗经典攻击，双保险。

---

## 二、A2A 协议密码学加固：熔铸 PQC

### 2.1 当前 A2A 协议架构

当前 A2A 总线基于 Supabase（PostgreSQL + REST API），通信链路：

```
砚坚桥接 → Supabase REST API → 总线 → 其他席位桥接
         (HTTPS/TLS)          (RLS)   (HTTPS/TLS)
```

**Linux 在 A2A 中的份额**：
- Supabase 服务端运行在 Linux（Ubuntu/Debian）
- 部分 AI 席位运行在 Linux 环境（如 quant-lab）
- SSH 用于服务器运维和席位间安全通道
- 未来可能扩展到更多 Linux 节点

### 2.2 PQC 加固方案

#### 层级一：SSH 运维通道加固（立即）

所有通过 SSH 连接的 Linux 服务器和席位节点，升级到支持混合 KEX 的配置：

```bash
# 检查当前 SSH 版本
ssh -V
# 需要 OpenSSH 9.0+ 支持 PQC KEX，10.0+ 默认启用

# 手动启用混合 KEX（OpenSSH 9.x）
ssh -o KexAlgorithms=mlkem768x25519-sha256 user@host

# 全局配置（~/.ssh/config 或 /etc/ssh/ssh_config）
Host *
    KexAlgorithms mlkem768x25519-sha256,curve25519-sha256@libssh.org
    HostKeyAlgorithms ssh-ed25519
    Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com
    MACs hmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@openssh.com
```

#### 层级二：A2A 总线传输层加固（计划）

当前 A2A 总线依赖 HTTPS/TLS。TLS 的 PQC 迁移进度落后于 SSH：

| 协议 | PQC 状态 | 建议 |
|------|----------|------|
| SSH | OpenSSH 10.0 默认启用混合 KEX | **立即采用** |
| TLS | draft-ietf-tls-hybrid-design-16（RFC Ed Queue） | **等待 OpenSSL 默认启用** |
| WebSocket | 依赖 TLS | 跟随 TLS 进度 |

**过渡方案**：在 TLS PQC 尚未默认启用前，通过 SSH 隧道为 A2A 总线提供 PQC 保护：

```
砚坚桥接 → SSH隧道(mlkem768x25519) → Supabase → SSH隧道 → 其他席位
```

#### 层级三：应用层混合 KEX（创新）

借鉴 SSH 的混合 KEX 思路，在 A2A 总线的应用层实现混合密钥交换：

```javascript
// A2A 混合 KEX 概念设计
// 经典路：X25519 ECDH（Node.js crypto 内置）
// PQC路：ML-KEM-768（需 liboqs-node 绑定）

const { createECDH, createHash } = require('crypto');

// 经典路：X25519
const ecdh = createECDH('prime256v1'); // 或 X25519
const classicPublicKey = ecdh.generateKeys();

// PQC路：ML-KEM-768（需要 liboqs-node）
// const oqs = require('liboqs-node');
// const mlkem = new oqs.KeyEncapsulation('ML-KEM-768');
// const pqPublicKey = mlkem.generate_keypair();

// 合成：session_key = SHA256(ss_pq || ss_classic)
// 只要任意一路未被攻破 → 安全
```

### 2.3 "回环"概念与密码学

机主提到的"回环"（Loopback）在密码学语境中有两层含义：

1. **近端回环（Near-end Loopback）**：发送端内部自环测试，验证本端发送链路完整性
   - 密码学类比：自签名证书验证、本地密钥派生验证
   - A2A 应用：席位内部消息回环测试（发送→接收→验证哈希一致性）

2. **远端回环（Far-end Loopback）**：经传输介质后返回，验证对端及传输链路
   - 密码学类比：双向认证（mTLS）、挑战-响应认证
   - A2A 应用：席位间回环测试（A发送→B接收→B回复→A验证）

**PQC 回环验证方案**：
```
席位A → 发送 PQC 混合 KEX 发起消息 → 席位B
席位B → 回环：PQC 混合 KEX 响应 → 席位A
席位A → 验证：ss_pq 一致 + ss_classic 一致 + session_key 一致 → 回环通过
```

---

## 三、Paramiko 与 PQC 的差距分析

### 3.1 Paramiko 当前状态

| 组件 | Paramiko 5.0.0 | OpenSSH 10.x | 差距 |
|------|----------------|--------------|------|
| KEX | Curve25519（最强经典） | mlkem768x25519-sha256（混合 PQC） | **缺 PQC 路** |
| 加密 | AES-256-GCM（AEAD） | ChaCha20-Poly1305 / AES-256-GCM | 已对齐 |
| MAC | HMAC-SHA2-512-ETM | implicit（AEAD） | 已对齐 |
| 签名 | Ed25519 | Ed25519（PQC 签名实验性） | PQC 签名全行业缺失 |
| 常数时间 | constant_time.bytes_eq | 同 | 已对齐 |

### 3.2 Paramiko PQC 升级路径

```python
# 概念：Paramiko 混合 KEX 扩展
from paramiko.kex_curve25519 import KexCurve25519
# from paramiko.kex_mlkem_x25519 import KexMLKEM768X25519  # 未来新增

class Transport:
    _preferred_kex = (
        "mlkem768x25519-sha256",        # 新增：混合 PQC（最高优先级）
        "curve25519-sha256@libssh.org",  # 现有：经典最强
        "ecdh-sha2-nistp256",
        ...
    )
```

**实施依赖**：
- `liboqs-python`（Open Quantum Safe 的 Python 绑定）
- `cryptography` 库的 ML-KEM 支持（预计 2027 年）
- SSH PQC KEX RFC 最终发布（draft-ietf-sshm-mlkem-hybrid-kex-10 即将发布）

---

## 四、"还差什么"穷举分析

机主引用的五个缺口，逐一分析在 A2A 协议中的具体表现和解决方案：

### 4.1 统一互操作标准

| 问题 | A2A 中的表现 | 解决方案 |
|------|-------------|----------|
| 不同 SSH 实现的 PQC 算法命名不一致 | OpenSSH 用 `mlkem768x25519-sha256`，Paramiko 可能用不同名称 | 跟随 IETF draft-ietf-sshm-mlkem-hybrid-kex 标准化 |
| A2A 席位使用不同密码库 | Node.js crypto vs Python cryptography vs Go circl | 定义 A2A 密码学最小兼容集（ML-KEM-768 + X25519 + SHA-256） |
| 混合 KEX 的共享秘密拼接顺序 | `ss_pq || ss_classic` vs `ss_classic || ss_pq` | 统一为 NIST SP 800-56C 规定的 PQ-first 顺序 |

### 4.2 MTU 分片优化

| 问题 | A2A 中的表现 | 解决方案 |
|------|-------------|----------|
| ML-KEM-768 公钥 1184 bytes vs X25519 公钥 32 bytes | SSH KEXINIT 消息膨胀 | SSH 协议已有分片机制（RFC 4253 §6.1） |
| PQC 签名（ML-DSA 2.4-4.6KB）导致认证消息超 MTU | A2A 认证握手延迟 | 使用 KEMTLS 替代签名认证（用 KEM 做隐式认证） |
| A2A 总线消息大小限制 | Supabase REST API 有 payload 限制 | 大消息分片传输 + SHA-256 完整性校验 |

### 4.3 大规模部署验证

| 问题 | A2A 中的表现 | 解决方案 |
|------|-------------|----------|
| 混合 KEX 在高并发下的性能 | 多席位同时握手可能导致 CPU 峰值 | ML-KEM-768 封装/解封装 ~0.1ms，可接受 |
| 跨网络延迟（LAN/WAN/跨洲） | A2A 席位分布在不同地理位置 | 混合 KEX 仅增加 0.5%-50% 握手延迟 |
| 长期运行稳定性 | 密钥轮换、会话重协商 | 实施自动密钥轮换（每 1 小时重协商 KEX） |

### 4.4 动态密钥管理

| 问题 | A2A 中的表现 | 解决方案 |
|------|-------------|----------|
| PQC 密钥的生成、存储、轮换 | ML-KEM 密钥对需要安全存储 | 借鉴 Paramiko 的 bcrypt KDF + AES-CBC 私钥保护 |
| 密钥撤销机制 | 席位退出时需撤销其密钥 | A2A 总线增加密钥撤销列表（CRL）机制 |
| 多席位密钥同步 | 新席位加入时需分发密钥 | 使用 AGConnect 的统一身份认证 + 密钥分发 |

### 4.5 撤销方案

| 问题 | A2A 中的表现 | 解决方案 |
|------|-------------|----------|
| PQC 签名撤销 | ML-DSA 签名证书的撤销 | 等待 X.509 PQC 扩展标准化 |
| 会话密钥撤销 | 活跃 A2A 会话的强制终止 | Supabase RLS 策略 + 会话 token 黑名单 |
| 席位级撤销 | 恶意席位的密钥撤销 | 总线治理层增加席位密钥撤销广播 |

---

## 五、建议的行动计划

| 优先级 | 行动 | 时间 | 依赖 |
|--------|------|------|------|
| 🔴 立即 | 所有 Linux 服务器 SSH 升级到支持混合 KEX | 1周 | OpenSSH 9.0+ |
| 🔴 立即 | A2A 桥接脚本 MD5→SHA-256（已识别的 S3/S4） | 立即 | 无 |
| 🟠 短期 | 凭据金库 AES-256-GCM 加密（已识别的 S2） | 2周 | VAULT_MASTER_KEY |
| 🟡 中期 | A2A 应用层混合 KEX 原型验证 | 1月 | liboqs-node |
| 🟡 中期 | Paramiko PQC KEX 扩展开发 | 1月 | liboqs-python |
| 🟢 长期 | A2A 总线 TLS PQC 迁移 | 待 OpenSSL | OpenSSL 3.5+ |
| 🟢 长期 | 密钥撤销列表（CRL）机制 | 3月 | AGConnect |

---

*本报告基于 cipherhub.cloud PQC 迁移报告（2026-04-17）和 Paramiko 5.0.0 源码实证分析。*