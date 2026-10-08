#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只读扫源码；不触网、不改动任何件。
r"""lint_cn_quotes.py —— 机检【本席最常复发的那条规矩】：中文串里不许用直引号。 v1.0.0

为什么单独立一件器
────────────────────
本席轮 5–8 里，同一条规矩（中文里用「」而非直引号）【反复复发】，
每次都靠编译报错才发现 —— ★ 而"靠报错发现"意味着：没报错的地方就漏过去了。
⇒ 规矩不能靠记性，只能靠机检。本器即为此。

判据（★ 只报嫌疑，不自动改；改须人看）
────────────────────────────────────────
  S1 一行内有 print(...) 且其中出现【中文紧贴直引号】的形态
  S2 一行内出现 r"...中文..."（原始串里带中文与直引号）
⇒ 二者都会在 Python 里造成 SyntaxError 或语义漂移，故值得单列。

用法: lint_cn_quotes.py [--seat <路径>]
"""
from __future__ import annotations
import argparse
import pathlib
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

CJK = "\u4e00-\u9fff"
# ★ 2026-10-02 轮 8 修（首版 12 命中里 7 处是假阳性，其中一处还是【我自己写的、说明会误报】的那行）：
#   结论：本缺陷类的【精确仪器是 py_compile】——直引号落在中文串里必然编译失败。
#   故本器改为【以编译为准】，正则只作辅助且【标注为不精确】。
S1 = re.compile(r"print\([^\n]*[%s]\"[%s]" % (CJK, CJK))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seat", default=None)
    a = ap.parse_args()
    root = pathlib.Path(a.seat) if a.seat else pathlib.Path(__file__).resolve().parent.parent
    print("═══ 中文直引号机检（只读）═══")
    print("  范围 = %s（递归 .py，排除 __pycache__）" % root.name)

    files = [p for p in root.rglob("*.py")
             if "__pycache__" not in str(p)
             # ★ 2026-10-02 轮 8 增：排除 _retired\。
             #   理由：那里放的是【我故意退役的实验品】——例如
             #   `_未采用_正则引号检查器_属重写解析器_cairn-dsh.py` 名字就写着"未采用、属重写解析器"，
             #   它【本来就不该编译通过】。若不排除，本检查将【永远到不了 0】。
             #   ★ 一个永远失败的检查，与一个永不失败的检查【一样没用】。
             and "_retired" not in str(p)]

    # ① 主判据：编译。★ 精确——直引号落在中文串里必然 SyntaxError。
    import py_compile
    broken = []
    for p in files:
        try:
            py_compile.compile(str(p), doraise=True, cfile=str(p) + ".lintcheck")
            pathlib.Path(str(p) + ".lintcheck").unlink(missing_ok=True)
        except py_compile.PyCompileError as e:
            msg = str(e).splitlines()
            line = next((m.strip() for m in msg if "line" in m.lower()), "")
            broken.append((p, line))
        except Exception:
            broken.append((p, "（编译期异常）"))

    print("  扫过 .py = %d（★ 已排除 _retired\\：退役的故意坏件不算缺陷）" % len(files))

    # ★ 2026-10-02 轮 20 扩范围：把 .json 也纳入【编译级】判据（改用 json 解析）。
    #   缘由：本轮【三次】把声明写成坏 JSON，病根全是【中文里的未转义直引号】；
    #   而首版机检只扫 .py ⇒ ★ 范围缺口在本轮被实证三次。
    import json as _json
    bad_json = []
    for p in list(root.rglob("*.json")):
        # ★ 轮 20：必须排除【别人仓库】handshake\ —— 否则会报出与己无关的件
        #   （现场实例：handshake\qoder-skills-hub\...\300209_tech.json 是别人仓库里
        #    一份【扩展名写成 .json 的纯文本报告】，不是本席写坏的）
        if any(k in str(p) for k in ("__pycache__", "_retired", "handshake")):
            continue
        try:
            _json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            bad_json.append((p, str(e)[:78]))
    print("  ★ .json 解析失败 = %d（★ 轮 20 新增此栏；已排除 _retired\\ 与 handshake\\）" % len(bad_json))
    for p, err in bad_json[:20]:
        print("       ★ %-44s %s" % (p.name[:44], err))
    print()
    print("  ── 主判据（编译）★ 精确 ──")
    print("     ★ 编译失败 = %d（★ 范围：本席 .py，共扫 %d 件；★ 已排除 _retired\\）"
          % (len(broken), len(files)))
    for p, line in broken[:20]:
        print("       %-34s %s" % (p.name, line))
    print()
    if broken or bad_json:
        # ★ 轮 20：JSON 栏【必须影响判词】——否则按轮 8 的对称律，它只是装饰。
        if broken:
            print("  ⇒ ★ 有编译失败 ⇒ 修订后再跑，直到 0。")
        if bad_json:
            print("  ⇒ ★ 有 JSON 解析失败（中文未转义直引号会把 JSON 写坏）⇒ 修订后再跑，直到 0。")
        # ★ 2026-10-03 轮 73 加：机器可读判词行（★ 两条路各一句）。
        print("★ VERDICT=BAD")
        return 1
    print("  ⇒ ✅ 全席位 .py 编译通过 ＋ 全部本席 .json 可解析（＝本缺陷类已清）")
    print("     ★ 本器【只以编译为准】：首版曾用正则，12 条命中里 7 条是假阳性，")
    print("        其中一条还是【我自己写的、说明该判据会误报】的那行 ⇒ 故已整栏撤掉，不再保留不精确的判据。")
    # ★ 2026-10-03 轮 73 加：机器可读判词行（承轮 72）。
    print("★ VERDICT=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
