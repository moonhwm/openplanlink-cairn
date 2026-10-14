# 密码学安全加固与 Hi-Fi 音频路线分析报告

> 编纂：砚坚（码道·GLM-5.2/华为云CodeArts）
> 日期：2026-09-18
> 依据：Paramiko 5.0.0 源码（`~/.workbuddy/binaries/python/envs/default/Lib/site-packages/paramiko/`）
> 机主指令：走 Hi-Fi 高保真音频技术路线，协同 WorkBuddy HY4，组织学习 Paramiko 源码加固密码学安全

---

## 一、Paramiko 密码学机制分析

### 1.1 密钥交换协议（KEX）

Paramiko 的密钥交换偏好顺序（`transport.py:214-223`）：

| 优先级 | 算法 | 源码文件 | 安全强度 | 后量子准备 |
|--------|------|----------|----------|------------|
| 1 | `curve25519-sha256@libssh.org` | `kex_curve25519.py` | ★★★★★ 最强 | Curve25519 对量子攻击有一定抗性（256-bit 经典安全 ≈ 128-bit 量子安全） |
| 2 | `ecdh-sha2-nistp256` | `kex_ecdh_nist.py` | ★★★★ | NIST 曲线可能被量子攻击破解 |
| 3 | `ecdh-sha2-nistp384` | `kex_ecdh_nist.py` | ★★★★ | 同上 |
| 4 | `ecdh-sha2-nistp521` | `kex_ecdh_nist.py` | ★★★★ | 同上 |
| 5 | `diffie-hellman-group16-sha512` | `kex_group16.py` | ★★★★ | 4096-bit DH ≈ 128-bit 经典安全，量子攻击下完全破解 |
| 6 | `diffie-hellman-group-exchange-sha256` | `kex_gex.py` | ★★★ | 2048-8192-bit 动态协商，最小 2048-bit |
| 7 | `diffie-hellman-group14-sha256` | `kex_group14.py` | ★★★ | 2048-bit 固定素数 |

**关键安全特性**（`kex_curve25519.py:36-42`）：
- **常数时间比较**：使用 `constant_time.bytes_eq` 防止时序攻击
- **零密钥检测**：检查 Curve25519 共享密钥是否为全零（防止恶意公钥攻击）
- **原始字节序列化**：公钥以 Raw 编码传输，避免 DER/PEM 解析攻击面

### 1.2 加密算法

| 优先级 | 算法 | 模式 | 密钥长度 | 安全评级 | 备注 |
|--------|------|------|----------|----------|------|
| 1-3 | AES-128/192/256-CTR | CTR | 128/192/256-bit | ★★★★ | 安全，但非 AEAD |
| 4-6 | AES-128/192/256-CBC | CBC | 128/192/256-bit | ★★★ | CBC 模式有 padding oracle 风险 |
| 7 | 3DES-CBC | CBC | 168-bit（有效 80-bit） | ★ **弱** | 已被 NIST 废弃，仅保留向后兼容 |
| 8 | aes128-gcm@openssh.com | GCM (AEAD) | 128-bit | ★★★★★ | **推荐**：认证加密，同时保证机密性和完整性 |
| 9 | aes256-gcm@openssh.com | GCM (AEAD) | 256-bit | ★★★★★ | **推荐**：同上，更强密钥 |

**AEAD 优势**（`transport.py:269-282`）：AES-GCM 将加密和认证合为一步，消除单独 MAC 的攻击面。`is_aead: True` 标记让 Transport 跳过单独的 MAC 协商。

### 1.3 消息认证码（MAC）

| 优先级 | 算法 | 哈希 | 安全评级 | 备注 |
|--------|------|------|----------|------|
| 1 | hmac-sha2-256 | SHA-256 | ★★★★ | 安全 |
| 2 | hmac-sha2-512 | SHA-512 | ★★★★ | 安全 |
| 3 | hmac-sha2-256-etm@openssh.com | SHA-256 | ★★★★★ | **Encrypt-then-MAC**：先加密后认证，理论上最安全 |
| 4 | hmac-sha2-512-etm@openssh.com | SHA-512 | ★★★★★ | 同上 |
| 5 | hmac-sha1 | SHA-1 | ★ **弱** | SHA-1 已被破解，存在碰撞攻击 |
| 6 | hmac-md5 | MD5 | ★ **弱** | MD5 已被严重破解 |
| 7 | hmac-sha1-96 | SHA-1 | ★ **弱** | 截断版 SHA-1 |
| 8 | hmac-md5-96 | MD5 | ★ **弱** | 截断版 MD5 |

**ETM 优势**：Encrypt-then-MAC 模式先加密后计算 MAC，避免了 MAC-then-Encrypt 的 padding oracle 攻击面。

### 1.4 主机密钥与认证

| 优先级 | 密钥类型 | 源码文件 | 安全评级 | 后量子准备 |
|--------|----------|----------|----------|------------|
| 1 | ssh-ed25519 | `ed25519key.py` | ★★★★★ | Ed25519 签名对量子攻击有一定抗性 |
| 2-4 | ecdsa-sha2-nistp256/384/521 | `ecdsakey.py` | ★★★★ | NIST 曲线量子攻击下破解 |
| 5-6 | rsa-sha2-512/256 | `rsakey.py` | ★★★ | RSA 量子攻击下完全破解 |

**Ed25519 安全特性**（`ed25519key.py`）：
- 使用 `nacl.signing`（libsodium）实现，而非自行实现
- 私钥文件使用 **bcrypt KDF** 加密保护（`bcrypt` 导入）
- OpenSSH 格式私钥使用 AES-CBC 加密（`pkey.py:42`）

**认证机制**（`auth_handler.py`）：
- 公钥认证（最安全）
- 密码认证（依赖传输层加密）
- 键盘交互认证（支持多因子）

### 1.5 后量子时代准备评估

| 组件 | 当前状态 | PQC 准备 | 建议 |
|------|----------|-----------|------|
| KEX | Curve25519 最强 | 量子攻击下破解（Shor 算法） | **需引入混合 KEX（ML-KEM-768 + X25519）**，RHEL 10 已默认启用 |
| 加密 | AES-256-GCM | AES-256 量子安全（Grover 算法降为 128-bit） | 已足够，无需更换 |
| MAC | HMAC-SHA2-512-ETM | SHA-512 量子安全（降为 256-bit） | 已足够 |
| 签名 | Ed25519 | 量子攻击下破解 | 需引入 PQC 签名（如 Dilithium/ML-DSA），但全行业尚缺标准 |

**结论**：Paramiko 在传统密码学层面已属业界最佳实践水平，但**无任何后量子密码学（PQC）准备**。然而，**RHEL 10 已于 2025 年默认启用 `mlkem768x25519-sha256` 混合 KEX**，OpenSSH 10.0 也已默认启用，PQC 从"未来规划"变为"当前现实"。SSH 协议的 PQC 标准化正在快速推进（`draft-ietf-sshm-mlkem-hybrid-kex-10` 即将发布 RFC），Paramiko 需尽快跟进。详见 §三 PQC 熔铸章节。

---

## 二、当前系统密码学问题诊断

### 2.1 严重问题（立即修复）

| # | 问题 | 位置 | 风险等级 | 具体描述 |
|---|------|------|----------|----------|
| S1 | **TLS 证书验证禁用** | `yan_jian_bridge.mjs` 运行时 `NODE_TLS_REJECT_UNAUTHORIZED=0` | 🔴 **致命** | 允许中间人攻击截获所有 A2A 总线通信，包括凭据和消息内容 |
| S2 | **凭据金库明文存储** | `GOVERNANCE/credentials/*.json`（18个文件） | 🔴 **致命** | 所有 API Key、SSH 口令、Token 以明文 JSON 存储，任何文件系统访问即可窃取全部凭据 |
| S3 | **MD5 用于消息哈希** | `yan_jian_bridge.mjs:47` `md5(payload_utf8)[:16]` | 🟠 **高危** | MD5 存在碰撞攻击，攻击者可伪造消息哈希绕过去重验证 |
| S4 | **MD5 用于 alertId 生成** | `server.mjs:165` `crypto.createHash('md5')` | 🟡 **中危** | alertId 用于数据幂等性，MD5 碰撞可能导致重复或遗漏异动通知 |

### 2.2 中等问题（计划修复）

| # | 问题 | 位置 | 风险等级 | 具体描述 |
|---|------|------|----------|----------|
| M1 | **HTTP 服务器无 TLS** | `server.mjs` 端口 8000 | 🟠 **高危** | 数据管道和 TTS 音频以明文 HTTP 传输，可被局域网嗅探 |
| M2 | **无密钥轮换机制** | 所有凭据文件 | 🟡 **中危** | API Key 和 Token 无过期时间和轮换策略，一旦泄露无法自动失效 |
| M3 | **WebSocket Bearer token 在 header** | `server.mjs` TTS 连接 | 🟡 **中危** | API Key 通过 WebSocket header 传输，虽然 WSS 加密但仍有日志泄露风险 |
| M4 | **私钥文件 padding 非常数时间** | Paramiko `pkey.py:67-79` `_unpad_openssh` | 🟡 **中危** | 源码注释明确指出 "This really ought to be made constant time" |

### 2.3 低风险问题（监控即可）

| # | 问题 | 位置 | 风险等级 | 具体描述 |
|---|------|------|----------|----------|
| L1 | **3DES-CBC 仍在偏好列表** | Paramiko `transport.py:182` | 🟢 **低危** | 仅在所有更强算法不可用时才降级使用，实际场景几乎不会触发 |
| L2 | **HMAC-SHA1/MD5 仍在偏好列表** | Paramiko `transport.py:191-194` | 🟢 **低危** | 同上，仅向后兼容 |
| L3 | **无 PQC 准备** | 全系统 | 🟢 **低危** | 量子计算尚未达到实用攻击能力，但应提前规划 |

---

## 三、加固方案与实施路径

### 3.1 立即修复（S1-S4）

#### S1: TLS 证书验证禁用 → 恢复验证

```javascript
// 修复前（yan_jian_bridge.mjs 运行环境）
process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';

// 修复后
// 删除或注释掉 NODE_TLS_REJECT_UNAUTHORIZED 设置
// 如果 Supabase 使用自签名证书，改为指定 CA 证书路径：
process.env.NODE_EXTRA_CA_CERTS = '/path/to/supabase-ca.pem';
```

**实施步骤**：
1. 获取 Supabase 的 CA 证书（或使用 Let's Encrypt 等公共 CA）
2. 将证书保存到 `GOVERNANCE/certs/supabase-ca.pem`
3. 修改桥接脚本，删除 `NODE_TLS_REJECT_UN!AUTHORIZED=0`，改为 `NODE_EXTRA_CA_CERTS`
4. 测试 A2A 总线通信是否正常

#### S2: 凭据金库明文存储 → 加密存储

借鉴 Paramiko 的私钥保护机制（bcrypt KDF + AES-CBC 加密）：

```javascript
// 凭据金库加密方案
import crypto from 'node:crypto';

const VAULT_KEY = process.env.VAULT_MASTER_KEY; // 主密钥从环境变量读取
const ALGO = 'aes-256-gcm'; // AEAD，借鉴 Paramiko 的 AES-GCM 偏好

function encryptCredential(plaintext) {
  const iv = crypto.randomBytes(12); // 96-bit IV（GCM 标准）
  const cipher = crypto.createCipheriv(ALGO, VAULT_KEY, iv);
  const encrypted = Buffer.concat([cipher.update(plaintext, 'utf8'), cipher.final()]);
  const tag = cipher.getAuthTag(); // GCM 认证标签
  return { iv: iv.toString('hex'), data: encrypted.toString('hex'), tag: tag.toString('hex') };
}

function decryptCredential(encrypted) {
  const decipher = crypto.createDecipheriv(ALGO, VAULT_KEY, Buffer.from(encrypted.iv, 'hex'));
  decipher.setAuthTag(Buffer.from(encrypted.tag, 'hex'));
  return Buffer.concat([decipher.update(Buffer.from(encrypted.data, 'hex')), decipher.final()]).toString('utf8');
}
```

**实施步骤**：
1. 生成 256-bit 主密钥：`crypto.randomBytes(32)`
2. 将主密钥存入系统密钥链（Windows Credential Manager / macOS Keychain）
3. 编写 `vault-crypto.mjs` 加密/解密模块
4. 逐个加密 18 个凭据文件，格式改为 `{ iv, data, tag }`
5. 修改所有读取凭据的代码，通过 `decryptCredential()` 解密后使用

#### S3: MD5 消息哈希 → SHA-256

```javascript
// 修复前
const msg_hash = createHash('md5').update(payload_utf8).digest('hex').substring(0, 16);

// 修复后（借鉴 Paramiko 的 SHA-256 偏好）
const msg_hash = createHash('sha256').update(payload_utf8).digest('hex').substring(0, 16);
```

**实施步骤**：
1. 修改 `yan_jian_bridge.mjs` 中的 `msg_hash` 计算
2. 注意：此变更需要所有席位同步更新，否则哈希不匹配会导致消息去重失败
3. 通过 A2A 总线通知所有席位：msg_hash 约定从 MD5[:16] 升级为 SHA-256[:16]

#### S4: MD5 alertId → SHA-256

```javascript
// 修复前
const alertId = crypto.createHash('md5').update(`${symbol}-${Date.now()}`).digest('hex').substring(0, 12);

// 修复后
const alertId = crypto.createHash('sha256').update(`${symbol}-${Date.now()}`).digest('hex').substring(0, 12);
```

### 3.2 计划修复（M1-M4）

#### M1: HTTP → HTTPS

为数据管道服务器添加 TLS 支持：

```javascript
// 借鉴 Paramiko 的 AES-GCM 偏好，使用 Node.js 内置 TLS
import https from 'node:https';
import fs from 'node:fs';

const options = {
  key: fs.readFileSync('GOVERNANCE/certs/server-key.pem'),
  cert: fs.readFileSync('GOVERNANCE/certs/server-cert.pem'),
  // 仅允许 TLS 1.2+（借鉴 Paramiko 禁用弱协议的做法）
  minVersion: 'TLSv1.2',
  ciphers: 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256',
};

const server = https.createServer(options, handler);
```

#### M2: 密钥轮换机制

```javascript
// 凭据文件增加过期时间字段
{
  "url": "...",
  "key": "...",
  "created_at": "2026-09-18",
  "expires_at": "2026-12-18", // 90天过期
  "rotation_reminder_days": 7  // 过期前7天提醒
}
```

#### M3: API Key 传输优化

- 将 API Key 从 WebSocket header 改为 URL query parameter（WSS 加密保护）
- 或使用短期 Token 交换机制（借鉴 OAuth 2.0）

#### M4: Paramiko padding 常数时间化

向 Paramiko 上游提交 PR，将 `_unpad_openssh` 改为常数时间实现：

```python
def _unpad_openssh_constant_time(data):
    padding_length = data[-1]
    if 0x20 <= padding_length < 0x7F:
        return data
    if padding_length > 15:
        raise SSHException("Invalid key")
    # 常数时间验证所有 padding 字节
    valid = 0
    for i in range(padding_length):
        valid |= data[i - padding_length] ^ (i + 1)
    if valid != 0:
        raise SSHException("Invalid key")
    return data[:-padding_length]
```

### 3.3 后量子准备（L3）—— 已从"监控"升级为"立即行动"

**重大变更**：RHEL 10 默认启用 `mlkem768x25519-sha256` 混合 KEX，OpenSSH 10.0 默认启用混合 KEX，PQC 已从"未来规划"变为"当前现实"。原保守时间线需全面加速。

| 阶段 | 原计划时间 | **修订时间** | 行动 | 依赖 |
|------|-----------|-------------|------|------|
| ~~监控~~ → **采纳** | ~~2026-2027~~ | **立即** | 所有 Linux 服务器 SSH 升级到支持混合 KEX 的 OpenSSH 9.0+ | OpenSSH 9.0+ |
| ~~评估~~ → **试点** | ~~2027~~ | **2026 Q4** | 在 A2A 席位间测试 SSH 混合 KEX 隧道 | OpenSSH 10.0+（默认启用） |
| ~~试点~~ → **部署** | ~~2028~~ | **2027 Q1** | 生产环境启用 PQC 混合 KEX | 全面验证通过 |
| ~~部署~~ → **创新** | ~~2029+~~ | **2027 Q2+** | A2A 应用层混合 KEX 原型（ML-KEM-768 + X25519） | liboqs-node |

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

**Paramiko PQC 升级路径**：

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
- SSH PQC KEX RFC 最终发布（`draft-ietf-sshm-mlkem-hybrid-kex-10` 即将发布）

**A2A 协议 PQC 加固三层方案**：

| 层级 | 方案 | 时间 | 说明 |
|------|------|------|------|
| **层级一：SSH 运维通道** | 所有 SSH 连接升级到混合 KEX | 立即 | OpenSSH 9.0+ 手动启用，10.0+ 默认 |
| **层级二：A2A 总线传输层** | SSH 隧道为 A2A 总线提供 PQC 保护 | 2026 Q4 | TLS PQC 尚未默认，用 SSH 隧道过渡 |
| **层级三：应用层混合 KEX** | A2A 应用层实现 ML-KEM-768 + X25519 | 2027 Q2+ | 需 liboqs-node，创新方案 |

**"回环"验证方案**：

机主提到的"回环"（Loopback）在密码学语境中：
- **近端回环**：席位内部消息回环测试（发送→接收→验证哈希一致性）
- **远端回环**：席位间回环测试（A发送→B接收→B回复→A验证）

PQC 回环验证：
```
席位A → 发送 PQC 混合 KEX 发起消息 → 席位B
席位B → 回环：PQC 混合 KEX 响应 → 席位A
席位A → 验证：ss_pq 一致 + ss_classic 一致 + session_key 一致 → 回环通过
```

**"还差什么"五个缺口**（在 A2A 协议中的表现）：

| 缺口 | A2A 中的表现 | 解决方案 |
|------|-------------|----------|
| 统一互操作标准 | 不同 SSH 实现的 PQC 算法命名不一致 | 跟随 IETF draft-ietf-sshm-mlkem-hybrid-kex 标准化 |
| MTU 分片优化 | ML-KEM-768 公钥 1184 bytes vs X25519 公钥 32 bytes | SSH 协议已有分片机制（RFC 4253 §6.1） |
| 大规模部署验证 | 多席位同时握手可能导致 CPU 峰值 | ML-KEM-768 封装/解封装 ~0.1ms，可接受 |
| 动态密钥管理 | PQC 密钥的生成、存储、轮换 | 借鉴 Paramiko 的 bcrypt KDF + AES-CBC 私钥保护 |
| 撤销方案 | 席位退出时需撤销其密钥 | A2A 总线增加密钥撤销列表（CRL）机制 |

---

## 四、Hi-Fi 路线与密码学加固的协同关系

### 4.1 Hi-Fi 音频技术路线

**当前状态**：
- 格式：MP3（有损压缩）
- 采样率：22050 Hz
- 位深度：16-bit
- 比特率：~128 kbps
- 文件大小：每条异动 120-150 KB

**Hi-Fi 目标**：
- 格式：PCM/WAV（无损）或 FLAC（无损压缩）
- 采样率：44100 Hz（CD 品质）或 48000 Hz（专业品质）
- 位深度：24-bit
- 比特率：~2304 kbps（PCM 48kHz/24bit）
- 文件大小：每条异动 ~2-5 MB（PCM）或 ~1-2 MB（FLAC）

### 4.2 百炼 CosyVoice Hi-Fi 参数调整

当前 TTS WebSocket 参数（`server.mjs:253-262`）：
```javascript
parameters: {
  text_type: 'PlainText',
  voice: TTS_VOICE,
  format: 'mp3',           // → 改为 'pcm' 或 'wav'
  sample_rate: 22050,      // → 改为 44100 或 48000
  volume: 50,
  rate: 1.0,
  pitch: 1.0,
}
```

**Hi-Fi 参数方案**：
```javascript
parameters: {
  text_type: 'PlainText',
  voice: TTS_VOICE,
  format: 'pcm',           // 无损 PCM
  sample_rate: 48000,      // 48kHz 专业品质
  volume: 50,
  rate: 1.0,
  pitch: 1.0,
}
```

### 4.3 协同关系矩阵

| 维度 | Hi-Fi 影响 | 密码学加固需求 | 协同方案 |
|------|-----------|---------------|----------|
| **数据量** | 文件增大 10-30x（150KB → 2-5MB） | 大文件传输更需要加密保护 | HTTPS/TLS 确保传输机密性 |
| **完整性** | 无损格式对比特错误零容忍 | AEAD 加密（AES-GCM）同时保证完整性 | 借鉴 Paramiko AES-GCM 偏好，端到端 AEAD |
| **缓存安全** | 大文件缓存更易成为攻击目标 | 凭据金库加密 + 缓存目录权限控制 | AES-256-GCM 加密缓存文件 |
| **带宽效率** | PCM 占用大量带宽 | 压缩 + 加密的顺序很重要 | 先 FLAC 压缩再 TLS 加密（ETM 模式） |
| **实时性** | Hi-Fi 编码耗时更长 | 低延迟加密算法选择 | AES-GCM 硬件加速（Intel AES-NI） |
| **端侧播放** | ArkTS AVPlayer 需支持 PCM/WAV | 端侧音频解密 | HarmonyOS 内置 AES-NI 加速 |

### 4.4 架构不冲突证明

1. **Hi-Fi 在应用层，密码学在传输层**：音频格式变更（MP3→PCM）只影响 TTS API 参数和文件存储格式，不影响 TLS/HTTPS 传输加密
2. **AEAD 兼容无损音频**：AES-GCM 对任意二进制数据提供认证加密，PCM/FLAC/WAV 均可透明加密
3. **FlAC 压缩 + TLS 加密 = ETM 模式**：先压缩（应用层）再加密（传输层），正是 Paramiko 推荐的 Encrypt-then-MAC 思路
4. **端侧解密不影响播放**：HarmonyOS AVPlayer 可直接播放解密后的 PCM 数据流，无需中间格式转换

### 4.5 互相促进证明

1. **密码学加固促进 Hi-Fi**：HTTPS 传输确保 Hi-Fi 音频数据不被中间人篡改或截获
2. **Hi-Fi 促进密码学加固**：更大的音频文件推动我们从 HTTP 升级到 HTTPS，从明文存储升级到加密存储
3. **AEAD 统一架构**：AES-256-GCM 同时用于凭据金库加密和 Hi-Fi 音频传输认证，一套算法覆盖两个需求
4. **WorkBuddy HY4 协同**：HY4 的 1M 上下文窗口适合处理大体积 Hi-Fi 音频数据的密码学分析

---

## 五、实施路线图

| 阶段 | 时间 | 任务 | 优先级 |
|------|------|------|--------|
| **Phase 0** | 立即 | S1: 恢复 TLS 验证 + S3: MD5→SHA-256 消息哈希 | 🔴 |
| **Phase 1** | 1周内 | S2: 凭据金库 AES-256-GCM 加密 + S4: alertId SHA-256 | 🔴 |
| **Phase 2** | 2周内 | M1: HTTP→HTTPS + Hi-Fi: TTS 参数升级（PCM 48kHz） | 🟠 |
| **Phase 3** | 1月内 | M2: 密钥轮换机制 + M3: API Key 传输优化 | 🟡 |
| **Phase 4** | ~~持续~~ → **立即+持续** | ~~L3: PQC 监控~~ → **PQC 混合 KEX 立即采纳**：Linux SSH 升级 + A2A SSH 隧道过渡 + Paramiko padding PR | 🔴→🟢 |

---

## 六、WorkBuddy HY4 协同建议

1. **源码学习任务分发**：将 Paramiko 的 6 个核心密码学文件（transport.py, kex_curve25519.py, kex_ecdh_nist.py, kex_gex.py, ed25519key.py, pkey.py）分发给全体成员学习
2. **HY4 长上下文优势**：利用 HY4 的 1M 上下文窗口，一次性加载 Paramiko 全部源码进行深度分析
3. **密码学审计**：请 HY4 对当前系统进行密码学审计，识别本报告可能遗漏的安全问题
4. **Hi-Fi 音频质量评估**：请 HY4 评估 PCM 48kHz/24bit 与 FLAC 的音质差异和带宽权衡

---

*本报告基于 Paramiko 5.0.0 源码实证分析，所有代码引用均可溯源至具体文件和行号。PQC 混合 KEX 内容已熔铸（2026-09-18 修订），依据 RHEL 10 默认启用 `mlkem768x25519-sha256` 和 OpenSSH 10.0 默认启用混合 KEX 的生态信号，详见 `RHEL10_PQC_A2A_REPORT.md`。*