#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""wechat_ctx.py —— 打印某 token 在文件中的出现上下文（±N 字符）。 v1.0.0
用法: wechat_ctx.py <文件> <token> [半宽]
"""
from __future__ import annotations
import pathlib
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

p = pathlib.Path(sys.argv[1])
tok = sys.argv[2]
half = int(sys.argv[3]) if len(sys.argv) > 3 else 110
t = p.read_text(encoding="utf-8", errors="replace")
print("  文件 %s ｜ 总字符 %d ｜ token「%s」出现 %d 次" % (p.name, len(t), tok, t.count(tok)))
for i, m in enumerate(re.finditer(re.escape(tok), t), 1):
    lo, hi = max(0, m.start() - half), min(len(t), m.end() + half)
    ctx = re.sub(r"\s+", " ", t[lo:hi])
    print("  #%d @%d: …%s…" % (i, m.start(), ctx))
