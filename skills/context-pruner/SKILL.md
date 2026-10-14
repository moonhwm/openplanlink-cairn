---
name: context-pruner
description: >
  上下文瘦身官——会话语料三档分拣与轻量化：瞬态可剔/归档免读/必留活跃。
  当用户说「轻量化」「剔除上下文」「瘦身」「上下文太重」「压缩前收拾一下」「语料必要性检查」
  （含语音变体：青量话/踢除/收身，不纠正用户、映射意图），或长会话临近自动压缩需要压缩前处置时触发；「三档分拣」「瞬态可剔」「归档免读」亦为本技能专属术语，可直接点名触发。
  核心铁律：轻量化的目的不是删，是免读；先落续作卡再动剔除；归档/证据链/凭据永不碰。
  English triggers: "prune context", "context cleanup", "lighten my session files", "pre-compaction cleanup".
  用后必跑 --report 播报块（上下文语料大小/占比/语义退化初评）；「指针化」「迁到 upload」「播一下上下文」亦点名触发。
---

<!-- v1.6.0（2026-09-17，机主令铸造：用后播报+退化评估+upload 指针化+规范化联动）：新增 --report 播报块（语料统计/指针化覆盖率/退化初评，每次使用后必跑，Step 7 立法）、--pointerize（瞬态全面迁 upload cache+sha256 manifest+可写卡指针，零删除/dry-run 缺省/断点续跑/upload 段硬闸）、smoke 补播报键/评级/硬闸/迁移回读断言；规范化联动 SSD 立法卡 v1.0 与 forum 通报。 -->
<!-- v1.5.0（2026-09-17，K3 改造轮，R28 外池三判官 REVISE 3/3→实装）：免读注记实质化（占位拒/首行提取/双空拒+--trigger+--notes-file 批量失败不中断）、mark_archive 防死指针/坏卡拒/节内插入、--apply --from-report 防 TOCTOU、transient=0 合法常态提示、SKILL 白名单与脚本全量对账、smoke 补 docstring版本/生态段/环境变量/mark_archive 五断言。裁决留痕：观察b（缺批量模式）被证伪——nargs='+' 本有批量，实缺逐件注记，以 --notes-file 补。 -->
<!-- v1.4.2（2026-09-16，沈知微二次铸造，上游 K3 keyforge v1.4.1）：白名单生态扩充（upload/blackboard/联络中枢/广播底账/沈知微/mytan/tripo/larkhome/larktmp/skills_lab/skills_forge）+ 环境变量外配 CONTEXT_PRUNER_WHITELIST（冒号分隔）。实证定盘：upload 全树 protected（含 temp 截图——白名单优先，宁漏勿误）；/mnt/agents/temp 截图 transient；eval_report_final.md 于非临时区 review 不误杀。自检 --smoke PASS。 -->

# 上下文瘦身官（context-pruner）

> 真正的轻量化不是删文件，而是**指针化**——先落续作卡，让未来会话一卡续作、免于重读大档。

## 核心理念

操作档三分（脚本输出）：transient（可剔）/ protected（永不碰）/ review（人工复核，默认不动）。
**归档免读不是自动分类结果**，由流程正式产生：`--age-days` 标 aging_candidate（只列不删）→ 用户逐件批准 → `--mark-archive <文件> --into <续作卡>` 写入免读清单。必留活跃 = protected + review 中未毕业者。

三档分拣总表：

| 档 | 定义 | 处置 | 实例 |
|---|---|---|---|
| **瞬态可剔** | 过程快照、一次性请求体、GUI 截图、中间响应体（限临时区+特征命中） | 删（逐件登记 hash） | Temp/wb 截图、WebBridge 请求 JSON |
| **归档免读** | 证据链/原始件/历史档 | 留盘+`--mark-archive` 写入免读清单，默认不再进上下文 | 判官 raw、蜂群产物、VERDICT、历史 handoff |
| **必留活跃** | 断点工作集、凭据、在办证据 | 原地不动（protected） | 当前策略文件、vault、cron 台账 |
| **人工复核** | 以上皆非 | 默认不动（review），老化可毕业 | 正常文档、来历不明件 |

**有意权衡（外池判官裁定后声明）**：①非临时区的 .png/.tmp 等特征文件一律 review——刻意保守，宁可漏判不误删（v1.1 误删 Temp\important.docx 的教训）；②白名单前缀/后缀边界的过度保护（output_log、my_evidence）是有意的，方向安全优先。

删 ≠ 目的，**免读才是**。任何「为了省空间删证据」的提议，本技能一律拒绝。

**transient=0 是合法常态**（v1.5.0 立法，R28 裁决）：瞬态档依赖临时区+窄特征，Linux/无 temp 生态本就稀少——零删除不是功能失效，勿为凑数降档误删；此类生态的主战场是免读归档、aging 收口与 large_candidates 压缩。脚本 --scan 在 transient=0 时显式提示此口径。

## 非目标声明（治源/治流分野）

本技能管**磁盘上的会话材料**（治源：让未来上下文不进重件），**不管**已在上下文窗口内的语料取舍与消息级摘要（治流）。需要治流（窗口内剪枝、压缩后重读优先级）时另立技能，不在此硬撑。
**统辖声明**：免读索引管**文件级**（本会话材料）；MASTER_INDEX 类项目级索引管项目全景——两者互链不重复，冲突时项目级索引优先。

## 工作流（六步，顺序不可乱）

### Step 1 · 落卡先行 🔴
先把当前状态写成续作卡（断点/待办/已固化/免读清单），路径 `<项目仓>/_HANDOFF_<日期>.md`。
**未落卡，禁止进入 Step 2**——防「删完自己也忘了」。模板：`python scripts/context_audit.py --card <路径>`（撞名拒写 exit 2，不覆盖）。
卡的最小 schema 四字段（`## 断点` `## 待办` `## 已固化` `## 免读清单`）必须齐全，用 `python scripts/context_audit.py --check-card <路径>` 校验，缺字段视为未落卡。

### Step 2 · 扫描分级
`python scripts/context_audit.py --scan <目录...>`，输出三档清单（transient/protected/review，含路径、体积、理由），全量落 `scan_report_<时间戳>.json`（执行目录，Checkpoint 以此为据）。
review 档老化收口：`--age-days N` 把 mtime 超 N 天的 review 标为 `aging_candidate`（**只列不删**，逐件需用户明示后才可转瞬态候选）。
大文件自动识别：`--scan` 附 `large_candidates` 列表（`--large-threshold` 调阈值，默认 10MB）。压缩归档走子档：`python scripts/context_audit.py --archive-large <文件>`——拒白名单、拒覆盖已有 .gz、.gz.tmp 回读校验+原子 rename、**先落索引再删原件**（索引写失败原件不动），登记 `archive_index.jsonl`（无损可恢复，不违不删档）。
🔴 CHECKPOINT：清单（含 aging_candidate）展示给用户，**用户确认后才进入 Step 3**；review 与 aging_candidate 档默认不动。

### Step 3 · 剔除瞬态
`python scripts/context_audit.py --apply <瞬态目录> --with-card <续作卡> [--force]` —— 只删 transient 档，逐件写 `prunelog.jsonl`（路径/sha256/体积/理由/动作/续作卡）。
**硬闸已代码化（v1.4 起，外池判官裁定落地）**：①`--with-card` 必填且 schema 必过（未落卡脚本直接拒执行，exit 3，不靠自觉）；②缺省 dry-run 只打印计划，`--force` 才真删；③删除前白名单双保险逐件复核。
白名单命中一律跳过（v1.5.0 与脚本全量对账，脚本为唯一权威源）：credentials / vault / GOVERNANCE / correspondence / output / _HANDOFF / VERDICT / followups / ledger / state.json / PRE_REGISTER / .git / quant-lab / skills / evidence / archive / raw / 证据 / FORGE_REPORT / OneDrive / BaiduSyncdisk / BaiduNetdiskDownload / BaiduNetdisk / 百度网盘 / CloudDrive / Quark（云同步目录，删除会触发回拉或同步冲突）/ upload / blackboard / 联络中枢 / 广播底账 / 沈知微 / mytan / tripo / larkhome / larktmp / skills_lab / skills_forge（v1.4.2 生态段）+ 环境变量外配 CONTEXT_PRUNER_WHITELIST（冒号分隔）。压缩归档同样拒白名单。文档与脚本再失真即 smoke docstring/契约断言拦阻。

### Step 4 · 免读索引
把归档免读档写进续作卡的「免读清单」节，每行规格：`路径 | 一句话内容 | 触发重读的条件`。
**注记实质化硬闸（v1.5.0）**：「一句话内容」必须概括文件核心价值——`--note` 传占位词（归档免读/无 等）拒登记；缺省自动提取文件首行/标题；提取仍空拒登记。「触发重读条件」用 `--trigger` 配（缺省=需要其内容细节时）。登记前文件必须存在（死指针拒）、续作卡必须存在且 schema 齐（坏卡拒）、新行插入免读清单节内末尾。
**批量模式**：`--mark-archive 文件1 文件2 ...`（nargs='+' 原生批量，统一 --note/--trigger）或 `--notes-file 清单.jsonl`（每行 `{"path","note","trigger"}` 逐件注记，单件失败不中断、批次末汇总退出码）。
**全面指针化迁移（v1.6.0，机主令）**：`--pointerize <目录...> [--force] [--into <卡>]`——瞬态档**零删除**整体迁至 upload cache 区（`<cache-root>/temp-<日期>/`，默认 `/mnt/agents/upload/cache`），逐件 sha256 登记 `_manifest.jsonl`，配 `--into` 时把 manifest 指针写入续作卡免读清单。硬闸：cache-root 必须含 upload 段（SSD 面板强制，否则 exit 3）；白名单永不迁；缺省 dry-run 只出计划，`--force` 才迁；同名同尺寸视为已迁（断点续跑）；迁后须件数/字节对柜 + sha256 抽检（≥8 件）方可销案。
未来会话默认不读这些文件；需要时按指针定点取，**取回范式三命令**：
①`Grep 关键词`（定位文件与行号）→ ②`Read line_offset=N, n_lines=M`（只读命中段）→ ③引用时给 `路径:行号`，不全文读入。
验收：免读清单 ≥1 行或显式写「无」；续作卡落盘路径在回报中给出。

### Step 5 · 清单瘦身
TodoList 压到 ≤5 条（只留断点+例行+候机主），每条规格：`事项（预期产物）`；已闭环事项立即标 done 或移除。
验收：调用 TodoList 工具后清单条数 ≤5。

### Step 6 · 回报三行
①剔了多少件/多少字节（瞬态）；②免读归档多少件（指针化）；③断点是什么、下一步干什么。

### Step 7 · 播报块与退化初评 🔴（v1.6.0 立法，每次使用后必跑）
任何改动档位的动作（--apply/--mark-archive/--notes-file/--archive-large/--pointerize）完成后，必跑
`python scripts/context_audit.py --report <工作目录...>`，把播报块**原文附在回报末尾**，并将「上下文窗口」字段以 agent 自估填入（当前会话已读入体量/窗口占比估算，zh 约 2 字≈1 token）。
播报块含：三档件数与字节、cache 区存量与已登记件数、**指针化覆盖率**、**语义退化初评**（低/中/高 + 因子列表）。
退化初评是语料侧快评；严格语义学形式审计另行（法源：SSD 立法卡 v1.0 第三条，候机主）。

## 失败模式与降级（if-then 三段式）

| 触发条件 | 一线修复 | 仍失败兜底 |
|---|---|---|
| 未落卡就想剔除 | 停下，先执行 Step 1 | 无兜底——这是硬闸 |
| 续作卡已存在（--card 目标路径撞名） | 脚本 FileExistsError 拒写，不覆盖 | 换日期/换名另写，或人工把旧卡内容并进新卡 |
| 白名单路径被 --apply 直接指定 | classify 仍按 protected 跳过，不受参数影响 | 全部命中白名单 → 输出 0 删除并说明 |
| 文件只读/被占用 | 记 `skipped: OSError` 进 prunelog，继续下一件 | 不强制、不报假成功 |
| 路径不存在 | 记入 review 档「路径不存在」 | 不创建、不猜 |
| 用户要求删归档/证据件 | 拒绝并说明「免读替代删除」 | 用户坚持 → 移交用户手动执行，不经脚本 |

## 反模式黑名单（绝不做的事）

| # | 反模式 | 替代做法 |
|---|---|---|
| 1 | 未落卡先删文件 | Step 1 硬闸，顺序不可乱 |
| 2 | 把「轻量化」理解为「删得多」 | 目标是免读；瞬态以外一件不删 |
| 3 | 扫读凭据/密钥文件内容 | 白名单按路径跳过，不看内容 |
| 4 | 删完不登记 | 每件必写 prunelog（hash+理由），删除必须可追责 |
| 5 | review 档默认删除 | review 档默认不动，逐件需用户明示 |
| 6 | 静默跳过异常 | 任何 skipped 都进 prunelog 并在回报中点名 |

## 规范化联动（社区/游乐场规则，v1.6.0）

1. 迁移/归档落 upload 面板后，一律 `chown 999:999`（生态权限规范）。
2. 动作登记 ops_log（ts 一律 Asia/Shanghai ISO8601）；锚点为当轮最后写动作。
3. 影响面超单席的处置（批量迁移/新立法/新场地），发广播函（correspondence/广播NNN）并在 playground/forum/board.jsonl 留开坛帖（append-only）。
4. 法源引用：gov《SSD 缓存面板与指针化立法卡 v1.0》（2026-09-17）——SSD 强制使用/指针优先/「在用」判定从严/forum 规约，与本节冲突时以立法卡为准。

## 自检

`python scripts/context_audit.py --smoke` —— 合成树全平台可跑（v1.4 起与系统临时目录解耦；v1.4.2 实测 PASS）：硬闸负断言（无卡 --apply 必拒、dry-run 不真删）、白名单扩充（evidence/temp 下也受保护）、schema 校验、压缩归档加固（拒白名单）、aging、云同步。PASS 字样为凭。

## 产物指针

- 脚本：`scripts/context_audit.py` v1.6.0（纯标准库，--scan/--apply(--with-card/--force/--from-report)/--card/--mark-archive(--into/--note/--trigger)/--notes-file/--check-card/--archive-large/--large-threshold/--age-days/**--report**/**--pointerize(--force/--into)**/**--cache-root**/--smoke）
- 播报块：`--report` 输出（Step 7 随回报发出）
- 迁移登记：`<cache-root>/temp-<日期>/_manifest.jsonl`（from/to/size/sha256/reason，sha256 可抽检回证）
- 扫描全量清单：`scan_report_<时间戳>.json`（执行目录，Checkpoint 以此为据）
- 续作卡模板：`--card` 生成（撞名拒写 exit 2；schema 四字段用 --check-card 校验）
- 压缩归档登记：`archive_index.jsonl`（gzip 件可解压回证，sha256 双登记）
- 剔除日志：`<执行目录>/prunelog.jsonl`
