#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只读台账【结构字段】；不扫正文文字，故不犯"提到当成做到"。不触网。
r"""audit_by_evtype.py —— 用【结构化字段】重算"推翻率"，以检验此前那个【按字样】的数字。 v1.0.0

★★ 2026-10-02 轮 14 标注：本器与 `audit_argument_arc.py`、`audit_deferrals.py` 在同一对象上重叠。
   ★ 而轮 11 的逐条手判已证：本器（按字段）会【低估】——因为本席常把真推翻写成 ARGUMENT。
   ⇒ 故本器【不下"哪个更接近真值"的判词】（轮 11 已撤稿）；
     **最终数字以轮 11 手判表为准：严格 62%（8/13）｜宽松 77%（10/13）。**

为什么必须重算
──────────────
轮 7–9 我报过两个头条数字：推翻率 54–57%、做与等 0.86:1。
★ 而它们都是【字符串匹配】的产物 —— 正是轮 9 我声明【不可靠】的那个方法。
⇒ 故本轮换判据：【ev_type】是我写台账时【显式选择】的结构字段，不是从正文里猜出来的。
   若两者结论不同 ⇒ 说明按字样的数字被污染了，须更正；若一致 ⇒ 原数字侥幸站得住。

★ 本器的局限（写在输出里，不藏）
   · `ev_type` 也是我填的 ⇒ 它仍是【自陈】，只是【比字样更结构化】；
   · 但二者的【误差机制不同】：字样会被"提到"污染，而字段是【我在写那一刻的归类】。
"""
from __future__ import annotations
import collections
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
LEDGER = SEAT / "ledger" / "frontier_ledger.jsonl"

# ★ 结构化判据：按 convention，CORRECTION / 自曝类 ev_type 才是"推翻自己"
OVERTURN_TYPES = {"CORRECTION"}
# 对照用的旧（按字样）判据，仅为复算，不作结论
WORDY = re.compile(r"更正|自曝|勘误|推翻|错|缺陷|停滞|停早|名不副实")


def main() -> int:
    if not LEDGER.is_file():
        print("ERR 台账不在 ⇒ ★ 器具故障")
        return 2
    rows = [json.loads(l) for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
    arc = [r for r in rows if str(r.get("ts", "")).startswith("2026-10-02T21:")]
    print("═══ 按【结构字段】重算（对照「按字样」旧结论）═══")
    print("  台账 %d 条 ｜ 论证时段 %d 条" % (len(rows), len(arc)))

    print()
    print("  ── A · 全台账 ev_type 分布（★ 结构化，不扫正文）──")
    dist = collections.Counter(r.get("ev_type", "（无）") for r in rows)
    for k, v in dist.most_common():
        print("     %-14s %4d" % (k, v))

    print()
    print("  ── B · 论证时段：结构判据 vs 字样判据 ──")
    by_type = [r for r in arc if r.get("ev_type") in OVERTURN_TYPES]
    by_word = [r for r in arc if WORDY.search((r.get("subject", "") or "") + (r.get("detail", "") or ""))]
    print("     ★ 结构判据（ev_type ∈ %s）= %d / %d = %.0f%%"
          % ("/".join(sorted(OVERTURN_TYPES)), len(by_type), len(arc), 100.0*len(by_type)/max(1,len(arc))))
    print("     ○ 字样判据（轮 7–9 报过）   = %d / %d = %.0f%%"
          % (len(by_word), len(arc), 100.0*len(by_word)/max(1,len(arc))))
    print()
    print("     ── 结构判为『推翻』的条目 ──")
    for r in by_type:
        print("       %s  %-12s %s" % (str(r.get("ts",""))[:19], r.get("ev_type"), str(r.get("subject",""))[:56]))
    print()
    only_word = [r for r in by_word if r not in by_type]
    print("     ── ★ 只被『字样』判为推翻、而【结构字段】未判的 %d 条（＝疑被污染的）──" % len(only_word))
    for r in only_word:
        print("       %s  %-12s %s" % (str(r.get("ts",""))[:19], r.get("ev_type"), str(r.get("subject",""))[:56]))

    print()
    print("  ═══ 判定 ═══")
    # ★ 2026-10-02 轮 11 撤稿：本器原本在此打印「字样判据多算 N 条 ⇒ 推翻率被高估」。
    #   而轮 11 的【逐条手判】证明那句话是错的（手判 62%–77% ⇒ 原报的 54–57% 其实偏低）。
    #   ⇒ 本器【不再下"高估/低估"的判词】：它只报两个计数与差异，
    #     并指向【手判表】；因为"哪个判据更接近真值"不是字符串或字段能答的。
    gap = len(by_word) - len(by_type)
    print("     字样计数 = %d ｜ 结构计数 = %d ｜ 差 = %d" % (len(by_word), len(by_type), gap))
    print("     ★ 本器【不下「哪个更接近真值」的判词】——轮 11 已证明这两个判据错向相反：")
    print("        字样会【高估】（把「叙述推翻」算成推翻）；字段会【低估】（本席归类不一致）。")
    print("     ★ 要接近真值：【逐条读】。见 outbox\\自指性论证十一…（含 18 行逐条判词，可逐格推翻）。")
    print("     ★ 手判结果：严格 62%（8/13）｜宽松 77%（10/13）⇒ 原报 54–57% 偏低；轮 10 的 12% 更偏低。")
    print("     ★ 本器局限：`ev_type` 也是本席填的 ⇒ 它仍是【自陈】；且本席 ledger 里有 58 个一次性 "
          "ev_type ⇒ 该字段【几乎不成其为结构】。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
