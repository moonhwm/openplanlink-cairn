#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""collect_inventory.py —— 取今晚产出的【真实清单】，供入口索引使用（不凭记忆）。 v1.0.0"""
from __future__ import annotations
import json
import pathlib
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

DESK = pathlib.Path(r"C:\Users\欧阳宏俊\OneDrive\桌面")
ROOT = DESK / "A2A新席_石敢当Cairn_20260928"
LEDGER = ROOT / "ledger" / "frontier_ledger.jsonl"


def main() -> int:
    print("═══ 今晚产出真实清单 ═══")
    # ① 桌面呈机主件
    mine = sorted([p for p in DESK.glob("【石敢当席呈机主】*") if p.is_file()],
                  key=lambda p: p.stat().st_mtime)
    print("\n① 桌面【石敢当席呈机主】件 = %d 件（按时刻）" % len(mine))
    for p in mine[-12:]:
        print("   %s ｜ %6d B ｜ %s" % (p.name[:64], p.stat().st_size,
                                       __import__("datetime").datetime.fromtimestamp(p.stat().st_mtime).strftime("%H:%M")))

    # ② 台账条目按 ev_type 计数
    types, last_ts = {}, ""
    n = 0
    with LEDGER.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            e = json.loads(line)
            n += 1
            types[e.get("ev_type", "?")] = types.get(e.get("ev_type", "?"), 0) + 1
            last_ts = e.get("ts", last_ts)
    print("\n② 台账 = %d 条 ｜ 按类型：%s" % (n, ", ".join("%s %d" % kv for kv in sorted(types.items(), key=lambda x: -x[1]))))
    print("   末条时刻 = %s" % last_ts)

    # ③ outbox 与共享面
    ob = [p for p in (ROOT / "outbox").glob("*") if p.is_file()]
    inbox = [p for p in (DESK / "全局声明_治理文档" / "a2a-inbox" / "cairn-dsh").glob("*") if p.suffix != ".sha256"]
    print("\n③ 本席 outbox = %d 件 ｜ 投共享面 = %d 件（不含 .sha256）" % (len(ob), len(inbox)))

    # ④ 工具件
    tools = sorted(p.name for p in (ROOT / "exp").glob("*.py")) + \
            sorted(p.name for p in (ROOT / "exp").glob("*.mjs"))
    print("\n④ 器具 = %d 件" % len(tools))
    for t in tools:
        print("   " + t)
    return 0


if __name__ == "__main__":
    sys.exit(main())
