# -*- coding: utf-8 -*-
"""kj34.py —— 核"变更"之真伪：对照相邻两次拉取之 sha3（2026-10-13）
缘由：-1432／-1433 判"伪变更＝两器自比"；然两器之比法★皆为"比 hash"（doc_refresh: h == prev["hash"]；
      doc_archive: changed = prev["hash"] != h）⇒ ★与"谁写了 prev"无关 ⇒ 若 hash 相同则应报"无变更"。
      故须核：★相邻两次拉取之 sha3 ★到底同否 ⇒ 判"变更"是真（云端微变）还是自比所致。
判据（可失败）：①六 key 皆读到史；②★给出"相邻两次 sha3 同否"之表；③★给出结论
（中文串一律用「」）
"""
import json, pathlib, sys

sys.stdout.reconfigure(encoding="utf-8")
H = pathlib.Path.home()
p = (H/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"
     /"A2A新席_石敢当Cairn_20260928"/"archive"/"docs"/"index.json")
j = json.loads(p.read_text(encoding="utf-8-sig"))
KEYS = ("outline", "polish", "polish_otl", "kd_PoRdSw", "kd_lGgqkZ", "kd_sbZsGm")
same_n = diff_n = 0
for k in KEYS:
    if k not in j:
        print("   ★缺 key：%s" % k); continue
    h = (j[k].get("history") or [])
    if len(h) < 2:
        print("   ★%s 史不足 2 条" % k); continue
    a, b = h[-2], h[-1]
    eq = (a.get("hash") == b.get("hash"))
    same_n += 1 if eq else 0
    diff_n += 0 if eq else 1
    print("   ★%-12s ｜ %s→%s ｜ sha3 前 12：%s → %s ｜ %s"
          % (k, str(a.get("ver")), str(b.get("ver")), str(a.get("hash"))[:12],
             str(b.get("hash"))[:12], "★相同（未变）" if eq else "★不同（内容确变）"))
print("   ── 判 ──")
print("   ★相邻同 %d ｜ ★相邻异 %d（共 %d key）" % (same_n, diff_n, len(KEYS)))
print("   ★★若异者多于 0 ⇒ 「变更」非自比所致，而系★该键之内容在两次拉取间确变（云端为活文档）")
print("   ★★且两器之比法皆为「比 hash」⇒ 与「谁写了 prev」无关 ⇒ 自比不产生变更")
