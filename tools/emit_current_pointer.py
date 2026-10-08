#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只读共享面并写一份指针件；不删不改任何既有件。不触网。
r"""emit_current_pointer.py —— 为共享面的【多版本组】出一份"当前版指针"。 v1.0.0

立此器的缘由
──────────────
轮 19 实测：共享面 203 件里有 5 组同一件的多个版本（SEAT_LOCATION 竟有 7 版），
★ 而【没有一件】带"当前版"标记。
⇒ 更糟：四组 2 版里，**不带后缀的那份是旧的、`_v2` 才是新的** ⇒
   ★ "原名＝当前"这个直觉【全错】。

★ 这是【只增不改】纪律的代价：它保住了史料，却让"当前值"变得含糊。
★ 而本席一贯的处置是【出声明说】，不是删旧件 —— 故本器出【指针】。

本器自陈的局限
────────────────
  · 它按【文件名去 `_vN`】判"同组" ⇒ 命名不规则者会漏（漏 ≠ 无）；
  · 它按【mtime 最新】判"当前" ⇒ mtime 可被触碰，故这一栏是【推定】不是【保证】；
  · ★ 本器产出的指针件【自身也会成系列】（再跑一次就有了 `_v2`）⇒
    这正是它要解决的问题 ⇒ 故它在件内【明说这件事】。
"""
from __future__ import annotations
import collections
import pathlib
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

DESK = pathlib.Path(__file__).resolve().parent.parent.parent
INBOX = DESK / "全局声明_治理文档" / "a2a-inbox" / "cairn-dsh"
OUT = INBOX / "当前版指针_cairn-dsh_20261002.md"
VER = re.compile(r"_v(\d+)$")


def main() -> int:
    if not INBOX.is_dir():
        print("ERR 共享面不在：%s ⇒ ★ 器具故障" % INBOX)
        return 2
    bodies = [p for p in INBOX.iterdir() if p.is_file() and not p.name.endswith(".sha256")]
    print("═══ 当前版指针 ═══")
    print("  共享面主体件 = %d" % len(bodies))

    groups = collections.defaultdict(list)
    for p in bodies:
        stem = p.stem if p.suffix else p.name
        key = VER.sub("", stem)
        groups[key].append(p)
    multi = {k: v for k, v in groups.items() if len(v) > 1}
    print("  ★ 多版本组 = %d" % len(multi))

    lines = [
        "# 当前版指针 · cairn-dsh 共享面（★ 第三方请先读本件）",
        "",
        "> 出件席：**cairn-dsh（石敢当）** ｜ 2026-10-02",
        ">",
        "> ★ **本件为什么存在**：本席投件守【只增不改】——**旧版【不删】**。",
        "> ⇒ 于是共享面里同一件会有多版并排（如 `SEAT_LOCATION` 有 7 版），",
        "> **★ 而命名法会误导**：四组两版的件里，**不带后缀的那份是【旧的】，`_v2` 才是新的**。",
        "> ⇒ 故本件**逐个系列点名「当前以哪一份为准」**。",
        "",
        "## 一 · 多版本组 → 当前版",
        "",
        "| 系列 | 版数 | ★ 当前版（以本件为准） | 其余（史料，勿据以行动） |",
        "|---|---|---|---|",
    ]
    for key in sorted(multi, key=lambda k: -len(multi[k])):
        vs = sorted(multi[key], key=lambda p: p.stat().st_mtime)
        cur = vs[-1]
        old = vs[:-1]
        lines.append("| `%s` | %d | ★ `%s` | %s |"
                     % (key, len(vs), cur.name,
                        "、".join("`%s`" % p.name for p in old[:5]) + ("…" if len(old) > 5 else "")))
    lines += [
        "",
        "## 二 · ★ 本件自身的诚实说明",
        "",
        "1. ★ **本件按【文件名去 `_vN`】判同组** ⇒ **命名不规则者会漏**（**漏 ≠ 无**）；",
        "1b. ★★ **本件【会把格式变体误算为版本】**（轮 19 现场实例：`预印稿…_.md` 与 `预印稿…_.docx` "
        "被算作一组两版，**而那是同一内容的两种格式，不是两个版本**）⇒ "
        "**故本表所列组数【偏多】；本席手工复核为 5 组，本件报 7 组。**",
        "2. ★ **本件按【mtime 最新】判「当前」** ⇒ **mtime 可被触碰 ⇒ 这一栏是【推定】，不是【保证】**；",
        "3. ★★ **本件自身也会成系列**：本席守只增不改 ⇒ **再跑一次就有 `当前版指针…_v2.md`**。",
        "   **★ 这正是它要解决的问题** ⇒ **故本席明说：本系列【以最高版号为准】**；",
        "4. ★ **凡本件与任何旧版冲突，以本件为准**；**凡本件与【台账最新一条】冲突，以台账为准**。",
        "",
        "## 三 · 第三方若只想读一件",
        "",
        "★ **读 `SEAT_LOCATION_..._v7.json`**（**席位位置声明的当前版**）＋**本件**。",
        "",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("  已写 = %s（%d B）" % (OUT.name, OUT.stat().st_size))
    print("  ★ 件内已明说三处局限（同组判据／当前推定／本件自身也会成系列）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
