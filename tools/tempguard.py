#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只做路径判断与断言；不写件、不触网。
r"""tempguard.py —— 可复用的一条断言：**实验室不在本席领地内**。 v1.0.0

为什么做它（轮 65，承轮 64 的边界）
──────────────────────────────────────
轮 64 我明写一处未做：**「『只在临时目录』这种声明，本器【无法自动核】。」**
★★ 而轮 42 我【已经为一件器造过】那条断言（工作目录不在领地内）——
   ⇒ 故这条不是不能核，★ 是【没推广】。

轮 65 实测（12 件会建临时目录/拷贝的器里）：
  ★ 有那条断言 = 4 件（blindspot_trials／neg_control_batch／neg_control_seat_location／neg_control_tool_hygiene）
  ○ 无断言     = 8 件（audit_filters／check_claims／forge_demo／outsider_trial／
                   smoke_pipeline／tamper_test／verify_hub_merkle／window_close_record）
⇒ ★★ 本器把那条断言抽成【一件可复用的东西】，让其余器【一行就能装上】。

用法
──────
    from tempguard import assert_outside_seat
    lab = assert_outside_seat(pathlib.Path(td), SEAT)     # 不成立则抛 OutsideSeat

★ 本器自陈三条盲点
  ① 它只证【那个目录不在领地内】⇒ 不证"过程里没有去读领地里的件"
  ② ★ 它靠【调用者主动调它】⇒ 不调的器【它管不到】
  ③ 它判的是【路径前缀】⇒ 符号链接等写法可能绕过（★ 本席未使用符号链接，但这一点我写明）
"""
from __future__ import annotations
import pathlib
import sys

# ★ 2026-10-03 轮 68 补：**UTF-8 stdout 块**。
#   缘由：本器轮 65 建立时【漏了这一段】⇒ 机检（tool_hygiene 的第①项）【从轮 65 起就是红的】，
#   ★ 而我到轮 68 才看见——因为★ 我不是每轮都跑收尾块生成器。
#   ★ 教训：新建器时【照抄旧器的头】，别凭记忆写。
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass


class OutsideSeat(AssertionError):
    """实验室落在本席领地内 ⇒ 拒绝继续。"""


def is_inside(path: pathlib.Path, seat: pathlib.Path) -> bool:
    """path 是否等于 seat 或在 seat 之下。"""
    p, s = pathlib.Path(path).resolve(), pathlib.Path(seat).resolve()
    return (s == p) or (s in p.parents)


def assert_outside_seat(lab: pathlib.Path, seat: pathlib.Path, verbose: bool = True):
    """★ 断言 lab 不在 seat 领地内；不成立即抛 OutsideSeat。返回 resolve 后的 lab。"""
    lab_r = pathlib.Path(lab).resolve()
    if verbose:
        print("  ★ 实验室 = %s" % lab_r)
        print("  ★ 本席领地 = %s" % pathlib.Path(seat).resolve())
    if is_inside(lab_r, seat):
        if verbose:
            print("  ★★ 断言失败：实验室在本席领地内 ⇒ 拒绝继续（否则可能碰真件）")
        raise OutsideSeat("实验室落在领地内：%s" % lab_r)
    if verbose:
        print("  ★ 断言：实验室不在领地内 ⇒ ✅ 成立")
    return lab_r


def selftest() -> int:
    """★ 两向自测：正例（领地外）应通过；负例（领地内）应抛。"""
    import tempfile
    seat = pathlib.Path(__file__).resolve().parent.parent
    print("═══ tempguard 自测 ═══")
    ok = 0
    with tempfile.TemporaryDirectory() as td:
        try:
            assert_outside_seat(pathlib.Path(td), seat)
            print("  ✅ 正例（临时目录）通过")
            ok += 1
        except OutsideSeat:
            print("  ★★ 正例误报")
        try:
            assert_outside_seat(seat / "exp", seat)
            print("  ★★ 负例未拦住")
        except OutsideSeat:
            print("  ✅ 负例（领地内）被拦住")
            ok += 1
    print("  ⇒ %s" % ("两向都按期望" if ok == 2 else "有方向不符"))
    return 0 if ok == 2 else 1


if __name__ == "__main__":
    raise SystemExit(selftest())
