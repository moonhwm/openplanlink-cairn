#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NET —— 本件可发起对外网络调用（探测公众号可达性）。声明供 blast_radius.py 审计。
r"""wechat_probe.py —— 看一篇公众号页面的真实结构（标记计数 + 标题提取）。 v1.0.0"""
from __future__ import annotations
import pathlib
import re
import sys
import urllib.request

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")



# ★ 轮108：网络总闸——只在 DSH_NO_NET 置上时装"拒绝外发"钩子；未置则【一行都不改行为】。
try:
    import netguard as _netguard
    _netguard.activate()
except Exception:
    pass

def main() -> int:
    url, out = sys.argv[1], pathlib.Path(sys.argv[2])
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    raw = urllib.request.urlopen(req, timeout=45).read()
    out.write_bytes(raw)
    print("  已存原始 HTML：%s（%d B）" % (out.name, len(raw)))
    t = raw.decode("utf-8", "replace")
    for k in ("js_content", "rich_media_title", "msg_title", "og:title", "<title>",
              "activity-name", "mpvideo", "小程序", "cgiData", "appmsg", "video_channel",
              "wappoc_appmsgcaptcha", "环境异常"):
        print("  %-22s 出现 %d 次" % (k, t.count(k)))
    for pat, label in ((r"<title>(.*?)</title>", "<title>"),
                       (r'property="og:title"\s+content="(.*?)"', "og:title"),
                       (r'var\s+msg_title\s*=\s*[\'"](.+?)[\'"]', "msg_title"),
                       (r'id="activity-name"[^>]*>(.*?)<', "activity-name")):
        m = re.search(pat, t, re.S)
        print("  %-22s = %s" % (label, (re.sub(r"\s+", " ", m.group(1)).strip()[:140] if m else "（无）")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
