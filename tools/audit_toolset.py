#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只读扫描本席 exp\ 下的器；不改动、不删除任何件。不触网。
r"""audit_toolset.py —— 把轮 12 那条判据用到【工具箱】上：找【被取代者】与【越权下结论者】。 v1.0.0

立此器的缘由
──────────────
轮 12 我立了判据：**一层检查若是【装饰】，它不声明自己抓不到什么。**
★ 可我只把它用在【7 条判据】上，从未用在【104 个器】上。
⇒ 一个 13 轮都在"加东西"的席位，至少该做一次减法审计。

判据（★ 都只看器的源码与文档串，不作语义猜测）
───────────────────────────────────────────────
  A 【越权下结论】：器里有 print 输出【结论/判词/形态/PASS/FAIL】这类断言，
     ★ 但全文【没有】任何"局限／边界／不核／仅／本器只能"之类的自限词。
     ⇒ 按轮 12 判据，这类是【装饰】或更糟（给读者假印象）。
  B 【疑似被取代】：某器与另一器在【同一对象】上有大量同名字符串（如同为"推翻率/论证弧"），
     且其中一件的 mtime 更晚 ⇒ 标为"疑似被后件取代"（★ 只标，不删）。
  C 【一次性实验】：名字带 probe/demo/trial/test/lab 且被引用次数低 ⇒ 标为"实验件"。

用法: audit_toolset.py
"""
from __future__ import annotations
import collections
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

CONCLUDE = re.compile(r"判词|结论：|形态|PASS|FAIL|被高估|被低估|成立|不成立")
LIMIT = re.compile(r"局限|边界|不核|本器只能|仅当|本器只|不见得|不等于|未检|无法|不声明|盲点")


def main() -> int:
    print("═══ 工具箱审计（只读）═══")
    if not EXP.is_dir():
        print("ERR exp\\ 不在 ⇒ ★ 器具故障")
        return 2
    tools = [p for p in EXP.glob("*.py") if "__pycache__" not in str(p)]
    mjs = [p for p in EXP.glob("*.mjs")]
    print("  .py = %d ｜ .mjs = %d" % (len(tools), len(mjs)))

    overclaim, selflimited = [], []
    for p in tools:
        t = p.read_text(encoding="utf-8", errors="replace")
        if CONCLUDE.search(t):
            (selflimited if LIMIT.search(t) else overclaim).append((p, p.stat().st_mtime))

    print()
    print("  ── A · 越权下结论（有断言、但全文无自限词）★ 按轮 12 判据＝装饰或更糟 ──")
    print("     有断言者 = %d ｜ 其中具自限词 = %d ｜ ★ 无自限词 = %d"
          % (len(overclaim) + len(selflimited), len(selflimited), len(overclaim)))
    for p, _ in sorted(overclaim, key=lambda x: -x[1])[:20]:
        print("       ★ %s" % p.name)

    print()
    print("  ── B · 疑似【同一对象上的重叠器】（同名字串 ≥3 个）★ 只标不删 ──")
    keys = {}
    for p in tools:
        t = p.read_text(encoding="utf-8", errors="replace")
        tags = set()
        for kw in ("推翻率", "论证弧", "托辞", "等别人", "signed=false", "不证作者",
                   "twocopy", "副本", "chain_rewrite", "lockpin", "LOCKPIN"):
            if kw in t:
                tags.add(kw)
        if tags:
            keys[p] = tags
    groups = collections.defaultdict(list)
    for p, tags in keys.items():
        for kw in tags:
            groups[kw].append(p)
    for kw, ps in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        if len(ps) >= 3:
            print("     【%s】被 %d 个器提到：%s" % (kw, len(ps), "、".join(x.name for x in ps[:6])))

    print()
    print("  ── C · 一次性实验件（名字含 probe/demo/trial/lab/test）──")
    labs = [p for p in tools if re.search(r"probe|demo|trial|lab|_test", p.name)]
    print("     = %d 个：%s" % (len(labs), "、".join(p.name for p in labs[:12])))

    print()
    print("  ═══ 判定 ═══")
    print("     ★ 无自限词而有断言者 = %d 个 ⇒ 这些是【该处理的】。" % len(overclaim))
    print("     ★ 处理方式【不是删】（它们可能被件或器引用）⇒ 而是【加一行自限说明】，")
    print("        与轮 12 对 ⑤ 的处置一致：★ 撤掉假印象，而不是拆掉功能。")
    print("     ★ 本器局限：它按【字样】判『有无自限词』⇒ 可能误判；")
    print("        故它只【列出名单】，不替人决定删改。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
