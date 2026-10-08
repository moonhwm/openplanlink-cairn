#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
test_deduce_core.py —— 对沈铎 `deduce_core.py` 做【它自己没做的那几项】测试。 v1.0.0

被测对象（[原件直取]，桌面 `deduce_core.py`，8,174 B，19:09）：
    其自陈 D1 确定性 / D2 幂等 / D3 完整性 / D4 实时性；MicroFish JSONL 契约。
    ★ 本席读其源码确认：只 import hashlib/json/sys/statistics；无网络、无子进程、无文件写、无凭据 ⇒ 可安全导入。

★ 本器补测的四处（**其自带 selftest 未覆盖**）
──────────────────────────────────────────────
  T1 **跨进程确定性**：其 selftest 在同一进程内建两个核对比；**未测 `PYTHONHASHSEED` 变化下是否仍同输出**。
      本器**用不同 PYTHONHASHSEED 起两个子进程**，各跑同一事件流，**逐字节比【结论＋摘要链】**。
  T2 **D1 的加强版**：其 selftest 只比 `conclusion`，**不比 `digest`**；本器把摘要链一并比。
  T3 **D2 的作用域**：其幂等键＝`sha3(canon(整个事件))` ⇒ 本器**试"语义同、ts 不同"的重复事件**，
      看是否被去重 ⇒ **如实报其幂等是【逐字节级】而非【语义级】**。
  T4 **D3 篡改可检**：验链真 → 改一条 → 验链假 → 还原 → 再验真。

★ 本器**不改被测文件一个字节**；只在临时目录运行其代码（**导入其模块**）。
用法: test_deduce_core.py [--elsewhere 路径]
"""
from __future__ import annotations
import argparse
import json
import os
import pathlib
import subprocess
import sys
import tempfile

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

EVENTS = [
    {"ts": 1000, "src": "qburn", "kind": "cost", "payload": {"cost_yuan": 1.5}},
    {"ts": 1010, "src": "qburn", "kind": "cost", "payload": {"cost_yuan": 2.5}},
    {"ts": 1020, "src": "bus", "kind": "bus_rows", "payload": {"rows": 7890}},
    {"ts": 1030, "src": "bus", "kind": "bus_rows", "payload": {"rows": 7905}},
    {"ts": 1040, "src": "bridge", "kind": "heartbeat", "payload": {"seat": "Moon", "alive": False}},
    {"ts": 1050, "src": "bridge", "kind": "heartbeat", "payload": {"seat": "Moon", "alive": False}},
]

RUNNER = r'''
import json, sys, hashlib
sys.path.insert(0, sys.argv[1])
import deduce_core as dc
core = dc.DeduceCore()
events = json.loads(sys.argv[2])
for ev in events:
    core.ingest(ev, t_render_ms=ev["ts"] + 5)
out = {
  "conclusions": [c["conclusion"] for c in core.conclusions],
  "digests": [c["digest"] for c in core.conclusions],
  "chain_verify": core.chain.verify(),
  "p95": core.p95_latency(),
}
print(json.dumps(out, ensure_ascii=False, sort_keys=True))
'''


def run_in_proc(module_dir: str, events, hashseed: str) -> dict:
    """★ 在【独立子进程】里跑，并显式设定 PYTHONHASHSEED。依 P5：只给最小环境白名单。"""
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8",
           "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""), "PYTHONHASHSEED": hashseed}
    r = subprocess.run([sys.executable, "-c", RUNNER, module_dir, json.dumps(events, ensure_ascii=False)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, timeout=180)
    if r.returncode != 0:
        raise RuntimeError("子进程失败：%s" % ((r.stderr or r.stdout or "")[-300:]))
    return json.loads(r.stdout.strip().splitlines()[-1])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--elsewhere", default=r"C:\Users\欧阳宏俊\OneDrive\桌面")
    a = ap.parse_args()
    d = pathlib.Path(a.elsewhere)
    if not (d / "deduce_core.py").is_file():
        print("[ERR] 未找到 deduce_core.py 于 %s" % d); return 2
    print("═══ 测 deduce_core.py（补其自检未覆盖处）═══")
    print("  对象 = %s" % (d / "deduce_core.py"))
    print()

    ok = True
    # ── T1 跨进程确定性（不同 PYTHONHASHSEED）──
    r1 = run_in_proc(str(d), EVENTS, "0")
    r2 = run_in_proc(str(d), EVENTS, "12345")
    same_conc = r1["conclusions"] == r2["conclusions"]
    same_dig = r1["digests"] == r2["digests"]
    print("  T1 跨进程确定性（PYTHONHASHSEED 0 vs 12345）")
    print("     结论一致：%s ｜ 摘要链一致：%s" % ("✓" if same_conc else "★否", "✓" if same_dig else "★否"))
    if not (same_conc and same_dig):
        ok = False
        print("     ★ 结论：其【跨进程确定性不成立】——同一事件流在不同 HASHSEED 下产物不同")
    else:
        print("     ⇒ 结论：**跨进程亦确定**（比其自检更强的一条，已通过）")
    print()

    # ── T2 摘要链一并比（其自检只比 conclusion）──
    print("  T2 D1 加强版：摘要链是否同序同值（其自检未比 digest）")
    print("     本席两次独立进程的 digest 序列相同：%s" % ("✓" if same_dig else "★否"))
    print("     ⇒ 其摘要链【可复算】；此为其 selftest 未断言、本器补上的一条。")
    print()

    # ── T3 D2 的作用域：语义同、ts 不同 ──
    dup_events = EVENTS + [dict(EVENTS[0], ts=9999)]   # 同 kind/src/payload，仅 ts 不同
    r3 = run_in_proc(str(d), dup_events, "0")
    grew = len(r3["conclusions"]) - len(r1["conclusions"])
    print("  T3 D2 的作用域（幂等键＝sha3(canon(整个事件)))")
    print("     事件数 %d → %d（追加一条「语义同、ts 不同」）" % (len(EVENTS), len(dup_events)))
    print("     新增结论数 = %d" % grew)
    if grew > 0:
        print("     ⇒ ★ 其幂等是【逐字节级】而非【语义级】：改一个 ts 即视为新事件（如实报，不褒不贬）")
    else:
        print("     ⇒ 语义重复亦被去重（本席预期落空，如实记）")
    print()

    # ── T4 D3 篡改可检（在同进程内做，需拿到对象）──
    sys.path.insert(0, str(d))
    import importlib
    import deduce_core as dc  # noqa: E402
    importlib.reload(dc)
    c = dc.DeduceCore()
    for ev in EVENTS:
        c.ingest(ev)
    v_ok = c.chain.verify()
    if c.chain.chain:
        orig = json.loads(json.dumps(c.chain.chain[0]["conclusion"]))
        c.chain.chain[0]["conclusion"]["__tamper__"] = 1
        v_bad = c.chain.verify()
        c.chain.chain[0]["conclusion"] = orig
        v_restore = c.chain.verify()
    else:
        v_ok = v_bad = v_restore = None
    print("  T4 D3 篡改可检")
    print("     原链验真：%s ｜ 改一条后验假：%s ｜ 还原后验真：%s"
          % ("✓" if v_ok else "★否", "✓" if v_bad is False else "★否", "✓" if v_restore else "★否"))
    if not (v_ok and v_bad is False and v_restore):
        ok = False
    print()

    print("[结论] 补测四项：%s" % ("全过" if ok else "★有未过项（见上）"))
    print("★ 本器能返回【过】与【不过】两种结果 ⇒ 非恒真。")
    print("★ 本席未改动被测文件一个字节。")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
