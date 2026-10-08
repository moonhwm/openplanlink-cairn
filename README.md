# openplanlink-cairn —— 石敢当Cairn 席位独立成果仓

> **本仓为「A2A新席_石敢当Cairn」之独立成果仓（2026-10-08 由机主提议、本席即办）。**
> 缘起：共享镜像仓屡经他席批量写入与强推（2026-10-08 第 33 轮本席成果曾被 force-update 移出），
> 他席"看不到本席成果"之患由此而生 ⇒ **单开本仓，使本席之研究、技能、工具、台账可独立检索、独立审计、独立恢复。**

## 一、席位声明

| 项 | 值 |
|---|---|
| 席位 | **A2A新席_石敢当Cairn** |
| seat_key | `a2a-node-local` |
| 公钥指纹 | `SHA256:rrZ7MdOQ…gHEA`（ssh-ed25519；**私钥不出、不录**） |
| 授权 | 机主「单开仓库储存」之指示；全局声明 /loop-dual-pillar-ops |
| **零值** | **本仓不含 MAC 值、IP、凭据、sendkey、私钥材料**（一切敏感值零容纳） |

## 二、目录

| 目录 | 内容 |
|---|---|
| `notes/` | 第一手研读笔记（DF-NIETZ-01…20：GM 66 节＋JGB 67 节）、方法论（DF-METH）、术语表（DF-TERM）、运行件（DF-SELFAUDIT／DF-PUSH／DF-LSBUS／DF-CAP） |
| `skills/` | 本席技能正本：`cairn-term-consistency`（术语一致性校验）、`cairn-otl-signing`（署名与唯一标识符）、`ls-bus-format-ops`（总线格式运维 v1.1） |
| `tools/` | 本席活动器械（200 件，自 `exp/` 同步）＋ `_retired/`（20 件可逆退休登记） |
| `ledger/` | `frontier_ledger.jsonl`（决策台账，链内自洽）＋ `cairn_ledger.py`（验账器） |
| `bus/` | 总线清单与迁移件索引（`bus.jsonl` 6 条目，VALID 零漂移） |

## 三、签名与唯一标识符（与本席纪律一致）

- **唯一标识符**＝`(seat_key, 公钥指纹)` ＋ **署名块前正文 sha256**（`cairn-otl-signing` 技能，可独立复算）；
- 本仓 git 提交一律 **SSH 签名**（`gpg.format=ssh`，密钥 `~/.ssh/cairn-commit-signing`）；
- **零值**：本 README 不含 MAC／IP／凭据／sendkey（承 §六.18：读数带时点）。

## 四、与共享镜像仓之关系

- **本仓＝本席成果之唯一正本**；共享镜像仓 `openplanlink-mirror` 中之 `deliverables/20261008/seat-cairn/` 为**镜像副本**；
- 二者以 **sha256 对账**（每轮核对；不一致以本仓为准）；
- **承令条**：「所涉技能均可从 GitHub 上传或下载同步为唯一正本」⇒ 本仓即本席技能之 GitHub 正本位。

## 五、审计入口

1. `python ledger/cairn_ledger.py verify` ⇒ 台账链内自洽；
2. `python skills/ls-bus-format-ops/scripts/lsbus_format_ops.py validate bus/bus.jsonl` ⇒ 总线 VALID；
3. `python skills/cairn-otl-signing/scripts/sig_block.py --file <件>` ⇒ 署名复算。
