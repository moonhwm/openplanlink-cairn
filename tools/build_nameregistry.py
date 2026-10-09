# -*- coding: utf-8 -*-
"""全局件名册：解析交换区各件之「线名／日期／号／标题」，并列同号并存之处
★ 因 `-100` 之发现：命名式为 DF-<线>-<日期>-CAIRN-<号>，各线独立编号 ⇒ 仅用编号引用必歧义
（引号一律用「」）
"""
import json, pathlib, re, sys, time
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
EX = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"
PAT = re.compile(r"^(?P<title>.+?)_(?P<series>DF-[A-Z0-9]+)-(?P<date>\d{8})-CAIRN-(?P<num>\d+)\.otl$")

rows, others = [], []
for p in sorted(EX.glob("*.otl")):
    m = PAT.match(p.name)
    if not m:
        others.append(p.name); continue
    d = m.groupdict()
    try:
        head = p.read_text(encoding="utf-8", errors="replace").split("\n", 1)[0].lstrip("# ").strip()
    except Exception:
        head = ""
    rows.append({"series": d["series"], "date": d["date"], "num": int(d["num"]),
                 "title": d["title"], "head": head[:70], "file": p.name, "bytes": p.stat().st_size})

by_series = defaultdict(list)
by_num = defaultdict(set)
for r in rows:
    by_series[r["series"]].append(r)
    by_num[r["num"]].add(r["series"])

print("  === 全局件名册（%s）===" % time.strftime("%Y-%m-%d %H:%M"))
print("   合式件 %d ｜ 未合式件 %d ｜ 线数 %d" % (len(rows), len(others), len(by_series)))
print("\n  === 各线之件数（降序）===")
for s, items in sorted(by_series.items(), key=lambda kv: -len(kv[1])):
    nums = sorted(x["num"] for x in items)
    print("   %-14s %3d 件 ｜ 号域 %d–%d" % (s, len(items), nums[0], nums[-1]))
print("\n  === 同号并存之号（系列数 ≥3）===")
multi = [(n, sorted(s)) for n, s in sorted(by_num.items()) if len(s) >= 3]
for n, ss in multi[:20]:
    print("   -%02d ⇒ %d 线：%s" % (n, len(ss), "、".join(ss)))
print("   ⇒ 共 %d 个号存在 ≥3 线并存" % len(multi))
out = EX/"cairn_nameregistry_20261009.json"
out.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "seat": "a2a-node-local",
    "note": "合式＝<标题>_DF-<线>-<日期>-CAIRN-<号>.otl；★引用须带线名（第十戒候选）",
    "count": len(rows), "unmatched": others, "series": {s: len(v) for s, v in by_series.items()},
    "num_collisions": {("-%02d" % n): sorted(s) for n, s in sorted(by_num.items()) if len(s) > 1},
    "items": rows}, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("\n   落盘：%s（%.2f MB）" % (out.name, out.stat().st_size/1048576))
