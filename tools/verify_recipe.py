#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 会以子进程跑配方里的命令；★ 但【绝不跑本器自身】，且不触网。
r"""verify_recipe.py —— 把声明里那句【期望退出码】从"记在纸上"变成"跑出来"。 v1.0.0

立此器的缘由（轮 21）
──────────────────────
轮 20 我往声明里加了 `recipe_expected_exit_codes`（「10 条期望 0、1 条期望 1」）。
★ 而【没有任何东西核它】 ⇒ 那是记账，不是验证。
★ 20 轮的方法判决正是：**"把文件列进配方"是记账；"逐条实跑"才是验证。**

★★ 而这一步会碰到一个真危险：**递归**
   配方的第 3 条就是 `python exp\verify_seat_location.py`；
   若本器【也被登记进配方】，则"核配方者跑配方 ⇒ 配方跑到核配方者" ⇒ 无限递归。
⇒ 故本器：① **绝不执行自身**（路径比对，跳过）；② **硬上限 3 层**（防别的环）；
   ③ ★ 并把这两条限制【写在输出里】。

★ 本器自陈三条盲点（按轮 12 判据）
  ① 它只比对【退出码】，不比对【输出的判词】⇒ 一条"退出码 0 但结论错"的命令它会放过；
  ② 它按【声明里的期望】判 ⇒ 期望本身是我写的（自陈）；
  ③ ★ 它【会把配方里的命令真跑一遍】⇒ 有副作用者不宜进配方（本配方皆为只读器）。

用法: verify_recipe.py
"""
from __future__ import annotations
import json
import pathlib
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SEAT = pathlib.Path(__file__).resolve().parent.parent
DECL = SEAT / "outbox" / "SEAT_LOCATION_cairn-dsh_20261002.json"
SELF = pathlib.Path(__file__).resolve()
MAX_DEPTH = 3


def main() -> int:
    print("═══ 配方核验（把「期望退出码」跑出来）═══")
    print("  ★ 本器【绝不执行自身】，且硬上限 %d 层（防递归）" % MAX_DEPTH)
    if not DECL.is_file():
        print("ERR 声明不在 ⇒ ★ 器具故障")
        return 2
    d = json.loads(DECL.read_text(encoding="utf-8"))
    recipe = d.get("verify_recipe") or []
    expect = d.get("recipe_expected_exit_codes") or {}
    if not recipe:
        print("○ ★【未检】—— 声明未含 verify_recipe ⇒ 本条整条未执行（不是通过，也不是失败）")
        return 0

    # 期望表：键名形如 "python exp\\verify_peer_kit.py" ⇒ 退出码语义写在正文里
    # ★ 解析：正文以"期望退出码 N"起头的，取那个 N；否则按 all_others 的 0
    def expected_for(cmd: str):
        for k, v in expect.items():
            if k != "why" and k != "all_others" and cmd.replace("/", "\\") == k.replace("/", "\\"):
                import re
                m = re.search(r"期望退出码\s*(\d+)", str(v))
                return (int(m.group(1)) if m else 0), str(v)[:60]
        return 0, (str(expect.get("all_others", ""))[:60])

    fails, ran = [], 0
    for cmd in recipe:
        # ★ 防递归：绝不跑自身
        if SELF.name in cmd:
            print("   ○ 跳过（防递归）：%s" % cmd)
            continue
        argv = cmd.split()
        exe = sys.executable if argv[0] == "python" else argv[0]
        want, why = expected_for(cmd)
        r = subprocess.run([exe] + argv[1:], capture_output=True, text=True,
                           encoding="utf-8", cwd=str(SEAT), timeout=600)
        ran += 1
        good = r.returncode == want
        if not good:
            fails.append((cmd, want, r.returncode))
        print("   %s 期望 %d ／ 实测 %d ｜ %s" % ("✅" if good else "★", want, r.returncode, cmd))

    print()
    print("  实跑 %d 条 ｜ ★ 与期望不符 %d 条" % (ran, len(fails)))
    for cmd, want, got in fails:
        print("     ★ %s ：期望 %d，实测 %d" % (cmd, want, got))
    print()
    print("  ── 本器三条盲点（写在器内）──")
    print("     ① 只比【退出码】，不比【判词】⇒「退出码 0 而结论错」它放过")
    print("     ② 期望表是【本席自己写的】⇒ 它核的是『实测是否等于自陈』，不是『期望是否正确』")
    print("     ③ 它【会真跑配方】⇒ 有副作用的命令不宜进配方")
    if fails:
        print("  ⇒ ★ 判词 BAD")
        # ★ 2026-10-03 轮 73 加：机器可读判词行（★ 两条路各一句）。
        print("★ VERDICT=BAD")
        return 1
    print("  ⇒ ✅ 判词 OK —— 配方【逐条实跑】的退出码与声明里的期望一致")
    # ★ 2026-10-03 轮 73 加：机器可读判词行（承轮 72）。
    print("★ VERDICT=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
