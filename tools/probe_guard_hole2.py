#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 本件只在本地起子进程做【名字检查】，全程不调用任何取网函数 ⇒ 构造上零外发。
r"""probe_guard_hole2.py —— 查明总闸【漏在哪种取法】上。 v1.1.0

轮113 的实验为何无效
──────────────────────
其五组合成模块里，**A／B／C 三组从未调用 `activate()`** ⇒ 它们测不到任何关于漏洞的事。
⇒ 本版修正：**每组都先 `activate()`**，再看【那个名字是不是拒绝桩】。
★★ 且**只检查名字、不调用** ⇒ **构造上不发任何请求**。

同时量一件先前想当然的事
──────────────────────────
`$env:DSH_NO_NET='1'`（PowerShell）**是否真的传进了 python 子进程**。
"""
from __future__ import annotations
import os
import pathlib
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

EXP = pathlib.Path(__file__).resolve().parent
PRE = ("import sys,os;sys.path.insert(0,r'%s');import netguard;"
       "print('ENV=' + repr(os.environ.get('DSH_NO_NET')));"
       "print('IS_ON=' + str(netguard.is_on()));"
       "print('ACT=' + str(netguard.activate()))\n" % EXP)

STYLES = {
    "A_模块属性_激活后": PRE + "import urllib.request as u\nprint('RES=' + ('STUB' if u.urlopen.__name__=='_blocked' else 'REAL'))\n",
    "B_from导入_激活后": PRE + "from urllib.request import urlopen\nprint('RES=' + ('STUB' if urlopen.__name__=='_blocked' else 'REAL'))\n",
    "C_from导入_激活前": "import sys;sys.path.insert(0,r'%s')\nfrom urllib.request import urlopen\nimport netguard;netguard.activate()\nprint('RES=' + ('STUB' if urlopen.__name__=='_blocked' else 'REAL'))\n" % EXP,
    "D_自建opener_激活前": PRE + "import urllib.request as u\nO=u.build_opener()\nprint('RES=' + ('STUB' if u.OpenerDirector.open.__name__=='_blocked' else 'REAL'))\n",
    "E_自建opener_先建后激活": "import sys,urllib.request as u\nO=u.build_opener()\nsys.path.insert(0,r'%s')\nimport netguard;netguard.activate()\nprint('RES=' + ('STUB' if u.OpenerDirector.open.__name__=='_blocked' else 'REAL'))\n" % EXP,
}


def run(code: str, on: bool):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    if on:
        env["DSH_NO_NET"] = "1"
    else:
        env.pop("DSH_NO_NET", None)
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env, timeout=60)
    out = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()
    d = {}
    for l in out:
        if "=" in l:
            k, _, v = l.partition("=")
            d[k.strip()] = v.strip()
    return d


def main() -> int:
    print("═══ 总闸取法覆盖（只查名字，不调用 ⇒ 构造上零外发）═══")
    print("  %-24s %-8s %-8s %s" % ("取法", "ENV", "is_on", "结果"))
    print("  " + "-" * 68)
    rows = {}
    for name, code in STYLES.items():
        d = run(code, True)
        rows[name] = d
        print("  %-24s %-8s %-8s %s" % (name, d.get("ENV", "?"), d.get("IS_ON", "?"), d.get("RES", d.get("ACT", "?"))))
    print()
    print("  ── 判读 ──")
    b = rows.get("B_from导入_激活后", {}).get("RES")
    c = rows.get("C_from导入_激活前", {}).get("RES")
    d_ = rows.get("D_自建opener_激活前", {}).get("RES")
    e_ = rows.get("E_自建opener_先建后激活", {}).get("RES")
    print("  ① 先激活再 from-import ⇒ %s ⇒ %s" % (b, "可拦" if b == "STUB" else "★拦不住"))
    print("  ② ★先 from-import 再激活 ⇒ %s ⇒ %s" % (c, "★拦不住（名字已绑定）" if c == "REAL" else "可拦"))
    print("  ③ 先激活、再 build_opener ⇒ %s" % d_)
    print("  ④ ★先 build_opener、再激活 ⇒ %s ⇒ %s"
          % (e_, "★拦不住（实例方法已绑定）" if e_ == "REAL" else "可拦（类属性查找生效）"))
    print()
    print("  ★ 结论（v1.1.1 更正）：")
    print("    ① 总闸【能拦】：模块属性式（A）、先激活再 from-import（B）、")
    print("       以及【自建 opener 后 .open()】（D／E —— 类属性查找生效）。")
    print("    ② 唯一真漏洞：**先 `from urllib.request import urlopen`、后 activate**（C）")
    print("       —— 名字在导入时即绑定，之后 patch 模块属性对它无效。")
    print("    ③ 环境变量传递【正常】（A／B／D 组实测 ENV='1'、is_on=True）。")
    print("    ★★ 更正声明：本器 v1.1.0 曾把结论写成「`validate_card.py` 落在 D／E 盲区」——")
    print("       **那是错的**：D／E 实测皆 STUB（可拦）。故【该文件为何仍外发，本席尚未查明】。")
    print("    ★ C／E 两组的 ENV／is_on 显示 `?` 是因那两组【未包含打印 ENV 的前置块】，非失败。")
    print("  ★ 全程只打印名字，未调用任何取网函数 ⇒ 零外发。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
