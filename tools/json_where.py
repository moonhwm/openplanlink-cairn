#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
json_where.py —— 用【解析器】定位 JSON 里的坏引号，并给出上下文窗口。 v1.0.0

来由
────
本席台账 JSON 多次因【中文里混入 ASCII 直引号】而不可解析。前两次都靠"肉眼找、改一处、再报一处"，
**来回三次才改完**。而本席第 7 轮已立规：**能被解析器判定的，不该用正则再判一遍**。
⇒ 本器即由解析器驱动：**失败即报出错位置，并打印该位置前后的窗口**，供一次性改净。

★ 为什么不写"直引号正则"：中文句号后本就该跟收尾引号，正则判据必然假阳性（本席实测 9 命中 8 合法）。

用法
────
    json_where.py <文件> [窗口半宽，默认 60]
    json_where.py --all <文件>     # 反复定位：每修一处即可再跑，直到 PASS
退出码：0 = 可解析；1 = 不可解析（并打印位置与窗口）
"""
from __future__ import annotations
import json
import pathlib
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__); return 2
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    p = pathlib.Path(args[0])
    half = int(args[1]) if len(args) > 1 else 60
    txt = p.read_text(encoding="utf-8")
    try:
        json.loads(txt)
        print("  [OK] 可解析：%s（%d B）" % (p.name, len(txt)))
        return 0
    except json.JSONDecodeError as e:
        # e.pos 是【绝对字符偏移】，e.lineno/e.colno 是 1 基行列
        pos = e.pos
        lo, hi = max(0, pos - half), min(len(txt), pos + half)
        window = txt[lo:hi].replace("\n", "⏎")
        print("  [FAIL] %s" % p.name)
        print("     %s（第 %d 行 第 %d 列，绝对偏移 %d）" % (e.msg, e.lineno, e.colno, pos))
        print("     ---- 出错点前后 %d 字符 ----" % half)
        print("     %s" % window)
        print("     %s^" % (" " * min(pos - lo, len(window))))
        # 附：该行内所有 ASCII 双引号的位置（供对照，不作判据）
        line = txt.splitlines()[e.lineno - 1] if e.lineno - 1 < len(txt.splitlines()) else ""
        idxs = [i for i, ch in enumerate(line) if ch == '"']
        print("     该行 ASCII 双引号共 %d 个，位置（列号）：%s" % (len(idxs), idxs[:40]))
        print("     ★修法：把中文语境里的直引号改为「」——**改在编译前，省一个来回**。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
