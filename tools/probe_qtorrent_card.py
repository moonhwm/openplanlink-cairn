#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NET —— 本件可发起对外网络调用（探测观测站名片）。声明供 blast_radius.py 审计。
r"""probe_qtorrent_card.py —— 分辨 200/404 矛盾：同一客户端、三种 Accept 头、多次取样。 v1.0.0

背景（轮 68）：
  19:37 本席 check_handshake52.py（urllib，Accept: application/json）对
         https://qtorrent.ok.kimi.link/.well-known/agent-card.json 得 **HTTP 200 ｜ 2320 B**
  19:38 本席以 Invoke-WebRequest（默认 Accept）同一路径得 **404**
⇒ 矛盾必须当场分辨，不得据任一方下结论。本器用**同一客户端**变【请求头】与【取样次数】：
      A) Accept: application/json
      B) 不带 Accept
      C) Accept: */*
      D) Accept: text/html
  并对每个组合取 3 次，看是否稳定。
"""
from __future__ import annotations
import sys
import time
import urllib.error
import urllib.request

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
URL = "https://qtorrent.ok.kimi.link/.well-known/agent-card.json"
COMBOS = [
    ("A Accept: application/json", {"Accept": "application/json"}),
    ("B 不带 Accept", {}),
    ("C Accept: */*", {"Accept": "*/*"}),
    ("D Accept: text/html", {"Accept": "text/html"}),
]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"



# ★ 轮108：网络总闸——只在 DSH_NO_NET 置上时装"拒绝外发"钩子；未置则【一行都不改行为】。
try:
    import netguard as _netguard
    _netguard.activate()
except Exception:
    pass

def hit(headers: dict):
    h = {"User-Agent": UA}
    h.update(headers)
    try:
        req = urllib.request.Request(URL, headers=h)
        with OPENER.open(req, timeout=25) as r:
            b = r.read()
            return r.status, len(b), r.headers.get("Content-Type", ""), b[:60]
    except urllib.error.HTTPError as e:
        return e.code, 0, "", b""
    except Exception as e:
        return None, 0, str(e)[:50], b""


print("═══ 同客户端·多请求头·三次取样 ═══")
print("  URL =", URL)
print()
for name, hd in COMBOS:
    got = []
    for i in range(3):
        st, n, ct, head = hit(hd)
        got.append((st, n))
        print("  %-28s 第%d次 ⇒ HTTP %-5s %6s B  %s" % (name, i + 1, st, n, ct))
        time.sleep(0.4)
    stables = len({g[0] for g in got}) == 1
    print("      ⇒ %s：%s" % ("稳定" if stables else "★不稳定", got))
    print()

print("  判读指引：")
print("   · 若某一请求头稳定 200 而其余 404 ⇒ 【内容协商】所致，属真实差异，须报清。")
print("   · 若全部 404 而先前曾得 200 ⇒ 先前很可能是【部署窗口内的瞬时存在】，须报为瞬时。")
print("   · 若同组内时 200 时 404 ⇒ 【不稳定】，本席将如实报不稳定，不据任何一次下结论。")
