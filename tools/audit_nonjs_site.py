#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
audit_nonjs_site.py —— 对整站逐页做【非 JS 读者】审计，产出可复核的表。 v1.0.0

为什么
──────
本席轮 57 曾就【线上旧版】下过结论：「三页有静态兜底文案，其中只有 observe.html 是真缺陷」。
但 v2.1 是【整站重建】⇒ 旧的取舍不能沿用 ⇒ 必须【逐页重查】。

本器对每个页面回答四问
────────────────────────
  Q1 有没有静态兜底文案（非 JS 读者会看到的字）？
  Q2 真正内容是否靠 JS 才出现（隐没）？
  Q3 有没有 <noscript> 给出正确信息？
  Q4 ★ 判定：那静态文案在【非 JS 场景下是否成立】——
       FALSE      = 说了不成立的话（如"数据接口未载入"而它其实能载入）
       MISLEADING = 字面不算假，但会让读者以为此处就该是空白/出错
       TRUE       = 说的是真话（如"需启用 JS 以查看交互"）
       NONE       = 没有静态文案（非 JS 读者什么也看不到——也算一种缺陷，故单列）

★ 本器须能失败：若它对所有页面给出同一判定，即视为无分辨力并作废（见末行断言）。
用法: audit_nonjs_site.py <目录1> [目录2 …]
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

PAGES = ["index.html", "observe.html", "oracle.html", "sandbox.html",
         "sea.html", "cinema.html", "a2a-architecture.html"]

# ★ 判定用的词表（少而明确；命中即归类，不写模糊启发式）
FALSE_HINTS = ("未载入", "未接入", "加载失败", "数据接口")
TRUE_HINTS = ("请启用", "需要 JavaScript", "需启用", "未启用 JavaScript", "noscript")


def strip_tags(s: str) -> str:
    s = re.sub(r"(?s)<script.*?</script>", " ", s)
    s = re.sub(r"(?s)<style.*?</style>", " ", s)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def fallback_text(t: str) -> str:
    m = re.search(r'<div[^>]*id="fallback"[^>]*>(.*?)</div>', t, re.S)
    if m:
        return strip_tags(m.group(1))
    # 其它常见兜底容器
    for pat in (r'<div[^>]*class="[^"]*fallback[^"]*"[^>]*>(.*?)</div>',
                r'<p[^>]*id="fallback"[^>]*>(.*?)</p>'):
        m = re.search(pat, t, re.S)
        if m:
            return strip_tags(m.group(1))
    return ""


def hidden_content(t: str) -> bool:
    return bool(re.search(r'style="[^"]*display\s*:\s*none', t)) or \
           bool(re.search(r'id="grid"[^>]*style="[^"]*display\s*:\s*none', t))


def judge(fb: str, has_noscript: bool, body_text_len: int) -> str:
    fbl = fb.lower()
    if has_noscript:
        return "TRUE"
    if any(h.lower() in fbl for h in FALSE_HINTS):
        return "FALSE"
    if not fb:
        return "NONE" if body_text_len < 200 else "TEXT-OK"
    if any(h.lower() in fbl for h in TRUE_HINTS):
        return "TRUE"
    return "MISLEADING"


def audit(d: pathlib.Path):
    rows = []
    for name in PAGES:
        p = d / name
        if not p.is_file():
            rows.append((name, "-", "-", "-", "-", "缺文件")); continue
        t = p.read_text(encoding="utf-8", errors="replace")
        fb = fallback_text(t)
        ns = "<noscript" in t.lower()
        hid = hidden_content(t)
        body = strip_tags(t)
        v = judge(fb, ns, len(body))
        rows.append((name, "%d" % p.stat().st_size, (fb[:34] or "（无）"), "有" if ns else "无",
                     "是" if hid else "否", v))
    return rows


def main() -> int:
    dirs = [pathlib.Path(x) for x in sys.argv[1:]]
    if not dirs:
        print("用法: audit_nonjs_site.py <目录> [目录…]"); return 2
    verdicts = []
    for d in dirs:
        print("═══ %s ═══" % d)
        rows = audit(d)
        print("  %-24s %8s  %-36s %6s %6s  %s" % ("页面", "字节", "非JS读者看到的静态文案", "noscript", "内容隐没", "判定"))
        for r in rows:
            print("  %-24s %8s  %-36s %6s %6s  %s" % r)
            verdicts.append(r[5])
        print()
    bad = [v for v in verdicts if v in ("FALSE", "MISLEADING", "NONE")]
    print("  ── 汇总 ──")
    print("   受检页面 = %d ｜ FALSE = %d ｜ MISLEADING = %d ｜ NONE = %d ｜ TRUE = %d ｜ TEXT-OK = %d"
          % (len(verdicts), verdicts.count("FALSE"), verdicts.count("MISLEADING"),
             verdicts.count("NONE"), verdicts.count("TRUE"), verdicts.count("TEXT-OK")))
    print("   ★ 需修（FALSE/MISLEADING/NONE）= %d 页" % len(bad))
    # ★ 分辨力自证
    distinct = len(set(verdicts))
    print("   ★【分辨力自证】判定共出现 %d 种 ⇒ %s"
          % (distinct, "有分辨力" if distinct > 1 else "★无分辨力，本器作废"))
    if distinct <= 1:
        return 3
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
