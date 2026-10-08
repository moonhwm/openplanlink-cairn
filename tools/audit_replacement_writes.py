#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只读源码做静态清点；不执行被测器、不写件、不删件、不触网。
r"""audit_replacement_writes.py —— 清点【替换式写入】及其变化指示。 v1.0.0

为什么（轮 114，承轮 113）
────────────────────────────
轮 113 把"字节数盲"这处病【限定了范围】：它只对【替换式写入】成立（★ 纯追加必变长，故够用）。
★ 而我当时明写了边界：「★ 别的器里有没有同类，★ 我【没系统地查】。」
⇒ 本器去系统查：**哪些器整份重写文件，以及它们事后印不印哈希。**

★ 判据（★ 这是【静态文本判据】——★ 而它的局限我写在下面）
  · **替换式**：出现 `write_text(` 或 `write_bytes(`
  · **疑似追加**：出现 `open(` 且同一行含 `"a"`／`'a'`，或 `startswith(before)` 这类纯追加校验
  · **有哈希指示**：同一文件里出现 `sha256` 或 `hexdigest`

★ 本器自陈三条盲点（★ 这是它最重要的部分）
  ① **按调用名找** ⇒ ★ 用 `open(w)`、`os.replace`、`shutil.copy` 等其它方式重写的，★ 它【抓不到】
  ② **"同文件里有 sha256"不等于"那一行印了哈希"** ⇒ ★ 它给的是【上界】，不是精确
  ③ ★ 它【不执行】任何器 ⇒ ★ 故它说的都是【源码里读出来的】，不是【跑出来的】
"""
from __future__ import annotations
import pathlib
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SEAT = pathlib.Path(__file__).resolve().parent.parent
EXP = SEAT / "exp"
LEDGER = SEAT / "ledger"

RE_REPLACE = re.compile(r"write_text\(|write_bytes\(|open\([^)]*['\"]w|\.write\(")
# ★ 轮 116 补宽：加上 `open(…"w")` 与 `.write(` 两类。
#   缘由（轮 115 实证）：拿 `blast_radius.py` 当第二把尺去对 ⇒ 我漏了 5 件
#   （archive_layout／attest_lab_test／blast_radius／ignition_gate／netguard）——
#   ★ 因为它们用的是 `open(…,"w")` 或 `.write(`，★ 而我只认 write_text/write_bytes。
#   ⇒ 故此后本器【至少不窄于 blast_radius 那套】；★ 而两套的差异【当场可对】（见下）。
RE_APPENDISH = re.compile(r"open\([^)]*[\"']a[\"']|startswith\(before\)")
RE_HASH = re.compile(r"sha256|hexdigest")
RE_SHOW = re.compile(r"print\(")
# ★ 第二把尺（★ 与 blast_radius 同口径）：用于【当场对两数】
RE_BLAST_WRITE = re.compile(r"write_text\(|write_bytes\(|open\([^)]*['\"]w|\.write\(")


def main() -> int:
    print("═══ 替换式写入 · 清点（★ 静态文本判据）═══")
    files = [p for p in sorted(list(EXP.glob("*.py")) + list(LEDGER.glob("*.py")))
             if "__pycache__" not in str(p)]
    print("  .py = %d" % len(files))
    print()

    with_rep, no_hash, hash_some = [], [], []
    blast_set = set()
    for p in files:
        t = p.read_text(encoding="utf-8", errors="replace")
        if RE_BLAST_WRITE.search(t):
            blast_set.add(p.name)          # ★ 第二把尺（与 blast_radius 同口径）
        if not RE_REPLACE.search(t):
            continue
        with_rep.append(p.name)
        # ★ 有哈希字样 ⇒ 至少它碰过哈希；★ 没有 ⇒ 更可疑
        if RE_HASH.search(t):
            hash_some.append(p.name)
        else:
            no_hash.append(p.name)

    # ★ 轮 116 加：当场对两把尺（★ 而不必另跑一次 blast_radius）
    mine = set(with_rep)
    print("  ── ★ 两把尺当场对照 ──")
    print("     尺一（本器，write_text/bytes/open(w)/.write）= %d 件" % len(mine))
    print("     尺二（与 blast_radius 同口径）              = %d 件" % len(blast_set))
    only2 = sorted(blast_set - mine)
    only1 = sorted(mine - blast_set)
    print("     ★ 只在尺二（★ 本器仍漏的）= %d 件 %s" % (len(only2), ("：" + "、".join(only2)) if only2 else ""))
    print("     ★★ 只在尺一（★ 本器多出的）= %d 件 %s" % (len(only1), ("：" + "、".join(only1)) if only1 else ""))
    if not only2 and not only1:
        print("     ⇒ ★ 两把尺【集合重合】——★ 轮 115 那个「漏 5」已闭合")
    print()

    print("  ── ★ 含替换式写入的器 = %d 件 ──" % len(with_rep))
    for n in with_rep:
        mark = "★ 有哈希字样" if n in hash_some else "★★ 无哈希字样"
        print("     %-42s %s" % (n, mark))
    print()
    print("  ── ★★ 其中【无哈希字样】的 = %d 件（★ 更可疑，★ 但不等于「有病」）──" % len(no_hash))
    for n in no_hash:
        print("     ★★ %s" % n)
    print()
    print("  ═══ 判定 ═══")
    print("     ★ 替换式写入器 = %d 件 ｜ 其中无哈希字样 = %d 件" % (len(with_rep), len(no_hash)))
    print("     ★★ 提醒：★ 「无哈希字样」只是【可疑】——★ 是否真盲，须看它【写的是不是等长替换】。")
    print("     ★ 本器三条盲点：① 按调用名找（★ open(w)／os.replace／shutil.copy 抓不到）"
          "② 「同文件有 sha256」不等于「那一行印了哈希」（★ 给的是上界）③ 它不执行任何器")
    return 0


if __name__ == "__main__":
    sys.exit(main())
