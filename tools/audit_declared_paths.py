#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只读声明与台账；不写件、不删件、不触网。
r"""audit_declared_paths.py —— 查：声明里每一个 declared_divergences.path，是不是【真文件】。 v1.0.0

为什么做它（轮 81，承轮 56／80）
──────────────────────────────────
轮 56 我犯过一次：往 `declared_divergences` 里写【一段描述】当 `path`
  ⇒ ★ 核验器【按精确路径匹配】⇒ 那条声明【无效】，红照旧。
轮 80 我又犯了三次：`path` 写成 `exp/audit_verdict_coverage.py（第三次）` 之类
  ⇒ ★ 同样匹配不上（★ 而核验仍绿，因为【第一次那条精确路径已覆盖】）。
⇒ ★★ 故本器把这件事做成【可查】：**逐条问"这个 path 指得到真文件吗"。**

★ 判据
──────
  · **能 resolve 到本席内的一个【存在的文件】** ⇒ ★ OK
  · **否则** ⇒ ★★ 死条（dead）：★ 它【匹配不上任何差异】，★ 是纸上的字

★ 本器自陈三条盲点
  ① 它只查【指不指得到文件】⇒ ★ **不查那条声明的内容对不对**
  ② 有些 path【本就可能是目录或通配】⇒ ★ 本器按"是否存在该路径"判，★ 不展开通配（★ 明写）
  ③ ★ 它【不改】声明——★ 死条怎么处置仍须人定
"""
from __future__ import annotations
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


def main() -> int:
    print("═══ 声明里的 path，指得到真件吗 ═══")
    if not DECL.is_file():
        print("  ★ 声明不在：%s" % DECL)
        return 2
    d = json.loads(DECL.read_text(encoding="utf-8"))
    items = d.get("declared_divergences", {}).get("items", [])
    print("  已声明分叉 = %d 条" % len(items))
    print()

    ok, dead = [], []
    for i, it in enumerate(items, 1):
        p = str(it.get("path", ""))
        # ★ 按本席为根 resolve
        cand = (SEAT / p)
        hit = cand.is_file() or cand.is_dir()
        if hit:
            ok.append((i, p))
        else:
            dead.append((i, p))

    print("  ── ★ 指得到的 = %d 条 ──" % len(ok))
    for i, p in ok:
        print("     ★ [%2d] %s" % (i, p[:92]))
    print()
    print("  ── ★★ 指不到真件的（死条）= %d 条 ──" % len(dead))
    for i, p in dead:
        print("     ★★ [%2d] %s" % (i, p[:92]))
    print()
    print("  ═══ 判定 ═══")
    print("     ★ 死条 = %d 条 ⇒ ★ 这些声明【匹配不上任何差异】，是纸上的字" % len(dead))
    print("     ★ 本器三条盲点：① 只查指不指得到文件、不查内容对不对"
          "② 不展开通配、不判目录语义 ③ 它不改声明——死条怎么处置仍须人定")
    return 0 if not dead else 1


if __name__ == "__main__":
    sys.exit(main())
