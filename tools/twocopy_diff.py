#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只读比较两处副本；不触网、不移动、不删除。
r"""twocopy_diff.py —— 判定两处席位副本是【字节相同的重复】还是【内容不同的两半】。 v1.0.0

为什么需要它
──────────────
我的席位在桌面出现两份：根上 `A2A新席_石敢当Cairn_20260928\`，与
`_整理_各席交付\石敢当席\A2A新席_石敢当Cairn_20260928\`（守藏席 2026-10-02 归类所致）。

"该保留哪一份"这一问，**取决于两份的关系**：
   · 若【按内容同源】⇒ 定正本只需【声明】，不必搬动（零风险）；
   · 若【各含对方没有的件】⇒ 搬动不可避免，且必须先逐件对账。
故本器**先给出这个判定**，再谈处置。

判据（三层，逐层加严）
────────────────────────
  L1 件数            —— 粗
  L2 相对路径集合     —— 中
  L3 逐件 sha256      —— ★ 只有它算"相同"

用法: twocopy_diff.py [--a <目录A>] [--b <目录B>]
"""
from __future__ import annotations
import argparse
import hashlib
import pathlib
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

DESK = pathlib.Path("C:/Users/欧阳宏俊/OneDrive/桌面")
DEFAULT_A = DESK / "A2A新席_石敢当Cairn_20260928"
DEFAULT_B = DESK / "_整理_各席交付" / "石敢当席" / "A2A新席_石敢当Cairn_20260928"


def sha(p: pathlib.Path) -> str | None:
    try:
        h = hashlib.sha256()
        with p.open("rb") as f:
            for c in iter(lambda: f.read(1 << 20), b""):
                h.update(c)
        return h.hexdigest()
    except Exception:
        return None


def index(root: pathlib.Path) -> dict[str, pathlib.Path]:
    d = {}
    if root.is_dir():
        for p in root.rglob("*"):
            if p.is_file():
                d[p.relative_to(root).as_posix()] = p
    return d


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", default=str(DEFAULT_A))
    ap.add_argument("--b", default=str(DEFAULT_B))
    a = ap.parse_args()
    A, B = pathlib.Path(a.a), pathlib.Path(a.b)

    print("═══ 两份席位副本对照（只读）═══")
    for tag, r in (("A 根上", A), ("B 整理夹", B)):
        print("  %s = %s" % (tag, r))
    ia, ib = index(A), index(B)
    print("\n  L1 件数： A=%d ／ B=%d" % (len(ia), len(ib)))

    ka, kb = set(ia), set(ib)
    only_a, only_b, both = sorted(ka - kb), sorted(kb - ka), sorted(ka & kb)
    print("  L2 只在 A = %d ｜ 只在 B = %d ｜ 两处都有 = %d" % (len(only_a), len(only_b), len(both)))

    same = diff = 0
    diff_list, unreadable = [], []
    for k in both:
        ha, hb = sha(ia[k]), sha(ib[k])
        if ha is None or hb is None:
            unreadable.append(k); continue
        if ha == hb:
            same += 1
        else:
            diff += 1; diff_list.append(k)
    print("  L3 两处都有者：字节相同 = %d ｜ ★字节不同 = %d ｜ 读失败 = %d" % (same, diff, len(unreadable)))

    # 判定
    print("\n  ── 判定 ──")
    if diff == 0 and not only_a and not only_b:
        verdict = "完全同源（可按内容互替）⇒ ★ 定正本只需【声明】，不必搬动"
    elif diff == 0:
        verdict = "同源但各有独有件（A 独有 %d／B 独有 %d）⇒ 需【合并】而非择一" % (len(only_a), len(only_b))
    else:
        verdict = "★ 存在字节不同（%d 件）⇒ 两处均不可丢，必须先逐件对账" % diff
    print("  " + verdict)

    if only_a:
        print("\n  ── 只在 A（根上）的 %d 件，前 20 ──" % len(only_a))
        for k in only_a[:20]:
            print("     " + k)
    if only_b:
        print("\n  ── 只在 B（整理夹）的 %d 件，前 20 ──" % len(only_b))
        for k in only_b[:20]:
            print("     " + k)
    if diff_list:
        print("\n  ── 字节不同的 %d 件，前 20 ──" % len(diff_list))
        for k in diff_list[:20]:
            print("     " + k)
    return 0


if __name__ == "__main__":
    sys.exit(main())
