#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 本件只读本席 outbox 的 .md 并做字面扫描；不触网。
r"""check_envclaims.py —— 扫出【关于环境必然如何】的断言，尤其【没带证据】的那种。 v1.0.0

来由（轮152）
──────────────
我在《最后一件·按这个顺序读》里写「本件的名字使它排在【最前】」——
**没先排序就写下了**，一验是错的（「最」排在「窗」「请」之后）。
⇒ 故问题不是那一句，是【这一类】：**关于环境／器具【必然如何】的断言，没跑就先写。**

扫什么（**字面，启发式，会误报**）
────────────────────────────────────
  **绝对化措辞**：一定／必然／总是／永远／永不／绝不／总是会／必定／会排在／默认会
  **且同一行【没有】证据标记**：证据／实测／见／依据／（跑过）／=／＝／[:：]

三态：`未发现`（★ 不等于"没有这类断言"）／`待逐条看`（列出）／`ERR`
用法: check_envclaims.py
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

SEAT = pathlib.Path(__file__).resolve().parent.parent
OUTBOX = SEAT / "outbox"

ABS = re.compile(r"(一定|必然|总是|永远|永不|绝不|必定|会排在|默认会|总会)")
EVID = re.compile(r"(证据|实测|见《|依据|跑过|经验证|已验证|[=＝]|：|:)")


def main() -> int:
    files = sorted(p for p in OUTBOX.glob("*.md") if p.is_file())
    print("═══ 扫【关于环境必然如何】的断言（启发式）═══")
    print("  扫描范围：本席 outbox 的 .md，共 %d 件" % len(files))
    print("  ★ 本器【不能证明没有这类断言】，只能列出【需要人看一眼】的候选。")
    print()

    hits, total, files_hit = [], 0, set()
    for p in files:
        try:
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue
        in_fence = False
        for i, raw in enumerate(lines, 1):
            s = raw.strip()
            if s.startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence or s.startswith(">") or s.startswith("|"):
                # ★ 轮153 修：**表格行也排除**——政策表（"永不记完整值"等）是成文规定，
                #   不是"关于环境必然如何"的断言。首跑未排除，故 47 处里大半是噪声。
                continue
            if ABS.search(s) and not EVID.search(s):
                hits.append((p.name, i, s[:96]))
                total += 1
                files_hit.add(p.name)

    print("  ── 命中：%d 处（涉 %d 件）──" % (total, len(files_hit)))
    for name, i, s in hits[:20]:
        print("     %s:%d" % (name[:46], i))
        print("        %s" % s)
    if total > 20:
        print("     …（余 %d 处）" % (total - 20))
    print()
    print("  ── 判词 ──")
    if total == 0:
        print("     ○ 本次扫描【未发现】此类候选 —— ★但不等于「没有这类断言」。")
    else:
        print("     ★ 命中 %d 处 ⇒ 需【逐条判断】：" % total)
        print("        · 有的是【引文】（但不在引用块里）⇒ 不是我的断言；")
        print("        · 有的是【我的断言且当时验过】⇒ 但本器只看字面，认不出；")
        print("        · ★ 而【我没验过就写下的】——那才是要找的。")
    print("  ★ 本器能失败（命中即报并返回非零）⇒ 非恒真。")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
