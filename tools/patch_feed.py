#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""patch_feed.py —— 修正 feed_to_deduce.py 的校验段（v1.0.0 → v1.1.0）。 v1.0.0

为何修（承本轮实测）：
  v1.0.0 的第三项校验写成「净增 3 <10 ⇒ 不触发 BUS_SURGE」，**结果 FAIL**。
  查因：其 `_rule_bus_surge` 取 `prev = state.get(key, 0)` ⇒ **首次观测是与初始 0 比**，
        故首条 bus_rows(rows=127) 得 127-0 ≥10 ⇒ 触发。
  ⇒ **错的是本席的预期**（本席按 127→130 想，忘了初始态）；
  ⇒ **但同时暴露其规则一处真毛病：新 src 的首次读数 ≥10 即【冷启动误报涌流】**。
  v1.1.0 把二者分开测：首条【应】触发（记冷启动）、次条【应】不触发（记净增）、
  并单列冷启动为发现项。
"""
from __future__ import annotations
import pathlib
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

P = pathlib.Path(__file__).resolve().parent / "feed_to_deduce.py"

OLD = '''    checks = [
        ("费用 0 元【不】触发 COST_ALERT（其规则要求 c>0）", "COST_ALERT" not in types),
        ("净增 %d <10 ⇒ 不触发 BUS_SURGE" % 3, "BUS_SURGE" not in types),
        ("心跳转死 ⇒ 触发 SEAT_OFFLINE（证明规则确实会响）", "SEAT_OFFLINE" in types),
        ("链自洽（其 D3）", core.chain.verify() is True),
    ]'''

NEW = '''    surge_ts = [ts for ts, t, _ in fired if t == "BUS_SURGE"]
    # ★ v1.1.0：分开测"首条"与"次条"
    checks = [
        ("费用 0 元【不】触发 COST_ALERT（其规则要求 c>0）", "COST_ALERT" not in types),
        ("★【首条】bus_rows(0→%d) 触发 BUS_SURGE ⇒ 其规则存在【冷启动误报】" % (n_led - 3),
         surge_ts == [1002]),
        ("★【次条】bus_rows(%d→%d，净增 3<10) 【不】触发" % (n_led - 3, n_led),
         1003 not in surge_ts),
        ("心跳转死 ⇒ 触发 SEAT_OFFLINE（证明规则确实会响）", "SEAT_OFFLINE" in types),
        ("链自洽（其 D3）", core.chain.verify() is True),
    ]'''

OLD2 = '''    print("  ★ 本器能给出【符合/不符】两种结果 ⇒ 非恒真。")'''

NEW2 = '''    if surge_ts == [1002]:
        print("  ── ★ 发现（据本轮实测，且本席已自查预期之误）──")
        print("     其 `_rule_bus_surge` 取 prev = state.get(key, 0) ⇒ **任何新 src 的首次 bus_rows")
        print("     都是与初始 0 比** ⇒ 首次读数 ≥10 即报 BUS_SURGE ⇒ **冷启动误报**。")
        print("     ★ 最小修法（可不采纳）：首次见到该 key 时只记基线、不出结论；")
        print("       即 state.get(key) 为 None 时不比差。")
        print("     ★ 并记本席预期之误：v1.0.0 只按 127→130 想，忘了初始态 ⇒ FAIL 是【我错】在先。")
        print()
    print("  ★ 本器能给出【符合/不符】两种结果 ⇒ 非恒真。")'''

def main() -> int:
    t = P.read_text(encoding="utf-8")
    for old, new in ((OLD, NEW), (OLD2, NEW2)):
        if old not in t:
            print("[ERR] 锚点未找到"); return 1
        t = t.replace(old, new)
    t = t.replace('（本轮实测 130）', '（本轮实测）')
    t = t.replace('v1.0.0', 'v1.1.0', 1) if 'v1.1.0' not in t.split('\n')[0] else t
    P.write_text(t, encoding="utf-8")
    print("[OK] 已修正 feed_to_deduce.py（分开测首条/次条；单列冷启动误报；记本席预期之误）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
