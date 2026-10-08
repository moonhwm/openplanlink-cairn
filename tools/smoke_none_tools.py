#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: EXEC —— ★★ 轮 58 更正：原声明写的是 NONE，★ 而那【不实】。
#   本器会【执行 52 个别器】（subprocess.run([sys.executable, str(p)])）⇒
#   ★ 它的实际波及是【那 52 件的并集】，而不是"什么都不做"。
#   ★★ 实证（轮 56）：正因为它声明 NONE，我以"NONE ⇒ 安全"为理由跑了它，
#      而它跑到 verify_playbook.py ⇒ 后者子进程跑 ab_test_fixed.py ⇒ 写了真件 11 个。
#   ⇒ 故本声明改为 EXEC；★ 且它【不触网、不主动写件】这半句仍然成立——
#     但它【会连带别人的写】⇒ 这两件事必须分开写。
r"""smoke_none_tools.py —— 补上"编译 ≠ 能跑"那个缺口：★ 只在声明 NONE 的器上冒烟。 v1.0.1

为什么做它（轮 55，承轮 54）
──────────────────────────────
轮 54 撞出：我给新器用了 `argparse` 却忘了导入 ⇒ **编译通过，运行 NameError**。
★ 而本席的机检是【编译级】⇒ 这一类【看不见】。
★ 那就问：113 个器里有多少是"编译过而跑不起来"的？

★★ 而这里有个真障碍：**不能都跑一遍**——`blast_radius` 说有些器是 DEL／WRITE／NET 能力。
⇒ 故本器【只在声明 `BLAST: NONE` 的器上跑】——★ 那些器不写不删不触网，故冒烟是安全的。

判据（★ 关键：区分"跑不起来"与"跑了并报了结果"）
──────────────────────────────────────────────────
  · ★ **崩溃**：输出含 `Traceback (most recent call last)` 或 `SyntaxError` ⇒ 判 BAD（＝编译过但跑不起来）
  · ○ **非零但无 traceback**：★ 那是【器跑通了并报了结果】（如检查器发现不符）⇒ **不判 BAD**
  · ✅ 退出码 0 且无 traceback ⇒ OK

★ 本器自陈三条盲点
  ① 它只覆盖【声明 NONE 的器】⇒ 其余 62 件【本轮不碰】——★ 而那些里可能有同类缺陷
  ② 它用【无参数运行】来冒烟 ⇒ 需要参数的器会打印用法后正常退出，★ 那测不到其内部
  ③ 它按【输出里有无 traceback】判 ⇒ 若某器自己把异常吞掉并打印非 traceback 文本，它【测不出】
"""
from __future__ import annotations
import pathlib
import re
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SEAT = pathlib.Path(__file__).resolve().parent.parent
EXP = SEAT / "exp"
TB = re.compile(r"Traceback \(most recent call last\)|SyntaxError")


def declares_none(p: pathlib.Path) -> bool:
    head = p.read_text(encoding="utf-8", errors="replace")[:1500]
    m = re.search(r"BLAST:\s*([A-Z_,\s]+)", head)
    return bool(m) and m.group(1).strip() == "NONE"


def main() -> int:
    print("═══ 只在【声明 BLAST: NONE】的器上冒烟 ═══")
    tools = [p for p in sorted(EXP.glob("*.py")) if "__pycache__" not in str(p)]
    none_tools = [p for p in tools if declares_none(p)]
    print("  .py = %d ｜ ★ 声明 NONE = %d ｜ 其余【不碰】= %d"
          % (len(tools), len(none_tools), len(tools) - len(none_tools)))
    print("  ★ 判据：输出含 Traceback/SyntaxError ⇒ BAD；非零但无 traceback ⇒ 跑了并报了结果，不判 BAD")
    print()

    bad, nonzero_ok, ok, skipped = [], [], 0, []
    for p in none_tools:
        if p.name == pathlib.Path(__file__).name:
            skipped.append(p.name)      # ★ 不跑自身（防自递归冒烟）
            continue
        try:
            r = subprocess.run([sys.executable, str(p)], capture_output=True, text=True,
                               encoding="utf-8", cwd=str(SEAT), timeout=120)
            out = (r.stdout or "") + (r.stderr or "")
            if TB.search(out):
                first = next((l.strip() for l in out.splitlines()
                              if "Error" in l or "Traceback" in l), "")
                bad.append((p.name, r.returncode, first[:80]))
            elif r.returncode != 0:
                nonzero_ok.append((p.name, r.returncode))
            else:
                ok += 1
        except subprocess.TimeoutExpired:
            skipped.append(p.name + "（超时）")
    print("  ── ★ BAD：编译过但【跑不起来】（含 traceback）──")
    if bad:
        for n, rc, msg in bad:
            print("     ★ %-40s 退出码 %d ｜ %s" % (n[:40], rc, msg))
    else:
        print("     （无）")
    print()
    print("  ── ○ 非零但无 traceback（★ 跑了并报了结果，不算 BAD）──")
    for n, rc in nonzero_ok[:12]:
        print("     ○ %-40s 退出码 %d" % (n[:40], rc))
    if len(nonzero_ok) > 12:
        print("     …共 %d 件" % len(nonzero_ok))
    print()
    print("  ═══ 汇总 ═══")
    print("     冒烟 = %d 件 ｜ ✅ 退出码 0 = %d ｜ ○ 非零无崩溃 = %d ｜ ★ BAD = %d ｜ 跳过 = %d"
          % (len(none_tools), ok, len(nonzero_ok), len(bad), len(skipped)))
    if skipped:
        print("     跳过：%s" % "、".join(skipped[:6]))
    print()
    print("  ── 本器三条盲点 ──")
    print("     ① 只覆盖声明 NONE 的器 ⇒ 其余【本轮不碰】，而那些里可能有同类缺陷")
    print("     ② 用【无参数运行】冒烟 ⇒ 需参数的器只会打印用法，测不到其内部")
    print("     ③ 按【有无 traceback】判 ⇒ 自行吞掉异常者测不出")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
