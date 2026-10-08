#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只读声明与两个目录；不写件、不删件、不触网。
r"""audit_declared_still_diverges.py —— 查：声明过的分叉，**现在还是不是分叉**。 v1.0.0

为什么（轮 120，承轮 81／119）
────────────────────────────────
轮 81 查过一件事：声明里的 `path`【指不指得到真件】（★ 查出 14 条死条）。
★ 而那是【更弱】的一问。更强的一问是：**那条声明所指的差异，现在还在不在？**
  · 若【还在】⇒ ★ 声明仍是活的
  · 若【已不存在】（★ 两边现在字节相同）⇒ ★★ 那条声明【过期了】——★ 而它还挂在账上
⇒ ★ 故本器把"过期"也做成可查的。

★ 判据
──────
  对每条 `declared_divergences.items`：
    · path 指不到真件 ⇒ ★ 记为【死条】（★ 轮 81 已能查，这里也列）
    · 正本与副本【都无此件】⇒ ★ 记为【无副本可对】
    · 两边【都无此件】或【字节相同】⇒ ★★ 记为【已不再分叉】（= 过期）

★ 本器自陈三条盲点
  ① 它只对一个副本（★ 与核验器同源那个）⇒ ★ 多副本时可能误判
  ② "字节相同"不等于"那件事没发生" ⇒ ★ 它只说【现在看不出分叉】
  ③ ★ 它【不删】任何声明——★ 过期条怎么处置仍须人定（★ 声明只是只增的）
"""
from __future__ import annotations
import hashlib
import json
import pathlib
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SEAT = pathlib.Path(__file__).resolve().parent.parent
DECL = SEAT / "outbox" / "SEAT_LOCATION_cairn-dsh_20261002.json"
REPLICA = pathlib.Path(
    r"C:\Users\欧阳宏俊\OneDrive\桌面\_整理_各席交付\石敢当席\A2A新席_石敢当Cairn_20260928")


def sha(p: pathlib.Path):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    print("═══ 声明过的分叉，现在还是不是分叉 ═══")
    if not DECL.is_file():
        print("  ★ 声明不在：%s" % DECL)
        return 2
    d = json.loads(DECL.read_text(encoding="utf-8"))
    items = d.get("declared_divergences", {}).get("items", [])
    print("  已声明分叉 = %d 条" % len(items))
    print("  副本 = %s" % REPLICA)
    print()

    dead, live, gone, nopair = [], [], [], []
    for i, it in enumerate(items, 1):
        p = str(it.get("path", "")).strip()
        a = SEAT / p
        b = REPLICA / p
        if not a.is_file():
            dead.append((i, p))
            continue
        if not b.is_file():
            nopair.append((i, p))
            continue
        if sha(a) == sha(b):
            gone.append((i, p))          # ★ 已不再分叉 = 声明过期
        else:
            live.append((i, p))

    print("  ── ★ 仍是分叉的（声明活着）= %d 条 ──" % len(live))
    print("  ── ★★ 已不再分叉的（★ 声明过期）= %d 条 ──" % len(gone))
    for i, p in gone:
        print("     ★★ [%2d] %s" % (i, p[:88]))
    print("  ── ○ 正本有而副本无（★ 无副本可对）= %d 条 ──" % len(nopair))
    for i, p in nopair[:10]:
        print("     ○ [%2d] %s" % (i, p[:88]))
    print("  ── ★ 死条（正本也没有）= %d 条 ──" % len(dead))
    print()
    print("  ═══ 判定 ═══")
    print("     ★ 活 %d ｜ ★★ 过期 %d ｜ ○ 无副本 %d ｜ ★ 死条 %d"
          % (len(live), len(gone), len(nopair), len(dead)))
    print("     ★★ 过期条【不删】（★ 声明只增）——★ 但【该被看见】：★ 否则账上永远挂着已完成的事。")
    print("     ★ 本器三条盲点：① 只对一个副本 ② 「字节相同」不等于「那件事没发生」 ③ 它不删任何声明")
    return 0


if __name__ == "__main__":
    sys.exit(main())
