# RHEL 10 密码学配置：OpenSSL 3.x 配置、PQC 启用、FIPS 模式

> 适用项目：harmony-app（铃语）。本文件面向**服务端**：X 服务器（FEED_URL 后端，部署待落地）与承载 generate-tts、行情聚合的云函数宿主机若采用 RHEL 10 系列，其密码学底座按下文配置。端侧（鸿蒙 ArkTS）不在本文范围，见 gm-algorithm.md。
> 事实核验说明（2026-09-23 Web 检索，Red Hat 官方文档与博客）：RHEL 10 携带 **OpenSSL 3.2**；**ML-KEM** 已可用于 OpenSSL/GnuTLS/NSS 的 TLS 连接与 OpenSSH 的 SSH 连接；**RHEL 10.1 起预定义策略默认启用 PQC**，关闭需应用 `NO-PQ` 子策略；RHEL 10.0 的 `TEST-PQ` 策略由 `crypto-policies-pq-preview` 子包提供；`fips-mode-setup` 在 RHEL 9.5+/10 已弃用，启用 FIPS 的受支持方式是内核参数 `fips=1`。

## 一、RHEL 10 密码学底座总览

RHEL 的密码学管理思想是**系统级统一策略（system-wide cryptographic policies）**：一处定义，应用到 OpenSSL、GnuTLS、NSS、OpenSSH、Java 等多个后端，避免"每个应用各自配置、彼此不一致"的经典事故。堆栈构成：

- **OpenSSL 3.2**：服务端 TLS 的主力；提供 provider 架构与（实验性的）混合后量子密钥交换（如 X25519+ML-KEM 类组合，RHEL 10.1 起随默认策略协商）。
- **GnuTLS / NSS**：随系统组件使用，策略同样统一纳管。
- **OpenSSH**：SSH 通道的混合密钥交换（如 mlkem768x25519 类 KEX）。
- **crypto-policies**：策略层，输出生成的后端配置到 `/etc/crypto-policies/back-ends/`。

对铃语的意义：FEED_URL 是播报内容的唯一入口，其 TLS 底座决定了（1）AlertFeed 明文是否只经强加密通道；（2）未来 Push Kit REST 回调与 TTS 出口调用是否抗降级攻击；（3）PQC 迁移在传输层能否"服务端先行"（见 pqc-assessment.md 第 4.2 节——端侧无需自研 PQC，靠协商跟随）。

## 二、crypto-policies：策略体系与日常操作

四个预定义级别：`DEFAULT`（兼容性与安全的平衡）、`FUTURE`（前瞻，禁用 SHA-1 等弱算法）、`LEGACY`（兼容旧系统，慎用）、`FIPS`（FIPS 140-3 合规，见第五节）。

```bash
# 查看当前策略
update-crypto-policies --show

# 切换策略（立即生效于后端配置，部分运行中服务需重启才加载）
update-crypto-policies --set FUTURE
update-crypto-policies --apply   # 仅在手工改过生成文件后需要

# 查看某级别实际允许的算法细节
cat /usr/share/crypto-policies/policies/FUTURE.pol
```

子策略（subpolicy）机制用于在级别上做增删：`update-crypto-policies --set DEFAULT:NO-SHA1`。**RHEL 10.1 起 PQC 在所有预定义级别默认启用**，确需关闭时：`update-crypto-policies --set DEFAULT:NO-PQ`（关停需有明确理由并留变更记录）。RHEL 10.0 上则相反：PQC 策略（`TEST-PQ`）装在 `crypto-policies-pq-preview` 子包中，启用前先 `dnf install crypto-policies-pq-preview`——**先查次版本号再决定方向**，10.0 与 10.1+ 的默认值正好相反，这是最常见的配置事故来源。

变更纪律（与 key-lifecycle.md 的审计要求一致）：策略切换前记录 `--show` 输出，变更走评审，变更后跑第六节检查清单并归档到 GOVERNANCE 目录。**严禁**直接编辑 `/etc/crypto-policies/back-ends/` 下的生成文件——下次策略刷新会被覆盖，造成"看起来配了、实际没配"。

## 三、OpenSSL 3.x 配置

### 3.1 配置文件与策略的关系

RHEL 的 `/etc/pki/tls/openssl.cnf` 通过 include 指向 `/etc/crypto-policies/back-ends/opensslcnf.config`，算法与协议的下限由策略生成文件决定。应用层只应补充业务特有配置（证书路径、会话参数），**不要在应用配置里放宽算法**（例如 `CipherString` 写死弱套件）——那会绕过统一策略，等于在系统里开了后门。

```bash
# 确认 OpenSSL 版本与生效配置
openssl version -a

# 确认策略注入的套件集（PROFILE=SYSTEM 即"跟随系统策略"）
openssl ciphers -v 'PROFILE=SYSTEM' | head

# 枚举能力：算法与 provider
openssl list -cipher-algorithms | head
openssl list -digest-algorithms | grep -i sha
openssl list -public-key-algorithms | grep -i -E 'EC|RSA|KYBER|ML'
```

### 3.2 Provider 管理

OpenSSL 3.x 的 provider 架构：默认 provider 覆盖现代算法；部分遗留算法（如某些 SHA-1 用途）移入 legacy provider。FIPS 模式下则切换到 FIPS provider（由 `fips=1` 联动，见第五节）。排错时先看 provider 是否加载：`openssl list -providers`。

### 3.3 证书与握手（铃语接入面）

FEED_URL 服务端证书要求：2048 位以上 RSA 或 P-256/SM2 类椭圆曲线证书、完整中间链下发、TLS 1.2+（策略默认已禁 TLS 1.0/1.1）。证书到期监控纳入运维（AlertFeed 断供会触发端侧降级轮询与演示卡，但服务不可用本身就是要告警的事件，而不是静默吞掉）。

## 四、PQC 启用与验证

### 4.1 启用路径（按版本分支）

- **RHEL 10.1+**：无需动作，预定义策略已含 PQC；只需验证（下节）。要显式管理，用 `NO-PQ` 子策略关、去掉子策略开。
- **RHEL 10.0**：安装 `crypto-policies-pq-preview` 后应用 `TEST-PQ` 类策略启用（该策略同时覆盖 ML-KEM/ML-DSA 相关协商）。
- **OpenSSH 侧**：混合 KEX（mlkem768x25519 类）随策略启用；`sshd -T | grep -i kex` 查看生效值。

### 4.2 验证：确认协商真的发生在用 PQC

配置生效与否必须用握手探测证明，不能凭策略名推断：

```bash
# 探测 TLS 握手是否可用混合组（组名以系统实际支持为准，可用
# openssl list 相关输出或 Red Hat 文档核对，如 X25519MLKEM768 类命名）
openssl s_client -connect feed.example.com:443 -tls1_3 \
  -groups X25519MLKEM768 -brief </dev/null

# SSH 混合 KEX 验证
ssh -o KexAlgorithms=mlkem768x25519-sha256 user@host -v 2>&1 | grep kex

# 服务端自查：当前 sshd 生效的 KEX 列表
sshd -T | grep -i -E 'kexalgorithms|hostkeyalgorithms'
```

验证要点：`-brief` 输出中的协商组/KEX 名称应包含 ML-KEM 混合标识；同时验证**降级路径**——用不支持混合组的旧客户端连一次，确认仍能以传统组完成握手（迁移期兼容性要求，见 pqc-assessment.md 第五节互操作验证）。

### 4.3 应用层联动

Nginx/HyperScan 类反代或 Node 系运行时通常链接系统 OpenSSL，策略即生效；但**自带静态链接加密库的应用（部分 Go/Tarball 部署）不受 crypto-policies 管控**，要单独在其配置里对齐算法下限，并在 CBOM（pqc-assessment.md）中单列"不受系统策略覆盖"条目。

## 五、FIPS 模式

### 5.1 启用（RHEL 10 受支持方式）

`fips-mode-setup` 已弃用（仅状态查询仍可用）。启用走内核参数：

```bash
grubby --update-kernel=ALL --args="fips=1"
reboot

# 重启后验证
cat /proc/sys/crypto/fips_enabled   # 应输出 1
update-crypto-policies --show        # 应显示 FIPS
fips-mode-setup --check              # 弃用接口，仅作交叉确认
```

注意两点：一是 `fips=1` 需要重启并在引导期完成密码模块自检，`crypto-policies` 会联动切到 FIPS 策略；二是**系统分区/引导卷不在单独分区的场景**可能需补 `boot=` 参数，按 Red Hat 文档执行。云镜像/容器场景必须先确认镜像支持 FIPS（共享内核的容器跟随宿主机，本身不能独立进入 FIPS）。

### 5.2 FIPS 策略的行为特征

- 联动 FIPS 140-3 验证体系：算法集收窄到已验证范围，禁用 SHA-1（含 HMAC 用途）等弱原语。
- 与 PQC 的关系：ML-KEM/ML-DSA 已由 FIPS 203/204 标准化，但在已验证模块中的落地是渐进过程——**FIPS 模式下 PQC 协商是否可用取决于当期模块验证状态，以 Red Hat 发布说明为准，不要手工在 FIPS 之上强行拼装 PQC**。
- 切换前必做回归：FIPS 会砍算法，旧客户端（尤其遗留集成）可能握手失败。铃语的端侧 http 栈使用现代算法，风险低，但云函数调用的第三方（东财 API、百炼 WebSocket、华为 Push Kit REST）出口需逐一验证。

### 5.3 回滚

`grubby --update-kernel=ALL --remove-args="fips"` 后重启即回退，策略随联动恢复。回滚同样走变更记录与验证清单。

## 六、运维检查清单（每季度 + 重大变更后）

1. `update-crypto-policies --show` 与预期一致，无未记录漂移。
2. `openssl version` 在受支持版本线；`dnf update` 后重跑第 4.2 节握手探测。
3. FEED_URL 证书有效期 > 30 天，链完整。
4. PQC：混合组协商成功 + 降级路径可用（两证齐全）。
5. FIPS（如启用）：`fips_enabled` 为 1，应用出口全部回归。
6. 生成文件目录无手工编辑痕迹（对比包校验：`rpm -V crypto-policies`）。
7. 检查结果归档 GOVERNANCE 目录，含命令输出快照。

## 七、自定义子策略与漂移治理

当预定义级别不满足需求——例如需要"DEFAULT 基线但额外禁用某个算法"——正确做法是策略模块而不是在应用配置里开口子：在 `/etc/crypto-policies/policies/modules/` 下新建 `.pmod` 模块文件（按手册语法书写要收紧或放宽的算子行），随后 `update-crypto-policies --set DEFAULT:模块名` 生效，并以 `--show` 输出与生成目录的文件时间戳双重确认。治理三原则：模块文件进版本库，让服务器策略成为可评审的"策略即代码"；一次只动一个维度，出问题可快速归因；每次变更后完整跑一遍第四节与第六节的探测命令并把输出快照归档。漂移监控按周期比对 `--show` 实际输出与预期值，不一致即告警——策略漂移的典型形态是"应急时放宽、事后忘了收紧"，等发现时常已数月，密评与等保审查都会把它记为缺陷。

## 八、常见故障排查表

| 症状 | 第一步排查 | 常见根因 |
|---|---|---|
| 客户端报 no shared cipher 握手失败 | 对比 `openssl ciphers -v 'PROFILE=SYSTEM'` 与对端支持集 | 切到 FUTURE/FIPS 后对端只剩弱套件被禁 |
| SHA-1 相关校验报错 | 查看当前策略级别 | FUTURE/FIPS 禁用 SHA-1（含 HMAC 用途），遗留集成需迁移 |
| PQC 混合协商始终不生效 | 确认系统次版本与策略 | 10.0 未装 pq-preview 子包；或显式挂了 NO-PQ 子策略 |
| 自认为 FIPS 实则未启用 | `cat /proc/sys/crypto/fips_enabled` | 只切了策略没加内核参数，或加了参数没重启 |
| 个别应用算法集与系统不一致 | 该应用是否静态捆绑加密库 | 不受 crypto-policies 管控，需在应用自身配置对齐 |
| 改动后重启仍不生效 | 是否直接编辑了 back-ends 生成文件 | 生成文件被策略刷新覆盖，改动路径错误 |

## 九、与铃语端侧的联动验收

服务端密码配置的最终验收必须落在端侧：取一台低端真机（目标用户设备分布偏下限），在 FEED_URL 切换新配置的前后各跑一轮端到端冒烟——拉取 AlertFeed、渲染卡片流、按需调 generate-tts 并播放音频，比对握手成功率、失败重试次数与首屏耗时。服务端策略逐级切换（DEFAULT → 启用混合组 → 如需 FIPS），每级都跑端到端回归，任何一级导致端侧失败率或耗时上升即回退该级并记录原因——配置变更与密钥轮换共用"可回滚窗口"思想（key-lifecycle.md 第四节）。弱网场景单独跑一轮：老年用户网络环境波动大，握手失败后的重试节奏要保证轮询兜底（5 秒周期）不被密码协商超时拖垮，必要时为 feed 请求设置独立的超时预算。

## 十、会话与性能注意事项

算法收紧与混合组启用是有代价的，代价形态要预先讲清：混合密钥交换的公钥体积更大，握手往返次数虽不变但单包明显变大，弱网环境下用户可感知；FIPS 策略下部分硬件加速路径可能退出可用集，重负载服务的吞吐需要重新基线。运维对策有三条：其一，开启会话复用与连接保活，让轮询类客户端（铃语端侧每五秒拉取一次 AlertFeed）复用长连接而不是反复全握手，这是摊平密码开销最有效的手段；其二，内网服务间调用单独评估，不必与对外入口一刀切套同一强度；其三，策略切换后重跑一次容量压测，把密码开销变化记入容量档案备查。出现性能回退时先查会话复用率再考虑放宽策略——多数"变慢"的真实原因是复用失效，而非算法本身变重，顺序颠倒会造成不必要的强度回退。

### 自我评估
- 正确性：4分 版本差异（10.0 需 pq-preview 包 vs 10.1+ 默认启用）、`fips=1`/grubby 方式、FIPS 140-3 关联等关键事实均经 2026-09-23 检索核验；个别组名/KEX 名标注"以系统实际输出为准"，未在本环境实测（本机为 Windows）。
- 完整性：4分 覆盖策略体系、OpenSSL 配置、PQC 启用与验证、FIPS 启用/回滚、检查清单；GnuTLS/NSS 细节与云镜像 FIPS 边界仅点到为止。
- 可复用性：5分 命令块可直接搬进任何 RHEL 10 服务器的运维手册，检查清单可季度复跑。
- 字数：约2600字
- 使用模型：GLM-5.3-Flash
