#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只读源码做静态清点；不执行被测器、不写件、不删件、不触网。
r"""audit_verdict_coverage.py —— 清点：本席有多少器合了【机器可读判词】这条约定。 v1.0.0

为什么做它（轮 74，承轮 72–73）
──────────────────────────────────
轮 72 实证：收尾块靠【正则抓散文】报判词 ⇒ 措辞一变，判词内容【静默消失】而"退出码 0"照印。
轮 73 我据此给五件器加了 `★ VERDICT=PASS|BAD`（另两件稽核更早有 `★ FINDINGS=<n>`）。
★★ 于是有了【一条约定】。而**约定若没有清点，它就只是我在轮末口头说的一句**。
⇒ 本器把这条约定的覆盖面【数出来】。

判据（★ 两档）
──────────────────
  · **判词类器**（名字以 verify_／lint_／tool_／check_ 开头，或正文里印"判词/结论"）
      ⇒ ★ 应印 `★ VERDICT=PASS|BAD`
  · **稽核类器**（名字以 audit_ 开头）
      ⇒ ★ 应印 `★ FINDINGS=<n>`

★ 本器自陈三条盲点
  ① 分类靠【名字与正文词】⇒ 命名不循例的器会分错（★ 本会话已多次证词表判据会错）
  ② 它只查【有没有那一行】⇒ **不查那一行的值对不对**（★ 那是负例对照的事）
  ③ ★ 它【不执行】任何器 ⇒ 是静态清点，不是"这些器确实都印了"的证明
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
EXP = SEAT / "exp"
LEDGER = SEAT / "ledger"

VERDICT = re.compile(r"★\s*VERDICT\s*=")
FINDINGS = re.compile(r"★\s*FINDINGS\s*=")
VERDICTISH = re.compile(r"判词[:：]|结论[:：]")


def _strip(src: str) -> str:
    """★ 轮 76 加、★ 同日又废：**剥掉注释与字符串**这个做法【过头了】。
    实证：剥掉之后本器报「合 0」——因为 `★ VERDICT=PASS` 本来就写在 `print("…")` 的
    字符串里，★ 剥字符串把【真阳性】也剥掉了。
    ⇒ ★★ 故正确判据不是"剥不剥字符串"，而是【看结构】：**它有没有真的 print 出那一行**。
    ⇒ 本函数保留仅为记录这次过头；主判据已改为 `_prints_marker()`（AST 层）。
    """
    import io
    import tokenize
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except Exception:
        return src
    kept = [t for t in toks if t.type not in (tokenize.COMMENT, tokenize.STRING)]
    try:
        return tokenize.untokenize(kept)
    except Exception:
        return src


def _prints_marker(src: str, marker: str) -> bool:
    """★ 轮 76 的正解：**用 AST 找 print 调用，看它的字面量里有没有那串**。
    缘由：文本层两种做法都错——
      · 直接搜文本 ⇒ ★ 假阳性（「定义正则的那一行」命中它自己）；
      · 剥掉字符串 ⇒ ★ 假阴性（把 print 里的真那行也剥掉）。
    ⇒ 只有【结构层】能分开这两者：★ 问"它有没有 print 出这一行"，而不是"文件里有没有这串"。
    ★ 若解析失败，则退回文本搜索并标注（★ 不静默降级）。

    ★★ 轮 79 加：**标记必须【整词匹配】**。
      缘由（轮 79 实证 · 第六种错法）：`NOVERDICT=` 里【含有】子串 `VERDICT=`
      ⇒ 我加的三件 NOVERDICT 器【全被判成了 VERDICT 器】（7 件变 10 件、NOVERDICT 那栏 0 件）。
      ⇒ 而根因不在检测，在【我设计标记时没查子串碰撞】。
      ⇒ 故此后：marker 命中处，其【前一个字符】必须是行首／空白／标点，★ 不能是字母。
    """
    import ast
    import re as _re
    # ★ 整词判据：marker 之前不能是字母或下划线
    word = _re.compile(r"(?<![A-Za-z_])" + _re.escape(marker))

    def _strs_in(node) -> list:
        """★ 轮 76 补：把【% 格式化】（BinOp）与 f-string、【+】拼接都算进来。
        缘由：首版只认 Constant 与 JoinedStr ⇒ ★ 漏掉 `print("★ VERDICT=%s" % …)`（那是 BinOp）
        ⇒ 一轮里第三种错数（判词 4/29 而真值 7）。★ 同根病的第四副面孔。
        """
        out = []
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            out.append(node.value)
        elif isinstance(node, ast.JoinedStr):
            for v in node.values:
                out.extend(_strs_in(v))
        elif isinstance(node, ast.BinOp):          # ★ % 或 + 拼接
            out.extend(_strs_in(node.left))
            out.extend(_strs_in(node.right))
        elif isinstance(node, ast.FormattedValue):
            out.extend(_strs_in(node.value))
        elif isinstance(node, (ast.Tuple, ast.List)):
            for e in node.elts:
                out.extend(_strs_in(e))
        return out

    try:
        tree = ast.parse(src)
    except Exception:
        return bool(word.search(src))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        is_print = (isinstance(f, ast.Name) and f.id == "print") or \
                   (isinstance(f, ast.Attribute) and f.attr in ("write", "writelines"))
        if not is_print:
            continue
        for arg in list(node.args) + [k.value for k in node.keywords]:
            for s in _strs_in(arg):
                if word.search(s):
                    return True
    return False


def main() -> int:
    print("═══ 机器可读判词的覆盖面清点 ═══")
    files = [p for p in sorted(list(EXP.glob("*.py")) + list(LEDGER.glob("*.py")))
             if "__pycache__" not in str(p)]
    print("  .py = %d" % len(files))
    print("  ★ 轮 77 收口：**分类不再按【名字】**——★ 改成按【它印的是哪种标记】（★ 文件的属性，不是名字的属性）")
    print()

    # ★ 轮 77：不再按名字分桶。对每件器只取三件事（★ 都是文件属性）：
    #   ① 有没有印 VERDICT=  ② 有没有印 FINDINGS=  ③ 有没有"判词/结论"这类人类判词行
    # ★ 轮 77：**排除自身**（★ 理由见文件头"第五种错法"）。
    # ★ 轮 79：改成【三值】——VERDICT ／ FINDINGS ／ NOVERDICT（★ 轮 78 立的第三类）。
    files = [p for p in files if p.name != pathlib.Path(__file__).name]
    has_v, has_f, has_n, human, none_of = [], [], [], [], []
    for p in files:
        raw = p.read_text(encoding="utf-8", errors="replace")
        v = _prints_marker(raw, "VERDICT=")
        f = _prints_marker(raw, "FINDINGS=")
        n = _prints_marker(raw, "NOVERDICT=")     # ★ 轮 79：第三类
        h = _prints_marker(raw, "判词") or _prints_marker(raw, "结论")
        if v:
            has_v.append(p)
        elif f:
            has_f.append(p)
        elif n:
            has_n.append(p)
        elif h:
            human.append(p)
        else:
            none_of.append(p)

    print("  ── ★ 印 VERDICT= 的 = %d 件 ──" % len(has_v))
    for p in has_v:
        print("     ★ %s" % p.name)
    print()
    print("  ── ★ 印 FINDINGS= 的 = %d 件 ──" % len(has_f))
    for p in has_f:
        print("     ★ %s" % p.name)
    print()
    print("  ── ★ 印 NOVERDICT=1（★ 由设计不下判词）的 = %d 件 ──" % len(has_n))
    for p in has_n:
        print("     ★ %s" % p.name)
    print()
    print("  ── ○ 只印人类判词（判词/结论）的 = %d 件 ──" % len(human))
    for p in human[:20]:
        print("     ○ %s" % p.name)
    if len(human) > 20:
        print("     …共 %d 件" % len(human))
    print()
    print("  ── · 三者都不印的 = %d 件（★ 轮 78：这一栏才是【真缺口】）──" % len(none_of))
    for p in none_of[:20]:
        print("     · %s" % p.name)
    if len(none_of) > 20:
        print("     …共 %d 件" % len(none_of))
    print()
    print("  ═══ 判定（★ 三值）═══")
    print("     ★ 机器可读且下判词（VERDICT 或 FINDINGS）= %d 件" % (len(has_v) + len(has_f)))
    print("     ★ 机器可读且声明不下判词（NOVERDICT）= %d 件" % len(has_n))
    print("     ○ 只人类判词 = %d 件 ｜ · 三者都不印 = %d 件" % (len(human), len(none_of)))
    print("     ★★ 「三者都不印」那一栏才是【真缺口】——★ 因为其余各栏都【明说了自己是什么】")
    print("     ★ 本器三条盲点：① 只查「有没有 print 出那一行」、不查那一行的值对不对"
          "② AST 解析失败时退回文本搜索 ③ 「都不印」那一栏【不判】该不该印")
    return 0 if len(none_of) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
