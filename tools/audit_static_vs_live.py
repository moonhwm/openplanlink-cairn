#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只跑本席自有器两次、逐行比对；不写件、不删件、不触网。
r"""audit_static_vs_live.py —— 量"这件器的输出会不会随运行而变"。 v1.0.0

★★ 轮 60 的【空设计】——本器的原始意图与它实际量到的东西【不是一回事】
────────────────────────────────────────────────────────────────────
原始意图：量第③种失效形态（**永远报警 ⇒ 被当背景噪声**）。
实际量到：8 件器【全部】只出静态行（静态 466 行／活 0 行）。

★★★ 为什么这是空设计：**「两次连跑的差异」量的是【稳定性】，不是【相关性】。**
  · 对【核验器】而言，条件没变、判词当然一样 ⇒ 一律"只出静态行"【是正常的】。
  · 而**噪声的定义是【与条件无关】** ⇒ ★ 那必须**改变条件**才测得出来。
⇒ 故本器**测不出第③种形态**。★ 这不是精度不够，是【设计错了对象】。

★ 而问对问题之后，真缺口立刻现形（见轮 60 的件）：
  **8 件核验器里，只有 1 件有【负例对照】⇒ 对其余 7 件，「它印了 PASS」不是它能红的证据。**

★ 本器自陈三条盲点
  ① 它只跑【本席自选的那几件器】⇒ 不是全体
  ② 它按【逐行文本】比较 ⇒ 数字变了但排版偶然相同的行会被算成"静态"（反之亦然）
  ③ ★★ 它【测不出】它想测的东西——见上；（★ 保留它，是为了把这次空设计【留在案上】）
"""
from __future__ import annotations
import pathlib
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SEAT = pathlib.Path(__file__).resolve().parent.parent
PY = sys.executable

TARGETS = [
    ("声明核验", "exp/verify_seat_location.py"),
    ("配方核验", "exp/verify_recipe.py"),
    ("机检", "exp/tool_hygiene.py"),
    ("引号机检", "exp/lint_cn_quotes.py"),
    ("波及分级", "exp/blast_radius.py"),
    ("传递性稽核", "exp/audit_blast_transitivity.py"),
    ("交付稽核", "exp/audit_orphans.py"),
    ("过滤器稽核", "exp/audit_filters.py"),
]


def lines_of(rel: str) -> tuple[list[str], int]:
    r = subprocess.run([PY, rel], capture_output=True, text=True,
                       encoding="utf-8", cwd=str(SEAT), timeout=900)
    out = ((r.stdout or "") + (r.stderr or "")).splitlines()
    return [l.rstrip() for l in out if l.strip()], r.returncode


def main() -> int:
    print("═══ 静态行 vs 活行（每件器连跑两次、逐行比对）═══")
    print("  ★ 两次都一样的行 = 静态行；有变化 = 活行")
    print()
    tot_s = tot_l = 0
    only_static = []
    for label, rel in TARGETS:
        try:
            a, rca = lines_of(rel)
            b, rcb = lines_of(rel)
        except Exception as e:
            print("  ★ %-14s ⇒ 跑不起来：%s" % (label, str(e)[:60]))
            continue
        sa, sb = set(a), set(b)
        common = [l for l in a if l in sb]
        changed = [l for l in a if l not in sb] + [l for l in b if l not in sa]
        tot_s += len(common)
        tot_l += len(changed)
        flag = "★ 只出静态行！" if not changed else ""
        print("  ── %-14s（退出码 %d/%d）静态 %d ｜ 活 %d %s" %
              (label, rca, rcb, len(common), len(changed), flag))
        if not changed:
            only_static.append(label)
        for l in changed[:3]:
            print("        ★ 活：%s" % l[:96])
    print()
    print("  ═══ 汇总 ═══")
    print("     静态行合计 = %d ｜ 活行合计 = %d" % (tot_s, tot_l))
    print("     ★★ 只出静态行的器 = %d 件：%s" % (len(only_static), "、".join(only_static) or "（无）"))
    print()
    print("  ── 本器三条盲点 ──")
    print("     ① 只跑本席自选的那几件器 ⇒ 不是全体")
    print("     ② 按逐行文本比较 ⇒ 排版偶然相同会被算成静态")
    print("     ③ ★ 不判那些静态行对不对——「静态」不等于「错」")
    return 0


if __name__ == "__main__":
    sys.exit(main())
