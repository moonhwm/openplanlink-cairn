#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: EXEC —— 它会调用 emit_closing_block.py（★ 那条路会写一个本席内的临时件）。
#                   ★ 而它只写/删【它自己建的那个临时件】；★ 目标已存在则跳过（★ 轮 66 的教训）。
r"""check_closing_append.py —— 走一遍 `emit_closing_block.py --append-to` 那条路。 v1.0.0

为什么（轮 110，承轮 109）
────────────────────────────
轮 109 实证：我上一轮那个"修"把 `--append-to` 整段【变成不可达】——
  ★ 而配方（11 条）里【没有一条会走到那条路】（★ 它只跑不带参数那次）。
⇒ ★ 故立此器：**把那条路纳入每轮检查。**

★ 它做什么（三步）
  ① 在 outbox 建一个【临时试件】（★ 名字带 _tmp_ 且带本器归因）
  ② 跑 `emit_closing_block.py --append-to <试件>` ⇒ 期望：退出码 0、★ 且字节【增长】
  ③ 再跑一次 ⇒ 期望：退出码 3（★ 幂等拒绝）
  ④ 删掉试件（★ 只删【本器刚建的】；★ 建之前若已存在 ⇒ 跳过、不跑）

★ 本器自陈三条盲点
  ① 它只验【退出码与字节增长】⇒ ★ 不核写进去的内容对不对
  ② 它写一个真实文件到 outbox ⇒ ★ 若中途崩，★ 试件会留下（★ 故名字可辨、且它每次先清同名残留）
  ③ ★ 它【不构成独立检查】——★ 它调的就是被检的那件器
"""
from __future__ import annotations
import pathlib
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SEAT = pathlib.Path(__file__).resolve().parent.parent
TOOL = SEAT / "exp" / "emit_closing_block.py"
TMP = SEAT / "outbox" / "_tmp_check_closing_append.md"


def main() -> int:
    print("═══ 走一遍 --append-to 那条路（★ 轮 109 它断过）═══")
    # ★★ 轮 123：**层深闸**——防【经由 emit_closing_block 绕回来的环】。
    #   缘由（轮 122 实证·严重）：本器被接进配方后形成死循环：
    #     emit_closing_block → verify_recipe → check_closing_append → emit_closing_block → …
    #   ★ 现场：★ 5 个 python 进程，每隔约一分钟多一个；★ 试件被反复重建（★ 残留）。
    #   ★ 而 verify_recipe 那句「硬上限 3 层（防递归）」【只防它执行自身】——
    #     ★ 它【看不见】这个经由第三件绕回来的环。
    #   ⇒ 故此处【自己声明层深】：★ 由本器设置的环境变量传给子进程；
    #     ★ 若已经在本器的调用链里 ⇒ ★ 立刻返回【SKIP】（★ 退出码 0，★ 且明说"跳过，非通过"）。
    import os as _os
    DEPTH_ENV = "DSH_CHECK_CLOSING_APPEND_DEPTH"
    depth = int(_os.environ.get(DEPTH_ENV, "0") or "0")
    if depth >= 1:
        print("  ★★ 检测到【已在调用链内】（★ 层深 %d）⇒ ★ 本器【跳过】，不重复进入。" % depth)
        print("     ★ 缘由：emit_closing_block → verify_recipe → 本器 → emit_closing_block 是【环】。")
        print("     ★ 注意：★ 这是【跳过】，★ 不是【通过】——★ 它没有验任何东西。")
        print("★ VERDICT=SKIP")
        return 0
    if not TOOL.is_file():
        print("  ★ 被检器不在：%s" % TOOL)
        print("★ VERDICT=BAD")
        return 2

    # ★ 轮 123 修：把"我自己的残件"与"别人的件"【分开】。
    #   缘由（轮 122 实证）：本器建一个真文件在 outbox，finally 删它。
    #   ★ 而【任何中断】都会跳过 finally ⇒ 留下残件 ⇒ 下一次本器报 BAD ⇒
    #     **一次崩溃变成【一个永久的红】**（★ 而配方里它期望 0 ⇒ 整条配方红）。
    #   ⇒ 故：若占位者【带有本器自己的首行标记】⇒ ★ 那是【我的残件】⇒ 清掉重来（★ 并在输出里说明）；
    #     若占位者【没有那个标记】⇒ ★ 那是【别人的件】⇒ 照旧不动、报 BAD。
    MINE = "# 试件（★ 由 check_closing_append.py 建）"
    if TMP.exists():
        try:
            head = TMP.read_text(encoding="utf-8", errors="replace")
        except Exception:
            head = ""
        if head.startswith(MINE):
            print("  ★ 发现【本器上一次留下的残件】⇒ ★ 清掉重来（★ 那是我的，不是别人的）")
            TMP.unlink()
        else:
            print("  ★★ 试件路径已被【非本器】占：%s" % TMP)
            print("     ⇒ ★ 本器【不动它】——★ 按轮 66 的规矩：只碰自己建的。")
            print("★ VERDICT=BAD")
            return 1

    TMP.write_text("# 试件（★ 由 check_closing_append.py 建）\n", encoding="utf-8", newline="\n")
    # ★ 轮 123：★ 给子进程【打上层深标记】⇒ 若它绕回来，★ 环就被层深闸挡住。
    _env = dict(_os.environ)
    _env[DEPTH_ENV] = str(depth + 1)
    try:
        before = TMP.stat().st_size
        r1 = subprocess.run([sys.executable, str(TOOL), "--append-to",
                             "outbox/_tmp_check_closing_append.md"],
                            cwd=str(SEAT), capture_output=True, text=True, encoding="utf-8", env=_env)
        after = TMP.stat().st_size
        print("  ① 首跑 ⇒ 退出码 %d（★ 期望 0）｜ 字节 %d → %d（★ 期望增长）"
              % (r1.returncode, before, after))
        ok1 = (r1.returncode == 0 and after > before)

        r2 = subprocess.run([sys.executable, str(TOOL), "--append-to",
                             "outbox/_tmp_check_closing_append.md"],
                            cwd=str(SEAT), capture_output=True, text=True, encoding="utf-8", env=_env)
        print("  ② 再跑 ⇒ 退出码 %d（★ 期望 3 = 幂等拒绝）" % r2.returncode)
        ok2 = (r2.returncode == 3)

        ok = ok1 and ok2
        print("  ═══ 判定 ═══")
        print("     ★ 本器结论：★ 那条路【走得通且幂等】" if ok
              else "     ★★ 本器结论：★ 那条路【不通或幂等失效】")
        print("     ★ 本器三条盲点：① 只验退出码与字节增长、不核内容"
              "② 它写一个真实试件（★ 中途崩会留下）③ 它调的就是被检器、不构成独立检查")
        print("★ VERDICT=%s" % ("PASS" if ok else "BAD"))
        return 0 if ok else 1
    finally:
        if TMP.exists():
            TMP.unlink()
            print("  ③ 试件已删（★ 只删本器刚建的那个）")


if __name__ == "__main__":
    sys.exit(main())
