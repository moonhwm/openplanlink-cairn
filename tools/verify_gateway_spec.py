#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 本件只在本机 import 两件鉴权模块并跑判定；不触网。
r"""verify_gateway_spec.py —— 把 `gateway_spec.json` 的【主张】拿去跑，而不是读一遍。 v1.0.0

为什么
───────
轮 139 那份规格主张三件事：
  ① 裁决有【四态】：ALLOW／DENY／NEED-OWNER／UNDEFINED；
  ② `UNDEFINED` **既不等于放行、也不等于拒绝**；
  ③ 层由【证明强度】算出——**请求自封的 tier 不被采纳**。
★ **规格是主张。而我整晚都在要求别人：主张要能【跑】。** ⇒ 故本器跑它。

查什么（**每一项都能失败**）
──────────────────────────────
  A. 读 `gateway_spec.json`：need 表每条都调 `auth_policy.check()`，判词须落在四态内；
  B. 统计【四态中实际出现过几种】——若某种从未出现，如实标出（**不假装四态都活着**）；
  C. 造一个【表里未设策略】的组合，须回 `UNDEFINED`（**且不得回 DENY**）；
  D. 造一个【自封 T2 但证据只够 T1】的请求，跑 `auth_split.decide()`，**须不给出 T2**。
用法: verify_gateway_spec.py
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

HERE = pathlib.Path(__file__).resolve().parent
SEAT = HERE.parent
sys.path.insert(0, str(HERE))
import auth_policy            # noqa: E402
import auth_split             # noqa: E402

SPEC = SEAT / "outbox" / "gateway_spec.json"
FOUR = ("ALLOW", "DENY", "NEED-OWNER", "UNDEFINED")


def main() -> int:
    if not SPEC.is_file():
        print("★缺 gateway_spec.json ⇒ 先跑 emit_gateway_spec.py")
        return 2
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    fails = []

    print("═══ 跑规格的主张（不是读它）═══")
    print("  规格 schema = %s" % spec.get("schema"))

    # A ＋ B：逐条跑 need 表，统计四态出现情况
    seen = {}
    print()
    print("  ── A/B：need 表 %d 条逐条跑 check() ──" % len(spec["need_table"]))
    for r in spec["need_table"]:
        v, why = auth_policy.check(r["channel"], r["direction"], r["sensitivity"])
        seen[v] = seen.get(v, 0) + 1
        ok = v in FOUR
        if not ok:
            fails.append("A：%s 返回了四态之外的 %r" % (r["channel"], v))
        print("     %-14s %-4s %-10s 需 %s ⇒ %-10s %s" % (
            r["channel"], r["direction"], r["sensitivity"], r["required_tier"], v,
            "✅" if ok else "★越界"))
    print("  ── 四态实际出现次数 ──")
    for k in FOUR:
        n = seen.get(k, 0)
        print("     %-11s %d %s" % (k, n, "" if n else "← ★本批未出现（不假装它活着）"))
    live = [k for k in FOUR if seen.get(k, 0) > 0]
    print("     ⇒ 本批实际到达 %d / 4 态" % len(live))

    # C：表外组合须回 UNDEFINED，且不得回 DENY
    print()
    print("  ── C：表外组合须回 UNDEFINED ──")
    v1, w1 = auth_policy.check("____not_a_channel____", "out", "public")
    print("     check(表外通道) = %s ｜ %s" % (v1, w1[:60]))
    if v1 != "UNDEFINED":
        fails.append("C：表外组合应回 UNDEFINED，实为 %r" % v1)
    if v1 == "DENY":
        fails.append("C：表外组合被误报为 DENY（正是轮102 修过的那个错）")

    # D：自封 tier 无效（层由证明强度算出）
    # ★★ 轮141 修（轮140 我如实说了这一段【未覆盖 T1 分支】，此处走到）：
    #   根因：`auth_split.decide` 的 `roster` 是【指纹字符串的列表】，
    #   而轮140 我传的是【字典的列表】⇒ `fp in roster` 为假 ⇒ 只落到 T0。
    #   ⇒ 现按源码要件造四例：T1 正例／T2 正例（不同成员联署）／自联署（不构成第二证）／自封越权。
    print()
    print("  ── D：层由证明强度算出（★ 轮141 补：T1/T2 两条分支都走到）──")
    import time as _t
    now = _t.time()
    END = "e" * 64
    roster = ["cairn-dsh", "other-seat"]          # ★ 字符串列表——实现期望的形状
    cases = [
        ("T1 正例：指纹在册 ∧ 前驱衔接 ∧ 钟在窗内",
         {"fp": "cairn-dsh", "prev": END, "ts": now}, "T1"),
        ("T2 正例：另加【不同】成员联署",
         {"fp": "cairn-dsh", "prev": END, "ts": now, "cosign": "other-seat"}, "T2"),
        ("自联署：同一成员，不构成第二证",
         {"fp": "cairn-dsh", "prev": END, "ts": now, "cosign": "cairn-dsh"}, "T1"),
        ("★自封越权：证据只够 T1 却声称 T2",
         {"fp": "cairn-dsh", "prev": END, "ts": now, "claimed_tier": "T2"}, "T1"),
        ("陌生人：不在名册",
         {"fp": "stranger", "prev": END, "ts": now, "claimed_tier": "T2"}, "T0"),
        # ★★ 轮142 补（轮141 我如实说了这条在别处未进本组）：**时钟负例**
        ("★钟超窗：时间戳远在窗外的旧证", {"fp": "cairn-dsh", "prev": END, "ts": now - 10 ** 6}, "T0"),
        # ★★ 轮142 补：**前驱不衔接**（疑重放或旧证）
        ("★前驱不衔接：prev 与链末不符", {"fp": "cairn-dsh", "prev": "x" * 64, "ts": now}, "T0"),
        # ★★ 轮142 补：**无时间戳**
        ("★无时间戳", {"fp": "cairn-dsh", "prev": END}, "T0"),
    ]
    for name, req, want in cases:
        d = auth_split.decide(req, roster, END, now=now)
        got = d.get("tier")
        ok = (got == want)
        if not ok:
            fails.append("D：%s ⇒ 期望 %s，实得 %s" % (name, want, got))
        extra = ""
        if d.get("escalation_attempt"):
            extra = " ｜ ★越权企图已记"
        print("     %-34s ⇒ %-3s %s%s" % (name[:34], got, "✅" if ok else "★不符", extra))

    print()
    print("  ── 判词 ──")
    if fails:
        for f in fails:
            print("     ★ " + f)
        print("     ⇒ ★有 %d 项未过" % len(fails))
    else:
        print("     ✅ A/B/C/D 全过 ⇒ 规格的三条主张【跑得住】")
    print("  ★ 本器能失败（越界判词／表外回 DENY／自封得逞 皆会报）⇒ 非恒真。")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
