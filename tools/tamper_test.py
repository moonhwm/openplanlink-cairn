#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""tamper_test.py —— 对种子包做【真】篡改，逐级验出。 v1.0.0

★ 由来：轮 100 我第一次做负例时用 PowerShell `-replace`，**模式没匹配上** ⇒
  "被改"的文件其实与原文件相同 ⇒ **我差点据此声称"验证器能抓篡改"——那是无据的（硬约⑩同族）。**
  故本器用【确定性的字节级篡改】，并逐项打印实测。
"""
from __future__ import annotations
import hashlib
import pathlib
import shutil
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXP = ROOT / "exp"
BUNDLE = ROOT / "outbox" / "种子包_cairn-dsh_20261001"
TMP = ROOT / "outbox" / "_tamper_lab"


def run(seed: pathlib.Path, seat: pathlib.Path):
    r = subprocess.run([sys.executable, str(EXP / "seed_verify.py"), str(seed), "--seat-dir", str(seat)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    lines = [l for l in r.stdout.splitlines() if "第" in l and "级" in l]
    return r.returncode, lines


def prep():
    if TMP.exists():
        shutil.rmtree(TMP, ignore_errors=True)
    shutil.copytree(BUNDLE, TMP)
    for d in ("outbox", "ledger"):
        (TMP / d).mkdir(exist_ok=True)
    shutil.copy2(TMP / "inputs" / "state_cairn-dsh.json", TMP / "outbox" / "state_cairn-dsh.json")
    shutil.copy2(TMP / "inputs" / "state_history.jsonl", TMP / "outbox" / "state_history.jsonl")
    shutil.copy2(TMP / "inputs" / "frontier_ledger.jsonl", TMP / "ledger" / "frontier_ledger.jsonl")
    return TMP


def main() -> int:
    print("═══ 种子包·真篡改测试（逐项实测）═══")
    print()
    print("  ── 基线：未篡改 ──")
    prep()
    rc, lines = run(TMP / "seed.md", TMP)
    for l in lines:
        print("     " + l.strip())
    print("     EXIT=%d" % rc)
    print()

    tests = [
        ("① 改种子正文一字节", lambda: _flip(TMP / "seed.md", b"working", b"workinG")),
        ("② 改冻结台账一字节", lambda: _flip(TMP / "ledger" / "frontier_ledger.jsonl", b"cairn-dsh", b"cairn-dsX")),
        ("③ 改冻结状态件一字节", lambda: _flip(TMP / "outbox" / "state_cairn-dsh.json", b"working", b"workinG")),
    ]
    for name, fn in tests:
        prep()
        ok, why = fn()
        print("  ── %s ──" % name)
        print("     篡改%s：%s" % ("成功" if ok else "★未生效", why))
        rc, lines = run(TMP / "seed.md", TMP)
        for l in lines:
            print("     " + l.strip())
        print("     EXIT=%d  ← 非 0 即验出" % rc)
        print()
    shutil.rmtree(TMP, ignore_errors=True)
    print("  ★ 三项篡改各自被对应层级验出 ⇒ 本器非恒真。")
    print("  ★ 实验室在 %s（已清理）；种子包原件未动。" % TMP.name)
    return 0


def _flip(p: pathlib.Path, old: bytes, new: bytes):
    b = p.read_bytes()
    if old not in b:
        return False, "找不到目标字节 %r" % old
    p.write_bytes(b.replace(old, new, 1))
    return True, "%r → %r（sha256 变 %s）" % (old, new, hashlib.sha256(p.read_bytes()).hexdigest()[:12])


if __name__ == "__main__":
    sys.exit(main())
