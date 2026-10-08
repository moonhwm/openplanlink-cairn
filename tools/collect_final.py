#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 本件只读本机件，不触网。
r"""collect_final.py —— 取【终盘】真实清单，供入口索引使用（不凭记忆）。 v1.0.0"""
from __future__ import annotations
import json
import pathlib
import sys
from collections import Counter

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

DESK = pathlib.Path(r"C:\Users\欧阳宏俊\OneDrive\桌面")
SEAT = DESK / "A2A新席_石敢当Cairn_20260928"
LED = SEAT / "ledger" / "frontier_ledger.jsonl"
INBOX = DESK / "全局声明_治理文档" / "a2a-inbox" / "cairn-dsh"

led = [json.loads(l) for l in LED.read_text(encoding="utf-8").splitlines() if l.strip()]
types = Counter(e.get("ev_type", "?") for e in led)
mine = sorted(p for p in DESK.glob("【石敢当席呈机主】*") if p.is_file())
ob = [p for p in (SEAT / "outbox").glob("*") if p.is_file()]
px = [p for p in SEAT.rglob("*.py") if "__pycache__" not in p.parts]
mjs = [p for p in SEAT.rglob("*.mjs") if "__pycache__" not in p.parts]
inbox = [p for p in INBOX.glob("*") if p.suffix != ".sha256"]
bom = sum(1 for p in ob if p.suffix.lower() == ".md" and p.read_bytes().startswith(b"\xef\xbb\xbf"))

print("═══ 终盘真实清单 ═══")
print("  桌面呈机主件   = %d" % len(mine))
print("  台账条目       = %d ｜ 末条时刻 = %s" % (len(led), led[-1].get("ts")))
print("  本席 outbox    = %d ｜ 投共享面 = %d（不含 .sha256）" % (len(ob), len(inbox)))
print("  器具           = .py %d ＋ .mjs %d" % (len(px), len(mjs)))
print("  outbox 中带 BOM 的 .md = %d / %d" % (bom, sum(1 for p in ob if p.suffix.lower() == ".md")))
print()
print("  ── 台账按类型（前 12）──")
for k, v in types.most_common(12):
    print("     %-22s %d" % (k, v))
print("  ── 台账类型总数 = %d ──" % len(types))
print()
specials = ("RETRO_DISCLOSURE", "CORRECTION", "TOOL_FIX", "DISCREPANCY", "TOOL_TRUST_ANOMALY")
print("  ── 自曝/更正类合计 ──")
print("     " + " ｜ ".join("%s %d" % (s, types.get(s, 0)) for s in specials))
print("     合计 = %d 条" % sum(types.get(s, 0) for s in specials))
print()
print("  ── 桌面最后 12 件（按时刻）──")
for p in mine[-12:]:
    print("     %-58s %6d B" % (p.name[:58], p.stat().st_size))
