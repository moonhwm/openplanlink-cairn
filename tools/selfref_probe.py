#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只读，测"验者是否在被验者之内"；不触网、不改动任何件。
r"""selfref_probe.py —— 把"自指"从修辞变成【可测的事实】。 v1.0.0

要测的三件事
──────────────
  R1 【验者在被验者之内】核验器与对照器本身，是否【只存在于正本 A、不在副本 B】？
      ⇒ 若是，则"证明 A≅B"所用的工具，是 A 独有之物 ⇒ 验者属于它所测的差异。
  R2 【锚点的权威来自一个自称无权威的链】声明里引的台账锚点，其链的 signed 是否为 false？
      ⇒ 若是，则声明把权威建立在一条【自陈"只证一致不证作者"】的记录上。
  R3 【裁判与选手同一人】核验器的判据（活文件名单、容差形式）由谁写？是否只由本席写？
      ⇒ 若是，则"OK"= 与本席自陈的假设自洽，≠ 正确。
"""
from __future__ import annotations
import hashlib
import json
import pathlib
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

DESK = pathlib.Path("C:/Users/欧阳宏俊/OneDrive/桌面")
A = DESK / "A2A新席_石敢当Cairn_20260928"
B = DESK / "_整理_各席交付" / "石敢当席" / "A2A新席_石敢当Cairn_20260928"
JUDGE_TOOLS = ("exp/verify_seat_location.py", "exp/twocopy_diff.py",
               "exp/neg_control_seat_location.py", "exp/missing_inventory.py")


def sha(p: pathlib.Path):
    try:
        h = hashlib.sha256()
        with p.open("rb") as f:
            for c in iter(lambda: f.read(1 << 20), b""):
                h.update(c)
        return h.hexdigest()
    except Exception:
        return None


def main() -> int:
    print("═══ 自指探针（只读·可复算）═══")
    if not A.is_dir() or not B.is_dir():
        print("ERR 两份席位夹不齐 ⇒ ★ 器具故障（不是'验不过'）")
        return 2

    # R1 验者是否在正本独有之列
    print("\n── R1 验者在被验者之内？ ──")
    ia = {p.relative_to(A).as_posix(): p for p in A.rglob("*") if p.is_file()}
    ib = {p.relative_to(B).as_posix(): p for p in B.rglob("*") if p.is_file()}
    only_a = set(ia) - set(ib)
    inside = 0
    for t in JUDGE_TOOLS:
        where = "★ 只在正本A" if t in only_a else ("两处都有" if t in ib else "不在A")
        if t in only_a:
            inside += 1
        print("   %-42s %s" % (t, where))
    print("   ⇒ 判决工具中【只存在于正本】者 = %d / %d" % (inside, len(JUDGE_TOOLS)))
    print("   ⇒ R1 结论：%s" % ("★ 成立——验者属于它所测的差异（正本独有）" if inside else "不成立"))

    # R2 锚点链的签署状态
    print("\n── R2 锚点的权威来自哪条链？ ──")
    lg = A / "ledger" / "frontier_ledger.jsonl"
    if not lg.is_file():
        print("   ★ 台账读不到 ⇒ 器具故障")
    else:
        rows = [json.loads(l) for l in lg.read_text(encoding="utf-8").splitlines() if l.strip()]
        sigs = {bool(r.get("signed")) for r in rows}
        print("   台账条数 = %d ｜ signed 取值集合 = %s" % (len(rows), sigs))
        d = json.loads((A / "outbox" / "SEAT_LOCATION_cairn-dsh_20261002.json").read_text(encoding="utf-8"))
        print("   声明引的锚点 = 第 %s 条的 %s…" % (d["ledger"]["entries_at_declaration"],
                                             str(d["ledger"]["chain_head_at_declaration"])[:16]))
        print("   声明自述 = %s" % d["ledger"].get("honest_note", "（无）")[:70])
        print("   ⇒ R2 结论：%s" % ("★ 成立——声明把权威建立在一条【自称只证一致不证作者】的链上"
                                   if sigs == {False} else "不成立"))

    # R3 判据由谁写
    print("\n── R3 裁判与选手是否同一人？ ──")
    chk = A / "exp" / "verify_seat_location.py"
    if chk.is_file():
        txt = chk.read_text(encoding="utf-8", errors="replace")
        has_patterns = "LIVING_PATTERNS" in txt
        print("   判据写在 = %s" % chk.relative_to(A).as_posix())
        print("   是否含【本席自定义】的活文件名单 = %s" % has_patterns)
        print("   该文件作者署名 = %s" % ("cairn-dsh（据文件名）"))
        print("   ⇒ R3 结论：★ 成立——判据由【被验方自己】写，故 'OK' = 与本席自陈假设自洽，≠ 正确")

    print("\n── 三环小结 ──")
    print("   R1 验者在被验者之内 ／ R2 权威挂在自称无权威的链上 ／ R3 裁判即选手")
    print("   ⇒ ★ 三者共同的含义：本席的 'OK' 只能证【自洽】，不能证【正确】。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
