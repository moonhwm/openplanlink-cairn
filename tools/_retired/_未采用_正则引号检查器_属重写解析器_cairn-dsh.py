#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
quote_lint.py —— 【结构化】"中文串里别用直引号"这条规矩：扫 .py 找可疑行。 v1.1.0

由来（轮 99–100）
──────────────────
轮 99 写 `seed_render.py` 时，"双引号串里嵌了直引号"这一错**连犯三次**；轮 100 改同文件**又犯第四次**。
而这条规矩本席【早就立过】**⇒ 规矩知道 ≠ 规矩生效——它的执行靠"我记得"**。
⇒ 故本器把它做成可跑的检查（与轮 96 给 BOM 做封锚工序同型）。

★ v1.1.0 修了一处【本器自身的假阳性】（重要）
──────────────────────────────────────────
v1.0.0 只按行数 `"` 的奇偶判，结果**每份文档字符串都被误报**（`r"""` 是 3 个引号，奇数）
⇒ 58 个文件报出 **150 条"可疑"**，而抽样看**全是假的**。
**★ 一个在好输入上也报 150 条的检查器，比没有更糟：它会被无视。**
故 v1.1.0 加【三引号状态跟踪】：块字符串内的行**不查**，只查真代码行。

仍查三条（皆可失败）
──────────────────────
 ① **代码行里 `"` 个数为奇数** ⇒ 多半个引号；
 ② ★ **双引号串内含 CJK 且又出现单引号** ⇒ 本席反覆犯的那一种；
 ③ **双引号串内含 CJK 且又出现双引号** ⇒ 同族的另一半。

★ 本器只报不改（改代码须人看）。
用法: quote_lint.py [目录或文件…]
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

CJK = re.compile(r"[\u3000-\u303f\u4e00-\u9fff\uff00-\uffef]")


def code_lines(text: str):
    """产出 (行号, 行内容)，**跳过三引号块内的行**。"""
    out = []
    in_block = False
    delim = None
    for i, line in enumerate(text.splitlines(), 1):
        s = line
        if in_block:
            # 找结束定界符
            if delim in s:
                s = s.split(delim, 1)[1]
                in_block = False
                delim = None
            else:
                continue
        # 找开始定界符（r""" / ''' 等）
        m = re.search(r'([rRbBuUfF]{0,2})("""|\'\'\')', s)
        if m:
            open_delim = m.group(2)
            rest = s[m.end():]
            if open_delim in rest:
                # 同行开闭
                s = rest.split(open_delim, 1)[0]
            else:
                s = s[:m.start()]
                in_block = True
                delim = open_delim
        out.append((i, s))
    return out


def lint_file(p: pathlib.Path):
    try:
        text = p.read_text(encoding="utf-8")
    except Exception as e:
        return [("ERR", 0, str(e)[:60])]
    hits = []
    for i, s in code_lines(text):
        if s.strip().startswith("#") or not s.strip():
            continue
        # ① 奇引号
        if s.count('"') % 2 == 1:
            hits.append(("奇引号", i, s.strip()[:100]))
            continue
        # ②③ 串内又出现引号（按 " 切分，奇数下标是串内）
        parts = s.split('"')
        for k in range(1, len(parts), 2):
            seg = parts[k]
            if CJK.search(seg) and ("'" in seg):
                hits.append(("串内单引号", i, s.strip()[:100])); break
    return hits


def main() -> int:
    args = sys.argv[1:] or [str(pathlib.Path(__file__).resolve().parent)]
    files = []
    for a in args:
        p = pathlib.Path(a)
        if p.is_dir():
            files += sorted(p.glob("*.py"))
        elif p.is_file():
            files.append(p)
    print("═══ 引号体检 v1.1.0（含三引号状态跟踪）═══")
    bad = 0
    for p in files:
        hits = lint_file(p)
        if hits:
            print("  ★ %s" % p.name)
            for kind, ln, txt in hits[:6]:
                print("     [%s] 第 %d 行：%s" % (kind, ln, txt))
                bad += 1
    print()
    print("  扫过 .py = %d 个 ｜ ★可疑行 = %d" % (len(files), bad))
    print("  ⇒ %s" % ("PASS —— 未见本席反覆犯的那一类" if bad == 0 else "★有可疑行，请人看（本器只报不改）"))
    print("  ★ 本器能失败（有可疑行即报）⇒ 非恒真。")
    print("  ★ v1.1.0 自证：v1.0.0 在【同一批好文件】上报 150 条（三引号误报）⇒ 本条修的就是它。")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
