#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
add_bom_check.py —— 给 tool_hygiene.py 增补第④项：人读中文件的 BOM 检查。 v1.0.0

为什么补（轮 95 发现）
──────────────────────
本席普查：2,631 件产出里【2,629 件无 BOM】⇒ 在【假定系统 ANSI 代码页】的读取方（含本会话自己的 pwsh
默认 `Get-Content`）下会显示为乱码。而本席的体检器【原本没有这一项】——
其①查的是 `.py` 的 UTF-8 声明，不是 BOM ⇒ **器具对自身产出的这一类缺陷是盲的。**

规则（本席自定，附理由）
────────────────────────
  · 【给人读】的中文件（`.md`／`.tsv`／`.txt`）⇒ **建议有 BOM**（`utf-8-sig`），
    使默认 Windows 工具能正确显示中文；
  · 【给程序读】的（`.py`／`.mjs`／`.json`／`.led`）⇒ **必须无 BOM**
    （`node` 会因 BOM 报错；JSON 解析器多不容 BOM）。
★ 本器只【报告与计数】，不改任何文件——**存量 2,629 件不追改**：
   追改会（a）扰动共享面的只增不改纪律、（b）作废全部 `.sha256` 伴随物、
   （c）有碰到台账链的风险。**故只立规则于今后，并把存量属性如实披露。**
"""
from __future__ import annotations
import pathlib
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

H = pathlib.Path(r"C:\Users\欧阳宏俊\OneDrive\桌面\A2A新席_石敢当Cairn_20260928\exp\tool_hygiene.py")
MARK = "# ==== ④ 人读中文件的 BOM 检查（轮 95 增补） ===="

NEW = '''

# ==== ④ 人读中文件的 BOM 检查（轮 95 增补） ====
# 由轮 95 普查所得：本席 2,631 件产出中 2,629 件无 BOM ⇒ 在假定 ANSI 代码页的读取方
# （含本会话 pwsh 默认 Get-Content）下显示为乱码。原体检器无此项 ⇒ 对自身产出这一类缺陷是盲的。
# ★ 规则：人读的 .md/.tsv/.txt 建议有 BOM；程序读的 .py/.mjs/.json/.led 必须无 BOM。
# ★ 存量不追改（会扰动只增不改的共享面、作废 .sha256、有碰链风险）——只如实计数并披露。
BOM = b"\\xef\\xbb\\xbf"
HUMAN_EXT = {".md", ".tsv", ".txt"}
no_bom_human, bom_machine = [], []
for _p in _root.rglob("*"):
    if not _p.is_file():
        continue
    _e = _p.suffix.lower()
    try:
        _has = _p.read_bytes().startswith(BOM)
    except Exception:
        continue
    if _e in HUMAN_EXT and not _has:
        no_bom_human.append(_p)
    if _e in {".mjs", ".json"} and _has:
        bom_machine.append(_p)
print("\\n④ 人读中文件缺 BOM：%d 个 ｜ 程序读文件误带 BOM：%d 个" % (len(no_bom_human), len(bom_machine)))
if bom_machine:
    for _p in bom_machine[:5]:
        print("     ★误带 BOM（node/JSON 会出错）：" + _p.name)
print("   ★ 说明：第④项【只计数不阻断】——存量 %d 件按【不追改】处置（保共享面只增不改、保 .sha256 有效）；" % len(no_bom_human))
print("     今后新件按规则写：人读用 utf-8-sig，程序读用无 BOM。")
'''


def main() -> int:
    if not H.is_file():
        print("[ERR] 未找到 %s" % H); return 1
    t = H.read_text(encoding="utf-8")
    if MARK in t:
        print("[SKIP] 第④项已存在"); return 0
    # 插到文件末尾的 __main__ 之前；若无则直接追加
    idx = t.rfind('if __name__')
    if idx < 0:
        t = t + NEW
    else:
        t = t[:idx] + NEW.lstrip("\n") + "\n\n" + t[idx:]
    H.write_text(t, encoding="utf-8")
    print("[OK] 已给 %s 增补第④项（人读中文件 BOM 检查）" % H.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
