#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 本件只读手册机检器的期望表；不触网、不执行命令。
r"""check_expectations.py —— 扫《复现手册》机检器的【期望串】，标出"会变的计数式期望"。 v1.0.0

来由（轮166 → 169）
────────────────────
轮165 我把套件从十一项升到十二项 ⇒ 轮166 手册第 4 行【翻红】。
病根不是"坏了"，是**期望值被写成了一个【会变的计数】**（`通过 11 项`）——
⇒ **工具每加一项，那行就得改一次。**

★ 那三步（166 查因 → 167 改判据 → 168 验断言）都是【事后】。
  本器是【事前】：**在写期望的那一刻就该被提醒。**

它标什么（**报告式，不判失败**）
──────────────────────────────────
  · **裸计数式**：`通过 N 项`／`N 项`／`共 N` 之类——**N 会变 ⇒ 期望会过期**；
  · **比值式**：`4/4`／`25/25`／`N/M`——★ **这一类别【不是缺陷】**：
    它是"这 N 项全过"的意思，**分子分母绑在一起 ⇒ 加项不会让它过期**。
  ⇒ 故本器【只报，不判】：**因为"哪个数会变"是语义判断，字面判不了。**

三态：`未发现会变计数`／`发现 N 处待看`／`ERR`
用法: check_expectations.py
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
SRC = EXP / "verify_playbook.py"

# 期望串在 ROWS 里是【每行最后一个字符串字面量】——抓它
ROW = re.compile(r'^\s*\((.+?)\)\s*,\s*$')
# 裸计数：中文数词或阿拉伯数字 + 量词（项/条/处/张/件/级/个/位）
BARE = re.compile(r"([0-9]+|[一二三四五六七八九十百千]+)\s*(项|条|处|张|件|级|个|位)")
# 比值：N/M
RATIO = re.compile(r"[0-9]+\s*/\s*[0-9]+")


def main() -> int:
    if not SRC.is_file():
        print("ERR 读不到 %s" % SRC.name)
        return 2
    lines = SRC.read_text(encoding="utf-8", errors="replace").splitlines()

    print("═══ 扫手册机检器的期望串：哪些是【会变的计数】═══")
    print("  来源 = %s" % SRC.name)
    print("  ★ 报告式：本器【不判失败】——因为「哪个数会变」是语义判断。")
    print()

    n_rows, bare_hits, ratio_ok = 0, [], 0
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if not s.startswith("(") or "__MANUAL__" in s:
            continue
        if '"""' in s or s.startswith("#"):
            continue
        # 期望串 = 行内最后一个被引号包住的片段
        quoted = re.findall(r'"([^"]*)"', s)
        if not quoted:
            continue
        want = quoted[-1]
        # 只看"看着像从工具输出里抓来的签名串"（含中文或 / 或 =）
        if not re.search(r"[\u4e00-\u9fff/：=]", want):
            continue
        n_rows += 1
        if RATIO.search(want):
            ratio_ok += 1
            print("  [%2d] ○ 比值式（不算缺陷）：%r" % (i, want))
            continue
        m = BARE.search(want)
        if m:
            bare_hits.append((i, want, m.group(0)))
            print("  [%2d] ★ 裸计数式（会过期）：%r  ← 命中 %r" % (i, want, m.group(0)))
        else:
            print("  [%2d] ✅ 无计数：%r" % (i, want))

    print()
    print("  ── 判词 ──")
    print("     期望串共 %d 条 ｜ 比值式 %d ｜ ★裸计数式 %d" % (n_rows, ratio_ok, len(bare_hits)))
    if bare_hits:
        print("     ★ 上面每一条都是【工具加项就会过期】的写法 ⇒ 建议改为【承重的那半】")
        print("        （如「未过 0 项」而不是「通过 11 项」）。")
    else:
        print("     ○ 未发现裸计数式的期望串 —— ★但不等于没有：本器只查字面。")
    print("  ★ 本器能失败吗：它【只报不判】⇒ 恒返回 0。**这是刻意的**：")
    print("     判「哪个数会变」需要语义，机器判不了；故它【不装成能判】。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
