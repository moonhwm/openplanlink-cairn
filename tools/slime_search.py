#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""slime_search.py —— 黏菌聚合发散检索（open_access 发散多源 + slime_mold 聚合收敛）。

依新目标：最可以同步类似黏菌（圆桌、图寻等可能）混合策略聚合发散检索。
发散 = open_access 多源检索（OpenLibrary/Gutenberg/arXiv）；聚合 = slime_mold 按可信度收敛。
纯标准库，Windows 直跑。
"""
import sys
sys.path.insert(0, __file__.rsplit("\\", 1)[0])
import open_access as OA
import slime_mold as SM


def _score(row):
    """聚合评分：错误源置后，实测快稳源(openlibrary)优先，其余次之。"""
    if row.get("kind") == "error":
        return -1
    if row.get("source") == "openlibrary":
        return 2
    return 1


def slime_search(query, limit=3):
    """黏菌聚合发散检索：发散多源检索 → 聚合按可信度收敛。"""
    rows = OA.unified_search(query, limit)
    sm = SM.SlimeMold()
    for r in rows:
        sm.explore(query, [r])
    return sm.aggregate(_score, top_k=limit)


if __name__ == "__main__":
    print("  黏菌聚合发散检索『agent』：")
    for r in slime_search("agent", 3):
        print("    [%s] %s ｜ %s" % (r.get("kind"), (r.get("title") or "")[:36], r.get("source")))
