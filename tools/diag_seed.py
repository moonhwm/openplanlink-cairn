#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""diag_seed.py —— 诊断：盘上种子与现渲染为何不同（不猜，逐行量）。 v1.0.0"""
from __future__ import annotations
import hashlib
import pathlib
import re
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = pathlib.Path(__file__).resolve().parent.parent
SEED = ROOT / "outbox" / "种子_MiroFish形状_席位状态报告_cairn-dsh_20261001.md"
TS = "2026-10-01T20:55:00+08:00"
FOOT = re.compile(r"种子 digest（sha256）＝ `([0-9a-f]{64})`")
INP = re.compile(r"\|\s*([^|]*?(?:state_cairn-dsh\.json|state_history\.jsonl|frontier_ledger\.jsonl))\s*\|\s*`([0-9a-f]+)`")


def main() -> int:
    on_disk = SEED.read_text(encoding="utf-8")
    r = subprocess.run([sys.executable, str(ROOT / "exp" / "seed_render.py"), "--ts", TS],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    now = r.stdout
    print("  盘上 %d 字节 ｜ 现渲染 %d 字节" % (len(on_disk.encode()), len(now.encode())))
    a, b = on_disk.splitlines(), now.splitlines()
    print("  行数 %d vs %d" % (len(a), len(b)))
    for i in range(min(len(a), len(b))):
        if a[i] != b[i]:
            print("  ★首个不同在第 %d 行：" % (i + 1))
            print("     盘上：" + a[i][:110])
            print("     现在：" + b[i][:110])
            break
    else:
        print("  ⇒ 共有部分全同；差异只在行数（%d vs %d）" % (len(a), len(b)))
    for tag, t in (("盘上", on_disk), ("现在", now)):
        m = FOOT.search(t)
        print("  %s 页脚 digest = %s" % (tag, m.group(1)[:24] if m else "无"))
    for tag, t in (("盘上", on_disk), ("现在", now)):
        g = {k.strip()[:20]: v[:12] for k, v in INP.findall(t)}
        print("  %s 输入摘要：%s" % (tag, g))
    # 各输入件【当下】的真实摘要
    print("  ── 输入件当下真实摘要 ──")
    for p in (ROOT / "outbox" / "state_cairn-dsh.json", ROOT / "outbox" / "state_history.jsonl",
              ROOT / "ledger" / "frontier_ledger.jsonl"):
        if p.is_file():
            print("     %-28s %s" % (p.name, hashlib.sha256(p.read_bytes()).hexdigest()[:12]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
