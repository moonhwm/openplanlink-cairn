#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只读全盘扫描；不触网、不删改任何件。
r"""lost_probe.py —— 核【丢失的件是否被搬到了别处】：全用户目录按名找 + 按 sha256 定论。 v1.0.0

背景
──────
盘面被动过（共享面主体 140 件消失、旁证仍在），而回收站里【一件都没有】⇒
  可能是 (a) 被永久删除，或 (b) 被搬到了别处。**本器只回答 (b) 是否为真。**

做法
──────
1. 从共享面的 `.sha256` 旁证里取【缺件的应有 sha256】（旁证全在 ⇒ 清单可枚举）；
2. 在给定的若干根目录下【按文件名】先找（便宜）；
3. 对命中者算 sha256 —— **只有字节相同才算找回**；
4. 另对全部候选做一次【按内容】的反查（可选 --deep）。

用法
──────
  python lost_probe.py --roots C:\Users\欧阳宏俊          # 按名找 + 字节核
  python lost_probe.py --roots C:\Users\欧阳宏俊 --deep   # 另加内容反查
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

DESK = pathlib.Path(__file__).resolve().parent.parent.parent
INBOX = DESK / "全局声明_治理文档" / "a2a-inbox" / "cairn-dsh"
SKIP = ("__pycache__", ".venv", "node_modules", ".git", "site-packages")


def sha(p: pathlib.Path) -> str | None:
    try:
        h = hashlib.sha256()
        with p.open("rb") as f:
            for c in iter(lambda: f.read(1 << 20), b""):
                h.update(c)
        return h.hexdigest()
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--roots", nargs="+", required=True)
    ap.add_argument("--deep", action="store_true")
    a = ap.parse_args()

    # 1) 缺件与应有 sha256
    if not INBOX.is_dir():
        print("ERR 共享面不在：%s" % INBOX); return 2
    miss = {}
    for s in sorted(INBOX.glob("*.sha256")):
        t = s.with_name(s.name[:-7])
        if t.is_file():
            continue
        txt = s.read_text(encoding="utf-8", errors="replace").split()
        if txt:
            miss[t.name] = (txt[0].lower(), t.stat().st_size if t.exists() else None)
    print("═══ 丢失探针（只读）═══")
    print("  缺件（凭旁证）= %d" % len(miss))

    names = {n.lower(): n for n in miss}
    hit_by_name, hit_by_hash = {}, {}
    scanned = 0
    for r in a.roots:
        root = pathlib.Path(r)
        if not root.is_dir():
            print("  （跳过，不存在）%s" % r); continue
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            sp = str(p)
            if any(k in sp for k in SKIP):
                continue
            scanned += 1
            if p.name.lower() in names:
                h = sha(p)
                if h and h == miss[names[p.name.lower()]][0]:
                    hit_by_name.setdefault(names[p.name.lower()], []).append(p)
    print("  扫过文件 = %d" % scanned)
    print("  ★ 按名命中且【字节相同】= %d / %d" % (len(hit_by_name), len(miss)))

    if a.deep:
        want = {v[0]: k for k, v in miss.items()}
        found = 0
        for r in a.roots:
            root = pathlib.Path(r)
            if not root.is_dir():
                continue
            for p in root.rglob("*"):
                if not p.is_file():
                    continue
                if any(k in str(p) for k in SKIP):
                    continue
                h = sha(p)
                if h in want:
                    found += 1
                    hit_by_hash.setdefault(want[h], []).append(p)
        print("  ★ 按内容反查命中 = %d / %d" % (len(hit_by_hash), len(miss)))

    still = [n for n in miss if n not in hit_by_name and n not in hit_by_hash]
    print("  ★ 仍无字节相同者 = %d" % len(still))
    print()
    print("  ── 找回来源（前 15）──")
    merged = {**hit_by_hash}
    for k, v in hit_by_name.items():
        merged.setdefault(k, v)
    for k, v in list(merged.items())[:15]:
        print("     %s" % k[:60])
        print("         → %s" % str(v[0])[-100:])
    if still:
        print()
        print("  ── 仍找不到的（前 15）──")
        for n in still[:15]:
            print("     " + n[:80])
    return 0


if __name__ == "__main__":
    sys.exit(main())
