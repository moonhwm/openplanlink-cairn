#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
audit_evidence_source.py —— 台账【证据来源分级】：揪出"测了副本却写成原件"的条目。 v1.0.0

来由
────
本席轮 48 发现自己犯了一个系统性错误：**拿 09-30 的本地克隆跑验证，却把结论写成了
线上仓库的性质**（克隆里 E=0/N=12 是本机 git autocrlf，线上实际 E=12/N=0）。
⇒ 这不是孤例，是一类。故本器对全台账逐条判【证据取自何处】，把风险条目挑出来。

分级
────
  A 原件直取   : raw.githubusercontent / api.github.com / codeload / 线上端点(127.0.0.1:4173 等)
                  ⇒ 结论可直接支撑
  B 本机对象   : 本席所据的【本来就在本机、且它就是对象本身】的件
                  （inbox\底稿、本席自己的 outbox/exp/ledger）⇒ 不涉副本问题
  C 共享面     : 全局声明_治理文档\ ⇒ 生态自己的发布面，是对象的原件面 ⇒ 可
  D ★风险·副本 : 本地克隆/解包/缓存（_openplanlink_mirror、.zcode、WorkBuddy、Temp 解包等）
                  ⇒ ★ **若结论是关于【外部原件】的，必须对线上重测**
  ? 未判       : 无上述标记

用法: audit_evidence_source.py <frontier_ledger.jsonl> [--list]
"""
from __future__ import annotations
import collections
import json
import pathlib
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

RULES = [
    ("A 原件直取", re.compile(r"raw\.githubusercontent|codeload|api\.github\.com|"
                              r"127\.0\.0\.1:4173|120\.46\.86\.165|qoder\.website|"
                              r"Invoke-WebRequest|jsdelivr|feishuapp", re.I)),
    ("D 风险·副本", re.compile(r"_openplanlink_mirror|本地克隆|克隆|\.zcode|WorkBuddy\\|"
                               r"AppData\\Local\\Temp|解包|tar -xz|副本", re.I)),
    ("C 共享面",   re.compile(r"全局声明_治理文档|a2a-inbox|共享面", re.I)),
    ("B 本机对象", re.compile(r"inbox\\|底稿|outbox/|outbox\\|exp/|exp\\|ledger|"
                              r"frontier_ledger|handshake", re.I)),
]


def classify(e: dict) -> tuple:
    blob = json.dumps(e, ensure_ascii=False)
    hits = [name for name, pat in RULES if pat.search(blob)]
    # 优先级：风险副本最该被看见；但若同时有 A（原件直取），说明已对原件核过 ⇒ 降级
    if "D 风险·副本" in hits and "A 原件直取" not in hits:
        return "D 风险·副本", hits
    if "A 原件直取" in hits:
        return "A 原件直取", hits
    for k in ("C 共享面", "B 本机对象"):
        if k in hits:
            return k, hits
    return "? 未判", hits


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__); return 2
    p = pathlib.Path(sys.argv[1])
    rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    c = collections.Counter()
    risky = []
    for i, e in enumerate(rows, 1):
        k, hits = classify(e)
        c[k] += 1
        if k == "D 风险·副本":
            risky.append((i, e.get("ev_type", "?"), (e.get("subject") or "")[:88]))
    print("═══ 台账证据来源分级 ═══")
    print("  条目数 =", len(rows))
    print()
    for k, v in c.most_common():
        print("  %-14s %4d  %5.1f%%" % (k, v, 100.0 * v / len(rows)))
    print()
    if risky:
        print("  ★风险条目（证据含本地克隆/解包，且未见原件直取标记）＝ %d 条：" % len(risky))
        for i, t, s in risky:
            print("    #%-4d %-16s %s" % (i, t, s))
        print()
        print("  ⇒ 处置：逐条判其结论【是否关于外部原件】；若是，须对线上/原址重测后方可保留。")
    else:
        print("  ⇒ 未见风险条目。")
    print()
    print("  ★本器只按【文本标记】分级——**它判的是'证据里出现过什么路径'，不是'结论对不对'**。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
