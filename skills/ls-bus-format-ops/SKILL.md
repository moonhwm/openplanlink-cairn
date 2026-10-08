---
name: ls-bus-format-ops
description: >
  总线格式运维——为 A2A 网络之"总线"（各席共享之件目录）建立**统一条目格式**并作**机械校验**：
  一行一 JSON 之 canonical entry（seq/id/ts/seat/kind/path/bytes/sha256/refs），id 取 sha256 前 16 位（同内容同 id ⇒ 天然去重键），
  seq 严格递增无跳号（与事件链同法）；并提供 校验（validate：必填／十六进制／id 规则／seq 连续性／kind 合法）、
  规范化（norm：去重＋重排；默认只报不改）、漂移扫描（scan：有账无件／有件无账）与自检（--smoke）。
  解决三类总线病：①同件异记（各席记法不同，无法对账）②重复入总（同内容多条目，信噪比下降）③有件无账/有账无件（盘与索引漂移，审计断链）。
  触发（满足任一）：用户说「总线格式」「总线条目」「入总」「bus.jsonl」「总线对账」「有件无账」「有账无件」「总线漂移」
  「总线信噪比」「ls-bus-format-ops」或等价表述。
  红线：不删任何内容件（只动索引）；空范围即「未测」exit 2（不以空为通过）；写操作须显式指定；零凭据零 MAC 零 IP。
  三账分立：本器之 bus.jsonl 为「件之账」；ledger/frontier_ledger.jsonl 为「决策台账」；ops/ops_event.jsonl 为「事件链」——勿混。
---

# ls-bus-format-ops（总线格式运维）

> 立法定位：本件为**「全权授权…全面自我革命与初始化」下之首版**（2026-10-08）。此前该技能**四方核验皆缺**（GitHub 正本无、本席无、他席无引用、无下载源）⇒ 今由本席**初始化并落 GitHub 唯一正本**。

## 一、为什么需要它（三类总线病）

| 病 | 形态 | 后果 |
|---|---|---|
| **同件异记** | 同一件在不同席记为不同路径/名/无摘要 | **无法跨席对账** |
| **重复入总** | 同内容多条目 | **总线信噪比下降**（令条关切项） |
| **有件无账 / 有账无件** | 盘与索引漂移 | **审计追溯断链** |

## 二、条目格式（canonical bus entry）

```json
{"seq": 1, "id": "<sha256 前 16 位>", "ts": "2026-10-08 13:14:02 +0800",
 "seat": "a2a-node-local", "kind": "artifact|pack|note|skill|other",
 "path": "<相对总线根>", "bytes": 1196, "sha256": "<64hex>", "refs": []}
```

- **必填**：`seq / id / ts / seat / kind / path / bytes / sha256`；
- **id 规则**：`sha256` 前 16 位 ⇒ **同内容同 id**（幂等入总之据）；
- **seq 规则**：自 1 起**严格递增且无跳号**（与事件链同法）；
- **refs**：可选引用（如关联件号）。

## 三、用法

```bash
python scripts/lsbus_format_ops.py emit     --bus <总线根> --path <件> [--kind artifact|pack|note|skill] [--seat <席>] [--refs a,b]
python scripts/lsbus_format_ops.py validate <bus.jsonl>            # 0 通过／1 有缺陷（逐行报）／2 未测（空）
python scripts/lsbus_format_ops.py norm     <bus.jsonl> [--apply]  # 去重＋重排；默认只报不改
python scripts/lsbus_format_ops.py scan     --bus <总线根>         # 漂移：有账无件／有件无账
python scripts/lsbus_format_ops.py --smoke                         # 自检全链
```

## 四、退出码语义（★与 Cairn 术语闸同法）

| 码 | 义 |
|---|---|
| **0** | 通过（validate：0 缺陷；scan：无"有账无件"） |
| **1** | **有缺陷**（validate 报 INVALID；scan 报有账无件 ⇒ 索引指向不存在之件） |
| **2** | **未测**（总线为空／根不存在 ⇒ **不以"空"冒充"通过"**） |

## 五、自检（`--smoke` 五项，全过方可交付）

1. `emit` 两件 ⇒ 0；**重复 emit 同件 ⇒ 幂等跳过**（条数不变）；
2. `validate` ⇒ 0；
3. **负断言**：人为改 `seq` 造跳号 ⇒ `validate` 必报 **1**（★能报错才算检出）；
4. `norm` ⇒ 0；
5. **负断言**：空总线 ⇒ `validate` 必报 **2**（未测）。

## 六、首版实测（本席件）

- **`--smoke` PASS**；
- **总线实建**：`A2A共同体_共享交换区/bus/` ⇒ 3 条目（`cairn-context-20261008.manifest.json` id `876cfdc13f27644f`／`cairn-context-20261008.upack` id `b1570c7d35cec4f5`／`RETIRED_REGISTER.md` id `785f9e28beebc64b`）；
- **`validate` VERDICT=VALID（0 缺陷）**；**`scan`：有账无件 0 ／有件无账 0（零漂移）**。

## 七、自限与未决（照实登记）

| # | 项 |
|---|---|
| 1 | **本器只管"格式与账实一致"**，**不判内容对错、不判他席记法优劣**； |
| 2 | **`norm --apply` 会重排 seq** ⇒ 与他席既有条目混用时**须先协商**（本席默认只报不改）； |
| 3 | **尚未接入**：签名（每条目可加 `sig` 字段）／哈希链（seq 与前条 hash 相连）⇒ **候裁后增**（承则二十二：先证必要）； |
| 4 | **他席总线格式未知** ⇒ **首版仅为本席与共享总线之口径**，**不主张为全网标准**。 |
