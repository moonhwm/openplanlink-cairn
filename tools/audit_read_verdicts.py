#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只读件做计数；不执行被测器、不写件、不删件、不触网。
r"""audit_read_verdicts.py —— 数：哪几件器的【名字/判词】真被我出的件引用过。 v1.0.0

为什么做它（轮 75，承轮 74）
──────────────────────────────
轮 74 我数出：机器可读判词那条约定只覆盖 9/55。
★ 而我当时明写：**不把 46 件一次补完**，理由是
  「★ 这 46 件里多数器的判词【我从不引用】⇒ 给从不被读的判词加机器可读行，是做了不产生信息的工」。
⇒ ★★ 而那句话【当时没有证据】。本器就是去取那份证据：**按被引次数排序。**

判据
──────
  在被引件（outbox\*.md ＋ 各轮论证件）里，数每件 exp\*.py 的【文件名】出现次数。
  ★ 次数 = 该器的判词【被读】的代理指标（★ 这是代理，不是"真读"——见盲点①）。

★ 本器自陈三条盲点
  ① **"文件名出现次数"只是【引用】的代理**——★ 出现 ≠ 我读了它的判词（可能只在讲它别的事）
  ② 只数 outbox 的 .md ⇒ **台账 .json/.led 里的引用【不计】**（★ 那些更多是"做了什么"，不是"读判词"）
  ③ ★ 它【不判】哪个数算"会被读"——★ 那条线仍须人来划
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
OUTBOX = SEAT / "outbox"

# ★ 收尾块已读的那 5 件（轮 72–73 已加 VERDICT）
CLOSING = {
    "cairn_ledger.py", "verify_seat_location.py", "verify_recipe.py",
    "tool_hygiene.py", "lint_cn_quotes.py",
}


def main() -> int:
    print("═══ 哪几件器的判词真被引用过（★ 按出现次数排）═══")
    pieces = [p for p in OUTBOX.glob("*.md")]
    print("  被数件 = outbox\\*.md 共 %d 件" % len(pieces))
    blob = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in pieces)
    print("  ★ 注意：这是【引用次数】这一代理，不是「我读过它的判词」——★ 见本器盲点①")
    print()

    counts = collections.Counter()
    for p in sorted(EXP.glob("*.py")):
        n = blob.count(p.name)
        if n:
            counts[p.name] = n
    print("  ── 被引次数 ≥ 1 的器 = %d 件 ──" % len(counts))
    print("  %-36s %6s  %s" % ("器", "次数", "收尾块已读？"))
    for name, n in counts.most_common(30):
        mark = "★ 已读" if name in CLOSING else "○ 未读"
        print("  %-36s %6d  %s" % (name, n, mark))
    print()
    top = [n for n, _ in counts.most_common(15)]
    top_unread = [n for n in top if n not in CLOSING]
    print("  ═══ 判定 ═══")
    print("     ★ 被引最多的前 15 件里，收尾块【未读】的 = %d 件：" % len(top_unread))
    for n in top_unread:
        print("        ○ %s（被引 %d 次）" % (n, counts[n]))
    print()
    print("     ⇒ ★ 这 %d 件就是【下一批该补 VERDICT 的候选】——★ 而「哪几件算真被读」仍须人来划。"
          % len(top_unread))
    print("     ★ 本器三条盲点：① 出现次数只是引用代理 ② 只数 outbox 的 .md ③ 不画那条约线")
    return 0


if __name__ == "__main__":
    sys.exit(main())
