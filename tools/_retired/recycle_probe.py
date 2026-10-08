#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只读解析回收站元数据；不触网、不删改任何件。
r"""recycle_probe.py —— 从回收站 $I 记录反查【被删件的原始路径与删除时刻】。 v1.0.0

为什么用它
────────────
本席在收盘前发现盘面曾被动过（共享面主体 140 件消失、旁证仍在等），**成因未定**。
`$I*` 记录里存着**原始绝对路径 + 大小 + 删除时刻（FILETIME）** ⇒ 这是唯一能"事后读现场"的本地凭据。

$I 结构（Windows Vista+）
────────────────────────
  0..8   header（版本 2 时为 8 字节）
  8..16  uint64 原始大小
  16..24 uint64 删除时刻（FILETIME, UTC）
  24..28 uint32 路径长度（UTF-16 码元数，不含终止符；版本 2）
  28..   路径（UTF-16LE）
  若 24..28 为 0 ⇒ 版本 1 格式，路径在 0.. 处（本器一并兜住）

用法
──────
  python recycle_probe.py            # 汇总：按删除日期、按原始目录
  python recycle_probe.py --mine     # 只看落在本席/桌面归档/共享格里的
  python recycle_probe.py --grep 石敢当
"""
from __future__ import annotations
import argparse
import collections
import datetime
import pathlib
import struct
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

MINE_MARKS = ("石敢当Cairn", "石敢当席_2026100", "a2a-inbox", "石敢当席呈机主")
EPOCH = datetime.datetime(1601, 1, 1)


def parse_sidecar(b: bytes):
    """返回 (原始大小, 删除时刻-本地, 原始路径) 或 None。"""
    if len(b) < 28:
        return None
    try:
        size = struct.unpack("<Q", b[8:16])[0]
        ft = struct.unpack("<Q", b[16:24])[0]
        nlen = struct.unpack("<I", b[24:28])[0]
        if nlen == 0 or 28 + nlen * 2 > len(b):
            # 版本 1：路径紧跟在 8 字节头之后
            nlen = struct.unpack("<I", b[0:4])[0]
            name = b[8:8 + nlen * 2].decode("utf-16-le", errors="replace").rstrip("\x00")
        else:
            name = b[28:28 + nlen * 2].decode("utf-16-le", errors="replace").rstrip("\x00")
        when = EPOCH + datetime.timedelta(microseconds=ft // 10) + datetime.timedelta(hours=8)
        return size, when, name
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mine", action="store_true")
    ap.add_argument("--grep", default=None)
    a = ap.parse_args()

    rb = pathlib.Path("C:/$Recycle.Bin")
    print("═══ 回收站探针（只读）═══")
    print("  回收站根存在 = %s" % rb.is_dir())
    if not rb.is_dir():
        print("  ★ 读不到 ⇒ 本器【不能说】回收站里有什么。")
        return 2

    rows = []
    for sid in rb.iterdir():
        if not sid.is_dir():
            continue
        for f in sid.glob("$I*"):
            try:
                b = f.read_bytes()
            except Exception:
                continue
            r = parse_sidecar(b)
            if r:
                rows.append(r)
    print("  可解析条目 = %d" % len(rows))
    if not rows:
        print("  ★ 无可解析条目 ⇒ 可能是权限、或回收站为空。")
        return 0

    rows.sort(key=lambda r: r[1])
    print("\n  ── 按删除日期 ──")
    byday = collections.Counter(r[1].strftime("%m-%d") for r in rows)
    for d, n in sorted(byday.items()):
        print("     %s  %5d 件" % (d, n))

    sel = rows
    if a.mine:
        sel = [r for r in sel if any(m in r[2] for m in MINE_MARKS)]
    if a.grep:
        sel = [r for r in sel if a.grep in r[2]]

    print("\n  ── 命中 %d 件（最早 %s ／ 最晚 %s）──" % (
        len(sel),
        sel[0][1].strftime("%m-%d %H:%M:%S") if sel else "—",
        sel[-1][1].strftime("%m-%d %H:%M:%S") if sel else "—"))
    for size, when, name in sel[:40]:
        print("     %s  %9d B  ...%s" % (when.strftime("%m-%d %H:%M:%S"), size, name[-92:]))

    if sel:
        print("\n  ── 命中件的原始目录分布（前 12）──")
        dirs = collections.Counter(str(pathlib.PureWindowsPath(r[2]).parent) for r in sel)
        for d, n in dirs.most_common(12):
            print("     %5d  %s" % (n, d[-96:]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
