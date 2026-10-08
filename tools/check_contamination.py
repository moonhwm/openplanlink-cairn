#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 本件只读本席 outbox 的 .md 并做启发式扫描；不触网。
r"""check_contamination.py —— 对**自己的产出**做一次污染自审（机主红线：别被污染语料了）。 v1.0.0

为什么要它
───────────
今晚我读了大量外部文本（他席件、观测站页面、74号令、镜像 README/LICENSE、协调稿）。
**红线是「别被污染语料了」** —— 我一直在【程序上】守它（取回即数据、绝不执行）。
⇒ 但**从没审计过【自己的产出】**：有没有把别人的话当自己的话说、或把【指令】当成【事实】写进件里。

★ 必须说死的话（否则本件本身就是在骗人）
────────────────────────────────────────────
  启发式**不能证明"没被污染"**。它只能**列出【需要人看一眼的候选】**。
  ⇒ 故判词是「本次扫描未发现 X 类特征」，**不是「未被污染」**。

查三类特征（**都是启发式，都会误报**）
────────────────────────────────────────
  ① **无引用的指令式语言**：`你必须／你应该／请务必／必须执行／不得…` 等，
     **且该行不在引用块（`>` 开头）里、也不在代码围栏内**；
  ② **注入式措辞**：`忽略之前／ignore previous／forget／system:`／`你现在是` 等；
  ③ **替外部立言的句子**：以「它说／其称」起头却**没有件名或引号**的行。

三态：`干净` ／ `待看一眼`（命中 ①②③ 任一类）／ 本器自身 `ERR`
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

DIRECTIVE = re.compile(r"(你必须|你必须|你应该|你应当|请务必|必须执行|立刻执行|不得对外|禁止对外)")
INJECT = re.compile(r"(忽略之前|忽略以上|ignore\s+previous|forget\s+(?:all|everything)|system\s*:|你现在是|从现在起你)")
SPEAK_FOR = re.compile(r"^(它说|其称|对方称|他们要求|他们表示)")
ATTRIB = re.compile(r"(件名|原文|引自|见《|依据|\[原件直取\]|\[本地副本\]|如下|摘要)")


def main() -> int:
    files = sorted(p for p in OUTBOX.glob("*.md") if p.is_file())
    print("═══ 对自己的产出做污染自审（启发式）═══")
    print("  扫描范围：本席 outbox 的 .md，共 %d 件" % len(files))
    print("  ★ 本器【不能证明没被污染】，只能列出【需人看一眼】的候选。")
    print()

    hits = {"①无引用的指令式": [], "②注入式措辞": [], "③替外部立言": []}
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
            if in_fence:
                continue
            quoted = s.startswith(">") or s.startswith("|")     # 引用块/表格视为已标来源
            if DIRECTIVE.search(s) and not quoted:
                hits["①无引用的指令式"].append((p.name, i, s[:90]))
            if INJECT.search(s) and not quoted:
                hits["②注入式措辞"].append((p.name, i, s[:90]))
            if SPEAK_FOR.search(s) and not ATTRIB.search(s):
                hits["③替外部立言"].append((p.name, i, s[:90]))

    total = sum(len(v) for v in hits.values())
    for k, v in hits.items():
        print("  ── %s：%d 处 ──" % (k, len(v)))
        for name, i, s in v[:8]:
            print("     %s:%d  %s" % (name[:44], i, s))
        if len(v) > 8:
            print("     …（余 %d 处）" % (len(v) - 8))
    print()
    print("  ── 判词 ──")
    if total == 0:
        print("     ○ 本次扫描【未发现】上述三类特征 —— ★但不等于「未被污染」。")
        print("       本器只查【字面特征】，且【不查语义】：改了说法的注入它查不出。")
    else:
        print("     ★ 命中 %d 处 ⇒ 需人看一眼（**逐条判断，不是逐条定罪**）。" % total)
        print("       ★ 其中【引用块／表格】内的行【不计】—— 因为那已标明出处。")
    print("  ★ 本器能失败（命中即报并返回非零）⇒ 非恒真。")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
