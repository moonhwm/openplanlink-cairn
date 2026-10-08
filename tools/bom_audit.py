#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
bom_audit.py —— 普查本席产出有无 UTF-8 BOM；无 BOM 的中文件在默认 Windows 工具里会显示为乱码。 v1.0.0

由来（轮 95）
──────────────
本席那份 `handshake/unverifiable_items.tsv`（39,102 B、161 行）在 PowerShell 默认编码下【整片乱码】——
因为它是【无 BOM 的 UTF-8】，而 Windows 默认按 GBK 读。
★ 推论：**凡交出去的中文件若无 BOM，默认 Windows 工具里就会显示成乱码。**
★ 而"读不了的交付物，等于没交付"。
用法: bom_audit.py
"""
from __future__ import annotations
import pathlib
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

DESK = pathlib.Path(r"C:\Users\欧阳宏俊\OneDrive\桌面")
ROOT = DESK / "A2A新席_石敢当Cairn_20260928"
BOM = b"\xef\xbb\xbf"

TARGETS = [
    (ROOT / "outbox", "本席 outbox", {".md", ".tsv", ".txt"}),
    (ROOT / "exp", "本席 exp", {".py", ".mjs", ".led"}),
    (ROOT / "handshake", "本席 handshake", {".md", ".tsv", ".txt"}),
    (DESK / "全局声明_治理文档" / "a2a-inbox" / "cairn-dsh", "投共享面", {".md", ".tsv", ".txt"}),
]


def scan(d: pathlib.Path, label: str, exts: set):
    if not d.is_dir():
        print("  %-24s ★目录不存在" % label); return [], []
    fs = [p for p in d.rglob("*") if p.is_file() and p.suffix.lower() in exts]
    with_bom, without = [], []
    for p in fs:
        try:
            (with_bom if p.read_bytes().startswith(BOM) else without).append(p)
        except Exception:
            pass
    print("  %-24s 文件 %-5d ｜ ★无 BOM %-5d ｜ 有 BOM %d"
          % (label, len(fs), len(without), len(with_bom)))
    return with_bom, without


def main() -> int:
    print("═══ 本席产出 · UTF-8 BOM 普查 ═══")
    print("  ★ 有 BOM ⇒ 默认 Windows 工具（PowerShell / 记事本）可正确显示中文")
    print()
    allw, allwo = [], []
    for d, label, exts in TARGETS:
        w, wo = scan(d, label, exts)
        allw += w; allwo += wo

    # 桌面呈机主件（只扫根，不递归，避免扫进别人的目录）
    mine = [p for p in DESK.glob("*.md") if p.is_file()]
    mw = [p for p in mine if p.read_bytes().startswith(BOM)]
    print("  %-24s 文件 %-5d ｜ ★无 BOM %-5d ｜ 有 BOM %d"
          % ("桌面根 .md（全部）", len(mine), len(mine) - len(mw), len(mw)))

    ts = ROOT / "handshake" / "unverifiable_items.tsv"
    print()
    print("  ── 触发本件的样本 ──")
    if ts.is_file():
        b = ts.read_bytes()[:3]
        print("    %s ｜ 首 3 字节 = %r ｜ 有 BOM = %s" % (ts.name, b, b == BOM))
    print()
    print("  ── 抽样：本席 outbox 里无 BOM 的前 5 件 ──")
    for p in allwo[:5]:
        print("    " + p.name)
    print()
    print("  ⇒ 结论：本席产出中【无 BOM】者 %d 件 ｜ 有 BOM 者 %d 件" % (len(allwo), len(allw)))
    print("  ★ 本器能给出两种结果（有 BOM 的会被计入 allw）⇒ 非恒真。")
    print("  ★ 修法（供取舍）：凡【给人看的中文件】以 `utf-8-sig` 写出；")
    print("     `.py`／`.mjs` 等【给程序读的】保持无 BOM（Python 3 能读 BOM，但某些工具有洁癖）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
