#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 本件只读本机策略表并做双向覆盖比对；不触网。
r"""check_policy_coverage.py —— 对**我自己的策略表**做【双向覆盖核查】。 v1.0.0

为什么
───────
轮 140 那格印着「UNDEFINED 0 ← 本批未出现」。
⇒ 于是我问了一个【没查过】的问题：**我的 need 表覆盖了所有实测通道吗？反过来呢？**
    · 实测有、need 无 ⇒ **该组合会落到 UNDEFINED ⇒ 等于【无策略运行】** ← ★ 这可能是个洞
    · need 有、实测无 ⇒ **策略要求了，但我没有现状 ⇒ 只能 NEED-OWNER**（可接受，但要说清）
★ 我整晚在给别人做这种双向核查，却没对自己的表做过。

三态判词
──────────
  `已覆盖`（两侧都有）／`只为策略`（need 有、实测无）／`★只为实测`（实测有、need 无 ⇒ **无策略组合**）
用法: check_policy_coverage.py
"""
from __future__ import annotations
import pathlib
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import auth_policy            # noqa: E402


def main() -> int:
    need = {(k[0], k[1], k[2]): v for k, v in auth_policy.NEED.items()}
    meas = {(c["ch"], c["direction"]): c for c in auth_policy.CHANNELS}

    print("═══ 对我自己的策略表做双向覆盖核查 ═══")
    print("  need 组合数      = %d" % len(need))
    print("  实测通道（通道,方向）数 = %d" % len(meas))
    print()

    # ① 实测有、need 无（★ 无策略组合）
    print("  ── ① 实测有、need 无（★该组合会落到 UNDEFINED ⇒ 无策略运行）──")
    no_policy = []
    for (ch, d), c in sorted(meas.items()):
        has = any(k[0] == ch and k[1] == d for k in need)
        if not has:
            no_policy.append((ch, d, c.get("cur")))
            print("     ★ %-16s %-4s 现状=%-4s ⇒ 无任何 need 行" % (ch, d, c.get("cur")))
    if not no_policy:
        print("     （无 ⇒ 每条实测通道都至少有一行策略）")

    # ② need 有、实测无（可接受，但要报）
    print()
    print("  ── ② need 有、实测无（策略要求了，但无现状 ⇒ 只能 NEED-OWNER）──")
    no_meas = []
    for (ch, d, s) in sorted(need):
        has = any(k[0] == ch and k[1] == d for k in meas)
        if not has:
            no_meas.append((ch, d, s, need[(ch, d, s)]))
            print("     ○ %-16s %-4s %-10s 需 %s ⇒ 无实测" % (ch, d, s, need[(ch, d, s)]))
    if not no_meas:
        print("     （无）")

    # ③ 两侧都有（已覆盖）
    both = [(k, need[k]) for k in sorted(need)
            if any(m[0] == k[0] and m[1] == k[1] for m in meas)]
    print()
    print("  ── ③ 两侧都有（已覆盖）%d 条 ──" % len(both))

    print()
    print("  ── 判词 ──")
    print("     只为策略 %d 条 ｜ ★只为实测 %d 条 ｜ 已覆盖 %d 条" % (len(no_meas), len(no_policy), len(both)))
    if no_policy:
        print("     ⇒ ★有 %d 条实测通道【无策略】——它们落在 UNDEFINED，即【无策略运行】" % len(no_policy))
        print("        ★ 这不是网关的事，是【我的策略表有洞】。")
    else:
        print("     ✅ 每条实测通道都至少有【一行策略】⇒ 无'无策略运行'的组合")
    print("  ★ 本器能失败（出现'只为实测'即报）⇒ 非恒真。")
    return 0 if not no_policy else 1


if __name__ == "__main__":
    sys.exit(main())
