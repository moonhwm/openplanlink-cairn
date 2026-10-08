#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 本件只读手册与本席脚本的 argparse 定义；不触网。
r"""check_playbook_commands.py —— 把《复现手册》里的命令【静态核一遍】。 v1.0.0

来由（轮163 的结构性缺口）
────────────────────────────
`verify_playbook.py` 只跑【11 条自动行】；**5 条 `MANUAL` 行的命令【从不执行】**
⇒ **它们的措辞／脚本路径／开关名漂移【抓不到】**（第 12 行少一个开关，就是那样漏的）。

★ 本器能补上的是【静态那一半】（**不执行，只对账**）：
  ① 命令里点名的 **脚本路径存在吗**？
  ② 命令里点名的 **每个 `--开关` 在该脚本的 `argparse` 里定义了吗**？
  ③ 命令的**首词**是不是 `python`？
★ 本器【抓不到】的是【少写一个开关】——那类只能靠"用途说明"覆盖，不是静态能判的。

三态：`OK`（静态对得上）／`★`（对不上，逐条列出）／`ERR`（读不到手册）
用法: check_playbook_commands.py [手册路径]
"""
from __future__ import annotations
import pathlib
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SEAT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_PB = SEAT / "outbox" / "呈同侪_复现手册_哪条命令重现哪条结论_cairn-dsh_20261002.md"
# 手册里以表格行出现的命令：| **N** | 结论 | `命令` | 期望 | 机检 |
ROW = re.compile(r"^\|\s*\*\*(\d+)\*\*\s*\|(.+?)\|\s*`([^`]+)`\s*\|")
FLAG = re.compile(r"(--[A-Za-z0-9_\-]+)")


def flags_of_script(p: pathlib.Path) -> set:
    """从脚本源码里抓出它定义的 --开关（不 import、不执行）。"""
    try:
        src = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return set()
    got = set(FLAG.findall(src))
    # add_argument("--x") 与 add_argument('--x' 两种；上面已能抓到裸串，够用
    return got


def main() -> int:
    pb = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PB
    if not pb.is_file():
        print("ERR 读不到手册：%s" % pb)
        return 2

    print("═══ 静态核《复现手册》里的命令 ═══")
    print("  手册 = %s" % pb.name)
    print("  ★ 本器【不执行】命令；只核【脚本在不在】与【开关名对不对】。")
    print()

    rows, bad, checked = 0, [], 0
    seen_nums, unparsed, prose, external = set(), [], [], []
    for line in pb.read_text(encoding="utf-8", errors="replace").splitlines():
        # ★★ 轮164 修：**先记下"看着像表行、但没解析出来"的**——
        #   首跑就是这样【静默漏掉第 14 行】（其命令格是粗体套反引号，正则未匹配）。
        #   ★ 而"静默漏检"正是本器要治的病 ⇒ 本器自己不许犯。
        looks_like_row = bool(re.match(r"^\|\s*\*\*\d+\*\*\s*\|", line))
        m = ROW.match(line)
        if not m:
            if looks_like_row:
                # ★★ 轮165 修：**分开两件事**——
                #   · 命令格里【根本没有反引号命令行】（纯中文叙述）⇒ 那是【不可静态核】，不是"不符"
                #     （本席第⑪条：不把"未定义／前提未满足"折叠成"失败"）；
                #   · 命令格【有】反引号而我却没解析出来 ⇒ 那才是【真缺口】。
                # ★★ 轮165 再修：**"有反引号"太粗**——第14行含 `tools\x.mjs` 与 `25/25` 两处反引号，
                #   但那是【行内路径与期望值】，不是命令行。
                #   ⇒ 改看【命令格（第 4 个字段）】里有没有【像命令的东西】：
                #     以 python 起头，或以 .py/.mjs 结尾。
                cells = [c.strip() for c in line.split("|")]
                cmdcell = cells[3] if len(cells) > 3 else ""
                looks_cmd = bool(re.search(r"(python\s|\.py\b|\.mjs\b)", cmdcell))
                # ★★★ 轮165 三修：**第三态**——命令格点名了一个【本席之外的件】
                #   （如「在其观测站目录跑其 tools\math_core_check.mjs」）
                #   ⇒ 那一类【本机核不到】，属"不可核"，**不是"不符"**
                #   （本席第⑪条：不把"前提未满足"折叠成"失败"）。
                ext = bool(re.search(r"其[^，。]{0,8}(目录|观测站)", cmdcell))
                if ext:
                    external.append(line.strip()[:110])
                elif looks_cmd:
                    unparsed.append(line.strip()[:110])
                else:
                    prose.append(line.strip()[:110])
            continue
        rows += 1
        n, cmd = m.group(1), m.group(3).strip()
        seen_nums.add(int(n))
        # 只处理以 python 起头的行（其余如"在其观测站目录跑…"是纯文字）
        if not cmd.lower().startswith("python"):
            print("  [%2s] 非 python 命令，跳过静态核：%s" % (n, cmd[:60]))
            continue
        parts = cmd.split()
        # 找脚本：第一个以 .py 结尾的 token
        script = next((t for t in parts if t.lower().endswith(".py")), None)
        if script is None:
            print("  [%2s] ★ 命令里找不到 .py 脚本：%s" % (n, cmd[:60]))
            bad.append((n, "命令里找不到 .py 脚本"))
            continue
        sp = SEAT / script.replace("\\", "/")
        if not sp.is_file():
            print("  [%2s] ★ 脚本不存在：%s" % (n, script))
            bad.append((n, "脚本不存在：%s" % script))
            continue
        checked += 1
        defined = flags_of_script(sp)
        used = set(FLAG.findall(cmd))
        missing = sorted(f for f in used if f not in defined)
        if missing:
            print("  [%2s] ★ 命令用了脚本里没有的开关：%s" % (n, "、".join(missing)))
            bad.append((n, "开关不存在：%s" % "、".join(missing)))
        else:
            print("  [%2s] ✅ 脚本在 ｜ 开关名对得上（%d 个）" % (n, len(used)))

    print()
    print("  ── 覆盖情况（★ 本器不许自己静默漏检）──")
    print("     解析到行号 = %s" % ("、".join(str(x) for x in sorted(seen_nums)) or "（无）"))
    gaps = [i for i in range(1, (max(seen_nums) if seen_nums else 0) + 1) if i not in seen_nums]
    print("     ★ 未解析到的行号 = %s" % ("、".join(str(x) for x in gaps) or "（无）"))
    for u in unparsed:
        print("        [真缺口·有反引号却没解析出] %s" % u)
    for u in prose:
        print("        [非命令行·不可静态核] %s" % u)
    for u in external:
        print("        [外部件·本机不可静态核] %s" % u)
    if unparsed:
        print("     ★ 上面每一行【有命令行格式却没被核到】——那是真缺口。")
        bad.append(("覆盖", "有 %d 行有命令行却未被解析" % len(unparsed)))
    if external:
        print("     ○ 另有 %d 行点名了【本席之外的件】⇒ **不可静态核，本身不算不符**" % len(external))
    if prose:
        print("     ○ 另有 %d 行是【中文叙述而非命令行】⇒ **不可静态核，本身不算不符**" % len(prose))
        print("        （★ 本席第⑪条：不把「未定义／前提未满足」折叠成「失败」）")

    print()
    print("  ── 判词 ──")
    print("     表内行数 %d ｜ 静态核过 %d ｜ ★不符 %d" % (rows, checked, len(bad)))
    for n, why in bad:
        print("       [%s] %s" % (n, why))
    print("  ★ 本器【抓不到「少写一个开关」】——那类不是静态能判的（轮163 那条即属此类）。")
    print("  ★ 本器能失败（脚本缺失／开关名不符 即报并返回非零）⇒ 非恒真。")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
