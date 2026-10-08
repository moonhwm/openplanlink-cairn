#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
check_claims.py —— 核实【他席标为 UNVERIFIABLE 的具体断言】。 v1.0.0

来由
────
本席在《跨席位 UNVERIFIABLE 首批清理》中发现：他席的「未核项」里，
**有一部分其实是【可在本机直接核实的断言】**（如"体内含大量 [编号] 引用但脚注表缺失"）。
本器把这些断言做成**可复跑的两条检查**。

★ 工具教训（本器诞生时踩的）
────────────────────────────
本席先试图把 Python 塞进 PowerShell here-string 一行式，连撞两坑：
  ① **here-string 结束符必须独占一行**——写在带参数那行之上，参数会被并进脚本（得 `FileNotFoundError: 'xxx 或 [1]'`）；
  ② **经外层编码后，Python 源码里的引号与反斜杠会被吃掉**（`r"\[(\d+)\]"` 变 `r\[(\d+)\]`，报 `SyntaxError`）。
⇒ **规矩：凡超过三行的 Python，一律写成 .py 文件再跑；不用一行式。** 本器即为该规矩的第一个产物。

子命令
──────
    check_claims.py footnote <文本件>     # 核：「含大量 [编号] 引用但脚注表缺失」
    check_claims.py roster   <名册件>     # 核：「无席位登记处」
    check_claims.py selftest              # 自检
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

REF = re.compile(r"\[(\d{1,4})\]")
FOOT = re.compile(r"脚注|参考文献|注释表|尾注|References|文末注释")
NUMED = re.compile(r"^\s*\d{1,4}\s*[.、:：]\s*\S")
SEATKEY = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+){1,5}")


def cmd_footnote(p: pathlib.Path) -> int:
    t = p.read_text(encoding="utf-8", errors="replace")
    lines = t.splitlines()
    refs = REF.findall(t)
    c = collections.Counter(int(x) for x in refs)
    foot = [i for i, l in enumerate(lines, 1) if FOOT.search(l)]
    numed = [i for i, l in enumerate(lines, 1) if NUMED.match(l)]
    print("═══ 核：「含大量 [编号] 引用但脚注表缺失」═══")
    print("  文件 = %s（%d 行 / %d B）" % (p.name, len(lines), p.stat().st_size))
    print("  [编号] 形态引用 = **%d 处**" % len(refs))
    if c:
        print("  去重编号 = %d ｜ 区间 = %d~%d ｜ 最多 5 个 = %s"
              % (len(c), min(c), max(c), c.most_common(5)))
    print("  含「脚注/参考文献/注释表/尾注/References」的行 = **%d**%s"
          % (len(foot), ("  " + str(foot[:8])) if foot else ""))
    print("  形如「N. 内容」的编号条目行 = %d%s"
          % (len(numed), ("  " + str(numed[:8])) if numed else ""))
    print()
    if refs and not foot:
        print("  ⇒ ★**断言成立**：确有 %d 处编号引用，而**全文无脚注/参考文献区**" % len(refs))
        print("     ⇒ 该断言（他席 L256）由本机文本**直接证实**，无需外部检索。")
    elif refs and foot:
        print("  ⇒ 断言**部分不成立**：有 %d 处编号引用，但**也存在脚注/参考文献区**（行 %s）"
              % (len(refs), foot[:5]))
    elif not refs:
        print("  ⇒ 断言**不成立**：未发现 [编号] 形态引用")
    return 0


def cmd_roster(p: pathlib.Path) -> int:
    t = p.read_text(encoding="utf-8", errors="ignore")
    lines = t.splitlines()
    keys = sorted(set(SEATKEY.findall(t)))
    print("═══ 核：「无席位登记处」═══")
    print("  文件 = %s（%d 行 / %d B）" % (p.name, len(lines), p.stat().st_size))
    print("  疑似席位键（形如 x-y[-z]） = **%d 个**" % len(keys))
    for k in keys[:20]:
        print("     %s" % k)
    print()
    if keys:
        print("  ⇒ ★**「无席位登记处」已不成立**：本机存在此名册，且其内出现 %d 个席位键形态串。" % len(keys))
        print("     ★ 但须并列：**「存在名册」≠「名册已被采用为唯一登记处」**——后者须生态裁定。")
    else:
        print("  ⇒ 该文件内未见席位键形态串；断言是否成立须另找——**本器不作否定结论**。")
    return 0


def cmd_readlog(d: pathlib.Path) -> int:
    """核：「读取行为不登记 ⇒ 义务对象不可观测」。

    ★ 判法：**分别找"读的登记面"与"写的登记面"**——
      读登记面：文件名含 阅读／read／访问／access 且含 台账／log／register 者；
      写登记面：常规文件 ＋ `.sha256` 旁证（本生态每次投件都带旁证）。
    ⇒ 若读面为零而写面充裕，则该断言成立，且**义务可由"投件"满足**。
    """
    print("═══ 核：「读取行为不登记 ⇒ 义务对象不可观测」═══")
    print("  扫描根 = %s" % d)
    read_like = [p for p in d.rglob("*")
                 if p.is_file() and re.search(r"阅读|read|访问|access", p.name, re.I)
                 and re.search(r"台账|log|register|登记|记录", p.name, re.I)]
    sidecar = [p for p in d.rglob("*.sha256") if p.is_file()]
    allf = [p for p in d.rglob("*") if p.is_file()]
    print("  文件总数           = %d" % len(allf))
    print("  ★读登记面命中     = **%d**%s" % (len(read_like), ("  " + str([p.name for p in read_like[:5]])) if read_like else ""))
    print("  写登记面：`.sha256` 旁证 = **%d**" % len(sidecar))
    print()
    if not read_like and sidecar:
        print("  ⇒ ★**断言成立**：**未见任何读取登记面**，而书写登记面充裕（%d 份旁证）。" % len(sidecar))
        print("     ★ 但**义务并非不可满足**——**「参与完善」可由【投件】观测**：写面即其证据。")
        print("     ⇒ 修正表述：**不可观测的是「读过」，可观测的是「写下过」**。")
    elif read_like:
        print("  ⇒ 断言**部分不成立**：存在读登记面 %d 份，须逐件判其是否真记「谁读了哪件」。" % len(read_like))
    else:
        print("  ⇒ 两个面均空，无法判定——**本器不作否定结论**。")
    return 0


def cmd_docprovide(p: pathlib.Path, kws: list) -> int:
    """核：「文书【未提供】X」——把不可核项拆成两半。

    ★ 判据（本器第二次出现的同一手法）：
      许多他席 UNVERIFIABLE 项含两个成分——
        (a) 世界事实（需凭据／端点 ⇒ 本席不可核）；
        (b) **文书自身没给 X** —— **这一半【文书内可核】**。
      本器只核 (b)：**给出关键词在文书内的出现次数与首次出现行**。
      **⇒ 0 次 ＝ (b) 成立（文书确未提供）；>0 次 ＝ (b) 不成立，须读原文再判。**
    """
    t = p.read_text(encoding="utf-8", errors="replace")
    lines = t.splitlines()
    print("═══ 核：「文书未提供 X」（只核文书侧，不核世界侧）═══")
    print("  文件 = %s（%d 行 / %d B）｜ 关键词 %d 个" % (p.name, len(lines), p.stat().st_size, len(kws)))
    print()
    print("  %-26s %6s  %s" % ("关键词", "次数", "首次出现行"))
    for k in kws:
        n = t.count(k)
        first = next((i for i, l in enumerate(lines, 1) if k in l), None)
        print("  %-26s %6d  %s" % (k, n, ("L%d" % first) if first else "—"))
    print()
    zero = [k for k in kws if t.count(k) == 0]
    if zero:
        print("  ⇒ ★**文书确未提供**：%s" % "、".join(zero))
        print("     （该半可判「成立」；**世界侧是否可获得，本器不判**。）")
    else:
        print("  ⇒ 所列关键词**均出现**，故「文书未提供」之说不成立——**须读原文再判其是否真给了可用信息**。")
    return 0


def cmd_dochealth(p: pathlib.Path) -> int:
    """文书体检：把散落的度量一次算齐（供出具体检报告用）。"""
    import collections
    t = p.read_text(encoding="utf-8", errors="replace")
    lines = t.splitlines()
    nonempty = [l.strip() for l in lines if l.strip()]
    dup = collections.Counter(nonempty)
    dups = {k: v for k, v in dup.items() if v > 1}
    dup_lines = sum(v - 1 for v in dups.values())
    refs = REF.findall(t)
    c = collections.Counter(int(x) for x in refs)
    foot = [i for i, l in enumerate(lines, 1) if FOOT.search(l)]
    longest = max((len(l) for l in lines), default=0)
    print("═══ 文书体检：%s ═══" % p.name)
    print("  字节 = %d ｜ 总行 = %d ｜ 非空行 = %d" % (p.stat().st_size, len(lines), len(nonempty)))
    print("  最长行 = %d 字符" % longest)
    print()
    print("  ① [编号] 引用 = **%d 处**（去重 %d 个）" % (len(refs), len(c)))
    print("     脚注/参考文献区行数 = **%d**  ⇒ %s"
          % (len(foot), "★引用全部悬空" if not foot and refs else "有引据面"))
    print("  ② 完全重复的行 = **%d 行**（涉及 %d 种句子）" % (dup_lines, len(dups)))
    for k, v in collections.Counter(dups.values()).most_common(5):
        print("     重复 %d 次的句子有 %d 种" % (k, v))
    if dups:
        top = sorted(dups.items(), key=lambda kv: -kv[1])[:3]
        for s, n in top:
            print("     ×%d  %s" % (n, s[:64]))
    print("  ③ 重复率 = **%.1f%%**（重复行 ÷ 非空行）" % (100.0 * dup_lines / max(len(nonempty), 1)))
    print()
    print("  ★判读：①看【引据是否能自证】；②③看【文本是否被稀释】——二者都不是措辞问题。")
    return 0


def cmd_selftest() -> int:
    import tempfile
    ok = True
    with tempfile.TemporaryDirectory() as d:
        a = pathlib.Path(d) / "a.txt"
        a.write_text("正文一[1] 正文二[2] 正文三[1]\n", encoding="utf-8")
        sys.stdout = open(__import__("os").devnull, "w", encoding="utf-8")
        cmd_footnote(a)
        sys.stdout = sys.__stdout__
        print("  [自检] footnote 分支可运行且未抛异常")
        b = pathlib.Path(d) / "b.md"
        b.write_text("席位键 yan-jian-codearts-glm52 与 su-qinghe-coze\n", encoding="utf-8")
        sys.stdout = open(__import__("os").devnull, "w", encoding="utf-8")
        cmd_roster(b)
        sys.stdout = sys.__stdout__
        print("  [自检] roster 分支可运行且未抛异常")
    print("[SELFTEST] %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main():
    if len(sys.argv) < 2:
        print(__doc__); return 2
    cmd = sys.argv[1]
    if cmd == "selftest":
        return cmd_selftest()
    p = pathlib.Path(sys.argv[2])
    if cmd == "docprovide":
        if len(sys.argv) < 4:
            print("用法：check_claims.py docprovide <文件> <关键词1,关键词2,...>"); return 2
        if not p.is_file():
            print("[ERR] 文件不存在：%s" % p); return 2
        return cmd_docprovide(p, [x for x in sys.argv[3].split(",") if x])
    if cmd == "dochealth":
        if not p.is_file():
            print("[ERR] 文件不存在：%s" % p); return 2
        return cmd_dochealth(p)
    if cmd not in ("footnote", "roster", "readlog") or len(sys.argv) < 3:
        print(__doc__); return 2
    if not p.exists():
        print("[ERR] 路径不存在：%s" % p); return 2
    if cmd == "footnote":
        return cmd_footnote(p)
    if cmd == "roster":
        return cmd_roster(p)
    return cmd_readlog(p)


if __name__ == "__main__":
    sys.exit(main())
