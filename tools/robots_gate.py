#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NET —— 本件可发起对外网络调用（只读 robots.txt（为遵守 robots 必须能读））。声明供 blast_radius.py 审计。
r"""
robots_gate.py —— 取件前的 robots 闸口（把纪律结构化，不靠记忆）。 v1.0.0

由来（轮 74 自查）
──────────────────
本席今晚对 20 条外部取件做了 robots 合规审计，结果：
  ★违规 3 条（AppGallery 详情页 ×2；**mp.weixin.qq.com 文章 ×1——此条此前本席不知**）
  ✓取件前查过 2 条 ｜ ○robots 未声明 13 条 ｜ ◐未查但准 1 条
⇒ **二十次里只查过两次。** 教训同本席当夜那条：**要靠"记得"的规矩一定会漏，
  必须做成【器具】——本器即为此。**

★ 用法（把闸口放在取件之前）
    from robots_gate import check
    ok, why = check("https://mp.weixin.qq.com/s/xxx")
    if not ok: 停下，不取。

★ 自证能失败
    本器内置 demo：**必须拦下微信文那条**、**必须放行一条已知允许的**；
    两者若同结论 ⇒ 本器作废（见 selftest）。
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
UA = "Mozilla/5.0 (compatible; cairn-dsh robots-gate)"


def _fetch(url: str, timeout: int = 20):
    # ★ 轮107：网络总闸——置上则一律不取（含 robots.txt 本身）。
    import pathlib as _p
    import sys as _s
    _s.path.insert(0, str(_p.Path(__file__).resolve().parent))
    try:
        import netguard as _NG
        if not _NG.allowed():
            return None, ""
    except Exception:
        pass
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with OPENER.open(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:
        return None, ""


def _parse(txt: str):
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


def _re(pat: str):
    body, anchor = (pat[:-1], "$") if pat.endswith("$") else (pat, "")
    return re.compile("^" + re.escape(body).replace(r"\*", ".*") + anchor)


def _allowed(rules, path: str) -> bool:
    best = None
    for allow, pat in rules:
        if pat and _re(pat).match(path):
            L = len(pat)
            if best is None or L > best[0] or (L == best[0] and allow and not best[1]):
                best = (L, allow)
    return True if best is None else best[1]


def check(url: str):
    """返回 (allowed: bool|None, why: str)。None 表示 robots 未声明（无限制声明）。

    ★★ 轮104 增：**未声明时不再由本器写死的默认裁决，而是【问策略层】**——
      通道 `undeclared_fetch`（in）：所需 T2，**实测现状 T0** ⇒ 现为 DENY。
      机主若选 B 或 ★D，只改 `auth_policy.py` 一处，本器随之变。
    """
    import pathlib as _p
    import sys as _s
    _s.path.insert(0, str(_p.Path(__file__).resolve().parent))
    try:
        import auth_policy as _AP
    except Exception:
        _AP = None
    from urllib.parse import urlsplit
    u = urlsplit(url)
    if u.path == "/robots.txt":
        return True, "⊘豁免：为遵守 robots 必须可读（RFC 9309 前提）"
    st, txt = _fetch("%s://%s/robots.txt" % (u.scheme, u.netloc))
    if st is None:
        return None, "○robots 取不到 ⇒ 无法判定（本席不得据此认为无限制）"
    if st == 404:
        # ★★ 轮104：未声明 ⇒ **问策略层**（不再由本器写死默认）
        if _AP is None:
            return None, "○robots 未声明（404）⇒ 策略层不可用 ⇒ 从严：不取"
        v, why = _AP.check("undeclared_fetch", "in", "public")
        return (True if v == "ALLOW" else None), (
            "○robots 未声明（404）⇒ ★策略层裁决 %s：%s" % (v, why))
    if st != 200:
        return None, "○robots 返回 %s ⇒ 无法判定" % st
    rules = _parse(txt)
    path = u.path + (("?" + u.query) if u.query else "")
    ok = _allowed(rules, path)
    return ok, ("准" if ok else "★禁") + "（依 %s://%s/robots.txt）" % (u.scheme, u.netloc)


def selftest() -> int:
    print("═══ robots_gate 自证（必须能拦、也必须能放）═══")
    cases = [
        ("https://mp.weixin.qq.com/s/udYV67xgvcZlquYnFepHug", False, "★本案：本席确曾误取"),
        ("https://appgallery.huawei.com/app/detail?id=com.wzdxy.ssh.h", False, "含 ? ⇒ Disallow: /*?*"),
        ("https://appgallery.huawei.com/Featured", True, "其 robots 明写 Allow"),
        ("https://learn.microsoft.com/en-us/azure/quantum/concepts-dirac-notation", True, "只禁 /answers/*"),
        ("https://api.bilibili.com/x/web-interface/view", False, "Disallow: /"),
    ]
    bad = 0
    for url, want, note in cases:
        got, why = check(url)
        ok = (got == want)
        bad += 0 if ok else 1
        print("  %s %-58s ⇒ %-6s（期望 %-5s）｜%s"
              % ("✓" if ok else "★FAIL", url[:58], got, want, note))
    print()
    print("  ⇒ %s" % ("自证通过：本器同时能拦与能放" if bad == 0 else "★自证未过 %d 条" % bad))
    print("  ★ 关键：它对微信文与 MS Learn 给出【不同】结论 ⇒ 非恒真。")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        sys.exit(selftest())
    if len(sys.argv) > 1:
        ok, why = check(sys.argv[1])
        print("  %s ⇒ %s ｜ %s" % (sys.argv[1], ok, why))
        sys.exit(0 if ok is not False else 1)
    print("用法: robots_gate.py --selftest ｜ robots_gate.py <url>")
