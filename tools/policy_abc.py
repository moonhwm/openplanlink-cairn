#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NET —— 本件可发起对外网络调用（只读 robots.txt（政策的豁免项））。声明供 blast_radius.py 审计。
r"""
policy_abc.py —— 把"未声明 robots 主机取件政策"做成一份【有证据的选择题】。 v1.0.0

为什么
──────
本席轮 79 给取件器装了 robots 闸口，并把"未声明（robots 404）"的默认设为 **A：不取**。
轮 80 把 A/B/C 三选项呈请机主裁定。而**当晚 A 已【三次】挡住本席自己**（轮 83、85，及本轮）。

⇒ 故本器把抽象选项变成【逐 URL 的裁决对照】：
     · 每个 URL 的 robots 状态
     · **A 怎么判**（未声明 ⇒ 不取）
     · **B 怎么判**（未声明 ⇒ 视为无限制，但须标注）
     · ★ **D 怎么判**（本席轮 89 新提：**授权须来自【有名字的来源】**——
        机主点名、或生态自己的文书把该主机列为目标 ⇒ 才允许；沉默不等于授权）
   ★ 本器【不取任何内容】，只取 `robots.txt` 并对照一份【已具名的来源清单】。

★ 具名来源（本席逐条记明出处，不臆造）
用法: policy_abc.py
"""
from __future__ import annotations
import re
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
UA = "Mozilla/5.0 (compatible; cairn-dsh policy-probe)"

# ★ 本席今晚实际想取、而因 A 被挡下的目标（逐条附"被挡时损失了什么"）
WANTED = [
    ("https://qtorrent.ok.kimi.link/", "核 v2.1 是否已上线（轮 85/89 只能引旧读数）"),
    ("https://qtorrent.ok.kimi.link/observe.html", "核本席轮 81/84 交的全稿是否已被采纳"),
    ("https://qtorrent.ok.kimi.link/.well-known/agent-card.json", "核判据52「agent-card 可达」现状"),
    ("https://qtorrent.ok.kimi.link/llms.txt", "核其补丁是否已合入"),
]

# ★ 具名来源清单：每条都写明【谁在哪份文书里点了名】
NAMED_SOURCES = [
    ("qtorrent.ok.kimi.link",
     "机主原令点名该站为「您需要继续完善的」；且 74号令 §四／《交付说明》把它列为 v2.1 的发布目标"),
    ("raw.githubusercontent.com",
     "Star-Office-UI 官方仓库的原始文件面（其 README/SKILL.md 引用）"),
    ("api.github.com",
     "GitHub 公开 REST API（其官方文档面）"),
]



# ★ 轮108：网络总闸——只在 DSH_NO_NET 置上时装"拒绝外发"钩子；未置则【一行都不改行为】。
try:
    import netguard as _netguard
    _netguard.activate()
except Exception:
    pass

def fetch_robots(host: str):
    try:
        req = urllib.request.Request("https://%s/robots.txt" % host, headers={"User-Agent": UA})
        with OPENER.open(req, timeout=20) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return None, str(e)[:60]


def parse(txt: str):
    rules, in_star = [], False
    for line in txt.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        k, v = line.split(":", 1)
        k, v = k.strip().lower(), v.strip()
        if k == "user-agent":
            in_star = (v == "*")
            continue
        if in_star and k in ("allow", "disallow"):
            rules.append((k == "allow", v))
    return rules


def allowed(rules, path: str) -> bool:
    best = None
    for allow, pat in rules:
        if not pat:
            continue
        body, anchor = (pat[:-1], "$") if pat.endswith("$") else (pat, "")
        if re.compile("^" + re.escape(body).replace(r"\*", ".*") + anchor).match(path):
            L = len(pat)
            if best is None or L > best[0] or (L == best[0] and allow and not best[1]):
                best = (L, allow)
    return True if best is None else best[1]


def main() -> int:
    print("═══ 未声明 robots 主机：取件政策·逐 URL 裁决对照 ═══")
    print("  图例：A＝未声明即不取（现默认）｜B＝未声明视为无限制但标注｜D＝★授权须来自有名字的来源")
    print()
    hdr = "  %-46s %-14s %-6s %-6s %-6s %s"
    print(hdr % ("URL", "robots", "A", "B", "D", "损失（若按 A 不取）"))
    print("  " + "-" * 128)
    stats = {"A": 0, "B": 0, "D": 0}
    for url, loss in WANTED:
        u = urlsplit(url)
        st, txt = fetch_robots(u.netloc)
        path = u.path + (("?" + u.query) if u.query else "")
        if st == 200:
            rules = parse(txt)
            ok = allowed(rules, path)
            rstate = "有声明"
            A = "准" if ok else "禁"
            B = A
            D = A
        elif st == 404:
            rstate = "未声明"
            A, B = "不取", "取"
            named = any(n == u.netloc for n, _ in NAMED_SOURCES)
            D = "取(具名)" if named else "不取"
        else:
            rstate = "取不到"
            A, B, D = "不取", "不取", "不取"
        print(hdr % (url[:46], rstate, A, B, D, loss[:40]))
        for k, v in (("A", A), ("B", B), ("D", D)):
            if v.startswith("取") or v == "准":
                stats[k] += 1
    print()
    print("  ── 统计（这 4 个目标里，各政策放行几个）──")
    print("   A（现默认）放行 %d/4 ｜ B 放行 %d/4 ｜ ★D 放行 %d/4" % (stats["A"], stats["B"], stats["D"]))
    print()
    print("  ── ★ 具名来源清单（D 的依据，逐条附出处）──")
    for host, why in NAMED_SOURCES:
        print("   · %-28s ← %s" % (host, why))
    print()
    print("  ── 三种政策的短长（本席自陈，非代裁）──")
    print("   A 保守：不越雷池；代价＝连《交付说明》点名的发布目标也无法核验（见上表「损失」列）。")
    print("   B 通行：能干活；代价＝**把「沉默」读成「许可」**——这是本席不愿独自承担的推定。")
    print("   ★D 具名：**授权来自一个有名有姓的来源**（机主点名，或生态文书把该主机列为目标）；")
    print("           未具名者仍按 A 不取。⇒ 既不把沉默当许可，也不把合法核验一并冻住。")
    print()
    print("  ★ 本器【不取任何内容】，只取 robots.txt 并对照具名清单 ⇒ 换政策也不会自动放行。")
    print("  ★ 本席倾向 D；但这是请您裁的事，故本件只列证据与后果。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
