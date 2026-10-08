#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只读源码做静态查找；不执行被测器、不写件、不删件、不触网。
r"""audit_wording_siblings.py —— 给一个"我刚改掉的写法"，列出全席【剩余的同类处】。 v1.0.0

为什么做它（轮 69，承轮 68 的教训）
──────────────────────────────────────
轮 68 我【两次同构地犯错】：★ 改一处、留一处。
  ① 修假阴性时开大了假阳性
  ② 改 BAD 措辞时留了 PASS 措辞
⇒ ★★ 而收尾又查明：机检从轮 65 红到轮 68，★ 我【四轮没看见】。
★★★ 故那条教训是：**我不缺发现的能力，缺的是【每次改完，回头把同类的地方都看一遍】。**
⇒ 本器把"回头看一眼"这一步【机械化】。

它比 grep 多做的一件事（★ 关键）
──────────────────────────────────────
★ 它【分层报出】每一处命中是落在：
    · 【代码】里（去掉注释与字符串之后仍在）  ⇒ ★ 真需要改
    · 【注释或字符串】里                        ⇒ ○ 多半是说明文字（★ grep 会误报这一层）
★★ 这一分层来自轮 67 的实证：纯 grep 会把【文档串里的示例】也报出来。

★ 本器自陈三条盲点
  ① 它按【字面】找 ⇒ 改写过、同义不同字的同类处【它找不到】（★ 这是它的根本边界）
  ② "代码/注释"分层靠 tokenize ⇒ 语法有问题的文件会退回"整文件"，★ 那一层会变粗
  ③ ★ 它【只列，不判】⇒ 哪一处该改仍须人读
"""
from __future__ import annotations
import io
import pathlib
import sys
import tokenize

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SEAT = pathlib.Path(__file__).resolve().parent.parent


def strip_comments_strings(src: str):
    """返回 (去掉注释与字符串的源码, 是否成功)。失败则原样返回并标 False。"""
    toks = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            toks.append(tok)
    except Exception:
        return src, False
    kept = [t for t in toks if t.type not in (tokenize.COMMENT, tokenize.STRING)]
    try:
        return tokenize.untokenize(kept), True
    except Exception:
        return src, False


def main() -> int:
    if len(sys.argv) < 2:
        print("用法：python audit_wording_siblings.py <要找的字面> [<第二个> ...]")
        print("  例：python audit_wording_siblings.py 缺编码块 有编码块")
        print("  ★ 它会分成【代码里的命中】与【注释/字符串里的命中】两层报出。")
        return 2
    needles = sys.argv[1:]
    print("═══ 同类处查找：%s ═══" % "、".join(needles))
    print("  ★ 分层：① 代码里（去注释/字符串后仍在）⇒ 真要改  ② 注释/字符串里 ⇒ 多半是说明文字")
    print()
    ext = (".py", ".md", ".json", ".led", ".txt", ".mjs", ".ts", ".js")
    files = [p for p in SEAT.rglob("*")
             if p.is_file() and p.suffix.lower() in ext
             and not any(x in p.parts for x in ("handshake", "__pycache__", "_retired", ".git"))]
    code_hits, text_hits, fallback = [], [], []
    for p in files:
        try:
            raw = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if not any(n in raw for n in needles):
            continue
        rel = str(p.relative_to(SEAT))
        if p.suffix.lower() == ".py":
            code, ok = strip_comments_strings(raw)
            if not ok:
                fallback.append(rel)
            for n in needles:
                if n in code:
                    code_hits.append((rel, n, "代码"))
                elif n in raw:
                    text_hits.append((rel, n, "注释/字符串"))
        else:
            for n in needles:
                if n in raw:
                    text_hits.append((rel, n, "文本件"))
    print("  ── ① 代码里的命中 = %d ──" % len(code_hits))
    for rel, n, _ in code_hits[:40]:
        print("     ★ [%s] %s" % (n, rel))
    print()
    print("  ── ② 注释/字符串/文本件里的命中 = %d ──" % len(text_hits))
    for rel, n, _ in text_hits[:40]:
        print("     ○ [%s] %s" % (n, rel))
    if len(text_hits) > 40:
        print("     …共 %d 处" % len(text_hits))
    print()
    if fallback:
        print("  ── ③ ★ tokenize 失败（分层变粗）的文件 = %d ──" % len(fallback))
        for rel in fallback[:10]:
            print("     ☆ %s" % rel)
        print()
    print("  ═══ 判定 ═══")
    print("     ★ 代码里的命中 = %d ⇒ ★ 这些是【真需要改】的候选" % len(code_hits))
    print("     ○ 其余 = %d ⇒ ★ 多半是说明文字（★ grep 会把这些也报出来）" % len(text_hits))
    print("     ★ 本器三条盲点：① 按字面找 ⇒ 同义不同字的同类处找不到 ② 分层靠 tokenize、失败即变粗 ③ 只列不判")
    return 0


if __name__ == "__main__":
    sys.exit(main())
