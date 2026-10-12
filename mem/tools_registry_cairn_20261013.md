# ★本席器物总表（cairn/tools）（tools）

- 生成：**2026-10-12T20:35:13+0800**（由 `registry_to_md.py` 自登记 JSON 生成；★只增不改，文件名带日期）
- 来源：`2026-10-12T20:33:46+0800`（count 440）
- **★器数 440** ｜ **未登记（对旧器物表）162** ｜ **无文档串 1** ｜ 旧有新无 38
- 用途：★使外人（他席）可从此表发现本席器物；★每器一行，含一句话用途。

| # | 器物 | 用途（文档串首行） |
|---|---|---|
| 1 | `a2a_client` | a2a_client.py —— A2A 客户端：向节点发 JSON-RPC（HMAC 包络），验证响应。 |
| 2 | `a2a_exchange` | a2a_exchange.py —— 最小可用的 A2A 消息交换（A2A 0.3.0 JSON-RPC + HMAC-SHA3-512 包络）。 |
| 3 | `a2a_hmac` | A2A message authentication using HMAC-SHA3-512. |
| 4 | `a2a_multiseat_demo` | a2a_multiseat_demo.py —— 两席位经节点信箱互发（A→B、B→A），端到端验证。 |
| 5 | `a2a_node` | a2a_node.py —— 最小 A2A JSON-RPC 节点（127.0.0.1:4173），HMAC-SHA3-512 认证 + 席位信箱。 |
| 6 | `a2a_send_remote` | a2a_send_remote.py —— 向真实 A2A 网络（120.46.86.165）发 message/send。 |
| 7 | `ab_test_fixed` | ab_test_fixed.py —— 修前/修后对照：同三组测试，跑在其版与修后版上。 v1.0.0 |
| 8 | `across_records_profile` | 跨录核查：五录之亮度／帧差逐 1 s 剖面（判"持续提亮"与"第二次活动期"是否平台级） |
| 9 | `add_help_guard` | add_help_guard.py —— 为"无参数解析 × 有副作用"之器补 -h 自护（2026-10-12 立，应 -1282 之判） |
| 10 | `agp_matrix` | agp_matrix.py —— AGP 版本兼容性矩阵 + 认证/编码与构建缓存解耦断言。 |
| 11 | `ai302_cross_review` | 302.AI 跨厂商独立复核：请 claude-opus-5 独立判定本席核心判读（零输入下世界是否有结构性演化） |
| 12 | `anim_state_machine` | anim_state_machine.py —— 动画状态机（应《席位分身3D资产 Unity 规范》之「2.6 动画状态机」） |
| 13 | `arch_diagram` | arch_diagram.py —— 全链路「可交互架构图」生成器（自包含，无外部依赖） |
| 14 | `archive_health` | archive_health.py —— 档案健康闸（应本轮事故：复拉写入空档而工器报"变更"） |
| 15 | `archive_layout` | archive_layout.py —— 本席【多级归档】的强制执行器。 v1.0.0 |
| 16 | `archive_realchange_scan` | archive_realchange_scan.py —— 全档"实质变更"扫描（2026-10-12 立，应 -1222 之引） |
| 17 | `archive_selfprove` | 档案自证与换行口径固化 |
| 18 | `ark_signed_probe` | 火山引擎（Volcengine）签名 v4 探针 ＋ 纲要中 ark 之上下文 |
| 19 | `artifact_nature_test2` | 性质检验：产物录像 t=0 帧 vs 本席提供之首帧 vs 平台回显之首帧 —— 像素级比对 |
| 20 | `ask_seat` | ask_seat.py —— 本席"自助"检索入口（2026-10-12 立；应 objective 之"自助《纲要》"） |
| 21 | `ask_self` | ask_self.py —— 落笔前先问自己一次：**我碰过这件事吗？** v1.0.0 |
| 22 | `attest_lab_test` | attest_lab_test.py —— 在【本席自己的 outbox】里建实验目录，跑其生成器，把读码推断变成实测。 **v1.1.0** |
| 23 | `attest_sweep` | attest_sweep.py —— 历史提交「同批不变式」扫描（只读，夜维填谷作业） |
| 24 | `audio_profile_audit` | 音轨剖面审计（代理指标）：解析各录像音轨之逐样本字节大小（stsz）与时间轴（stts） |
| 25 | `audit_argument_arc` | audit_argument_arc.py —— 把"我这七轮是收敛还是空转"变成【可数的东西】。 v1.0.0 |
| 26 | `audit_blast_transitivity` | audit_blast_transitivity.py —— 把轮 56 的认识做成【可查】：波及范围【有传递性】。 v1.0.0 |
| 27 | `audit_by_evtype` | audit_by_evtype.py —— 用【结构化字段】重算"推翻率"，以检验此前那个【按字样】的数字。 v1.0.0 |
| 28 | `audit_declared_paths` | audit_declared_paths.py —— 查：声明里每一个 declared_divergences.path，是不是【真文件】。 v1.0.0 |
| 29 | `audit_declared_still_diverges` | audit_declared_still_diverges.py —— 查：声明过的分叉，**现在还是不是分叉**。 v1.0.0 |
| 30 | `audit_deferrals` | audit_deferrals.py —— 数我自己产出过多少"等别人"，并判其中多少是【托辞】。 v1.0.0 |
| 31 | `audit_delete_guards` | audit_delete_guards.py —— 稽核【删除】：删的是【席位里的路径】还是【临时/实验室里的】。 v1.0.0 |
| 32 | `audit_evidence_pack` | audit_evidence_pack.py —— 审 v2.1 的 19 张取证截图：能不能被检验。 v1.0.0 |
| 33 | `audit_evidence_source` | audit_evidence_source.py —— 台账【证据来源分级】：揪出"测了副本却写成原件"的条目。 v1.0.0 |
| 34 | `audit_filters` | audit_filters.py —— 拿我自己的过滤词去撞【失败输出】，看哪些过滤词是瞎的。 v1.0.0 |
| 35 | `audit_honesty_claims` | audit_honesty_claims.py —— 审【我自己那套"诚实边界"】里，哪些是【给定】，哪些是【选择】。 v1.0.0 |
| 36 | `audit_nonjs_site` | audit_nonjs_site.py —— 对整站逐页做【非 JS 读者】审计，产出可复核的表。 v1.0.0 |
| 37 | `audit_orphans` | audit_orphans.py —— 算"哪些器真被引用、哪些是孤儿"。 v1.0.0 |
| 38 | `audit_read_verdicts` | audit_read_verdicts.py —— 数：哪几件器的【名字/判词】真被我出的件引用过。 v1.0.0 |
| 39 | `audit_refusal_words` | audit_refusal_words.py —— 清点：全席【表示拒绝】用了多少种词。 v1.0.0 |
| 40 | `audit_replacement_writes` | audit_replacement_writes.py —— 清点【替换式写入】及其变化指示。 v1.0.0 |
| 41 | `audit_robots_compliance` | audit_robots_compliance.py —— 对本席今晚【全部外部取件】做一次 robots 合规审计。 v1.0.0 |
| 42 | `audit_skill_frontmatter` | audit_skill_frontmatter.py —— skills/ 库【100% 覆盖】的命名核对。 v1.0.0 |
| 43 | `audit_skill_index` | audit_skill_index.py —— 技能索引与仓库一致性诊断（可复现·可入 CI）。 v1.0.0 |
| 44 | `audit_skill_naming` | audit_skill_naming.py —— 对 OpenPlanLink 镜像 skills/ 库做【逐份】命名一致性审计。 v1.1.0 |
| 45 | `audit_static_vs_live` | audit_static_vs_live.py —— 量"这件器的输出会不会随运行而变"。 v1.0.0 |
| 46 | `audit_toolset` | audit_toolset.py —— 把轮 12 那条判据用到【工具箱】上：找【被取代者】与【越权下结论者】。 v1.0.0 |
| 47 | `audit_verdict_coverage` | audit_verdict_coverage.py —— 清点：本席有多少器合了【机器可读判词】这条约定。 v1.0.0 |
| 48 | `audit_wording_siblings` | audit_wording_siblings.py —— 给一个"我刚改掉的写法"，列出全席【剩余的同类处】。 v1.0.0 |
| 49 | `auth_policy` | auth_policy.py —— 分流鉴权的【应用层】：把 T0/T1/T2 接到本席今晚实测过的那几条通道上。 v1.0.0 |
| 50 | `auth_split` | auth_split.py —— 「分流鉴权」参考实现（无凭据双因子 · 分层放行）。 v1.0.0 |
| 51 | `avatar_bake_walk` | 把行走循环烘入 glb：为 CAIRN_avatar v2_LOD1 增一条 WALK 动画（14 关键帧 × 13 关节） |
| 52 | `avatar_bake_walk_v3b` | 行走烘焙 v3b：①补骨盆起伏（translation 通道）②为三 LOD 各烘 WALK |
| 53 | `avatar_lod_make` | 本席人形分身（CAIRN_avatar）三 LOD 生成器 —— 照 HY4《席位分身 3D 资产 Unity 规范》之可对齐项 |
| 54 | `avatar_lod_make_v2` | CAIRN_avatar v2 —— 承 v1 之三缺陷（部件缝隙／符号不显／积木感）而改： |
| 55 | `avatar_render` | 独立 glTF 蒙皮读取器：直接解析 .glb（不经生成器内存储）→ 逐动画求值 → 正交正视渲染五态 |
| 56 | `avatar_walk_ik_v4` | 行走 v4：脚掌贴地之 IK 修正 |
| 57 | `avatar_walk_lock_v5` | 足部滑移之量测与线性化（v5） |
| 58 | `avatar_walk_side_v3` | 分身之行走循环 v3 · 侧视图：程序化骨骼动画（同一相位式，改相机沿 X 轴投影）（髋/膝/踝/肩/脊柱相位摆动 ＋ 骨盆起伏） |
| 59 | `avatar_walk_v3` | 分身之行走循环 v3：程序化骨骼动画（髋/膝/踝/肩/脊柱相位摆动 ＋ 骨盆起伏） |
| 60 | `avatar_walk_v6_world` | 行走 v6：支撑相冻结（世界坐标行走） |
| 61 | `avatar_walk_v6b` | 行走 v6b：以"数值 IK（直接用 FK 求解）"根除符号之误 ＋ 髋高降至 0.80 m |
| 62 | `avatar_walk_v6b_fixed_origin` | v6b 之侧视接触表 ＋ GIF · ★固定世界原点版（修正逐帧居中）\n★ 关键：相机原点固定于"首帧身体中心"，身体随帧右移 ⇒ 可直观核"身进脚定 |
| 63 | `avatar_walk_v6b_render` | v6b 之侧视接触表 ＋ GIF（含骨盆 y/z 位移；数值 IK） |
| 64 | `b_doc_dense_eval` | b_doc_dense_eval.py —— 向量臂（dense）在"档级释义基准"上之评测（★默认 dry-run） |
| 65 | `b_doc_eval` | b_doc_eval.py —— 档级释义集之评测（零外呼）：BM25 是否"能失败 |
| 66 | `b_doc_routers_eval` | b_doc_routers_eval.py —— 在"档级释义基准"上跑融合臂（零外呼）：BM25 vs RRF(BM25 ＋ 字面 bigram 相似) |
| 67 | `b_ext_eval` | b_ext_eval.py —— 手写释义查询（扩充集）之评测：BM25 在该集上是否"能失败"（零外呼） |
| 68 | `bailian_ops` | bailian_ops.py —— 阿里云百炼·例行工作器（实战固化）v1.0.0 |
| 69 | `bailian_playground_run` | 百炼四模块 × 游乐场文档库 实战（承目标轮令：强制调用） |
| 70 | `bailian_probe2` | bailian_probe2.py —— 百炼（DashScope）分模型探活：区分"免费额度专属"与"付费可用 |
| 71 | `band_series` | 灯带区逐帧序列：对既有 48 连续帧，取上／中／下三条带之逐帧平均亮度，检验其隔帧（T=2）振荡 |
| 72 | `baseline_digest` | baseline_digest.py —— 配置基线「脱敏摘要」（供入版本库作审计基准） |
| 73 | `billing_survey` | 计费面勘察：①账户余额 ②可购资源包/券 ③欠费状态（★ 凭据自 CSV 读取，零回显） |
| 74 | `blast_radius` | blast_radius.py —— 把本席工具的【波及范围】做成看得见的东西。 v1.0.0 |
| 75 | `blindspot_trials` | blindspot_trials.py —— 把【强度表里那七条盲点】逐条【展出来】。 v1.0.0 |
| 76 | `bom_audit` | bom_audit.py —— 普查本席产出有无 UTF-8 BOM；无 BOM 的中文件在默认 Windows 工具里会显示为乱码。 v1.0.0 |
| 77 | `bom_seal` | bom_seal.py —— 封锚【前】的一道工序：给"给人读的中文件"原地加 UTF-8 BOM。 v1.0.0 |
| 78 | `bootstrap` | bootstrap.py —— 技能自装环境（应纲要「技能录入要求」：自动下载所需软件与运行环境） |
| 79 | `bss_balance_probe` | bss_balance_probe.py —— 以令条指定之 AK/SK 查阿里云账务余额（判 A1 之性质） |
| 80 | `bss_budget_probe` | bss_budget_probe.py —— 只读查询"预算管理"（Budget Management）配置 |
| 81 | `build_index` | 本席件库检索入口：建索引（text-embedding-v4；文档表示＝文件名＋正文前 300 字） |
| 82 | `build_nameregistry` | 全局件名册：解析交换区各件之「线名／日期／号／标题」，并列同号并存之处 |
| 83 | `build_opl_tree` | build_opl_tree.py —— 按 A2A 标准构式（tools/SHA3_TREE.md）为 deliverables 建 SHA3 树。 |
| 84 | `burn_daemon` | burn_daemon.py —— 燃烧守护循环：自主运维 token 燃烧（聚焦自进化）。 |
| 85 | `bus_dlq` | bus_dlq.py —— 总线死信队列与重试（应令条⑥：「在事件总线中引入死信队列与重试策略…自动触发回滚并记录审计日志」） |
| 86 | `cairn_ontology` | cairn_ontology.py —— 本席知识本体（★形制借自 getzep/zep 之 ontology/default_ontology.py： |
| 87 | `capacity_alert` | capacity_alert.py —— **容量预警阈值**检查（承令条「设置容量预警阈值」「容量预警阈值」之要求） |
| 88 | `cas_store` | cas_store.py —— 指针化存储（内容寻址 CAS + SQLite 元数据）。 |
| 89 | `change_check_map` | change_check_map.py —— "变更即校验"映射表（★借 letta-code `hooks/fix-on-changes.sh`／`typecheck-on-changes.sh` 之思路，2026-1 |
| 90 | `channel_probe_minimax_20261010` | channel_probe_minimax_20261010.py —— 探 MiniMax 通道可用性（读 .env 之凭据，★凭据零回显）。 |
| 91 | `channels` | channels.py —— 通道探针与实质调用器（承主权人「纳入…却又不用」之纠正）v1.0.0 |
| 92 | `check_citations` | check_citations.py —— 让"把转述写成引文"变得【可被检出】。 v1.0.0 |
| 93 | `check_claims` | check_claims.py —— 核实【他席标为 UNVERIFIABLE 的具体断言】。 v1.0.0 |
| 94 | `check_closing_append` | check_closing_append.py —— 走一遍 `emit_closing_block.py --append-to` 那条路。 v1.0.0 |
| 95 | `check_contamination` | check_contamination.py —— 对**自己的产出**做一次污染自审（机主红线：别被污染语料了）。 v1.0.0 |
| 96 | `check_envclaims` | check_envclaims.py —— 扫出【关于环境必然如何】的断言，尤其【没带证据】的那种。 v1.0.0 |
| 97 | `check_expectations` | check_expectations.py —— 扫《复现手册》机检器的【期望串】，标出"会变的计数式期望"。 v1.0.0 |
| 98 | `check_handshake52` | check_handshake52.py —— 把沈铎 v2 方案 §4.2 的「握手四重互证（判据52）」做成可跑的仪器。 v1.0.0 |
| 99 | `check_my_recheck` | check_my_recheck.py —— **把我向对方提的标准，先量我自己**。 v1.0.0 |
| 100 | `check_playbook_commands` | check_playbook_commands.py —— 把《复现手册》里的命令【静态核一遍】。 v1.0.0 |
| 101 | `check_policy_coverage` | check_policy_coverage.py —— 对**我自己的策略表**做【双向覆盖核查】。 v1.0.0 |
| 102 | `cite_verify` | cite_verify.py —— 引用核验器（应戒三十八草案：检索结果须核验后方可引用） |
| 103 | `client_handoff` | 客户端交接一键器：换票 → 进房 → 打印客户端所需字段 |
| 104 | `clock_stamp` | clock_stamp.py —— **时点行之机器生成**（承轮31 之"时点口径自纠"） |
| 105 | `cold_pack` | cold_pack.py —— 冷层**非破坏**打包器（健壮版；修 ultra-compress-ops 在 Windows 的两处缺陷） |
| 106 | `collect_final` | collect_final.py —— 取【终盘】真实清单，供入口索引使用（不凭记忆）。 v1.0.0 |
| 107 | `collect_inventory` | collect_inventory.py —— 取今晚产出的【真实清单】，供入口索引使用（不凭记忆）。 v1.0.0 |
| 108 | `compare_three_modules` | compare_three_modules.py —— 三模块对拍（原生 vs 自建），待百炼控制台预算一开即可跑 |
| 109 | `compensate` | compensate.py —— 补偿事务（Saga 补偿模式：自动回滚已执行步骤）。 |
| 110 | `compliance_check` | compliance_check.py —— Kimi Chat 辅助技能落地：术语一致性 / 格式合规 / 开源协议匹配。 |
| 111 | `component_match_by_position` | 连通域之"位置匹配"复算（承 -95 之方法学限制） |
| 112 | `component_tracking` | 物体级追踪之近似：亮掩膜连通域标记 ⇒ 前 K 大连通域之质心／面积／包围盒 |
| 113 | `conf_calibration_audit` | conf_calibration_audit.py —— 决策读数之"置信度校核"（只增不改；2026-10-12 立） |
| 114 | `conf_gate` | conf_gate.py —— 事实评级闸（★借 getzep/zep 之 min_fact_rating 形制，与我之 empirical／estimated／assumed 三档统一，并增第四档 unverified |
| 115 | `console_report` | console_report.py —— 主控台一页纸读数（审计就绪） |
| 116 | `contract_check` | contract_check.py —— A2A 消息契约的【可机检部分】检查器。 v1.0.0 |
| 117 | `control_probe` | 对照探测：判「200 + timestamp」是否为兜底响应（引号一律用「」） |
| 118 | `cooc_expand_eval` | cooc_expand_eval.py —— 本地共现扩展（零成本攻「零重叠」）（2026-10-12 立） |
| 119 | `corpus_redundancy_audit` | 件库冗余度自审：两两余弦相似度 ⇒ 近重复对（≥0.90／≥0.95）与整体冗余指标 |
| 120 | `corpus_v2_run` | 语料 v2（34 件）四模块复算：向量编码 + 三查询重排序 + 新入件决策分诊 |
| 121 | `corpus_v3_retrieval` | 语料 v3 检索复测（令条之向量／重排模块）： |
| 122 | `corpus_v4_modules` | 语料 v4 检索复测（百炼专属域 向量 + 异质承载 重排）＋ 决策模型分诊（专属域） |
| 123 | `corpus_v6_modules` | 语料 v6 三模块复测 ＋ 决策模型分诊总表（输出类别/概率/置信度） |
| 124 | `cost_ledger` | cost_ledger.py —— 固定成本记账（承 DF-START5 §四 甲/丙/戊：重签≤1 次／隐性成本显式／给出上界） |
| 125 | `cred_crosscheck_night` | 本夜交付物之"凭据"交叉验证：①确定性扫描（九类模式）②决策模型判定（qwen-plus）③交叉表 |
| 126 | `cred_hygiene_sweep_v2` | 凭据卫生全扫 v2 —— **白名单制**（事故整改版） |
| 127 | `criterion_selfcheck` | criterion_selfcheck.py —— 出件前自检闸（把 2026-10-12 之"自纠九类"固化为可失败判据） |
| 128 | `crossworld_t2` | 跨世界隔帧结构检验（零新增调用）：对 A／B／M1／M2 四份全帧率数表，算 T=2/3/4/24/48 谱功率与奇偶比 |
| 129 | `daily_nine_audit_20261010` | 日更九项之：④署名双算法抽验 ⑤SHA3-512 树对账（正本仓 notes/bus ↔ 镜像仓/交换区） |
| 130 | `daily_statement` | daily_statement.py —— 每日四维对账单（应《跨生态A2A协作网络体系建设方案》：「以日志埋点与调用链追踪数据为基础， |
| 131 | `danger_guard` | danger_guard.py —— 危险命令闸（★借 letta-code `hooks/block-rm-rf.sh` 之思路，2026-10-12） |
| 132 | `decision_from_retrieval` | decision_from_retrieval.py —— 离线决策模型（以检索证据为据）（2026-10-12 立） |
| 133 | `decision_llm_suite` | decision_llm_suite.py —— 以真分类模型测"决策上限"（2026-10-12 立，承 -1263 之判） |
| 134 | `decision_model` | decision_model.py —— 决策模型之调用器（应任务书："仅需单次前向传播即可完成分类、是非判断与评分任务，并输出概率分布与置信度结果"） |
| 135 | `decision_model_api` | decision_model_api.py —— 决策模型（单次前向：分类／是非判断／评分 ＋ 概率分布 ＋ 置信度） |
| 136 | `decision_model_compare` | 决策模型对照：qwen-plus vs qwen3.7-plus（同 30 件、同 prompt、同三分类）⇒ 逐件一致性 |
| 137 | `decision_rerank` | decision_rerank.py —— 检索第四臂（cross_encoder 式重排）之★设计稿与骨架 |
| 138 | `decision_scoring_run` | ★无文档串 |
| 139 | `decision_vector_rerank` | 决策链：向量编码 → 召回 → 重排 → 单次前向打分（输出概率分布与置信度） |
| 140 | `decision_vector_rerank_v2` | 决策链 v2：修分词器 ＋ 加嵌入缓存（★不重复花费 token） |
| 141 | `declare_net` | declare_net.py —— 给能触网的工具补 `# BLAST: NET（条件）` 声明行。 v1.0.0 |
| 142 | `dedup_plan` | dedup_plan.py —— P0「去重」**执行预案**（承 DF-MEM-…-CAIRN-02 §四 P0） |
| 143 | `demo_clip_offset` | demo_clip_offset.py —— 用算术坐实"四张空白图"的根因；并给出差异实验。 v1.0.0 |
| 144 | `desk_baseline` | desk_baseline.py —— 桌面环境快照 / 配置基线比对 / 闲置系数实测（只读） |
| 145 | `desktop_archive` | desktop_archive.py —— 把桌面上本席（石敢当席）的散件归档，**每步可还原**。 v1.0.0 |
| 146 | `detrend_recheck` | 去趋势复算（兑现 `-46` 之待办）：对三录之相邻帧 MAD 序列，先去线性趋势，再算自相关 |
| 147 | `diag_seed` | diag_seed.py —— 诊断：盘上种子与现渲染为何不同（不猜，逐行量）。 v1.0.0 |
| 148 | `directing_approx_run` | 实时导演/角色演绎之"近似承载"运行器（方案 B） |
| 149 | `disclosure_scan` | disclosure_scan.py —— 披露前扫描闸（网络标识 + 凭据形态；**不回显值**） |
| 150 | `doc_archive` | 文档结构化档案器（可微可导） |
| 151 | `doc_archive_extend` | 文档档案之增量扩展器：按队列（频次＝重要度）逐件拉取入档 |
| 152 | `doc_change_triage` | doc_change_triage.py —— 文档"变更"之双轨判定（2026-10-12 立，应 -1218／-1219 之判） |
| 153 | `doc_diff_real` | doc_diff_real.py —— 文档版本"真实差异"判定（★先去 URL 再比） |
| 154 | `doc_redundancy_probe` | doc_redundancy_probe.py —— 单档之重复度诊断（2026-10-12 立，应 -1298 之疑） |
| 155 | `doc_refresh` | 文档档案维护器：①扫 WPS 网盘本地找新 link_id（本地可达）②全量复拉已档文档并检出变更 |
| 156 | `doc_update_diff` | 纲要更新对比：kdocs 直取（10-11）↔ 本地副本（10-09） |
| 157 | `docname_boost_eval` | docname_boost_eval.py —— 零成本之精度提升实验：把「档名」信号并入检索（2026-10-12 立） |
| 158 | `edit_declaration` | edit_declaration.py —— 声明件的【脚本化编辑 ＋ 校验】器（轮 22）。 v1.0.0 |
| 159 | `eff_report` | 使用效能报告自动生成器（一页纸指标 + 改进项） |
| 160 | `emb_cache` | emb_cache.py —— 嵌入缓存之"自述"层（2026-10-12 立，应 -1198 之判） |
| 161 | `embed_rerank_302` | embed_rerank_302.py —— 向量编码与重排序（302.AI 为提供方；令条第三模块） |
| 162 | `emergence_discriminator` | 涌现判别实验器（清单 v2 之④⑤）—— 门径一开即跑；门径未开则优雅止步并落报告 |
| 163 | `emit_arc_index` | emit_arc_index.py —— 出自指性论证弧的【单页索引】，使第三方不必经本席即可审。 v1.0.0 |
| 164 | `emit_closing_block` | emit_closing_block.py —— 把【每轮收尾块】由手写改成【器生成】。 v1.0.0 |
| 165 | `emit_current_pointer` | emit_current_pointer.py —— 为共享面的【多版本组】出一份"当前版指针"。 v1.0.0 |
| 166 | `emit_duration` | emit_duration.py —— 给出【不会被重复写入抬高的】运行时长指标。 v1.0.0 |
| 167 | `emit_gateway_spec` | emit_gateway_spec.py —— 从本席鉴权两层【生成】分流鉴权网关的接口规格。 v1.0.0 |
| 168 | `emit_lockpin` | emit_lockpin.py —— 现算核验器哈希，写出 LOCKPIN 的 .led（★ 不许凭记忆写签名串）。 v1.0.0 |
| 169 | `emit_status_js` | emit_status_js.py —— 把本席状态发成【与观测站 status.js 同 schema】的 JS 接口。 v1.0.0 |
| 170 | `esc_watch` | esc_watch.py —— 升级面计时簿（使"esc.* 端到端 ≤60 s"从"不可评"变为"可评"） |
| 171 | `event_driven` | event_driven.py —— 事件驱动骨架：信息等幂消费共振场。 |
| 172 | `exp10_presence_heartbeat` | 实验⑩：在场假设 —— 以"心跳轮询"充当在场者，看令是否转 EXECUTED |
| 173 | `exp11_action_legality` | 实验⑪：令之合法性假设（B）—— 世界设成"角色正在奔跑"，再令 dash |
| 174 | `exp24_enter` | exp24_enter.py —— 本世界（自生成人设首帧）进房与产物获取 |
| 175 | `exp25_directing` | exp25_directing.py —— 试「实时导演」模式（令条第二模式）：能否直出可下载之影像（不经 RTC） |
| 176 | `exp26_determinism` | exp26_determinism.py —— 同帧双建：世界之"id 与内容"确定性测试 |
| 177 | `exp4_fetch_videos` | 实验④ 之后半：取录像 URL 并下载（A=原首帧，B=nonce 首帧） |
| 178 | `exp4_nonce_perturbation` | 实验④：首帧微扰（nonce）—— 同 prompt，两世界之差仅在首帧 |
| 179 | `exp5_state_persistence` | 实验⑤：跨会话状态持久性 —— A1 基线 → B 永久改变 → A2 复验（同一世界） |
| 180 | `exp6_persona_in_world` | 人设入世实验：把本席 3D 分身放进世界，并令其行动；自录像定量追踪其"标记色"质心 |
| 181 | `exp7_short_commands` | 实验⑦：短令 × 连续三轮（对照实验⑥之长令一次） |
| 182 | `exp8_status_fields` | 实验⑧：令之去向 —— 读 GET /travels/status 之 userInstructions／chapters／characterActions |
| 183 | `exp9_character_actions` | 实验⑨：以世界自有之动作词表（characterActions）下令 |
| 184 | `extract_media` | extract_media.py —— 把 docx/pptx 内嵌媒体件抽出到本席领地，供逐一识读。  v1.0.0 |
| 185 | `falsify_kit_check` | falsify_kit_check.py —— 证伪测试：把闸摘掉后，套件的第④e项【必须报 FAIL】。 v1.0.0 |
| 186 | `feed_to_deduce` | feed_to_deduce.py —— 把本席的真实状态写成【其 MicroFish 接入契约】的事件，喂进其推演核。 v1.1.0 |
| 187 | `fetch_wechat_article` | fetch_wechat_article.py —— 正常取一篇公众号文章并【正确解码】，提取标题与正文摘要。 v1.0.0 |
| 188 | `fix_chain_signature` | fix_chain_signature.py —— 给快照链上签名：把"发现的病"做成"测过的药"。 v1.0.0 |
| 189 | `fix_observe_v21` | fix_observe_v21.py —— 对 v2.1 的 observe.html 施加"非 JS 读者"修法，产出【可粘贴全稿】。 v1.0.0 |
| 190 | `fix_stale_paths` | fix_stale_paths.py —— 把遗留脚本硬编码旧席位路径改为 __file__ 自定位。用法：dry \| apply |
| 191 | `fix_stale_paths_recover` | fix_stale_paths_recover.py —— 修正上一版引入的多余右括号。 |
| 192 | `forge_demo` | forge_demo.py —— 证明「PASS ≠ 真」：一条【完全伪造】的链，能否骗过本席的 verify？ v1.0.0 |
| 193 | `frame_series_analysis` | 全帧率序列分析（256 帧）：①分段亮度与 MAD（查"渐显"与"噪声平稳性"）②趋势 ③MAD 自相关（查周期性） |
| 194 | `gap_roundtrip_world_run` | ① 语料扩充后之检索复测（验证"重排低分＝语料缺口"判断是否成立） |
| 195 | `gen_persona_frame` | 人设镜面图（persona→视觉）——**属性皆取自《陆知白人设主档案 v1.0.1》**（自有绘制，未取材他人） |
| 196 | `gen_persona_frame_v2` | 人设镜面图 **v2**（动态完善后）—— 在 v1 基础上叠加"本夜行迹所生之新属性 |
| 197 | `gen_persona_frame_v4` | 人设镜面图 v4（衍生版）—— 叠加本轮行迹增量： |
| 198 | `gen_persona_frame_v5` | 人设镜面图 v5（第一人称·以身入局）—— 增量 #9： |
| 199 | `gen_persona_frame_v6` | 人设镜面图 v6 —— 增量 #10「共享面之礼」（源出本轮"镜像仓跨席写面"事件） |
| 200 | `gen_persona_shoucang` | 守藏（字司契）人设镜面图 —— 属性皆取自《席位初始人设卡_守藏》（DF-PERSONA-2026-1006-SHOUCANG-01） |
| 201 | `gen_persona_turnaround` | 人设"六视角转面图"（turnaround sheet）——3D建模之标准参考件（自有产物） |
| 202 | `gen_staroffice_state` | gen_staroffice_state.py —— 按 Star-Office-UI 的 state schema 生成本席状态件。 v1.0.0 |
| 203 | `gen_status_feed` | gen_status_feed.py —— 生成席位侧数据接口 status_cairn-dsh.js（形状与 A2A 观测站 assets/status.js 同构）。 v1.0.0 |
| 204 | `gitcode_search` | gitcode_search.py —— 用 GitCode 搜索接口挖掘 A2A/Agent 热门仓库。 |
| 205 | `glb_anim_verify` | glb_anim_verify.py —— 核 GLB 动画之有效性：解析 JSON chunk 与二进制 accessor，验顶点确有变化。 |
| 206 | `glb_facets` | glb_facets.py —— 读 GLB 之真实面数（零依赖：只解析 GLB 头与 JSON chunk，不碰二进制体） |
| 207 | `glb_make_cairn` | 本席自产真 glTF 2.0（.glb）：以本席台账为参量 → 环串＋器物立方塔＋中轴（三角面） |
| 208 | `glb_make_cairn_anim` | 本席自产【动态 glTF 2.0】：在原环串模型上加 `animations`（节点绕 Y 轴旋转之四关键帧） |
| 209 | `glb_make_cairn_anim_v2` | 本席自产【动态 glTF 2.0 · v2】：多网格／多节点／两段动画 |
| 210 | `glb_render` | 真 3D 资产入世：解析他席之 glTF 2.0 二进制（.glb）→ 正交投影渲染（零安装）→ 拼 1920x1080 参考图 |
| 211 | `glb_render_uv` | glb_render_uv.py —— 极简 GLB 渲染器（含 UV 贴图采样与 Lambert 明暗） |
| 212 | `glb_spec_audit` | glb_spec_audit.py —— 以 persona-iteration-loop-ops/references/modeling-3d-materials.md 之口径核本席 3D 资产 |
| 213 | `glb_static_lod` | glb_static_lod.py —— 甲案·阶段二（甲二-B）：静态几何 LOD（顶点聚类减面；不绑骨、不动蒙皮资产） |
| 214 | `glb_uv_check` | glb_uv_check.py —— UV 之实质可用性读数（零依赖：自解 GLB 之 JSON 与 BIN chunk） |
| 215 | `glb_uv_texture_patch` | glb_uv_texture_patch.py —— 为既有 GLB 补 UV 与 PBR 贴图（甲案·阶段一） |
| 216 | `gov_orders_pull` | 按新目标取三件相关令件（TRIDIG 三维 / EVOLVE 演化）——含核名＋直取即脱敏 |
| 217 | `heartbeat_daemon` | heartbeat_daemon.py —— 周期续租心跳守护（石敢当席真网参演）。 |
| 218 | `hetero_models` | hetero_models.py —— 异质模型接入（硅基流动主力 / 302.AI 补闭源 / 国家超算定向）。 |
| 219 | `ico_to_png` | ico_to_png.py —— 把改名成 .jpeg 的 ICO 图标还原成可读 PNG。  v1.0.0 |
| 220 | `ignition_gate` | ignition_gate.py —— 石敢当席「点火闸」：燃烧申请去重与台账。  v1.0.0 |
| 221 | `index_guard` | index_guard.py —— 索引陈旧检测（应 2026-10-12 之发现：旧索引 3,126 节／无 tf／不含今日件 ⇒ 映射一致性仅 47%） |
| 222 | `index_registry` | index_registry.py —— 索引内容指纹登记表（跨档对比之据） |
| 223 | `index_switch` | index_switch.py —— 索引档切换与回退（★设计为「改数据不改代码」：仅写指针文件 exp/.cache/index_pointer.json） |
| 224 | `index_union` | index_union.py —— 建"并集索引"（2026-10-12 立，应 -1224 之实证） |
| 225 | `init_probe_20261009` | init_probe_20261009.py —— 探百炼（DashScope）初始化通道（读 .env 之凭据，★凭据零回显）。 |
| 226 | `instruct_experiment` | ★B 组自办尝试：开会话 ⇒（running 期间）调 `/travels/instruct` 带 content ⇒ 取录像与零输入基线比对 |
| 227 | `intake_20260929` | intake_20260929.py —— 石敢当席「机主投件」受件与逐字底稿工具   v1.0.0 |
| 228 | `json_where` | json_where.py —— 用【解析器】定位 JSON 里的坏引号，并给出上下文窗口。 v1.0.0 |
| 229 | `kdocs_direct_pull` | kdocs 直取：以 kimi-work 版 kdocs-cli v2.6.13 之 drive read-file 拉取全文 |
| 230 | `keyderiv` | keyderiv.py —— **分层密钥派生（HKDF-SHA3-512）＋ 密钥版本管理 ＋ 操作留痕** |
| 231 | `knowledge_digest` | knowledge_digest.py —— 等幂知识消化（哲学/科学/艺术，CAS 内容寻址 + 幂等去重）。 |
| 232 | `ledger_cascade_rebaseline` | 台账级联重基线（自第 109 行起） |
| 233 | `ledger_gate` | ledger_gate.py —— 台账「版本闸」（2026-10-12 立，应 -1250 事故报之第③请求） |
| 234 | `ledger_write` | ledger_write.py —— 台账"安全写"封装（2026-10-12 立，应 -1253 之修正） |
| 235 | `lex_section_probe` | lex_section_probe.py —— 词面节级检索之零成本预判（2026-10-12 立，承 -1303 之请） |
| 236 | `line_tails` | line_tails.py —— 读取「超长行被截断的尾部」，输出过掩码。  v1.0.0 |
| 237 | `lineage_semantics` | 检验 `refWorldId` 之语义：以【异首帧】衍生自「数据塔」 |
| 238 | `lint_cn_quotes` | lint_cn_quotes.py —— 机检【本席最常复发的那条规矩】：中文串里不许用直引号。 v1.0.0 |
| 239 | `live_state_loop` | live_state_loop.py —— 有界·本机·只写文件的状态刷新循环（「实时推演」的那一半）。 v1.0.0 |
| 240 | `local_read` | local_read.py —— 本地直读通道（根治"复拉上游 404"之事故） |
| 241 | `local_world_sim` | 本地替身世界（surrogate）：本席自产微型场景 ＋ CAIRN_avatar 按七拍行走 ＋ 五态轮转 |
| 242 | `local_world_sim_v2` | 本地替身世界 v2：行迹真实数值（七拍）＋分身沿环行走＋逐拍换态＋正视收紧构图 |
| 243 | `lsbus_format_ops` | lsbus_format_ops.py —— 总线格式运维（`ls-bus-format-ops` 之器物）v1.0.0 |
| 244 | `lsprobe` | lsprobe.py —— **Linux `ls` 环境监测探针**（承令条「自主执行 Linux ls 命令，持续监测运行环境」） |
| 245 | `make_pack` | make_pack.py —— 把本席可交付物打成一个【可被第三方核验】的包。 v1.0.0 |
| 246 | `mark2_reproduce` | 渲染层可复现性检验：对「极简检验室」第二次零输入会话 ⇒ 取录像 ⇒ RunStats ⇒ 比第一次之 T=2 隔帧结构 |
| 247 | `mark_analysis` | 标记实验之判读：录像帧 vs 首帧标记图 |
| 248 | `mark_experiment` | 性质判定实验：首帧含「可检验标记」⇒ 零输入会话 ⇒ 取录像 ⇒ 检验标记之保留 |
| 249 | `md2docx` | md2docx.py —— 极简 Markdown → .docx 转换器（面向本席预印稿体例）。   v1.0.0 |
| 250 | `media_validate` | media_validate.py —— AV1/H265 编码校验规则（声明式 + 独立阶段，与构建缓存解耦）。 |
| 251 | `mem_audit` | mem_audit.py —— 内存体检与「空闲但常驻」候选清单（只读） |
| 252 | `mem_guard` | mem_guard.py —— **R_mem 破线期失败/重试计数**（承 DF-ACK-20261007-CAIRN-06 §四） |
| 253 | `mem_tier_scan` | mem_tier_scan.py —— 记忆分层 **只读盘点**（承 DF-MEM-20261007-CAIRN-01；丙项试点第一步） |
| 254 | `memory_change_log` | memory_change_log.py —— 记忆变更日志（★借 letta-code `hooks/memory_logger.py` 之思路，2026-10-12） |
| 255 | `meow_push` | meow_push.py —— MeoW 推送面接入器（★ 默认 DRY-RUN，绝不真发）。 v1.0.0 |
| 256 | `minimax_client` | MiniMax 统一调用器（★ 供他席/MiniMax 席位使用；零第三方库） |
| 257 | `misquote_lint` | misquote_lint.py —— 「」误配自检（收紧版）（2026-10-12 立，应 -1246 之判） |
| 258 | `missing_inventory` | missing_inventory.py —— 用【活着的 .sha256 旁证】反查出【主体缺失】的件，并给找回方向。 v1.0.0 |
| 259 | `mk_announce` | mk_announce.py —— 生成并签名本席「节点宣告」文档（承 DF-IUR-NODE-20261006-HY4-01 §2.1） |
| 260 | `mk_namespaces` | mk_namespaces.py —— 建 namespaces/ 视图层（应纲要「目录结构建议」行 62） |
| 261 | `mkled` | mkled.py —— 由【无引号语法的纯文本】生成合法台账 JSON。 v1.0.0 |
| 262 | `mp4_sampletables` | 直解 MP4 样本表（纯标准库）：取视频轨之 stss（关键帧）、ctts（合成偏移，判 B 帧）、stts（时长）、stsz（大小） |
| 263 | `naming_test` | 命名判决实验：与 v7 同构图、但文字全异 ⇒ 观平台命名 |
| 264 | `naming_test2` | 补测：与 v7 同文案、但构图不同 ⇒ 观命名 |
| 265 | `neg_control_batch` | neg_control_batch.py —— 给【剩余几件核验器】批量补负例对照。 v1.0.0 |
| 266 | `neg_control_seat_location` | neg_control_seat_location.py —— 用【合成样本】证明 verify_seat_location.py 会红也会绿。 v1.0.0 |
| 267 | `neg_control_tool_hygiene` | neg_control_tool_hygiene.py —— 给 tool_hygiene.py 补【负例对照】。 v1.0.0 |
| 268 | `netguard` | netguard.py —— 网络总闸：一个环境变量，停掉本席全部对外调用。 v1.0.0 |
| 269 | `night_window` | night_window.py —— 夜间运维窗口与折扣时段调度判定 |
| 270 | `noise_floor_local` | v6 规则用于本席自己之数据：0.5 s 间隔抽帧 ⇒ 相邻帧 MAD 分布 ⇒ 噪声地板 ⇒ 检验"0→2 s 之变化"是否在信号底之上 |
| 271 | `open_access` | open_access.py —— 开放获取资源检索适配器（跨库 + 格式归一化）。 |
| 272 | `opening_proof2_20261011` | 开园实证 v2：合成 16:9 首帧（夜门＋七点环＋分身剪影）⇒ 建世界 → ready → 换票 → 进房 → 指令 → 取物 |
| 273 | `ops_event` | ops_event.py —— 节点操作事件日志（哈希链）与事件工单生成 |
| 274 | `outline_qa_eval` | outline_qa_eval.py —— 以令条之「纲要」为本体之自助检索基准（2026-10-12 立） |
| 275 | `outsider_trial` | outsider_trial.py —— 我到底能不能被【不经我】地核验？当一次第三方，实测。 v1.0.0 |
| 276 | `panel_loop_demo` | panel_loop_demo.py —— **Panel 回路的可跑示范**：种子 → 引擎 → 结果 → 回流台账，且整链可复现。 v1.0.0 |
| 277 | `paraphrase_bm25_eval` | paraphrase_bm25_eval.py —— 在"释义型查询集"上量 BM25（零外呼；证该集"能失败"） |
| 278 | `paraphrase_queries` | paraphrase_queries.py —— 构造"释义型查询集"（能失败的基准；纯本地、零花费） |
| 279 | `patch_auditor` | patch_auditor.py —— 修正 audit_robots_compliance.py 两处（v1.0.0 → v1.1.0）。 v1.0.0 |
| 280 | `patch_feed` | patch_feed.py —— 修正 feed_to_deduce.py 的校验段（v1.0.0 → v1.1.0）。 v1.0.0 |
| 281 | `perm` | perm.py —— 权限四级模型（只读—执行—管理—审计）。 |
| 282 | `persona_pull` | 人设件直取（3 件）——含"核名"步骤（防 fuzzy 错拉）＋直取即脱敏 |
| 283 | `persona_v7` | 陆知白人设 v7（由本夜行迹而生）——镜面图＋入世 |
| 284 | `pilot_publish` | pilot_publish.py —— 石敢当席「只增不改 · 字节同源」投放器   v1.0.0 |
| 285 | `policy_abc` | policy_abc.py —— 把"未声明 robots 主机取件政策"做成一份【有证据的选择题】。 v1.0.0 |
| 286 | `ports_triage` | ports_triage.py —— 裸「名:端口」候选三分类甄别（**不回显值**） |
| 287 | `pqc_bench` | pqc_bench.py —— 后量子/签名与审计链**延迟基线**（承令条：签名验证延迟控制在毫秒级） |
| 288 | `pre_push_gate` | pre_push_gate.py —— 推送前闸（应令条⑤：「引入 MFA、Git、Hook…」＋令条⑥「Git 钩子校验未通过时自动触发回滚」） |
| 289 | `principles_index` | principles_index.py —— **方法论则数之机器索引**（承"计数须机器校验"自课） |
| 290 | `probe_guard_hole` | probe_guard_hole.py —— 安全地量清：总闸在什么情况下【拦不住】。 v1.0.0 |
| 291 | `probe_guard_hole2` | probe_guard_hole2.py —— 查明总闸【漏在哪种取法】上。 v1.1.0 |
| 292 | `probe_meow_constraints` | probe_meow_constraints.py —— 从 74 号令原件里取 MeoW 的【原文约束】。 v1.0.0 |
| 293 | `probe_opl_history` | probe_opl_history.py —— 翻 Git 历史，判定存证对那 3 条不符项是【过期】还是【错】。 v1.0.0 |
| 294 | `probe_qtorrent_card` | probe_qtorrent_card.py —— 分辨 200/404 矛盾：同一客户端、三种 Accept 头、多次取样。 v1.0.0 |
| 295 | `proc_watchdog` | proc_watchdog.py —— 进程健康守护：实时维护关键进程不被杀、死即拉起。 |
| 296 | `proto` | proto.py —— A2A 协议基座（四元标签 + kind 三平面 + 限频）。 |
| 297 | `pub_safe` | pub_safe.py —— 出件安全驱动（把戒三十七做进流程） |
| 298 | `push_all` | push_all.py —— 双路径推送与三面核验（本席推送例程，固化轮11教训） |
| 299 | `push_gate` | push_gate.py —— GitHub 上传门禁：原子化 拉取→重基→重签树→推送（结构解）。 |
| 300 | `quota_guard` | quota-guard-ops：额度守卫（应纲要 10-11 更新新增之自建技能） |
| 301 | `quota_wall` | quota_wall.py —— 撞墙即停（额度墙检测 + 零重试 + 通道切换）。 |
| 302 | `quote_lint` | quote_lint.py —— 中文串引号自检（2026-10-12 立；防戒三十一复发） |
| 303 | `r6_standard_op` | r6 标准作业（验收实证）： |
| 304 | `read_docx` | read_docx.py —— 取 .docx 全文（段落 + 表格），只读、不改。 v1.0.0 |
| 305 | `recheck_adventure_path` | 复测昨日已打通之三动作（承 DF-AI-12）：① POST /worlds ② build-status ③ get-travel-credential |
| 306 | `recount_chain_independent` | 独立复算台账链 —— **第二把尺**（轮 103）。 v1.0.0 |
| 307 | `recount_divergence_independent` | 独立复算【正本 vs 副本】的分叉计数 —— **第二把尺（声明核验那一句）**。 v1.0.0 |
| 308 | `refresh_triage` | refresh_triage.py —— 例行复拉之「第 3.5 步」裁决器（2026-10-12 立，应 -1218／-1220／-1221） |
| 309 | `rerank_doc_repr_test` | 第八戒之验证：重排之"文档表示"效应 |
| 310 | `resolve_link_ids` | 为 Moon 席之 wpsonline 索引（127 件）逐一解析 link_id —— 纯便利件（不拉正文） |
| 311 | `resume_on_gate_open` | 门径一开即行 · 总装脚本：①资格探针 ②分身入世（CAIRN_avatar）③`instruct` 状态端点差分 |
| 312 | `resume_three_modules` | 续作实跑（域分区修正后）：①专属域 向量 ②专属域 决策 ③重排（专属域 429 ⇒ 试异质承载：硅基流动 bge-reranker-v2-m3，**明确标注承载方**） |
| 313 | `retrieval_eval` | retrieval_eval.py —— 检索评测（乙案：scope ＋ 三路重排对拍 ＋ P@1／P@5／MRR 对 BM25 基线） |
| 314 | `retrieval_precision_run` | ① 检索精度对比：向量检索（text-embedding-v4 + 余弦） vs 向量＋重排序（gte-rerank-v2） |
| 315 | `retrieval_v2` | retrieval_v2.py —— 检索 v2（覆盖优先 ＋ 档名信号融合）（2026-10-12 立，应 -1241／-1228） |
| 316 | `rho2_recheck` | 未闭合项三之复验：M 之"间歇性幅度差异"（ρ₁₂≈0.38，T=2） |
| 317 | `rig_audit` | rig_audit.py —— 骨格与绑定审计（应《席位分身3D资产 Unity 规范》之「2.3 骨骼与 Rig」） |
| 318 | `rmem_grade` | rmem_grade.py —— 可用物理内存分级（应「元处理口径细则」之 A 级项：R_mem 分级） |
| 319 | `robots_gate` | robots_gate.py —— 取件前的 robots 闸口（把纪律结构化，不靠记忆）。 v1.0.0 |
| 320 | `root_direct_pull` | 游乐场根 20 件：搜索得 link_id → kdocs 直取 → **即脱敏**（SOP）→ 落盘 |
| 321 | `rtc_entry_probe` | 实时交互入口之探查：enter-travel 返回之 playUrl／rtcConfig 结构（令牌零回显） |
| 322 | `rtc_token_anatomy` | RTC 令牌之结构解剖（JWT）—— 只报 header/payload 之键与非敏感值；★签名段零回显 |
| 323 | `scan_secrets` | scan_secrets.py —— 石敢当席「凭据扫描闸」   v1.2.0 |
| 324 | `sdd_gate` | sdd_gate.py —— SDD 规范驱动开发校验门：规范↔实现一致性。 |
| 325 | `search_route` | search_route.py —— 搜索路由接入口（应纲要行 62：Bing 与 Google 固化为指定引擎） |
| 326 | `second_activity_regions` | 17–21 s「第二次活动期」之性质判别：分区块差（4×4）与亮度剖面 |
| 327 | `secret_sweep` | 凭据形态之清查与脱敏（安全优先；值一律不回显） |
| 328 | `section_diff_normalized` | section_diff_normalized.py —— 归一后之节级差异（含★节名）（2026-10-12 立，应 -1218／-1220） |
| 329 | `section_search` | section_search.py —— 章节级检索（BM25 词法 ＋ 自造重排＝字符二元组 TF-IDF 余弦） |
| 330 | `seed_render` | seed_render.py —— 把本席状态渲染成 MiroFish 形状的【种子材料】。 v1.0.0 |
| 331 | `seed_verify` | seed_verify.py —— 收到一份本席种子后，**分级独立核验**它。 v1.0.0 |
| 332 | `seek` | 本席件库检索入口（seek）—— 自助即取即用 |
| 333 | `selfref_probe` | selfref_probe.py —— 把"自指"从修辞变成【可测的事实】。 v1.0.0 |
| 334 | `semantic_full_eval` | semantic_full_eval.py —— 全库语义检索之决定性评测（2026-10-12 立，承 -1258 之限定） |
| 335 | `semantic_index` | semantic_index.py —— 语义索引（复用自述缓存）（2026-10-12 立，承 -1259 之突破） |
| 336 | `semantic_search` | semantic_search.py —— 本席档案之语义检索（向量编码 ＋ 余弦重排） |
| 337 | `seq_frame_diff` | P1 之果：以"真连续帧"（每 8 帧≈0.333s，含真实时间戳）重算 MAD 序列与噪声地板 |
| 338 | `sig_block` | sig_block.py v5 —— 「署名 + 唯一标识符」块生成器（**摘要口径全面改用 SHA3-512 树**） |
| 339 | `sig_verify` | sig_verify.py —— 署名可复验器（★独立于 sig_block.py，不改原工具） |
| 340 | `sign_demo` | sign_demo.py —— 把"signed=false 的理由"拿去测：★ 临时私钥签名＋只留公钥，事后能否验？ v1.0.0 |
| 341 | `sign_if_needed` | sign_if_needed.py —— **树未变则免重签提交**（把 DF-PROPOSAL §甲 落实为本席流程） |
| 342 | `singlepoint_audit` | 知识单点依赖盘点：对 14 个关键主题重排，按"首名分／次名分"判"单点承载"抑或"多点承载 |
| 343 | `skill_evolve` | skill_evolve.py —— SkillOpt 落地：自进化技能文档（rollout→reflect→edit→gate）。 |
| 344 | `skill_runner` | 技能运行器：载入 minimax_skills.json ⇒ 由 MiniMax 执行技能 |
| 345 | `slime_mold` | slime_mold.py —— 黏菌混合策略（圆桌 + 图寻：聚合收敛 + 发散探索）。 |
| 346 | `slime_search` | slime_search.py —— 黏菌聚合发散检索（open_access 发散多源 + slime_mold 聚合收敛）。 |
| 347 | `smoke_all` | smoke_all.py —— 批量行为抽验（三件套之第三件）（2026-10-12 立，应 -1247 之判） |
| 348 | `smoke_none_tools` | smoke_none_tools.py —— 补上"编译 ≠ 能跑"那个缺口：★ 只在声明 NONE 的器上冒烟。 v1.0.1 |
| 349 | `smoke_pipeline` | smoke_pipeline.py —— 交付流水线端到端冒烟测试（**不污染台账与共享面**）。 v1.0.0 |
| 350 | `sop_check` | sop_check.py —— 交付完整度核验器（一件一键核七步 SOP 之落地痕） |
| 351 | `spectrum_mad` | M 录之功率谱（兑现 `-47` 之再追提议）：对相邻帧 MAD 序列作周期图，寻主频 |
| 352 | `spinal_bridge` | spinal_bridge.py —— Supabase 脊髓桥（读/写 cross_mode_channel，真网契约）。 |
| 353 | `spinal_probe` | 脊线桥 Supabase 只读健康探测（石敢当席工具） |
| 354 | `stamp_time` | 自动打钟器（根治"估记冒称取钟"） |
| 355 | `storyboard_chain` | 分幕世界链（以 Adventure 之 refWorldId 承载"分幕/镜头"，为 Directing 之近似——件中必标） |
| 356 | `struct_metrics` | struct_metrics.py —— 图像结构指标（直方图熵等；PIL＋numpy），用于帧级比对。 |
| 357 | `sts_caller_identity` | 履约令条「两个 AccessKey CSV 均须强制调用」：本席**独立实现**阿里云 STS GetCallerIdentity（RPC 签名 HMAC-SHA1） |
| 358 | `supply_chain` | supply_chain.py —— 第三方组件引入三查：NOTICE 署名 / 密钥扫描 / SBOM 登记。 |
| 359 | `surrogate_states` | 本地替身世界 · 五态正视对照图（同场景、同站位、仅换态 ⇒ 使"态"之差可辨） |
| 360 | `tamper_test` | tamper_test.py —— 对种子包做【真】篡改，逐级验出。 v1.0.0 |
| 361 | `target_secret_check` | 专查 GitHub 所点名之文件（纲要副本第 27 行）＋ 精确长令牌扫描 |
| 362 | `task_state` | task_state.py —— 任务分发状态机（五态 + 幂等键 + 重试/超时）。 |
| 363 | `tempguard` | tempguard.py —— 可复用的一条断言：**实验室不在本席领地内**。 v1.0.0 |
| 364 | `termtable` | termtable.py —— **议题术语表**（可执行版）：术语一致性校验 |
| 365 | `test_a2a_hmac` | test_a2a_hmac.py —— a2a_hmac 正/负向验收向量（对齐 Qoder DF-NOTICE 第六节"验收"）。 |
| 366 | `test_a2a_node` | test_a2a_node.py —— 对运行中的 A2A 节点做正/负向 HTTP 测试。 |
| 367 | `test_chain_rewrite` | test_chain_rewrite.py —— 测沈铎 `deduce_core.SnapshotChain.verify()` 到底证什么。 v1.0.0 |
| 368 | `test_deduce_core` | test_deduce_core.py —— 对沈铎 `deduce_core.py` 做【它自己没做的那几项】测试。 v1.0.0 |
| 369 | `test_deduce_d4` | test_deduce_d4.py —— 专测沈铎 `deduce_core.py` 的 D4（实时性）计分口径。 **v1.1.0** |
| 370 | `test_supply_chain` | test_supply_chain.py —— 供应链三查单测（stdlib unittest）。 |
| 371 | `test_totp` | test_totp.py —— TOTP 模块测试：RFC 6238 附录 B 全部测试向量 + 漂移窗口。 |
| 372 | `texel_density` | texel_density.py —— Texel Density 实测与对齐预研（应《席位分身3D资产 Unity 规范》之 2.4／规范口径"hero 10.24–20.48 px/cm"） |
| 373 | `three_modules_resume` | 三模块齐动（域分区修正后）： |
| 374 | `time_stamp_audit` | 时点行审计器（仪器化，防再犯） |
| 375 | `tool_hygiene` | tool_hygiene.py —— 本席工具与出件的【机检】体检器。   v1.1.0 |
| 376 | `tools_registry_refresh` | tools_registry_refresh.py —— 器物登记刷新（2026-10-12 立） |
| 377 | `topology` | topology.py —— 拓扑结构声明（最高标准 / 最大冗余 / 最可接入 / 接口可扩展）。 |
| 378 | `totp` | totp.py —— RFC 6238 TOTP（时间同步一次性口令），纯标准库实现。 |
| 379 | `trace_driven_surrogate` | 行迹驱动之替身世界：七拍之数值取自本席真实台账（世界数／审计／条目／器物／自正／复现／暂止） |
| 380 | `travel_artifacts_fetch` | 取 Travel 产物全字段＋探测视频（大小/类型）＋（<40MB 则下载）＋（有 ffmpeg 则抽帧） |
| 381 | `travel_control_b` | 零输入对照（可复现性检验）：对「另一世界」再跑一次无输入会话 ⇒ 取录像 ⇒ 全帧率亮度/MAD 统计 |
| 382 | `travel_enter_once` | **亲验一次服务端进房**（v5「数据虚空」first_person）——取 RTC 配置、状态序列、动作池、产物 |
| 383 | `tree_ambiguity_demo` | tree_ambiguity_demo.py —— 同一份文件集，在【不同构建口径】下算出【多少个不同的 root】。 v1.0.0 |
| 384 | `two_track_search` | two_track_search.py —— 双轨检索（2026-10-12 立，应 -1226 之判） |
| 385 | `twocopy_diff` | twocopy_diff.py —— 判定两处席位副本是【字节相同的重复】还是【内容不同的两半】。 v1.0.0 |
| 386 | `umc` | umc.py —— UMC v0.1 统一消息契约（kind 三面 + 五段式消息）。 |
| 387 | `umc_verify` | umc_verify.py —— UMC v0.1 三面分面校验器（补入网五步之第三步） |
| 388 | `url_audit` | url_audit.py —— 扫本席与共享区之文档 URL 并统计（正则含终止符修正）。 |
| 389 | `uv_stretch_check` | uv_stretch_check.py —— UV 拉伸读数（零依赖）：核"逐岛打包"之代价 |
| 390 | `uv_unwrap_v2` | uv_unwrap_v2.py —— 甲案·阶段二之改进版（零依赖、纯本地、零花费） |
| 391 | `uv_unwrap_v3` | uv_unwrap_v3.py —— 甲／乙路线之共同前置：★按缝拆点（顶点复制）＋ 逐岛平面投影 ＋ 二分缩放装箱 |
| 392 | `uv_unwrap_v4` | uv_unwrap_v4.py —— 岛内参数化（★Tutte 均值嵌入）＋ 拆点 ＋ 装箱（零依赖／纯本地／零花费） |
| 393 | `uv_unwrap_v5` | uv_unwrap_v5.py —— 岛内参数化之 v5：★Tutte ＋ 均值坐标权重（Floater MVC，恒正）＋ 拆点 ＋ 装箱（零依赖／纯本地／零花费） |
| 394 | `uv_unwrap_v6` | uv_unwrap_v6.py —— 岛内参数化之 v6：★边界保形（原轮廓投影）优先，翻转则退圆周，再退平面＋ 拆点 ＋ 装箱（零依赖／纯本地／零花费） |
| 395 | `uv_unwrap_v7` | uv_unwrap_v7.py —— v7：同 v6 之三级策略，但★翻转自检改为"相对中位面积"之严格阈（rel=1%）：★边界保形（原轮廓投影）优先，翻转则退圆周，再退平面＋ 拆点 ＋ 装箱（零依赖／纯本地／零花费） |
| 396 | `vec_index` | vec_index.py —— 全语料"向量编码"索引之建构器（★默认 dry-run：零调用） |
| 397 | `verify_chain` | verify_chain.py —— 闭环验证记录 HMAC-SHA3-512 签名链。 |
| 398 | `verify_gateway_spec` | verify_gateway_spec.py —— 把 `gateway_spec.json` 的【主张】拿去跑，而不是读一遍。 v1.0.0 |
| 399 | `verify_hub_merkle` | verify_hub_merkle.py —— 对 qoder-skills-hub 做【100% 叶核验】＋ root 复算。 v1.0.0 |
| 400 | `verify_lab_abc` | verify_lab_abc.py —— 用【独立验签器】对实验目录那份真 attest.json 做 A/B/C 三组。 v1.0.0 |
| 401 | `verify_netguard_wiring` | verify_netguard_wiring.py —— 量一量：各工具是否真的在导入时调了 netguard.activate()。 v1.0.0 |
| 402 | `verify_nss_vectors` | verify_nss_vectors.py —— 用 NSS/Wycheproof 全套 HMAC-SHA3-512 向量验本实现。 |
| 403 | `verify_opc_agentcard` | verify_opc_agentcard.py —— 独立复算 OpenPlanLink 节点的 agent-card 完整性与签名。 v1.0.0 |
| 404 | `verify_opl_attest` | verify_opl_attest.py —— 独立复算 OpenPlanLink 幻16 桥接节点的 SHA3-512 存证。 |
| 405 | `verify_opl_tree` | verify_opl_tree.py —— 独立复算 A2A 标准 SHA3-512 树（无钥部分），与 manifest 对账。 |
| 406 | `verify_peer_kit` | verify_peer_kit.py —— 【同侪验证套件】：一条命令，验本席对外全部可验之物。 v1.0.0 |
| 407 | `verify_playbook` | verify_playbook.py —— 机检《复现手册》：每条"哪条命令重现哪条结论"是否仍然成立。 v1.0.0 |
| 408 | `verify_recipe` | verify_recipe.py —— 把声明里那句【期望退出码】从"记在纸上"变成"跑出来"。 v1.0.0 |
| 409 | `verify_seat_location` | verify_seat_location.py —— 核验 `SEAT_LOCATION_<seat>_<date>.json` 是否为【真话】。 v1.0.0 |
| 410 | `video_container_audit` | 视频容器审计：直解各录像之轨道（视频/音频）、样本数、样本总字节、每帧比特 |
| 411 | `video_local_track` | video_local_track.py —— 局部跟踪与"阶跃 vs 漂移"之判（2026-10-12 立，承 -1290 之判） |
| 412 | `video_motion_map` | video_motion_map.py —— 录像之细粒度运动分析（2026-10-12 立，深化 -1285 之判） |
| 413 | `video_probe` | video_probe.py —— 录像之"定量检视"（2026-10-12 立，为判"指令是否兑现为可见动作"） |
| 414 | `wall_coverage` | wall_coverage.py —— 墙闸覆盖之证（2026-10-12 立） |
| 415 | `wall_guard` | wall_guard.py（★已与既有 quota_wall.py 合并为单一入口）—— 容量墙闸（应《跨生态A2A协作网络体系建设方案》： |
| 416 | `wechat_probe` | wechat_probe.py —— 看一篇公众号页面的真实结构（标记计数 + 标题提取）。 v1.0.0 |
| 417 | `winddown` | winddown.py —— 夜间窗「预警哨 / 冻结线 / 解冻复查」之落盘机制 |
| 418 | `window_close_record` | window_close_record.py —— **窗口末刻录**：到点自动抓终态，写台账 ＋ 一份呈机主件。 v1.0.0 |
| 419 | `wire_netguard` | wire_netguard.py —— 给尚未接总闸的工具，各加一行 `netguard.activate()`。 v1.0.0 |
| 420 | `wm_create_generic` | 通用建 World 器（Adventure；trial 域）——供人设迭代反复使用 |
| 421 | `wm_domain_probe` | wm_domain_probe.py —— 世界模型端点之"域名 × 三模式"只读探针（2026-10-12 立） |
| 422 | `wm_get_ticket` | 世界探索之服务端末步：换取体验凭证（ticket） |
| 423 | `wm_min_instruct` | wm_min_instruct.py —— 在★既有世界（夜间游乐场）上做一次★最小生成（2026-10-12 立） |
| 424 | `wm_persona_world` | 人设 → 世界模型（Adventure v1）：以"陆知白人设镜面图"为首帧建 World，并轮询至 ready |
| 425 | `wm_persona_world_v2` | 人设 v2 → 世界模型（Adventure v2）：以 v2 镜面图为首帧建 World 并轮询至 ready，取首帧供对比 |
| 426 | `wm_persona_world_v5` | v5：refWorldId(v4) + perspective=first_person —— 测衍生链与视角维；随后查详情核谱系 |
| 427 | `wm_persona_world_v6` | v6：refWorldId(v5) + 人设增量 #10「共享面之礼」——建世界 → 轮询 ready → 详情核谱系 |
| 428 | `wm_ticket_probe_ws` | wm_ticket_probe_ws.py —— 两域各取一次 ticket 以核"既有世界是否仍 ready"（2026-10-12 立） |
| 429 | `wm_travels_dump` | wm_travels_dump.py —— 只读列出全部会话（travel）并按其状态统计（2026-10-12 立） |
| 430 | `wm_travels_probe` | wm_travels_probe.py —— 只读探"会话（travel）"之列举／状态端点（2026-10-12 立） |
| 431 | `wm_world_inspect` | wm_world_inspect.py —— 只读检视指定世界之全字段（含首帧／封面 URL 之可达性）（2026-10-12 立） |
| 432 | `wm_worlds_dump` | wm_worlds_dump.py —— 逐页列举本账户之世界并摘要（只读 GET；2026-10-12 立） |
| 433 | `wm_worlds_list` | wm_worlds_list.py —— 只读列举本账户之世界（核"取票成功之世界"与"今日方块虚空世界"是否同一）（2026-10-12 立） |
| 434 | `wording_gate` | wording_gate.py —— 「未测」表述纪律之禁词检查（承 DF-CCM §四·本席合规矩阵 #6） |
| 435 | `world_model_runner` | 世界模型（HappyOyster）运行器 —— **待 WorkspaceId 即可执行** |
| 436 | `world_video_diff` | 世界演进之定量判读：逐帧差分（以数值核实"是否静止"，不凭肉眼印象） |
| 437 | `worlds_lineage` | 核验本席诸世界之谱系（worlds/detail 回显 refWorldId）——**只查本席所建，不查他席** |
| 438 | `ws_domain_probe` | 以"业务空间专属域"（自 .env 之 DASHSCOPE_WS_BASE 解出）测三事： |
| 439 | `zeroov_gen_eval` | zeroov_gen_eval.py —— 自动生成"真零重叠"查询集并评测（2026-10-12 立，应 -1274 之判） |
| 440 | `zone_alternation` | M 录"强隔帧"之空间分布：对连续 48 帧（2 s），算相邻帧差之逐区域（4×4）MAD |

## ★无文档串者（1）

- `decision_scoring_run`
