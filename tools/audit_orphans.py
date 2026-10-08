#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只读扫描本席 exp\ 与声明；不改动、不删除任何件。不触网。
r"""audit_orphans.py —— 算"哪些器真被引用、哪些是孤儿"。 v1.0.0

立此器的缘由（轮 20 里程碑）
──────────────────────────────
二十轮攒下 ~106 个 .py。★ 而从未算过：**哪些被别处引用，哪些是孤儿。**
⇒ 一个无人引用的器若还下着断言，**比没有它更糟**——**因为它看起来像基础设施**。

★ 本器【自陈三条盲点】（按轮 12 判据：不声明盲点的检查是装饰）
  ① 它按【文件名出现】判"被引用" ⇒ **提及 ≠ 调用**（正是轮 17 那类错）；
  ② 它扫的范围是 exp\ ＋ 声明的 verify_recipe ＋ outbox\ 的件 ⇒ **范围外的不算**；
  ③ ★ 它【不下"该删"的结论】——**只给候选名单**（轮 11／14／17：数只给候选）。

用法: audit_orphans.py
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
DECL = SEAT / "outbox" / "SEAT_LOCATION_cairn-dsh_20261002.json"
OUTBOX = SEAT / "outbox"
ASSERT = re.compile(r"判词|结论：|PASS|FAIL|成立|不成立|形态|揭示")


def main() -> int:
    print("═══ 孤儿审计（只读）═══")
    tools = [p for p in EXP.glob("*.py") if "__pycache__" not in str(p)]
    print("  .py = %d" % len(tools))

    # 语料：其他器 + 声明 + outbox 的 .md
    corpus = []
    for p in tools:
        corpus.append((p.name, p.read_text(encoding="utf-8", errors="replace")))
    if DECL.is_file():
        corpus.append((DECL.name, DECL.read_text(encoding="utf-8", errors="replace")))
    for p in OUTBOX.glob("*.md"):
        corpus.append((p.name, p.read_text(encoding="utf-8", errors="replace")))
    print("  语料 = %d 份（器 %d ＋ 声明 1 ＋ outbox 件）" % (len(corpus), len(tools)))

    orphans, referenced = [], []
    for p in tools:
        n = 0
        for src, text in corpus:
            if src == p.name:
                continue
            if p.name in text:
                n += 1
        (referenced if n >= 1 else orphans).append((p, n))

    print()
    print("  ── A · 被别处提及 = %d ｜ ★ 从未被提及（孤儿）= %d ──"
          % (len(referenced), len(orphans)))
    print("  ── B · 孤儿中【含断言】者（★ 最该处置：看起来像基础设施）──")
    orph_assert = [(p, n) for p, n in orphans if ASSERT.search(p.read_text(encoding="utf-8", errors="replace"))]
    print("     = %d / %d" % (len(orph_assert), len(orphans)))
    for p, _ in sorted(orph_assert, key=lambda x: x[0].stat().st_size, reverse=True)[:18]:
        print("       ★ %-42s %6d B" % (p.name, p.stat().st_size))

    print()
    print("  ── C · 引用最多的前 10（★ 主干）──")
    for p, n in sorted(referenced, key=lambda x: -x[1])[:10]:
        print("       %-42s 被 %d 处提及" % (p.name, n))

    print()
    print("  ═══ 判定 ═══")
    print("     ★ 孤儿含断言 = %d 个 ⇒ 这是【候选名单】，不是【该删名单】。" % len(orph_assert))
    print("     ★ 本器三条盲点（写在器内）：")
    print("        ① 按文件名出现判引用 ⇒ 【提及 ≠ 调用】")
    print("        ② 范围只含 exp\\ ＋ 声明 ＋ outbox ⇒ 范围外不算")
    print("        ③ ★ 不下『该删』的结论 —— 数只给候选")
    print("     ★ 处置方向（按轮 11–14 的规矩）：【标注】，不是【删除】。")
    # ★ 2026-10-03 轮 63 加：**一行机器可读的发现数**。
    #   缘由（轮 62 实测）：本器注入坏件后【退出码恒 0】而【输出变了】⇒
    #   ★ 凡只盯退出码的监控（如 verify_recipe）【对本器瞎】。
    #   ⇒ 故补这一行：★ 它的值会随发现数变化 ⇒ 监控可据此看见变化。
    #   ★ 注意：它【不改退出码】——本器仍是【稽核】（报候选），不是【闸】。
    print("★ FINDINGS=%d" % len(orph_assert))
    return 0


if __name__ == "__main__":
    sys.exit(main())
