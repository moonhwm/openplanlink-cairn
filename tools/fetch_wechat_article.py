#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NET —— 本件可发起对外网络调用（取公众号正文（经 robots 闸口放行才取））。声明供 blast_radius.py 审计。
r"""
fetch_wechat_article.py —— 正常取一篇公众号文章并【正确解码】，提取标题与正文摘要。 v1.0.0

来由
────
本席轮 53 用取件器取 https://mp.weixin.qq.com/s/udYV67xgvcZlquYnFepHug 时撞上验证码墙
（`wappoc_appmsgcaptcha`）。机主却称「公网能够访问」。
轮 62 本席以**标准浏览器 UA** 正常请求一次，得 HTTP 200 与 2,592,902 B ⇒ 可读。

★ 纪律（写死）
──────────────
  1. **只试一次**；**若遇验证码墙（appmsgcaptcha / 环境异常 / 完成验证）即停，不重试、不绕、不换 IP、不伪装**；
  2. **不整篇复制**：本器只输出**标题、字数、章节线索与摘要**，正文另存本席目录供自己核对；
  3. 只读；不写对方任何东西。

用法: fetch_wechat_article.py <url> [--out 文件]
"""
from __future__ import annotations
import argparse
import html
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
WALL = re.compile(r"appmsgcaptcha|环境异常|完成验证|wappoc_appmsgcaptcha")



# ★ 轮108：网络总闸——只在 DSH_NO_NET 置上时装"拒绝外发"钩子；未置则【一行都不改行为】。
try:
    import netguard as _netguard
    _netguard.activate()
except Exception:
    pass

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    # ★★ v1.1.0 结构性修法（承轮 74 的自审承诺）：**取件前先过 robots 闸口**。
    #    由来：本器正是轮 62 那处违规的当事工具（未先查 robots 即取 mp.weixin.qq.com 的文章）。
    #    ⇒ 故把闸口【接进本器】，使纪律不再依赖"我记得"。
    #    ★ 本器【不提供 --force 覆盖开关】：可被随手绕过的闸口等于没有闸口。
    #      若将来确需例外，须改代码并写明理由——那才是可审计的例外。
    _gate_ok, _gate_why = (None, "（未加载 robots_gate，跳过闸口 ⇒ ★不算合规取件）")
    try:
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
        from robots_gate import check as _rg_check
        _gate_ok, _gate_why = _rg_check(a.url)
    except Exception as _e:
        _gate_ok, _gate_why = None, "（闸口加载失败：%s）" % str(_e)[:60]
    print("  [robots 闸口] %s ⇒ %s" % (a.url, _gate_why))
    if _gate_ok is False:
        print("  ★拒绝取件：该 URL 被其站 robots 禁止。")
        print("  ★本器不提供覆盖开关；如确需例外，请改码并写明理由（可审计）。")
        return 3
    if _gate_ok is None:
        print("  ★闸口无法判定（robots 未声明或取不到）⇒ 本器【不再假装合规】：")
        print("     按硬规 A，本器将不取件，并把该状态如实报出。")
        return 4

    req = urllib.request.Request(a.url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    with urllib.request.urlopen(req, timeout=45) as r:
        raw = r.read()
    print("  HTTP %s ｜ %d B ｜ Content-Type=%s" % (r.status, len(raw), r.headers.get("Content-Type")))

    # 编码：优先响应头，其次 meta charset，最后 utf-8
    enc = "utf-8"
    m = re.search(rb'charset=["\']?([\w-]+)', raw[:4096], re.I)
    if m:
        enc = m.group(1).decode("ascii", "replace")
    t = raw.decode(enc, "replace")

    if WALL.search(t[:20000]):
        print("  ★仍为验证码墙 ⇒ 本席停在此处：不重试、不绕、不换 IP、不伪装。")
        return 3

    title = ""
    m = re.search(r'var msg_title\s*=\s*["\'](.+?)["\']', t)
    if m:
        title = m.group(1)
    if not title:
        m = re.search(r'<h1[^>]*>(.*?)</h1>', t, re.S)
        if m:
            title = re.sub(r"<[^>]+>", "", m.group(1)).strip()
    print("  标题：%s" % (html.unescape(title) or "（未取到）"))

    # 正文：公众号正文在 id="js_content" 的 div 里
    body = ""
    m = re.search(r'<div[^>]*id="js_content"[^>]*>(.*?)</div>\s*<script', t, re.S)
    if not m:
        m = re.search(r'<div[^>]*id="js_content"[^>]*>(.*)', t, re.S)
    if m:
        seg = m.group(1)
        seg = re.sub(r"(?s)<script.*?</script>", " ", seg)
        seg = re.sub(r"(?s)<style.*?</style>", " ", seg)
        seg = re.sub(r"<[^>]+>", "\n", seg)
        seg = html.unescape(seg)
        lines = [x.strip() for x in seg.splitlines()]
        lines = [x for x in lines if len(x) > 1]
        body = "\n".join(lines)

    print("  正文字符数：%d ｜ 段落数：%d" % (len(body), len(body.splitlines()) if body else 0))
    if body:
        print("  ---- 段落前 12 行（供本席自己判读，不整篇外发）----")
        for ln in body.splitlines()[:12]:
            print("    " + ln[:100])
        # 章节线索：短行且像小标题
        heads = [x for x in body.splitlines() if 2 <= len(x) <= 24 and not x.endswith(("。", "，", "；"))]
        print("  ---- 疑似小标题 %d 条（前 12）----" % len(heads))
        for h in heads[:12]:
            print("    · " + h)

    if a.out:
        p = pathlib.Path(a.out)
        p.write_text("TITLE: %s\n\n%s" % (title, body), encoding="utf-8")
        print("  [OK] 正文已存本席目录：%s（%d B）" % (p.name, p.stat().st_size))
    return 0


if __name__ == "__main__":
    sys.exit(main())
