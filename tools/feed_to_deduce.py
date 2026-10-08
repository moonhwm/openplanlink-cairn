#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
feed_to_deduce.py —— 把本席的真实状态写成【其 MicroFish 接入契约】的事件，喂进其推演核。 v1.1.0

为什么
──────
74号令 §二 记生态真实数据面为：Supabase `a2a_signals`/`a2a_questions`/`a2a_runs`/`a2a_swarm_runs`、
Tushare 本地库、Neon 决议库、L0 总线 `cross_mode_channel`。
而沈铎 `deduce_core.py` 的 **MicroFish 接入契约**是：
    任何开源项目以 JSONL 追加事件 `{ts, src, kind, payload}` 即可被推演。
其内置三条规则认得三种 `kind`：`cost`（费用）／`bus_rows`（总线行数）／`heartbeat`（席位心跳）。

⇒ **故"作为直接 Pannel"最实的验证是：把本席的真实状态写成这三种事件，喂进去，看它出不出结论。**
   ★ 全程本机、零网络、零凭据、不改其代码一个字节。

本席真实数据来源
────────────────
· 台账条数（本轮实测）⇒ 作 `bus_rows` 的 rows
· 本席花费 ⇒ **0 元**（今晚未点任何火）⇒ 作 `cost` 的 cost_yuan
· 本席心跳 ⇒ 活 ⇒ 作 `heartbeat` 的 alive

用法: feed_to_deduce.py [--deduce 路径] [--entries N]
"""
from __future__ import annotations
import argparse
import json
import pathlib
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = pathlib.Path(__file__).resolve().parent.parent
LEDGER = ROOT / "ledger" / "frontier_ledger.jsonl"


def ledger_entries() -> int:
    try:
        n = 0
        with LEDGER.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    n += 1
        return n
    except Exception:
        return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deduce", default=r"C:\Users\欧阳宏俊\OneDrive\桌面")
    ap.add_argument("--entries", type=int, default=0)
    a = ap.parse_args()
    d = pathlib.Path(a.deduce)
    if not (d / "deduce_core.py").is_file():
        print("[ERR] 未找到 deduce_core.py"); return 2
    sys.path.insert(0, str(d))
    import deduce_core as dc

    n_led = a.entries or ledger_entries()
    print("═══ 本席状态 → 其 MicroFish 接入契约 → 其推演核 ═══")
    print("  推演核 = %s" % (d / "deduce_core.py"))
    print("  本席实测：台账 %d 条 ｜ 花费 ¥0.00（今晚未点火）｜ 心跳 活" % n_led)
    print()

    # ── 构造事件（★ 只用其三种已知 kind，字段名照其规则读法）──
    events = [
        # ① 席位心跳：本席在册且活
        {"ts": 1000, "src": "cairn-dsh", "kind": "heartbeat",
         "payload": {"seat": "cairn-dsh", "alive": True}},
        # ② 费用：本席花费 0 元（⇒ 其规则要求 c>0 才出结论 ⇒ 应【不】出结论，这是诚实的地方）
        {"ts": 1001, "src": "cairn-dsh", "kind": "cost",
         "payload": {"cost_yuan": 0.0}},
        # ③ 总线行数：以本席台账条数为读数（先给基线，再给终值；净增 <10 ⇒ 应不出涌流）
        {"ts": 1002, "src": "cairn-dsh-ledger", "kind": "bus_rows",
         "payload": {"rows": max(0, n_led - 3)}},
        {"ts": 1003, "src": "cairn-dsh-ledger", "kind": "bus_rows",
         "payload": {"rows": n_led}},
        # ④ 心跳转死：用于验证其 SEAT_OFFLINE 规则确实会响（对照）
        {"ts": 1004, "src": "cairn-dsh", "kind": "heartbeat",
         "payload": {"seat": "cairn-dsh", "alive": False}},
    ]
    print("  ── 喂入的事件（其契约形状 {ts, src, kind, payload}）──")
    for e in events:
        print("     " + json.dumps(e, ensure_ascii=False))
    print()

    core = dc.DeduceCore()
    fired = []
    for e in events:
        out = core.ingest(e, t_render_ms=e["ts"] + 5)
        for entry in out:
            fired.append((e["ts"], entry["conclusion"]["type"], entry["conclusion"]))
    print("  ── 其推演核产出的结论 ──")
    if not fired:
        print("     （无）")
    for ts, typ, c in fired:
        print("     t=%s ｜ %-12s ｜ %s" % (ts, typ, json.dumps(c, ensure_ascii=False)))

    types = [t for _, t, _ in fired]
    print()
    # ── 校验（本器须能给出"符合预期"与"不符预期"两种结果）──
    surge_ts = [ts for ts, t, _ in fired if t == "BUS_SURGE"]
    # ★ v1.1.0：分开测"首条"与"次条"
    checks = [
        ("费用 0 元【不】触发 COST_ALERT（其规则要求 c>0）", "COST_ALERT" not in types),
        ("★【首条】bus_rows(0→%d) 触发 BUS_SURGE ⇒ 其规则存在【冷启动误报】" % (n_led - 3),
         surge_ts == [1002]),
        ("★【次条】bus_rows(%d→%d，净增 3<10) 【不】触发" % (n_led - 3, n_led),
         1003 not in surge_ts),
        ("心跳转死 ⇒ 触发 SEAT_OFFLINE（证明规则确实会响）", "SEAT_OFFLINE" in types),
        ("链自洽（其 D3）", core.chain.verify() is True),
    ]
    bad = 0
    for name, ok in checks:
        bad += 0 if ok else 1
        print("  %s %s" % ("✓" if ok else "★FAIL", name))
    print()
    # ── D2 幂等：原样重放，应零新增 ──
    before = len(core.conclusions)
    for e in events:
        core.ingest(e)
    grew = len(core.conclusions) - before
    print("  %s 原样重放零新增（其 D2）：新增 %d 条" % ("✓" if grew == 0 else "★FAIL", grew))
    bad += 0 if grew == 0 else 1
    print()
    print("  ⇒ %s" % ("全项符合预期：本席数据可被其推演核直接消费" if bad == 0 else "★有 %d 项不符（见上）" % bad))
    if surge_ts == [1002]:
        print("  ── ★ 发现（据本轮实测，且本席已自查预期之误）──")
        print("     其 `_rule_bus_surge` 取 prev = state.get(key, 0) ⇒ **任何新 src 的首次 bus_rows")
        print("     都是与初始 0 比** ⇒ 首次读数 ≥10 即报 BUS_SURGE ⇒ **冷启动误报**。")
        print("     ★ 最小修法（可不采纳）：首次见到该 key 时只记基线、不出结论；")
        print("       即 state.get(key) 为 None 时不比差。")
        print("     ★ 并记本席预期之误：v1.0.0 只按 127→130 想，忘了初始态 ⇒ FAIL 是【我错】在先。")
        print()
    print("  ★ 本器能给出【符合/不符】两种结果 ⇒ 非恒真。")
    print("  ★ 全程本机、零网络、零凭据；未改其代码一个字节。")
    print()
    print("  ★【这一演示说明了什么】本席的状态【不需要另造接口】：")
    print("     它写成 {ts,src,kind,payload} 就能进其推演核 ⇒ 即为其 §3.3 所称")
    print("     「任何 MicroFish 类开源项目以标准 JSONL 接入即可上 Panel」的那条入口。")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
