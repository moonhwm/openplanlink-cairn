#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""wechat_extract.py —— 从已存的公众号 HTML 里提取正文（结构已知后精确取）。 v1.0.0

已知结构（轮 62 探测）：id="js_content"（2 处）、cgiData（184）、appmsg（347）、无验证码。
本器取 js_content 段到常见收尾标记（js_tags / rich_media_tool / qr_code / 赞赏）为止。
★ 只输出【标题 ＋ 字数 ＋ 段落结构 ＋ 前若干段】，不整篇外发。
"""
from __future__ import annotations
import html
import pathlib
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

END_MARKERS = ("js_tags", "rich_media_tool", "js_pc_qr_code", "js_article_comment",
               "rich_media_area_extra", "js_handle_bar", "js_profile_qrcode")


def main() -> int:
    t = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
    m = re.search(r'id="js_content"', t)
    if not m:
        print("  ★未见 js_content"); return 1
    start = m.end()
    end = len(t)
    for k in END_MARKERS:
        i = t.find(k, start)
        if i > 0:
            end = min(end, i)
    seg = t[start:end]
    seg = re.sub(r"(?s)<script.*?</script>", " ", seg)
    seg = re.sub(r"(?s)<style.*?</style>", " ", seg)
    seg = re.sub(r"<br\s*/?>", "\n", seg)
    seg = re.sub(r"</p>|</section>|</div>|</h\d>|</li>", "\n", seg)
    seg = re.sub(r"<[^>]+>", "", seg)
    seg = html.unescape(seg)
    lines = [re.sub(r"\s+", " ", x).strip() for x in seg.splitlines()]
    lines = [x for x in lines if len(x) > 1]
    body = "\n".join(lines)
    print("  正文字符数 = %d ｜ 段落数 = %d" % (len(body), len(lines)))
    print()
    print("  ══ 前 40 段（供本席判读；本件不整篇外发）══")
    for i, ln in enumerate(lines[:40], 1):
        print("  %2d| %s" % (i, ln[:110]))
    out = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else None
    if out:
        out.write_text(body, encoding="utf-8")
        print("\n  [OK] 正文已存：%s（%d B）" % (out.name, out.stat().st_size))
    return 0


if __name__ == "__main__":
    sys.exit(main())
