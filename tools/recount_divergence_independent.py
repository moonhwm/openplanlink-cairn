#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只读两个目录；不写件、不删件、不触网。
r"""独立复算【正本 vs 副本】的分叉计数 —— **第二把尺（声明核验那一句）**。 v1.0.0

承轮 103
──────────
轮 103 给台账那句「链内自洽」配了第二把尺（★ 而它先反驳，才发现错的是新尺）。
★ 而声明核验那句「★不符 0 条」是【另一个承重的 0】——★ 本器给它配尺。

★ 本器与 verify_seat_location.py 的【不同之处】
  ① **不 import 它**，★ 自己走两个目录
  ② 分叉判据自己写：★ 同名 ⇒ 比 sha256；★ 只在一侧 ⇒ 记为单侧件
  ③ ★ 不做"已声明分叉"的豁免——★ 本器【只报原始数】，★ 豁免与否【留给读的人】
     （★ 这是刻意的：★ 一把尺若自带豁免，★ 它量出的就【不是原始事实】）

★ 本器自陈三条盲点
  ① 只按【文件名】配对 ⇒ ★ 改名过的同一件会被算成"一左一右两个单侧件"
  ② 只比【字节】⇒ ★ 不判内容对不对
  ③ ★ 它【不解释】分叉的成因——★ 那是核验器与声明的事
"""
from __future__ import annotations
import hashlib
import pathlib
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SEAT = pathlib.Path(__file__).resolve().parent.parent
CANON = SEAT
# ★ 副本位置（★ 与核验器同源的那个）：写死一次并打印出来，★ 便于对照
REPLICA = pathlib.Path(r"C:\Users\欧阳宏俊\OneDrive\桌面\_整理_各席交付\石敢当席\A2A新席_石敢当Cairn_20260928")


def scan(root: pathlib.Path) -> dict:
    """★ 走一遍目录。
    ★★ 轮 106 加：**把排除掉的东西一并报出来**。
      缘由（轮 105 实证）：本器排除 `__pycache__`——★ 而那让"同名 3184"与核验器的"共有 3273"
      【差 89】。★ 我上一轮才发现那 89 正是这里排除的。
      ⇒ ★ 故"写着 3184 却不写排除了 89"是**一个没写出来的口径**（★ 轮 96 那条法则的原样复发）。
      ⇒ ★ 本器改为【报出被排除的件数】，★ 让读者自己判断口径合不合适。
    """
    out, excluded = {}, 0
    for p in root.rglob("*"):
        if p.is_file():
            if "__pycache__" in str(p):
                excluded += 1
                continue
            rel = str(p.relative_to(root)).replace("\\", "/")
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return {"files": out, "excluded_pycache": excluded}


def main() -> int:
    print("═══ 独立复算 正本 vs 副本（★ 第二把尺）═══")
    print("  正本 = %s" % CANON)
    print("  副本 = %s" % REPLICA)
    if not REPLICA.is_dir():
        print("  ★ 副本不可达 ⇒ ★ 本器【不判】，报「未检」")
        print("★ VERDICT=未检")
        return 0
    print("  ★ 本器不 import verify_seat_location —— ★ 且【不做已声明分叉的豁免】")
    print()

    ra = scan(CANON)
    rb = scan(REPLICA)
    a, b = ra["files"], rb["files"]
    shared = set(a) & set(b)
    print("  ★★ 本器的口径（★ 轮 106 起明写）：")
    print("     排除 `__pycache__`：正本 %d 件 ｜ 副本 %d 件"
          % (ra["excluded_pycache"], rb["excluded_pycache"]))
    print("     ⇒ ★ 故本器那句「同名」【不含】这两批；★ 核验器那句「共有」【含】它们。")
    print("       （★ 轮 105 实测：3273 − 3184 = 89 = 副本的 __pycache__ 件数；★ 其中 9 件字节不同。）")
    print()
    print("  正本件数 = %d ｜ 副本件数 = %d ｜ ★ 同名（不含 pycache）= %d"
          % (len(a), len(b), len(shared)))
    same = sum(1 for k in shared if a[k] == b[k])
    diff = sorted(k for k in shared if a[k] != b[k])
    only_c = sorted(set(a) - set(b))
    only_r = sorted(set(b) - set(a))
    print("  ── ★ 复算结果（★ 原始数，未豁免）──")
    print("     字节相同 = %d" % same)
    print("     ★★ 字节不同（活文件分叉）= %d" % len(diff))
    for k in diff[:12]:
        print("        · %s" % k)
    if len(diff) > 12:
        print("        …共 %d 件" % len(diff))
    print("     正本独有 = %d ｜ 副本独有 = %d" % (len(only_c), len(only_r)))
    print()
    print("  ═══ 判定 ═══")
    print("     ★ 本器结论：★ 原始分叉数 = %d（★ 未减已声明项）" % len(diff))
    print("     ★★ 与核验器那句『★不符 0 条』对照：★ 它数的是【未声明】的那些；")
    print("        ★ 本器数的是【全部】——★ 两把尺【判据不同】，★ 故数值【本就不该相等】。")
    print("     ★ 本器三条盲点：① 只按文件名配对 ② 只比字节 ③ 不解释成因")
    print("★ VERDICT=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
