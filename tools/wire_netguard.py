#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 本件只改本席自己的源码文本，不触网。
r"""wire_netguard.py —— 给尚未接总闸的工具，各加一行 `netguard.activate()`。 v1.0.0

做法（**改一处钩子，而不是改九处调用点**）
────────────────────────────────────────────
`netguard.activate()` 在【总闸置上时】替换 `urllib.request.urlopen` 与
`OpenerDirector.open` ⇒ 各工具只需在【模块级、导入之后】加一行调用即可。
★ 插入点规则：**第一个顶格的 `def `／`class ` 之前** ⇒ 即模块级、且在各 import 之后。
★ 幂等：已有 `netguard` 者跳过。
★ 开关未置时 `activate()` 返回 False 且不装钩子 ⇒ **不改变任何既有行为**。
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

EXP = pathlib.Path(__file__).resolve().parent

TARGETS = [
    "fetch_wechat_article.py", "policy_abc.py", "probe_opl_history.py",
    "probe_qtorrent_card.py", "wechat_probe.py", "audit_robots_compliance.py",
    "check_handshake52.py", "gen_status_feed.py", "audit_skill_naming.py",
]

BLOCK = '''
# ★ 轮108：网络总闸——只在 DSH_NO_NET 置上时装"拒绝外发"钩子；未置则【一行都不改行为】。
try:
    import netguard as _netguard
    _netguard.activate()
except Exception:
    pass

'''


def main() -> int:
    print("═══ 给未接闸的工具补 netguard.activate() ═══")
    done = skip = bad = 0
    for name in TARGETS:
        p = EXP / name
        if not p.is_file():
            print("  ★缺件：%s" % name); bad += 1; continue
        t = p.read_text(encoding="utf-8")
        if "netguard" in t:
            print("  — 已接：%s" % name); skip += 1; continue
        lines = t.splitlines(keepends=True)
        idx = None
        for i, ln in enumerate(lines):
            if re.match(r"^(def |class )", ln):
                idx = i
                break
        if idx is None:
            print("  ★找不到插入点：%s" % name); bad += 1; continue
        lines.insert(idx, BLOCK)
        p.write_text("".join(lines), encoding="utf-8")
        print("  ✅ 已接：%-32s ｜ 插在第 %d 行前" % (name, idx + 1))
        done += 1
    print("\n  ⇒ 新接 %d 件 ｜ 已接 %d 件 ｜ 失败 %d 件" % (done, skip, bad))
    print("  ★ 声明与钩子都只是【如实标注与阻止】，开关未置时行为不变。")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
