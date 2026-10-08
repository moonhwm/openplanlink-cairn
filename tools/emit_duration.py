#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 本件只读本机台账与状态历史；不触网。
r"""emit_duration.py —— 给出【不会被重复写入抬高的】运行时长指标。 v1.0.0

来由（轮150 的账）
────────────────────
轮150 我认了：起了同伴作业后成了【两个写者】⇒ `state_history.jsonl` 每分钟两行 ⇒
**我在收束件里引用的「状态历史行数」被我自己的重复写入抬高了**。

★ 而正确的收尾不是"记下它坏了"，是【换一个不会坏的指标】
     · **不同分钟数**（`t[:16]` 去重）：重复写入写的是【同一分钟】⇒ **不受影响**
     · **台账首末 `ts` 之差**：直接量运行跨度，**与任何计数无关**
  ⇒ 两者交叉核对。

三态：`一致`／`有出入`（如实列出）／`ERR`（读不到）
用法: emit_duration.py
"""
from __future__ import annotations
import json
import pathlib
import sys
from datetime import datetime

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SEAT = pathlib.Path(__file__).resolve().parent.parent
LED = SEAT / "ledger" / "frontier_ledger.jsonl"
HIST = SEAT / "outbox" / "state_history.jsonl"


def parse_ts(s: str):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def main() -> int:
    if not LED.is_file() or not HIST.is_file():
        print("ERR 读不到台账或状态历史")
        return 2

    rows = [json.loads(l) for l in LED.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]
    stamps = [parse_ts(e.get("ts", "")) for e in rows]
    stamps = [t for t in stamps if t is not None]
    if not stamps:
        print("ERR 台账里没有可解析的 ts")
        return 2
    first, last = min(stamps), max(stamps)
    span_min = (last - first).total_seconds() / 60.0

    hrows = [json.loads(l) for l in HIST.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]
    lines = len(hrows)
    minutes = sorted({r["t"][:16] for r in hrows if r.get("t")})
    hist_first, hist_last = (minutes[0], minutes[-1]) if minutes else ("", "")
    hist_span_min = len(minutes)          # ★ 不同分钟数——重复写入不改变它

    print("═══ 运行时长（两个指标交叉核对）═══")
    print("  ── 指标一：台账首末 ts 之差（直接量跨度）──")
    print("     首条 ts = %s" % first.isoformat(timespec="seconds"))
    print("     末条 ts = %s" % last.isoformat(timespec="seconds"))
    print("     跨度    = %.1f 分钟" % span_min)
    print("  ── 指标二：状态历史的【不同分钟数】（★ 不受重复写入影响）──")
    print("     总行数        = %d   ← ★ 这个数被轮150 的重复写入抬高了" % lines)
    print("     ★ 不同分钟数   = %d   ← ★ 这个数【没被抬高】（重复写入写的是同一分钟）" % hist_span_min)
    print("     历史首／末分钟 = %s ／ %s" % (hist_first, hist_last))
    print()
    print("  ── 交叉核对（★ 首跑此项【报错】——而查下去是【本器的前提错】，不是数据错）──")
    print("     首跑我拿【台账寿命】去对【心跳时长】（4399.4 vs 149）⇒ 两者本就不该相等。")
    print("     ⇒ 改为【同类相比】：心跳窗口内【写入台账的分钟数】 vs 【历史的不同分钟数】")
    h0, h1 = minutes[0], minutes[-1]
    led_in_win = sorted({t.strftime("%Y-%m-%dT%H:%M") for t in stamps
                         if h0 <= t.strftime("%Y-%m-%dT%H:%M") <= h1})
    print("     心跳窗口          = %s → %s" % (h0, h1))
    print("     窗口内写台账的分钟数 = %d" % len(led_in_win))
    print("     窗口内历史的不同分钟数 = %d" % hist_span_min)
    diff = abs(len(led_in_win) - hist_span_min)
    print("     |两者之差| = %d 分钟" % diff)
    if diff <= 3:
        print("     ⇒ ✅ 一致（两者互证：在该窗口里，两者都按分钟级在记录）")
    else:
        print("     ⇒ ★有出入 ⇒ 如实列出：说明两者的【活跃程度不同】")
        print("        （★ 这不必然是错：心跳每分钟都写，而台账只在【有件】时才加）")
    print()
    print("  ── 两个指标各表示什么（★ 说明白，免得被当成同一件事）──")
    print("     台账首末 ts 之差 = **本席台账存在了多久**（首条 2026-09-28）")
    print("     不同分钟数       = **心跳跑了多久**（首／末 19:32 → %s）" % h1[-5:])
    print("     ★ 而总行数 = %d —— 它在轮150 被重复写入抬高过，**故本器不拿它当跨度**。" % lines)
    print()
    print("  ★ 本器【不给「行数＝分钟数」的换算】——那正是轮150 出错的地方。")
    print("  ★ 本器能失败（读不到、ts 不可解析、同类相比出入过大 皆会报）⇒ 非恒真。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
