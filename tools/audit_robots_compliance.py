#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NET —— 本件可发起对外网络调用（复核历史取件的 robots（只读 robots.txt））。声明供 blast_radius.py 审计。
r"""
audit_robots_compliance.py —— 对本席今晚【全部外部取件】做一次 robots 合规审计。 v1.0.0

为什么做
────────
轮 73 本席自查发现：对 AppGallery 详情页，本席【取件两次都未先查 robots】。
⇒ 那就该把问题放大到全量：**今晚取过的每一个 URL，是否都先查过？有没有别的违规？**

★ 器具必须自证能分辨（否则又是一次"不会失败的检查"）
────────────────────────────────────────────────────
本器自带**双向对照**，先验求值器，再拿去审计：
  对照① `appgallery.huawei.com` + `/app/detail?id=com.wzdxy.ssh.h` ⇒ **必须判「禁」**
  对照② `appgallery.huawei.com` + `/Featured`                    ⇒ **必须判「准」**
  ★ 若求值器对二者给出同一结论 ⇒ 本器作废，不输出审计结论。

★ 纪律
──────
  · 只读 `robots.txt`（这本身是公开声明，取它是为了【遵守】它）；
  · **不改写、不绕过**；判为「禁」者，本器只记录，不再取任何内容；
  · 每条结论注明【依据原文】。

用法: audit_robots_compliance.py
"""
from __future__ import annotations
import re
import sys
import urllib.error
import urllib.request

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
UA = "Mozilla/5.0 (compatible; cairn-dsh robots-audit; +local)"



# ★ 轮108：网络总闸——只在 DSH_NO_NET 置上时装"拒绝外发"钩子；未置则【一行都不改行为】。
try:
    import netguard as _netguard
    _netguard.activate()
except Exception:
    pass

def fetch(url: str, timeout: int = 20):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with OPENER.open(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:
        return None, ""


def parse_robots(txt: str):
    """只取 User-agent: * 段。返回 [(allow_bool, pattern)]，按出现顺序。"""
    rules, in_star = [], False
    for line in txt.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k, v = k.strip().lower(), v.strip()
        if k == "user-agent":
            in_star = (v == "*")
            continue
        if not in_star:
            continue
        if k in ("allow", "disallow"):
            rules.append((k == "allow", v))
    return rules


def to_regex(pat: str):
    """robots 通配：* ⇒ .* ；$ ⇒ 结尾锚。"""
    if pat.endswith("$"):
        body, anchor = pat[:-1], "$"
    else:
        body, anchor = pat, ""
    esc = re.escape(body).replace(r"\*", ".*")
    return re.compile("^" + esc + anchor)


def allowed(rules, path: str) -> bool:
    """最长匹配优先（robots 惯例）；同长时 Allow 优先。"""
    best = None  # (len, allow)
    for allow, pat in rules:
        if pat == "":
            continue
        if to_regex(pat).match(path):
            L = len(pat)
            if best is None or L > best[0] or (L == best[0] and allow and not best[1]):
                best = (L, allow)
    return True if best is None else best[1]


# ───────── 先验求值器（双向对照）────────
AG = """User-agent: *
Allow: /$
Allow: /Featured
Disallow: /*#*
Disallow: /*?*
Disallow: /*
"""
_r = parse_robots(AG)
c1 = allowed(_r, "/app/detail?id=com.wzdxy.ssh.h")
c2 = allowed(_r, "/Featured")
print("═══ 先验求值器（双向对照，不过则本器作废）═══")
print("  对照① AppGallery「/app/detail?id=…」⇒ 期望【禁】 ｜ 实算 = %s ｜ %s"
      % ("禁" if not c1 else "准", "✓" if c1 is False else "★不符"))
print("  对照② AppGallery「/Featured」        ⇒ 期望【准】 ｜ 实算 = %s ｜ %s"
      % ("禁" if not c2 else "准", "✓" if c2 is True else "★不符"))
if c1 == c2:
    print("  ★ 求值器无分辨力 ⇒ 本器作废，不输出审计结论。")
    sys.exit(2)
print("  ⇒ 求值器有分辨力，可用于审计。")
print()

# ───────── 本席今晚的外部取件清单（据本席台账与出件记录）────────
#  (host, path, 本席是否【取件前】查过其 robots)
FETCHES = [
    ("appgallery.huawei.com", "/app/detail?id=com.wzdxy.ssh.h", False),
    ("appgallery.huawei.com", "/app/detail?id=com.chuckfang.meow", False),
    ("appgallery.huawei.com", "/robots.txt", False),
    ("qtorrent.ok.kimi.link", "/", False),
    ("qtorrent.ok.kimi.link", "/observe.html", False),
    ("qtorrent.ok.kimi.link", "/oracle.html", False),
    ("qtorrent.ok.kimi.link", "/sandbox.html", False),
    ("qtorrent.ok.kimi.link", "/sea.html", False),
    ("qtorrent.ok.kimi.link", "/cinema.html", False),
    ("qtorrent.ok.kimi.link", "/a2a-architecture.html", False),
    ("qtorrent.ok.kimi.link", "/.well-known/agent-card.json", False),
    ("qtorrent.ok.kimi.link", "/llms.txt", False),
    ("qtorrent.ok.kimi.link", "/assets/status.js", False),
    ("mp.weixin.qq.com", "/s/udYV67xgvcZlquYnFepHug", False),
    ("www.chuckfang.com", "/MeoW/api_doc.html", False),
    ("raw.githubusercontent.com", "/ringhyacinth/Star-Office-UI/master/README.md", False),
    ("raw.githubusercontent.com", "/ringhyacinth/Star-Office-UI/master/SKILL.md", False),
    ("api.github.com", "/repos/ringhyacinth/Star-Office-UI", False),
    ("learn.microsoft.com", "/en-us/azure/quantum/concepts-dirac-notation", True),
    ("api.bilibili.com", "/x/web-interface/view", True),   # 查过其 robots 为 Disallow: / ⇒ 本席【未取内容】
]

# ★ v1.1.0 修正两处（承轮 74 自查）：
#   ① 豁免 /robots.txt 本身——为遵守 robots 必须先能读它；RFC 9309 亦以其可读为前提。
#      故本器对 /robots.txt 一律记「豁免」，不计入违规。
#   ② 把「robots 未声明」独立成类——v1.0.0 把它错并入「已预查」，属标签错误，已改。
print("═══ 全量审计：今晚外部取件 vs 各主机 robots（v1.1.0）═══")
print("  图例：★违规＝未预查 且 判为禁 ｜ ◐未预查但准 ｜ ✓已预查 ｜ ○robots未声明 ｜ ⊘豁免")
print()
viol, unpre, okc, undecl = [], [], 0, []
cache = {}
for host, path, prechecked in FETCHES:
    if host not in cache:
        st, txt = fetch("https://%s/robots.txt" % host)
        cache[host] = (st, parse_robots(txt) if st == 200 else None)
    st, rules = cache[host]
    if path == "/robots.txt":
        tag, verdict = "⊘豁免", "为遵守 robots 必须可读（RFC 9309 前提）"
    elif rules is None:
        tag, verdict = "○未声明", "robots %s ⇒ 无限制声明" % (st if st else "取不到")
        undecl.append((host, path, prechecked))
    else:
        allowed_now = allowed(rules, path)
        verdict = "准" if allowed_now else "★禁"
        if allowed_now is False and not prechecked:
            tag = "★违规"; viol.append((host, path))
        elif allowed_now is False and prechecked:
            tag = "✓已预查(故未取内容)"
        elif allowed_now is True and not prechecked:
            tag = "◐未预查但准"; unpre.append((host, path))
        else:
            tag = "✓已预查"; okc += 1
    print("  %-16s %-52s ⇒ %s" % (tag, host + path, verdict))

print()
print("  ── 汇总 ──")
print("   取件条目 = %d" % len(FETCHES))
print("   ★违规（未预查 且 判为禁）= %d 条" % len(viol))
for h, p in viol:
    print("       · https://%s%s" % (h, p))
print("   ◐未预查但现判为准 = %d 条" % len(unpre))
for h, p in unpre:
    print("       · https://%s%s" % (h, p))
print("   ○robots 未声明 = %d 条（其中取件前未查者 %d 条）"
      % (len(undecl), sum(1 for _, _, pc in undecl if not pc)))
for h, p, pc in undecl:
    print("       · https://%s%s  ｜ 取件前查过？%s" % (h, p, "是" if pc else "★否"))
print()
print("★ 本器能返回【违规】与【不违规】两种结果，且先验对照已证其分辨力 ⇒ 非恒真。")
print("★ 本器只读 robots.txt；判为禁者不再取任何内容。")
