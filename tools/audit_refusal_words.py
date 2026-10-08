#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只读源码做静态清点；不执行被测器、不写件、不删件、不触网。
r"""audit_refusal_words.py —— 清点：全席【表示拒绝】用了多少种词。 v1.0.0

为什么做它（轮 85，承轮 84）
──────────────────────────────
轮 84 我给 edit_declaration.py 的 11 处拒绝加了同一个 token `★ REFUSE`——
★ 而当时明写边界：「★ 别的器用的是另一种写法 ⇒ ★ 未统一」。
⇒ 本器去量：**全席有多少种"拒绝"的写法。**

★ 为什么这件事重要（★ 轮 84 的实证）
  ★ 我因为过滤词只有「拒写」，**没看见**落于「拒改」的两次拒绝。
  ⇒ **一个意思若说法不止一种，靠词表读的人必然漏掉其中一些。**

★ 本器自陈三条盲点
  ① 它按【正则在字符串里】找 ⇒ ★ 它自己也**可能命中文档串里的示例**（★ 轮 67／76 已栽过两次）
  ② 它只清点措辞 ⇒ ★ **不判哪一处是"真拒绝路径"、哪一处只是描述**
  ③ ★ 它【不改】任何东西——★ 收不收、怎么收仍须人定
"""
from __future__ import annotations
import collections
import pathlib
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SEAT = pathlib.Path(__file__).resolve().parent.parent
EXP = SEAT / "exp"
LEDGER = SEAT / "ledger"

# ★ "拒绝"的各种说法（★ 收的时候要比找的时候宽，否则量不到）
WORDS = re.compile(r"拒绝|拒写|拒改|拒收|REFUSE|拒绝写入|不予|驳回|不收|不写")


def main() -> int:
    print("═══ 全席「拒绝」措辞清点 ═══")
    files = [p for p in sorted(list(EXP.glob("*.py")) + list(LEDGER.glob("*.py")))
             if "__pycache__" not in str(p)]
    print("  .py = %d" % len(files))
    print()

    counts = collections.Counter()
    per_file = collections.defaultdict(collections.Counter)
    for p in files:
        t = p.read_text(encoding="utf-8", errors="replace")
        for m in WORDS.finditer(t):
            w = m.group(0)
            counts[w] += 1
            per_file[p.name][w] += 1

    print("  ── ★ 各措辞的出现次数 ──")
    for w, n in counts.most_common():
        print("     %-10s %4d 次" % (w, n))
    print()
    print("  ★ 不同措辞数 = %d 种" % len(counts))
    print()
    print("  ── ★ 含 REFUSE 的器 ──")
    withref = [n for n, c in per_file.items() if c.get("REFUSE")]
    for n in withref:
        print("     ★ %s" % n)
    print()
    print("  ── ○ 有「拒绝类词」但【不含 REFUSE】的器 = %d 件 ──"
          % len([n for n, c in per_file.items() if c and not c.get("REFUSE")]))
    for n, c in sorted(per_file.items()):
        if c and not c.get("REFUSE"):
            print("     ○ %-38s %s" % (n[:38],
                                       "、".join("%s×%d" % (k, v) for k, v in c.most_common(3))))
    print()
    print("  ═══ 判定 ═══")
    print("     ★ 有 REFUSE 的器 = %d 件 ｜ ○ 只有别的说法的 = %d 件"
          % (len(withref), len([n for n, c in per_file.items() if c and not c.get("REFUSE")])))
    print()
    # ★ 轮 85 收紧：**只数【被 print 出来的】拒绝**。
    #   缘由：上面那个"9 种／53 件"【虚高】——★ 多数是【描述】（如 netguard 的"默认拒绝"政策说明），
    #   ★ 不是【拒绝路径】；而过滤器要抓的是【后者】。
    #   ⇒ 判据与轮 76 同：用 AST 找 print 调用，看它的字面量里有没有那些词（★ 整词匹配）。
    import ast

    def _printed(src, pat):
        r = re.compile(pat)
        try:
            tree = ast.parse(src)
        except Exception:
            return bool(r.search(src))
        def _strs(n):
            out = []
            if isinstance(n, ast.Constant) and isinstance(n.value, str):
                out.append(n.value)
            elif isinstance(n, ast.JoinedStr):
                for v in n.values:
                    out.extend(_strs(v))
            elif isinstance(n, ast.BinOp):
                out.extend(_strs(n.left)); out.extend(_strs(n.right))
            elif isinstance(n, ast.FormattedValue):
                out.extend(_strs(n.value))
            elif isinstance(n, (ast.Tuple, ast.List)):
                for e in n.elts:
                    out.extend(_strs(e))
            return out
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                f = node.func
                if (isinstance(f, ast.Name) and f.id == "print") or \
                   (isinstance(f, ast.Attribute) and f.attr in ("write", "writelines")):
                    for a in list(node.args) + [k.value for k in node.keywords]:
                        for s in _strs(a):
                            if r.search(s):
                                return True
        return False

    printed_ref = {}
    for p in files:
        t = p.read_text(encoding="utf-8", errors="replace")
        # ★ 轮 87：**带「★ 说明」标记的 print 不算拒绝路径**。
        #   缘由（轮 86 读出来的）：netguard 的四句含"拒绝"字样，★ 而它们是【政策说明】。
        #   ⇒ 故给这类 print 加标记，本器据此扣除——★ 否则它【每次都把说明算进来】。
        def _is_refusal_print(src: str) -> bool:
            import ast as _a
            pat = re.compile(r"(?<![A-Za-z_])(拒绝|拒写|拒改|拒收|REFUSE|不予|驳回|不收)")
            desc = re.compile(r"★\s*说明")
            try:
                tree = _a.parse(src)
            except Exception:
                return bool(pat.search(src)) and not bool(desc.search(src))
            def _strs(n):
                out = []
                if isinstance(n, _a.Constant) and isinstance(n.value, str):
                    out.append(n.value)
                elif isinstance(n, _a.JoinedStr):
                    for v in n.values:
                        out.extend(_strs(v))
                elif isinstance(n, _a.BinOp):
                    out.extend(_strs(n.left)); out.extend(_strs(n.right))
                elif isinstance(n, _a.FormattedValue):
                    out.extend(_strs(n.value))
                elif isinstance(n, (_a.Tuple, _a.List)):
                    for e in n.elts:
                        out.extend(_strs(e))
                return out
            for node in _a.walk(tree):
                if isinstance(node, _a.Call):
                    f = node.func
                    if (isinstance(f, _a.Name) and f.id == "print") or \
                       (isinstance(f, _a.Attribute) and f.attr in ("write", "writelines")):
                        for a in list(node.args) + [k.value for k in node.keywords]:
                            for s in _strs(a):
                                if pat.search(s) and not desc.search(s):
                                    return True
            return False

        if _is_refusal_print(t):
            printed_ref[p.name] = _printed(t, r"(?<![A-Za-z_])REFUSE")
    print("  ── ★★ 收紧后：会【print 出】拒绝的器 = %d 件 ──" % len(printed_ref))
    yes = sorted(n for n, v in printed_ref.items() if v)
    no = sorted(n for n, v in printed_ref.items() if not v)
    print("     ★ 其中带 REFUSE 的 = %d 件：%s" % (len(yes), "、".join(yes)))
    print("     ○ 不带 REFUSE 的 = %d 件：" % len(no))
    for n in no:
        print("        ○ %s" % n)
    print()
    print("     ⇒ ★ 这 %d 件才是【真候选】——★ 而上面那个 53 是【虚高】（含大量描述）" % len(no))
    print("     ★★ 若「别的说法」多于一种 ⇒ ★ 又一个「一个意思多种说法」的场面（★ 与轮 52／84 同形）")
    print("     ★ 本器三条盲点：① 正则可能命中文档串里的示例 ② 不判真拒绝路径与描述之别 ③ 它不改任何东西")
    return 0


if __name__ == "__main__":
    sys.exit(main())
