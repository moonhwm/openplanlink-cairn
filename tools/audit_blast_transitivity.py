#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只读源码做静态分析；不执行任何被测器、不写件、不触网。
r"""audit_blast_transitivity.py —— 把轮 56 的认识做成【可查】：波及范围【有传递性】。 v1.0.0

为什么做它（轮 57，承轮 56 的教训）
──────────────────────────────────────
轮 56 实测：我以「声明 BLAST: NONE ⇒ 安全」为理由跑冒烟，★ 而它【在同一次运行里就被证伪】：
  verify_playbook.py（声明 NONE）──子进程──▶ ab_test_fixed.py（无声明）──写了真件
  make_pack.py（声明 NONE）───────────────────写了 exp/_pack_manifest.tsv 等
★★ 故那条推论错在：**声明只覆盖一个件的【静态文本】，而波及范围【有传递性】。**

⇒ 本器把这件事做成【可查】：**列出所有【声明 NONE】的器里，哪些会【去调别的 .py】。**

★ 本器自陈三条盲点
  ① 它只做【静态文本】匹配（subprocess/os.system/EXP/"x.py" 等）⇒ **动态拼接的命令它测不到**；
  ② 它只报【是否调用了别的 .py】⇒ **不判那个被调者会不会写**（★ 那要递归，且本文本判据会误报）；
  ③ ★ 它【不执行】任何器 ⇒ 故它【只是提示】，不是"这些器确实写了"的证明。
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
EXP = SEAT / "exp"

# 会去"调别的东西"的信号
CALL = re.compile(r"subprocess\.|os\.system|os\.exec|Popen\(|run\(\[|check_output")
# 指向本席 .py 的信号
# ★ 2026-10-03 轮 63 修：**原模式不认【带路径的写法】。**
#   原文：PYREF = re.compile(r"[\"']([A-Za-z0-9_\-]+\.py)[\"']")
#   ⇒ ★ 它只匹配裸文件名（"x.py"），而【'exp/audit_orphans.py' 因含 / 而落空】。
#   ★★ 实证（轮 63）：我在临时副本里注入一个写了 'exp/audit_orphans.py' 的调用者，
#      本器扫到了 119 个 .py（比本席多 1）却【不列出它】⇒ ★ 说明这一类引用【全被漏掉】。
#   ⇒ 故我上一轮那句「声明 NONE 而会调别的 .py = 10 件」★ 是【下界】，不是全数。
#   ⇒ 修法：把 / 与 \ 放进字符类。
PYREF = re.compile(r"[\"']([A-Za-z0-9_\-/\\]+\.py)[\"']")
BLASTLINE = re.compile(r"BLAST:\s*([A-Z_,\s]+)")


def decl_of(p: pathlib.Path) -> str:
    m = BLASTLINE.search(p.read_text(encoding="utf-8", errors="replace")[:1500])
    return m.group(1).strip() if m else "（无声明）"


def main() -> int:
    print("═══ 波及范围的【传递性】稽核（只读源码）═══")
    tools = [p for p in sorted(EXP.glob("*.py")) if "__pycache__" not in str(p)]
    print("  .py = %d" % len(tools))
    print()

    rows = []
    dynamic = []
    c_only = []
    for p in tools:
        t = p.read_text(encoding="utf-8", errors="replace")
        calls = bool(CALL.search(t))
        refs = sorted(set(PYREF.findall(t)))
        # ★ 轮 58 加：**调用是【变量】而非字面量** ⇒ 本器【测不到具体对象】。
        #   缘由：上一轮那张 10 件名单【漏掉了肇事者 smoke_none_tools.py】——
        #   它的调用是 subprocess.run([sys.executable, str(p)])，★ 变量，不是 "x.py"。
        #   ⇒ 故本器此后把这一类【单独报出来】，★ 并明说"对象测不到"，
        #     而不是【沉默地漏掉】——★ 这正是"永远失败的检查＝没有检查"的镜像：
        #     ★ 一个【沉默漏报】的检查，看起来像"没有这一类"。
        has_dyn = bool(re.search(r"subprocess\.(run|Popen|call|check_\w+)\s*\([^)]*sys\.executable", t)) \
                  or bool(re.search(r"subprocess\.(run|Popen|call|check_\w+)\s*\(\s*[A-Za-z_]", t))
        # ★ 轮 59 细化：**`subprocess.run([python, "-c", <代码字符串>])` 并不调别的 .py**。
        #   缘由（轮 59 实读 probe_guard_hole*.py）：它们声明的 NONE【成立】——它们只跑一段 -c 代码，
        #   ★ 不调任何 .py 文件。而我上一轮把它们列进"测不到"栏 ⇒ 那是【过报】。
        #   ★ 而过报也是失效：**永远报警的检查，会被当背景噪声忽略**（与"永远不报警"同一族的错）。
        #   ⇒ 故此处把"只跑 -c 代码"这一类【单列且标明不调 .py】，不进"测不到"栏。
        only_c = bool(re.search(r"subprocess\.\w+\s*\([^)]*[\"']-c[\"']", t)) and not refs
        if calls and refs:
            rows.append((p, decl_of(p), refs, calls))
        elif calls and only_c:
            c_only.append((p, decl_of(p)))
        elif calls and has_dyn:
            dynamic.append((p, decl_of(p)))

    print("  ── 会【调别的 .py】的器 = %d 件 ──" % len(rows))
    print()
    none_bad = [r for r in rows if r[1] == "NONE"]
    print("  ── ★★ 其中【声明 NONE】的 = %d 件 ⇒ 这些是【上一轮那类洞】的候选 ──" % len(none_bad))
    for p, decl, refs, _ in none_bad:
        print("     ★ %-34s 声明 NONE ⇒ 调：%s" % (p.name[:34], "、".join(refs[:4])))
    print()
    print("  ── ★★★ 会调、但【对象是变量】⇒ 本器【测不到】= %d 件（★ 上一轮就漏在这里）──"
          % len(dynamic))
    for p, decl in dynamic:
        mark = "★★ 声明 NONE！" if decl == "NONE" else ("声明 " + decl)
        print("     ★ %-34s %s ⇒ ★ 调谁【测不到】，须人读" % (p.name[:34], mark))
    print()
    print("  ── ○ 只跑 `python -c <代码字符串>`、★ 不调任何 .py = %d 件（★ 轮 59 单列：不进「测不到」栏）──"
          % len(c_only))
    for p, decl in c_only:
        print("     ○ %-34s 声明 %s ⇒ ★ 不调别的器（★ 故其 NONE 声明【成立】）" % (p.name[:34], decl))
    print()
    print("  ── 其余（无声明或非 NONE）＝ %d 件 ──" % (len(rows) - len(none_bad)))
    for p, decl, refs, _ in rows:
        if decl != "NONE":
            print("     · %-34s 声明 %-16s 调：%s" % (p.name[:34], decl[:16], "、".join(refs[:3])))

    print()
    print("  ═══ 判定 ═══")
    print("     ★ 声明 NONE 而【会调别的 .py（字面量可查）】= %d 件" % len(none_bad))
    print("     ★★ 声明 NONE 而【调谁测不到】= %d 件 ⇒ ★ 这些必须人读 —— ★ 上一轮的漏报就在这一类里"
          % len([1 for _, d in dynamic if d == "NONE"]))
    print("     ★ 本器三条盲点：")
    print("        ① 只做静态文本匹配 ⇒ 动态拼接的命令【对象】测不到（★ 本轮已单独报出这一类，但仍测不到对象）")
    print("        ② 只报'是否调了别的 .py' ⇒ 不判被调者会不会写")
    print("        ③ 不执行任何器 ⇒ 它是【提示】，不是'这些器确实写了'的证明")
    # ★ 2026-10-03 轮 63 加：**一行机器可读的发现数**（★ 同 audit_orphans 的理由）。
    #   轮 62 实测：本器注入坏件后【退出码恒 0】而【输出变了】⇒ 只盯退出码者【看不见】。
    #   ⇒ 故补这一行：三个计数合成一个数，★ 任一变化都会让它变。
    print("★ FINDINGS=%d" % (len(none_bad) + len(dynamic) + len(c_only)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
