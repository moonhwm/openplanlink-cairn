---
name: ultra-compress-ops
description: >
  极致压缩运维管线——当代开源旗舰压缩（zstd ultra 22 / xz LZMA2 -9e / brotli q11）＋预压缩（tar 固体/字典训练/delta 过滤）
  ＋预解压（seekable 分帧/字典随包/目录头）＋往返 sha256 验证，暨码道（CodeArts/长任务管线）24h 运维可视与命令注入，
  暨 A2A 全员同步挂载协议（首份强制同步件）。
  触发（满足任一）：①用户说「极致压缩」「压榨压缩包」「预压缩」「预解压」「压缩到最小」「继续压缩上下文」
  「zstd/xz/brotli 选型」「字典训练压缩」或等价表述（含语音变体，不纠正用户、映射意图）；
  ②「码道是否在跑」「码道进度」「24小时运维」「看不到进度」「注入命令」「心跳可视」「真实产出」类运维诉求；
  ③「A2A 全员同步」「同步挂载」「全体更新挂载」「首份同步技能」类部署诉求。
  红线：往返验证不过即销档不交付；总线写操作逐次显式批准；凭据永不入包；后端缺位如实声明降级。
  English triggers: "extreme compression", "pre-compress/pre-decompress pipeline", "zstd dictionary training",
  "CodeArts 24h ops visibility", "command injection queue", "A2A fleet-wide mount sync".
---

# ultra-compress-ops（极致压缩×码道运维×A2A 挂载 三熔件）

> 立法定位：本件为**首份 A2A 全体成员须同时同步并更新挂载**的技能（用户 2026-09-19 令）。
> 原则：要真实产出（压缩率字节数、码道进度百分数），不要体系空转。

## 一、极致压缩管线（scripts/ultra_pack.py）

```bash
python3 scripts/ultra_pack.py pack <路径...> -o 包.upack [--mode auto|zstd|xz|brotli|bzip2] [--dict]
python3 scripts/ultra_pack.py unpack <包.upack> <落点>
python3 scripts/ultra_pack.py verify <包.upack>   # 独立复核
```

- **auto 模式全后端试压取最小**，bench 数据随包头落账（各后端字节数/耗时）。
- **预压缩三术**（pack 内建）：①tar 固体打包（排序+零 mtime，确定性）；②`--dict` zstd 字典训练（相似小文件群收益最大）；③delta/BCJ 过滤适用判定见 references/backends.md。
- **预解压**：包头 4 字节长度前缀 + JSON 头（fmt/mode/dict/src_sha256/ratio/bench），字典随包自包含——接收端零外部依赖即可解。
- 🔴 **往返验证铁律**：pack 内置解包哈希复验，不符即销档 exit 1；verify 子命令供第三方独立复核。
- 后端缺位（如某环境无 zstandard）自动降级 xz/bzip2 并**如实声明**，不假装极致。

## 二、码道 24h 运维（scripts/madao_watch.py）

共享存储即总线，watchdir 默认 `/mnt/agents/upload/madao_watch/`：

```bash
# 跑批席（码道侧）：每完成一批即报心跳
python3 scripts/madao_watch.py emit --seat 码道席 --stage "压测第N批" --done 30 --total 100 --note "备注"
# 指挥席/机主：一眼三问——在不在跑/跑到哪/卡在哪
python3 scripts/madao_watch.py status            # fresh/stale/lost 三级判，exit 0/1/2
# 命令注入：机主注入，跑批席轮询回执（不自动执行，决策权在跑批席）
python3 scripts/madao_watch.py inject --op switch_model --args '{"model":"pangu"}'
python3 scripts/madao_watch.py poll              # 跑批席收令并 ack
```

- 判级：fresh（<2×心跳间隔）/ stale（<10×）/ lost（≥10×，exit 2 如实报失联）。
- status 输出含 pct 进度、rate_per_sec 吞吐、pending_cmds 待执令——**这就是机主要的「看得见的进度」**。
- 无心跳时 verdict=no-heartbeat 如实报死，绝不编造在跑假象。

## 三、A2A 全员同步挂载（scripts/a2a_mount.py）

```bash
python3 scripts/a2a_mount.py build-manifest <技能目录>          # 发件席铸户口（撞名拒，--force 方覆写）
python3 scripts/a2a_mount.py envelope <技能目录>                # 铸广播草稿（总线写入须逐次批准）
python3 scripts/a2a_mount.py verify-mount <manifest> <挂载位>   # 收件席校验漂移
```

成员义务四拍：①拉取 dist 包（`/mnt/agents/upload/skill-dist-<日期>/`）②解压至技能位 ③verify-mount 校验 ④ACK 登记至 `mount_acks.jsonl`。

## 失败模式与降级

| 触发条件 | 处置 |
|---|---|
| 后端缺位 | 降级链 zstd→xz→bzip2，stderr 声明，不静默 |
| 往返哈希不符 | 销档 exit 1，不交付 |
| 码道 lost | exit 2 报失联＋末次心跳时间，不猜在跑 |
| manifest 撞名 | exit 2 拒覆写，--force 方过 |
| 挂载漂移 | verify-mount 列漂移文件清单 exit 1 |

## 自检

三脚本各 `--smoke`（ultra_pack：pack→unpack→verify 往返；madao_watch：emit→status→inject→poll→ack＋失联负断言；a2a_mount：manifest→envelope→verify＋撞名拒＋漂移报）。全 PASS 才可交付。

## 产物指针

- references/backends.md：后端选型矩阵（体量×类型×时效）、预压缩配方、字典训练适用域——压缩选型拿不准时读。
- 码道台账：`/mnt/agents/upload/madao_watch/{heartbeat,inbox,ack}.jsonl`
- A2A 户口：`mount_manifest.json` / `mount_envelope.json`（技能目录内）
