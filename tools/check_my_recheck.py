#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 本件只读本机台账，不触网。
r"""check_my_recheck.py —— **把我向对方提的标准，先量我自己**。 v1.0.0

来由（轮131）
──────────────
轮 130 我向码道席提了三项要求，其中第三项是：
  ★ **每一项主张配一个 `recheck`，指向【一个可复算的量】。**
⇒ 那就该先问：**我自己的 185 条台账，做到了吗？**
  **若我自己不合，那就是我对别人提了我自己不满足的标准。**

怎么量（**判据写在明处**）
──────────────────────────
对每条台账，看其 `evidence` 与 `subject` 里**有没有【可复算指认】**（任一即算）：
  · 脚本/文件路径样式：`exp/xxx.py`、`x.mjs`、`x.json`、`x.md`
  · 命令样式：`python …`、`node …`
  · 摘要/哈希：`sha256=`、`sha256 …`、`= 16/32/64 位十六进制`
  · 计数样式：`N 项`、`N 条`、`N/M`
★ 本器**只做字面识别**，**故它给的是【下界】**：**也许有可复算而写法我没认出的**。
三态：`有指认` ／ `无指认` ／ `字段缺`（**第三种单独列，不并进第二种**）。
"""
from __future__ import annotations
import json
import pathlib
import re
import sys
from collections import Counter

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SEAT = pathlib.Path(__file__).resolve().parent.parent
LED = SEAT / "ledger" / "frontier_ledger.jsonl"

PATS = [
    ("路径", re.compile(r"[\w\u4e00-\u9fff./_-]+\.(?:py|mjs|js|json|jsonl|md|tsv|txt|html|led|docx)")),
    ("命令", re.compile(r"\b(?:python|node|pwsh|powershell)\b")),
    ("哈希", re.compile(r"sha256\s*=|sha256[=: ]|[0-9a-f]{16,}")),
    ("计数", re.compile(r"\d+\s*(?:项|条|件|处|/)\s*\d*")),
]


def main() -> int:
    rows = []
    for line in LED.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            pass

    have, lack, missing = [], [], []
    kinds = Counter()
    for e in rows:
        ev = e.get("evidence")
        if ev is None or str(ev).strip() == "":
            missing.append(e)
            continue
        blob = str(ev) + " " + str(e.get("subject", ""))
        hit = None
        for name, rx in PATS:
            if rx.search(blob):
                hit = name
                break
        if hit:
            have.append(e)
            kinds[hit] += 1
        else:
            lack.append(e)

    n = len(rows)
    print("═══ 自查：我向对方提的『每条主张配 recheck』，我自己做得如何 ═══")
    print("  台账总条数            %d" % n)
    print("  ── 三态（**分开列，不并**）──")
    print("     ✅ 有可复算指认      %d  （%.0f%%）" % (len(have), 100.0 * len(have) / max(n, 1)))
    print("     ○ 无指认（字面未见）  %d  （%.0f%%）" % (len(lack), 100.0 * len(lack) / max(n, 1)))
    print("     — 字段缺（无 evidence）%d" % len(missing))
    print("  ── 指认种类分布 ──")
    for k, v in kinds.most_common():
        print("     %-6s %d" % (k, v))
    print()
    print("  ── 无指认的条目（最多列 12 条）──")
    for e in lack[:12]:
        print("     #%-4s %-16s %s" % (e.get("seq", "?"), e.get("ev_type", "?"), str(e.get("subject", ""))[:64]))
    if len(lack) > 12:
        print("     …（余 %d 条）" % (len(lack) - 12))
    print()
    print("  ── 判词 ──")
    rate = 100.0 * len(have) / max(n, 1)
    print("     合规率（下界，字面识别）=%.0f%%" % rate)
    print("     ⇒ " + ("★ 我自己【未达到】我向对方提的标准 ⇒ **要么补上，要么把要求降到我做得到的水平**。"
                       if rate < 95 else "○ 我方基本满足（但仍是字面下界，非逐条人工核过）"))
    print("  ★ 本器只做字面识别 ⇒ 所报数字是【下界】，不是精确合规率；")
    print("     且【字段缺】单独列，不并进『无指认』——两件事不同。")
    print("  ★ 本器能失败（合规率低即报）⇒ 非恒真。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
