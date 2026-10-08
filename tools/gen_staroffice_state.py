#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
gen_staroffice_state.py —— 按 Star-Office-UI 的 state schema 生成本席状态件。 v1.0.0

为什么
──────
目标要「开放为实时推演（作为后续 MicroFish 等类似开源项目的**直接 Pannel**）」。
而 Star-Office-UI（`ringhyacinth/Star-Office-UI`）的 state schema **只有四个字段**（[原件直取] state.sample.json，104 B）：
    { "state": "idle", "detail": "Waiting...", "progress": 0, "updated_at": "…" }
⇒ 故"作为直接 Pannel"最实的做法是：**把我的状态写成【它本来就读的那个形状】。**
   ★ 这样谁跑起它，本席就能出现在那间像素办公室里——**不用改它一行代码**。

★ 纪律
──────
  1. 台账数/链末/判定**调用权威工具取得**（`cairn_ledger.py verify`），不重实现链算法；
  2. 依 P5：子进程只给最小环境白名单；
  3. **只写本席 outbox**，不写任何外部对象、不写对方仓库。

用法: gen_staroffice_state.py [--out outbox/state_cairn-dsh.json]
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import os
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
LEDGER = ROOT / "ledger" / "frontier_ledger.jsonl"
TOOL = ROOT / "ledger" / "cairn_ledger.py"

# 本席窗口（【目标】里写明的"到今晚23点"）
WINDOW_START = dt.datetime(2026, 10, 1, 16, 30)
WINDOW_END = dt.datetime(2026, 10, 1, 23, 0)


def ledger_facts() -> dict:
    """调用权威工具取台账事实（不重实现）。"""
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8",
           "SYSTEMROOT": os.environ.get("SYSTEMROOT", "")}
    try:
        r = subprocess.run([sys.executable, str(TOOL), "verify"], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", env=env, timeout=120)
        out = (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return {"entries": 0, "end": "", "verdict": "调用失败"}
    entries, end, verdict = 0, "", ""
    for line in out.splitlines():
        line = line.strip()
        m = re.search(r"条目数[：:]\s*(\d+)", line)
        if m:
            entries = int(m.group(1))
        m = re.search(r"链末 hash[：:]\s*([0-9a-f]{16,})", line)
        if m:
            end = m.group(1)
        if "结论" in line:
            verdict = line.split("结论", 1)[1].lstrip("：: ")[:40]
    return {"entries": entries, "end": end, "verdict": verdict}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "outbox" / "state_cairn-dsh.json"))
    a = ap.parse_args()

    now = dt.datetime.now()
    led = ledger_facts()
    total = (WINDOW_END - WINDOW_START).total_seconds()
    done = max(0.0, min(total, (now - WINDOW_START).total_seconds()))
    progress = int(round(100.0 * done / total))

    state = {
        "state": "working" if progress < 100 else "idle",
        "detail": "石敢当席（cairn-dsh）｜台账 %d 条 ｜ 链末 %s… ｜ %s ｜ 值守中"
                  % (led["entries"], (led["end"] or "?")[:8], led["verdict"] or "?"),
        "progress": progress,
        "updated_at": now.isoformat(timespec="seconds"),
    }

    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("═══ 按 Star-Office-UI 的 schema 生成本席状态 ═══")
    print(json.dumps(state, ensure_ascii=False, indent=2))
    print()
    # ★ 自校验：字段名与类型必须与其 state.sample.json 同构
    ref = {"state": str, "detail": str, "progress": int, "updated_at": str}
    ok = set(state.keys()) == set(ref.keys()) and all(isinstance(state[k], t) for k, t in ref.items())
    print("  [校验] 字段名与类型与其 state.sample.json 同构：%s" % ("✓ 是" if ok else "★否"))
    print("  [校验] progress 在 0..100：%s" % ("✓" if 0 <= state["progress"] <= 100 else "★否"))
    print("  [OK] 已写 %s（%d B）" % (out.name, out.stat().st_size))
    print("  ★ 这一份【不改它一行代码】即可被其面板读取 ⇒ 本席即出现在那间像素办公室里。")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
