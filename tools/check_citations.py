#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只读本席件与台账；不写任何件、不触网。
r"""check_citations.py —— 让"把转述写成引文"变得【可被检出】。 v1.0.0

立此器的缘由（轮 24）
────────────────────────
轮 23 我命名了一类新形态：**转述自己时的错**——
我凭记忆把轮 5 的理由转述成「密钥只在内存 ⇒ 事后无法验证」，而原文说的是「持久密钥带来托管负担」。
★ 它隐蔽，因为【转述看起来像回顾，不像主张】，所以没人去核。

⇒ 机械的对策只有一条：**凡我引旧件或声明的话，必须逐字可核。**

本器做什么
────────────
  1. 把本席 outbox 的 .md 与台账条目的 subject/detail 当作【语料】；
  2. 从每件里抽出【「」包裹、长度 ≥ 12 字】的片段（＝被当作引文呈现的部分）；
  3. 对每个片段，问：它是否【逐字】出现在【本件之外的】语料里？
  4. 列出【找不到出处】的片段 —— ★ 它们是候选："可能是转述被写成了引文"。

★ 本器自陈三条盲点（按轮 12 判据）
  ① ★ **它只判"逐字有没有出处"，不判"转述对不对"**——语义层面的错它【管不了】；
  ② ★ **「」在我文里也用于【强调】而非引用** ⇒ **会有假阳性**（我明知这一点，故只列候选）；
  ③ ★ **语料只含本席 outbox 与台账** ⇒ **引他席文、引外部文时它必然报"无出处"**（那不一定是错）。

用法: check_citations.py [--min-len 12] [--top 30]
"""
from __future__ import annotations
import argparse
import json
import pathlib
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SEAT = pathlib.Path(__file__).resolve().parent.parent
OUTBOX = SEAT / "outbox"
LEDGER = SEAT / "ledger" / "frontier_ledger.jsonl"
SPAN = re.compile(r"「([^」]{6,})」")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-len", type=int, default=12)
    ap.add_argument("--top", type=int, default=30)
    a = ap.parse_args()

    print("═══ 引文出处机检（只读）═══")
    pieces = sorted(OUTBOX.glob("*.md"))
    corpus = {p.name: p.read_text(encoding="utf-8", errors="replace") for p in pieces}
    if LEDGER.is_file():
        for i, line in enumerate(LEDGER.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            r = json.loads(line)
            corpus["台账第%d条" % i] = (str(r.get("subject", "")) + "\n" + str(r.get("detail", "")))
    print("  语料 = %d 份（件 %d ＋ 台账条目）" % (len(corpus), len(pieces)))

    rows = []
    for name, text in corpus.items():
        if not name.endswith(".md"):
            continue
        for m in SPAN.finditer(text):
            s = m.group(1).strip()
            if len(s) < a.min_len:
                continue
            hits = [k for k, v in corpus.items() if k != name and s in v]
            rows.append((name, s, hits))

    unmatched = [r for r in rows if not r[2]]
    print("  抽出的引文片段（≥ %d 字）= %d" % (a.min_len, len(rows)))
    print("  ★ 在本席语料里【找不到逐字出处】= %d ／ %.0f%%"
          % (len(unmatched), 100.0 * len(unmatched) / max(1, len(rows))))
    print()
    print("  ── 候选名单（前 %d 条）★ 只是候选，不是判罪 ──" % a.top)
    for name, s, _ in unmatched[:a.top]:
        print("     ★ [%s]" % name[:40])
        print("        「%s」" % s[:96])

    print()
    print("  ── 本器三条盲点（写在器内）──")
    print("     ① 只判『逐字有无出处』，不判『转述对不对』——语义错它管不了")
    print("     ② 「」在本席文里也用于【强调】而非引用 ⇒ 有假阳性，故只列候选")
    print("     ③ 语料只含本席 outbox 与台账 ⇒ 引他席/外部文时必然报『无出处』")
    print()
    print("  ★ 本器的用处不是判罪，而是：★ 让『把转述写成引文』【有代价】——")
    print("    因为一旦写成「」，它就会进这份候选名单。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
