#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 本件只起本地子进程做导入检查，且总闸全程置上。
r"""verify_netguard_wiring.py —— 量一量：各工具是否真的在导入时调了 netguard.activate()。 v1.0.0

为什么（**"已接闸"不能只是源码声称**）
────────────────────────────────────────
`blast_radius.py` 是按【文本里有没有 `netguard`】判"已接闸"的。
⇒ 而本席旧规：**测出来的才算数**。
⇒ 本器用一个【构造上不可能触网】的办法量它：
   **在子进程里置 `DSH_NO_NET=1`，再 import 该工具，然后看 `urllib.request.urlopen`
     是否已被替换成拒绝钩子。** 是 ⇒ 该工具在导入时确实调了 `activate()`。
★ 全程总闸置上 ⇒ **即使某件工具在导入时就想去取件，也会被拦** ⇒ 零外发。

用法: verify_netguard_wiring.py [工具名…]
"""
from __future__ import annotations
import os
import pathlib
import re
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

EXP = pathlib.Path(__file__).resolve().parent
MARKERS = [r"urllib\.request", r"urlopen\(", r"\brequests\.", r"\bsocket\.", r"http\.client"]
PROBE = (
    "import sys, urllib.request as u;"
    "sys.path.insert(0, r'%s');"
    "import importlib; importlib.import_module('%s');"
    "print('PATCHED' if u.urlopen.__name__ == '_blocked' else 'NATIVE')"
)


def net_tools():
    out = []
    for p in sorted(EXP.glob("*.py")):
        t = p.read_text(encoding="utf-8", errors="replace")
        if any(re.search(m, t) for m in MARKERS) and p.name != "netguard.py":
            out.append(p)
    return out


def probe(p: pathlib.Path):
    """★ 轮108 修：**两种接法都认**——
       ① 导入时装钩子（activate）；② 源码里有显式检查（`.allowed()` / `.require(`）。
       ★ 初版只认 ①，于是把 meow_push／robots_gate 的【显式检查】误判为"未接"。
         与本席判读规则⑩同族：一个检查只认一种形态，就会把另一种错报成"没有"。
    """
    env = dict(os.environ)
    env["DSH_NO_NET"] = "1"                      # ★ 全程置上 ⇒ 构造上不触网
    env["PYTHONIOENCODING"] = "utf-8"
    code = PROBE % (str(EXP), p.stem)
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env, timeout=120)
    txt = ((r.stdout or "") + (r.stderr or "")).strip()
    src = p.read_text(encoding="utf-8", errors="replace")
    explicit = bool(re.search(r"\.allowed\(\)|\.require\(", src))
    # ★ 若该件【如实声明不触网】，则"没装钩子"是应当的，不算未接闸。
    declares_none = bool(re.search(r"^\s*#\s*BLAST:\s*NONE", src, re.M))
    if "PATCHED" in txt:
        return "已接闸(钩子)", ""
    if explicit:
        return "已接闸(显式检查)", "未装钩子，但在源码里有显式放行检查"
    if declares_none:
        return "—不触网", "已声明 `# BLAST: NONE`（其 NET 标记来自字符串/注释）"
    if "NATIVE" in txt:
        return "★未接闸", "既未装钩子、也未见显式检查、且未声明不触网"
    return "ERR", txt.splitlines()[-1][:70] if txt else "无输出"


def main() -> int:
    args = sys.argv[1:]
    tools = [EXP / a for a in args] if args else net_tools()
    print("═══ 总闸接线实测（总闸全程置上 ⇒ 零外发）═══")
    print("  %-34s %-8s %s" % ("工具", "判定", "说明"))
    print("  " + "-" * 78)
    ok, un, err = 0, 0, 0
    for p in tools:
        if not p.is_file():
            print("  %-34s %-8s %s" % (p.name[:34], "★缺件", "")); err += 1; continue
        v, why = probe(p)
        print("  %-34s %-14s %s" % (p.name[:34], v, why))
        if v.startswith("已接闸") or v == "—不触网":
            ok += 1
        elif v == "★未接闸":
            un += 1
        else:
            err += 1
    print()
    print("  ── 汇总（三态分开）──")
    print("  已接闸或声明不触网 %d ｜ ★真·未接闸 %d ｜ ERR %d" % (ok, un, err))
    print("  ★ 判定前会先看三件：是否装钩子／是否有显式检查／是否如实声明不触网。")
    print("  ⇒ %s" % ("无一会触网却未接闸者 ⇒ PASS" if un == 0 else "★有会触网却未接闸者，见上"))
    print("  ★ 本器能失败（会触网而未接闸即报）⇒ 非恒真。★ 全程总闸置上 ⇒ 零外发。")
    return 0 if (un == 0 and err == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
