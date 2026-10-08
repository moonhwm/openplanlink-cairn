#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""gitcode_search.py —— 用 GitCode 搜索接口挖掘 A2A/Agent 热门仓库。"""
import json
import os
import sys
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

# 凭据从环境变量读取，不硬编码入库（仓库公开）。
TOKEN = os.environ.get("GITCODE_TOKEN", "")
BASE = "https://gitcode.com/api/v5/search/repositories"


def search(q, per_page=8):
    url = "%s?%s" % (BASE, urllib.parse.urlencode(
        {"q": q, "per_page": per_page, "access_token": TOKEN}))
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return [{"_error": str(e)}]


for term in ["a2a", "agent", "智能体"]:
    print("══ 搜『%s』══" % term)
    items = search(term)
    if not items:
        print("  （空）")
        continue
    if isinstance(items, dict):
        items = items.get("items") or items.get("data") or []
    for it in items[:8]:
        if "_error" in it:
            print("  ✗ 错误：", it["_error"][:80]); continue
        name = it.get("full_name") or it.get("name", "?")
        desc = (it.get("description") or "")[:60]
        stars = it.get("stargazers_count") or it.get("stars_count") or it.get("stars") or "?"
        print("  · %s ｜ ⭐%s ｜ %s" % (name, stars, desc))
    print()
