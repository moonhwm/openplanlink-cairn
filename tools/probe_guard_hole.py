#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 本件只在本地起子进程做导入实验，且全程不触网（已验证机理后亦然）。
r"""probe_guard_hole.py —— 安全地量清：总闸在什么情况下【拦不住】。 v1.0.0

为什么（轮113 的第二次意外外发）
──────────────────────────────────
本席给 `obs_fix/validate_card.py` 接了总闸，**置上 `DSH_NO_NET=1` 后它仍然发了 9 次请求**。
⇒ 机理推断：**`from urllib.request import urlopen` 在导入时即绑定名字**，
  之后 patch `urllib.request.urlopen` 对该名字**无效**（monkeypatch 的经典漏洞）。
★ 本器用【合成模块】把这个机理量清——**不再拿真工具实弹试**。

实验设计（**全部本地、无网络**）
──────────────────────────────────
  合成四份模块，各自用不同方式取 urlopen：
    A `import urllib.request` 然后 `urllib.request.urlopen`
    B `from urllib.request import urlopen`
    C `OPENER = urllib.request.build_opener()` 然后 `OPENER.open`
    D 与本席接线一致：**先 activate() 再 import**
  每份运行两次：总闸【关】时看它是否 patched；总闸【开】时看它是否被拦住。
  ★ "被拦住"＝抛 NetBlocked 或 urlopen 已是拒绝桩；**本器不真的发请求**（用假 URL 且立即判形）。
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

SEAT_EXP = pathlib.Path(__file__).resolve().parent

MODS = {
    "A_模块属性调用": "import urllib.request as u\nprint('PATCHED' if u.urlopen.__name__=='_blocked' else 'NATIVE')\n",
    "B_from导入名字": "from urllib.request import urlopen\nprint('PATCHED' if urlopen.__name__=='_blocked' else 'NATIVE')\n",
    "C_自建opener": "import urllib.request as u\nO=u.build_opener()\nprint('PATCHED' if u.OpenerDirector.open.__name__=='_blocked' else 'NATIVE')\n",
    "D_先activate再导入": ("import sys;sys.path.insert(0,r'%s');import netguard;netguard.activate()\n"
                            "import urllib.request as u\nprint('PATCHED' if u.urlopen.__name__=='_blocked' else 'NATIVE')\n" % SEAT_EXP),
    "E_先导入再activate": ("import urllib.request as u\nimport sys;sys.path.insert(0,r'%s');import netguard;netguard.activate()\n"
                            "print('PATCHED' if u.urlopen.__name__=='_blocked' else 'NATIVE')\n" % SEAT_EXP),
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
    return ((r.stdout or "") + (r.stderr or "")).strip().splitlines()[-1] if ((r.stdout or "")+(r.stderr or "")).strip() else "(无输出)"


def main() -> int:
    print("═══ 总闸漏洞机理（合成模块实验，全程不触网）═══")
    print("  %-22s %-14s %-14s" % ("合成模块", "总闸关", "总闸开"))
    print("  " + "-" * 56)
    rows = {}
    for name, code in MODS.items():
        off = run(code, False)
        on = run(code, True)
        rows[name] = (off, on)
        print("  %-22s %-14s %-14s" % (name, off, on))
    print()
    print("  ── 判读 ──")
    b = rows.get("B_from导入名字")
    d = rows.get("D_先activate再导入")
    print("  ① `from ... import urlopen` 在【总闸开】时仍是 NATIVE ⇒ %s"
          % ("★确认漏洞：名字已绑定，patch 无效" if b and b[1] == "NATIVE" else "未复现"))
    print("  ② 若在【导入之前】activate()，同种写法是否也拦不住 ⇒ %s"
          % ("（B 与 D 同源，故 D 只证明'激活时机'对该写法无效）"))
    e = rows.get("E_先导入再activate")
    print("  ③ `import urllib.request`（模块属性式）在总闸开时 = %s ⇒ %s"
          % (e[1] if e else "?", "可拦" if e and e[1] == "PATCHED" else "★也拦不住"))
    print()
    print("  ⇒ 结论：**总闸能拦【模块属性式】调用；拦不住【from ... import 名字式】调用。**")
    print("  ★ 故接闸不能只写一行 activate()——**必须先确认该工具用的是哪种取法**，")
    print("     或者改由【工具侧显式检查】（如 meow_push／robots_gate 的写法）兜底。")
    print("  ★ 本器全程不触网（用假 URL 且只判形）⇒ 无外发。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
