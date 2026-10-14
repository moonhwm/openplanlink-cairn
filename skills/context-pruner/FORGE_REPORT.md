# 《context-pruner 上下文瘦身官》首锻战报（女娲-仓颉-达尔文-女娲-达尔文 五节点管线，2026-09-16）

## 管线与开源本体
- 女娲 = alchaincyf/nuwa-skill ★32.7K（造 skill：框架提炼/反模式/诚实边界）
- 仓颉 = kangarooking/cangjie-skill（蒸馏成文：自包含 SKILL.md 规范）
- 达尔文 = alchaincyf/darwin-skill ★6.0K（9 维 rubric + paired 多数决棘轮 + HL 实战守则）

## 五节点纪事
1. **女娲①（创造）**：从本会话实战（Temp/wb 55 件 5.2MB 三档分拣）提炼方法论——「轻量化的目的不是删，是免读；落卡先行；白名单永护」。产物：目录 + scripts/context_audit.py v1.0.0。
2. **仓颉（成文）**：SKILL.md v1（三档表/六步流/失败模式三段式/反模式黑名单/自检）。
3. **达尔文①（压测）**：独立判官（explore 子代理）9 维 rubric 评分 **79.2/100**——文档 8.5 分、脚本 5 分；8 个实证 bug（瞬态 hints 转义失效 6 中 5、--card 覆盖、白名单子串误伤、smoke 假注释、日志落点矛盾、--scan 截断、触发词回链、Step4/5 无规格）。
4. **女娲②（再造）**：v1.1.0 修 8 缺陷 → paired 三判官（结构/实证/对抗用户三视角）**3-0 better/clear**；但合力再抓 8 条残余 → v1.2.0 修（死代码复活收窄、首段锚、help 同步、友好拒写、产物指针、复数兜底）→ 二轮 **3-0 better（clear×2/slight×1）**；再抓「锻造者宣称与文件不符（smoke 注释没改成）+ name-hint 子串误伤（evaluation_report.docx）」→ v1.2.1（注释真据实、hint 改 stem 全词/数字边界、断言补强）。
5. **达尔文②（复测终审）**：**3-0 better（clear×2/slight×1）→ keep**；残余收敛至 macOS smoke 注释一句假话——删句（v1.2.1 终版），HL-4 见好就收，不再开第四轮。

## 终版实测（确定性证据）
- `python -W error context_audit.py --smoke` PASS（零警告）
- 边界用例 12/12：Temp\a.tmp✓T、important.docx✓R、evaluation_report.docx✓R、navigation_notes.txt✓R、eval2/nav2/tree.json/dump✓T、shots/a.png✓T、tmp\dump.json✓T、outputs✓P、.gitignore✓R、myoutput✓R、VERDICT_*✓P、state.json✓P
- 棘轮史：SKILL.md.v1.bak / context_audit.py.v1.bak 留存（paired 比较基准）

## 判官金句（锻出纪律）
- 「SKILL.md 是 8.5 分的规范文档，脚本却是 5 分的实现——--smoke PASS 给了虚假安全感。」（达尔文①）
- 「三次修订，smoke 注释两次宣称修好、两次与代码不符——锻造者的自检报告本身需要一次 audit。」（判官B 终审）

## 已知边界（诚实声明）
- smoke 自检仅 Windows/posix-/tmp 可运行（macOS $TMPDIR 无 temp 段）；
- 白名单 CJK 后缀目录（如 output报告\）不保护（方向保守，不误删）；
- review 档永远默认不动，逐件需用户明示。


---

# 外池评审全案（2026-09-16，机主令「调用外池评审」）

## 初审（forge_review v1.0，三池：zhipu glm-4.7 / hw_maas GLM-5.2 / volcano DS-v4-flash）
- 主控重推导裁定：成立必修 8 项 / 证伪 3 项（A posix 白名单失效=B 判官推演错、B verify_edit.py 幽灵依赖=证据包不全、C 独立判官不可实现=不适用于本宿主）/ 有意权衡 2 项。
- 修复 → v1.4.0（硬闸代码化 --with-card+dry-run 默认+双保险；smoke 合成 tmp 子树全平台解耦；白名单扩充 evidence/archive/raw/证据/FORGE_REPORT；archive_large 原子化+拒覆盖+拒白名单；large_candidates；pipeline 触顶熔断 FAILED+9 维枚举+margin 定义+残余登记+证据包全件条款+无脚本技能变体）。

## 复审（forge_review v1.1，修复核验+证伪终判）
- 证伪终判：**A/B/C 三票全接受反证**。
- 8 项修复：glm-4.7 全成立 / GLM-5.2 全成立 / DS 7 成立（其「#2 不成立」经主控实测**系误判**：TRANSIENT_DIR_PAT 完好含 `[/\]tmp[/\]`，`/tmp/a.png`、`/var/folders/.../tmp/x/x.png` 实测 transient 命中，反证在案）。
- pipeline v2.2：**三票放行/带条件放行**。
- 新 bug hunt 主控核验：真 6 修 2 证伪——
  - 修：scan 不存在路径 KeyError（补 size:0）；check_card 不存在文件（schema 不过而非 traceback）；mark_archive docstring 语义对齐（protected 正是归档免读主体，允许；transient 拒）；main 层 mark_archive/archive_large 异常友好捕获；verify_edit.py 参数越界+目标不存在友好 FAIL；os.walk 显式 followlinks=False 加固。
  - 证伪：DS#1（posix /tmp 不识别——实测反例）；glm-4.7 符号链接遍历攻击（os.walk 默认 followlinks=False，攻击前提不成立）。
- 修复 → **v1.4.1 终版**：smoke 全过（-W error）+ CLI 负断言四连（不存在路径不崩/无卡 exit 3/白名单归档拒 exit 1/缺参友好 FAIL）。

## 判官金句（外池轮）
- DS：「两个技能都不能原样放行……它自己声称的硬闸在代码层不存在。」——初审最锋利一刀，v1.4 硬闸代码化即其产物。
- 5.2：「管线的首锻实证反而证明了管线的无效性。」——v1.4 全面加固的直接鞭策。
- glm-4.7：「--apply 默认行为改为 --dry-run，只有 --force 才允许真删」——v1.4 安全闸原案。
