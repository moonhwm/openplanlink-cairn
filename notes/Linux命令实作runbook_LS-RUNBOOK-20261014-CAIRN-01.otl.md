# Linux 常用命令实作 runbook（`ls` 族）（LS-RUNBOOK-20261014-CAIRN-01）

- 档号：**LS-RUNBOOK-20261014-CAIRN-01**｜采集：**2026-10-14 05:4x**（真实钟）｜席位：**A2A新席_石敢当Cairn**
- 依据：令条「**系统掌握Linux常用命令（如ls）及其主要参数（如-l、-a、-lh）**，结合**文件权限识别、隐藏文件排查及可读格式输出**等应用场景，支撑**语义退化防范、目录查询和运维排障**」
- **★体例**：**「命令 → 真实输出 → 读法 → 用途」四栏**；**★全部输出为本机实测**（**`A:\Git\usr\bin\ls.exe`，Git for Windows**）
- **★可核命令**：**`A:\Git\usr\bin\ls.exe -l <目录>`**（**本机 Git 自带 POSIX `ls`**）

## 一、★★★★★ `ls -l`（**长格式：权限识别**）

**命令**：`ls -l "<席位>/assets"`

**真实输出（节选）**：
```
total 1320
-rw-r--r-- 1 欧阳宏俊 197609  124420 Oct  9 08:50 CAIRN_avatar_3lod_4phases_20261009.png
-rw-r--r-- 1 欧阳宏俊 197609   31300 Oct  9 08:48 CAIRN_avatar_LOD0.glb
-rw-r--r-- 1 欧阳宏俊 197609   35896 Oct 11 19:00 CAIRN_avatar_LOD0_actions_20261011.glb
drwxr-xr-x 1 欧阳宏俊 197609       0 Oct  3 16:06 __pycache__
-rwxr-xr-x 1 欧阳宏俊 197609   15000 Oct  3 16:17 cairn_ledger.py
```

**★ 读法（权限串十位）**：
| 位 | 含义 | 本例 |
|---|---|---|
| **1** | **类型：`-` 普通文件／`d` 目录／`l` 符号链接** | **`-` 与 `d`** |
| **2–4** | **属主权限（`r`／`w`／`x`）** | **`rw-`** |
| **5–7** | **属组权限** | **`r--`** |
| **8–10** | **其他用户权限** | **`r--`** |
| **★注** | **组列在本机显示为数字 GID `197609`**（**Git-for-Windows 无组名映射**）⇒ **★不可误读为用户名** | — |
| **★注** | **`total` 为块数（`-lh` 时为人读单位）** | **`total 1320`** |

**★ 用途**：**①权限识别（`rwx` 判可执行／可写）②运维排障（某脚本无 `x` ⇒ 不可执行）**。

## 二、★★★★★ `ls -a`（**隐藏文件排查**）

**命令**：`ls -a "<席位>/exp"`

**真实输出（节选）**：
```
.
..
.cache
CAIRN_avatar_3lod_4phases_20261009.png
CAIRN_avatar_LOD0.glb
```

**★ 读法**：**`.`（当前目录）与 `..`（上级目录）恒列出**；**其余以 `.` 开头者即隐藏项**（**本例为 `.cache`**）。
**★ 用途**：**①隐藏项排查（配置／缓存／密钥文件常隐藏）②配合 `-l` 成 `-la` 以看隐藏项之权限**。

## 三、★★★★★ `ls -lh`（**可读格式输出**）

**命令**：`ls -lh "<席位>/ledger"`

**真实输出（节选）**：
```
total 3.1M
-rw-r--r-- 1 欧阳宏俊 197609  199 Oct 14 05:36 _version_snapshot.json
-rw-r--r-- 1 欧阳宏俊 197609   18K Oct 12 19:27 bus_audit.jsonl
-rw-r--r-- 1 欧阳宏俊 197609  1.1K Oct 12 16:10 bus_dlq.jsonl
-rwxr-xr-x 1 欧阳宏俊 197609   15K Oct  3 16:17 cairn_ledger.py
-rw-r--r-- 1 欧阳宏俊 197609  114K Oct 12 14:22 conf_backfill.jsonl
```

**★ 读法**：**`K`／`M`／`G` 为 1024 进制人读单位**（**`18K`＝约 1.8 万字节**）。
**★ 用途**：**①快速辨"大件"（如 `114K` 之 `conf_backfill.jsonl`）②与"大件闸（>5 MB）"联用**。

## 四、★★★★★ `ls -la`（**组合**）

**命令**：`ls -la "<席位>/ops"`
```
total 28
drwxr-xr-x 1 欧阳宏俊 197609      0 Oct 12 12:32 .
drwxr-xr-x 1 欧阳宏俊 197609      0 Oct 14 02:05 ..
-rw-r--r-- 1 欧阳宏俊 197609   2038 Oct  8 08:35 key_ops.jsonl
-rw-r--r-- 1 欧阳宏俊 197609   3637 Oct  8 08:35 key_registry.json
-rw-r--r-- 1 欧阳宏俊 197609 115459 Oct 12 12:32 ops_event.jsonl
-rw-r--r-- 1 欧阳宏俊 197609 17886 Oct 14 03:15 运行口径_20261012.md
```
**★ 注**：**`运行口径_20261012.md` 17,886 B（`10-14 03:15`）＝ 径 `kj46` 补第 13 条后之**69 条版**（**与其副本一致，无漂移**）** ✓

## 五、★★★★★ 目录统计（**运维排障之量化法**）

**命令**：`ls -l <目录> | 按首字符归类`
**真实读数**：**条目 **3,277**｜`-`（文件）**3,263**｜`d`（目录）**14****
**命令**：`ls -a <席位> | 计 `.`开头者`
**真实读数**：**顶层 **26** 项｜★隐藏 **0** 项**

## 六、★★★★★ 与令条之对应（**"语义退化防范"**）

| 令条要求 | **本 runbook 之落点** |
|---|---|
| **文件权限识别** | **§一（十位权限串读法；数字 GID 之辨）** |
| **隐藏文件排查** | **§二（`.cache` 之实见；`.`／`..` 之恒在）** |
| **可读格式输出** | **§三（`-lh` 之 K／M／G）** |
| **语义退化防范** | **★"同名不同物"之辨：以 `ls -l` 之**大小＋时间＋权限**三量并观，不作单量判断（**与口径"世界标识须三者合取"同族**）** |
| **目录查询与运维排障** | **§五（按首字符归类统计；隐藏项计数）** |
| **跨平台之辨** | **★本机 `ls` 为 Git-for-Windows 之 POSIX 版（`A:\Git\usr\bin\ls.exe`）；★PowerShell 之 `Get-ChildItem` 与之参数不同，勿混** |

<!-- OTL-META
otl_meta:
  spec: OTL-SPEC-20261014-CAIRN-01
  form: full-text            # 乙形态（全文）
  source_path: Linux命令实作runbook_LS-RUNBOOK-20261014-CAIRN-01.md
  revision: 2
  prev_sha256: 55f91d7caed3060cdbf2c0407a929a80e52a7d9d43ec23856eec8b7cc8dc8fc7
  body_sha256: 55f91d7caed3060cdbf2c0407a929a80e52a7d9d43ec23856eec8b7cc8dc8fc7
  attachments: []
  seat_tree: outbox/otl
  acl: {seat: write-own, 常务局: read, 辩护席位: read, 他席: read-via-bus}
  archive_ref: archive/docs/<key>/v_<YYYYMMDD_HHMM>.md
  converted_at: 2026-10-14T05:48:02+0800
  by: cairn-dsh
-->
