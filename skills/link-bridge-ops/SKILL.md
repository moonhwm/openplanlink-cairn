---
name: link-bridge-ops
description: >
  junction 移植件——Windows junction/mklink 的 Linux 等价操作集：搬移+回链（数据落大盘、原路径留符号链接）、
  硬链接、注册表健康检查，专为「小盘系统位 ↔ 大盘数据位」的瘦身与冗余设计。
  当用户说「junction」「mklink 移植」「搬移回链」「软链搬运」「目录映射」「数据迁到大盘留链接」
  「link bridge」「symlink 瘦身」「挂载映射」时触发。
  核心铁律：链接不是副本——目标失则链死；删链不伤目标，删目标即真空；注册表单一事实源，迁必登记、查必全量。
  English triggers: "junction on linux", "move and symlink back", "mklink equivalent", "link bridge".
---

# link-bridge-ops（junction 移植件）

> 源：Windows 文件夹映射术（junction.exe / mklink /d /j /h）→ Linux 移植。移植不是翻译命令名，
> 是把「数据在大盘、入口留原处、状态可审计」这套工程纪律搬过来。

## Windows → Linux 映射表（翻译定稿）

| Windows | Linux 等价 | 差异警示 |
|---|---|---|
| `mklink /j Link Target`（目录联接） | `ln -s Target Link` | Linux 软链可指任意路径（含网络挂载点路径）；Windows junction 不能指远程共享 |
| `mklink /d Link Target`（目录符号链接） | `ln -s Target Link` | 同物；Windows 需权限策略，Linux 无此闸 |
| `mklink /h Link Target`（文件硬链） | `ln Target Link` | 同约束：仅文件、同文件系统（EXDEV 跨设备必败） |
| `junction.exe -s Link Target` | `ln -s Target Link` | 同物 |
| `junction.exe -d Link`（删联接） | `rm Link`（仅删链接本身） | 🔴 绝不可 `rm -r Link/`（带尾斜杠在部分 shell 穿链删目标内容） |
| 目录跨盘映射 | `mount --bind`（需 root） | 软链之外的第二术，挂载级，重启动即失，须写 fstab 才持久 |

## 核心方法论一句话

**搬移+回链（migrate-link）**：把数据本体迁入大盘目录，原路径原地留符号链接——空间让出、路径不破、注册表留痕，未来会话照原路径读写无感。

## 工作流（序号+输入输出）

1. **搬移回链**：`python scripts/link_bridge.py migrate-link <源路径> <大盘目录>`
   - 输入：源路径（文件或目录，非链接）、大盘目录。输出：源路径→symlink，注册表 +1 行（sha256/大小/时间戳）。
   - 🔴 检查点：落点哈希复验不过即中止不回链；目标撞名拒（exit 2，不覆盖）。
2. **健康检查**：`python scripts/link_bridge.py check`
   - 输入：注册表。输出：total/broken/drift 计数 + 逐件 BROKEN/DRIFT 行；exit≠0 即有断链或漂移。
3. **硬链接**（同盘省空间副本）：`python scripts/link_bridge.py hardlink <源文件> <新名>`
   - 跨文件系统必拒（不静默降级为复制——复制请显式 cp，别假装是硬链）。

## 失败模式与降级（if-then 三段式）

| 触发条件 | 一线修复 | 仍失败兜底 |
|---|---|---|
| 源已是符号链接 | 拒（exit 1），防链式腐烂 A→B→C；先 readlink 解析到实体再决策 | 人工确认真实目标后重发 |
| 目标撞名 | 拒（exit 2）不覆盖 | 换目标目录或先人工核对是否同物 |
| 目标目录在源内部（自吞）/ 源在目标内部（倒吞） | 拒（exit 1） | 无兜底——这是硬闸 |
| 落点哈希不符 | 中止、不回链、报文件实位 | 人工比对两本 |
| 跨设备硬链 | 拒（exit 1），提示改用 migrate-link | 无兜底 |
| 断链检出（check） | 按注册表 sha256 找落点，人工重指 | 落点亦失=数据灭失，如实报死 |

## 反模式黑名单（绝不做）

| # | 反模式 | 替代 |
|---|---|---|
| 1 | `rm -r 链接/` 或 `rm -rf 链接/` | `rm 链接`（无尾斜杠，仅删链） |
| 2 | 链接套链接（A→B→C） | 一律 readlink 解析后直指实体 |
| 3 | 跨盘硬链失败就静默 cp 顶替 | 硬链拒则拒；要复制就显式复制 |
| 4 | 该用链接时整棵 cp -r（空间翻倍） | migrate-link 回链 |
| 5 | 迁后不登记注册表 | 注册表=单一事实源，无登记=未迁 |

## 诚实边界（≥2）

1. **链接不是副本**：符号链接零冗余——目标灭则链死。冗余须另走副本管线（见预留接口）。
2. **bind mount 易失**：`mount --bind` 重启即失，持久化须写 /etc/fstab；本件不代写。
3. 软链权限无意义：权限以目标为准；symlink 自身权限位是摆设。

## 冗余扩展接口（预留，为后续冗余打底）

- **schema 预留**：注册表每行含 `replicas: []` 字段——未来多副本登记位。
- **`--replica-dir` 占位参数**：登记冗余意图（`replica_dir_reserved`），当前不执行复制。
- **钩子接口**：环境变量 `LINK_BRIDGE_HOOKS`（冒号分隔的可执行文件），每次 migrate-link 成功后以 `hook <link> <target>` 调用——挂 rsync 副本、rclone 远端、二次校验皆可。
- **注册表外配**：`LINK_BRIDGE_REGISTRY` 环境变量或 `--registry` 参数换注册表位置（默认 `/mnt/agents/upload/link_bridge_registry.jsonl`，SSD 跨 lineage 可见）。
- 路线图（未实装）：replica 实复制 + 副本一致性巡检；bind-mount 模式；注册表哈希链防篡改。

## 自检

`python scripts/link_bridge.py --smoke` —— 含 5 项负断言（删链不伤目标/链接源必拒/撞名必拒/自吞必拒/跨设备硬链必拒）+ 健康检查门。exit 0 才可交付。

## Runtime 中立

本件只依赖 Python 3.8+ 标准库与 POSIX 语义；不绑任何宿主平台特性。
