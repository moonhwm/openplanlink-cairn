#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只读源码做静态分析；不执行被测器、不删任何件、不触网。
r"""audit_delete_guards.py —— 稽核【删除】：删的是【席位里的路径】还是【临时/实验室里的】。 v1.0.0

★★★ 轮 67 的【实证假阴性】——本器当前的判定【不可信】
────────────────────────────────────────────────────
本器首跑报：「删【席位内路径】的 = 0 件」。
★ 而我【知道那是错的】：轮 66 我亲眼读过 smoke_pipeline.py 会删席位根下的件。
⇒ ★★ 故我做了对照：把副本里的 smoke_pipeline.py 还原成【轮 66 修之前】的写法
   （L108 dst = SEAT/"_smoke_published.md" ／ L109 if dst.exists(): ／ L110 dst.unlink()），
   ★ 而本器【仍报 0 件】。
⇒ ★★★★ 即：**本器对它本该抓的那一处【视而不见】——假阴性，已实证。**

★ 根因（精确）
  它在【含 unlink 的那一行】找 SEAT/／ROOT/ 等字样，★ 而真相是：
    dst = SEAT / "_smoke_published.md"     ← 变量定义在【上一行】
    if dst.exists(): dst.unlink()          ← ★ 这一行【没有 SEAT】
  ⇒ ★★ **变量把"这是席位内路径"这一点带走了，而本器不追变量。**

★ 这条根因可推广
  判断「删的是不是真件」需要【数据流跟踪】（这个变量从哪来），
  ★ 而不是【行内词表匹配】——★ 这正是本会话反复出现的那条（轮 17）：
  **「是否存在某类话」不能用词表判。**

★ 故本器现在的定位
  ★ 它【不是】"删席位件"的判据；★ 它是一个【已证有假阴性的提示器】。
  ★ 保留它，是为了把这次实证【留在案上】——★ 并提醒：**这一栏的 0 不能当结论读。**

★ 本器自陈三条盲点
  ① 只做【静态文本】判断 ⇒ 动态拼出的目标它测不到
  ② ★ 它【不追变量】⇒ 对"目标先赋值、后删除"的写法【必漏】（★ 已实证）
  ③ ★ 它【不执行】任何器 ⇒ 它是【提示】，不是"这些器确实删过真件"的证明
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

DEL = re.compile(r"\.unlink\(|shutil\.rmtree|os\.remove|os\.unlink|\.rmdir\(")
# 席位内目标的信号
SEATISH = re.compile(r"\b(SEAT|ROOT|HERE)\b\s*/")
# 护栏的信号
GUARD = re.compile(r"if\s+\w+\.exists\(\)|preexisting|只删|本次自己造|存在件")


def strip_comments_and_strings(src: str) -> str:
    """★ 轮 68 加：**剥掉注释与字符串**。
    缘由（轮 67 实证的假阳性）：我把一段示例代码写进本器文档串后，
    ★ 本器【报出了自己】——因为它把说明文字当成了代码。
    ⇒ 故匹配前先剥掉 COMMENT 与 STRING token（★ 保留其余一切）。
    ★ 失败时【原样返回】并标记——★ 不静默降级。
    """
    import io
    import tokenize
    out, toks = [], []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            toks.append(tok)
    except Exception:
        return src, False
    for tok in toks:
        if tok.type in (tokenize.COMMENT, tokenize.STRING):
            continue
        out.append(tok)
    try:
        return tokenize.untokenize(out), True
    except Exception:
        return src, False


def seat_bound_names(code: str) -> set:
    """★ 轮 68 加：**一步变量绑定** —— 找出被赋成席位内路径的变量名。
    缘由（轮 67 实证的假阴性）：`dst = SEAT / "x"` 后，`dst.unlink()` 那一行【没有 SEAT】，
    ★ 变量把真相带走了。⇒ 本函数做【一步】绑定（不做完整数据流）：
        X = <SEAT|ROOT|HERE> / …        ⇒ X 记入
        X = <已记入的名字> / …          ⇒ 也记入（允许一层传递）
    ★ 它【不追函数参数、不追返回值】——★ 那是它的边界，写在盲点里。
    """
    names = set()
    for _ in range(2):   # ★ 两层足够覆盖 X = SEAT/…；Y = X/…
        for line in code.splitlines():
            m = re.match(r"\s*([A-Za-z_]\w*)\s*=\s*(.+)$", line)
            if not m:
                continue
            var, rhs = m.group(1), m.group(2)
            if SEATISH.search(rhs) or re.search(r"\b(SEAT|ROOT|HERE)\b", rhs):
                names.add(var)
            elif any(re.search(r"\b%s\b" % re.escape(n), rhs) for n in names):
                names.add(var)
    return names


def decl_of(t: str) -> str:
    m = re.search(r"BLAST:\s*([A-Z_,\s]+)", t[:1500])
    return m.group(1).strip() if m else "（无声明）"


def main() -> int:
    print("═══ 删除稽核：删的是【席位内】还是【临时内】═══")
    tools = [p for p in sorted(EXP.glob("*.py")) if "__pycache__" not in str(p)]
    print("  .py = %d" % len(tools))
    print()
    del_tools, seat_del, temp_del, nolex = [], [], [], []
    for p in tools:
        raw = p.read_text(encoding="utf-8", errors="replace")
        code, ok = strip_comments_and_strings(raw)
        if not ok:
            nolex.append(p.name)
        if not DEL.search(code):
            continue
        del_tools.append(p)
        lines = code.splitlines()
        bound = seat_bound_names(code)       # ★ 轮 68：一步变量绑定
        seatish, guarded = [], False
        for i, line in enumerate(lines):
            if DEL.search(line):
                ctx = "\n".join(lines[max(0, i - 3):i + 1])
                if GUARD.search(ctx):
                    guarded = True
                direct = bool(SEATISH.search(line) or re.search(r"\bSEAT\b", line))
                via_var = any(re.search(r"\b%s\b" % re.escape(n), line) for n in bound)
                if direct or via_var:
                    how = "★ 直接" if direct else "★ 经变量 %s" % ",".join(sorted(bound))[:40]
                    seatish.append((i + 1, "%s ｜ %s" % (how, line.strip()[:70])))
        if seatish:
            seat_del.append((p, decl_of(raw), seatish, guarded))
        else:
            temp_del.append((p, decl_of(raw), guarded))

    print("  ── 会删的器 = %d 件 ──" % len(del_tools))
    print()
    print("  ── ★★ 删【席位内路径】的 = %d 件 ──" % len(seat_del))
    for p, d, s, g in seat_del:
        print("     ★ %-34s 声明 %-8s 护栏 %s" % (p.name[:34], d[:8], "★ 有" if g else "○ 无"))
        for ln, txt in s[:2]:
            print("          L%-4d %s" % (ln, txt))
    print()
    print("  ── ○ 只删【临时/实验室】的 = %d 件 ──" % len(temp_del))
    for p, d, g in temp_del:
        print("     ○ %-34s 声明 %-8s 护栏 %s" % (p.name[:34], d[:8], "有" if g else "无"))
    print()
    print("  ═══ 判定 ═══")
    print("     ★ 删席位内路径而【无护栏】的 = %d 件"
          % len([1 for _, _, _, g in seat_del if not g]))
    print("     ★ 本器三条盲点：")
    print("        ① 只做静态文本判断 ⇒ 动态拼出的目标测不到")
    print("        ② '是不是席位内'按变量名判 ⇒ 命名怪异的会误分类")
    print("        ③ 不执行任何器 ⇒ 它是【提示】，不是'确实删过真件'的证明")
    print("★ NOVERDICT=1 —— 本器只列，★ 不下判词（由设计）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
