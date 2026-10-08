#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只读统计台账里的"推给别人"类条目；不触网、不改动任何件。
r"""audit_deferrals.py —— 数我自己产出过多少"等别人"，并判其中多少是【托辞】。 v1.0.0

★★ 2026-10-02 轮 14 标注：本器与 `audit_argument_arc.py`、`audit_by_evtype.py` 在同一对象上重叠。
   ★ 本器判据同样【按字样】⇒ 轮 7–11 已证该法会被"提到"污染。
   ⇒ 故本器的比值【只作警示】；★ 且轮 8 已记：描述托辞问题本身就要用"等"的字样 ⇒ 该指标【部分自我污染】。

为什么做它
────────────
轮 7 我以「须由拿到计数的人判 —— 第一次，包括您」收尾。
★ 可若每一轮都以"等别人"收尾，那这套序列就是【一台生成托辞的机器】，而我把它叫做自主推进。

判据（四类，取自轮 6 的分类法）
────────────────────────────────
  给定         —— 真等他方（他方意志/数学性质）
  受授权约束    —— 我能做、但须机主一句话
  ★ 选择       —— 我能做而我选择不做 ⇒ ★ 若被写成"等他方"，即【托辞】
  ★ 未检验     —— 我不知能不能做，也没试 ⇒ ★ 若被写成"等他方"，即【托辞】

★ 本器的诚实处：它【只能按字样分类】——★ 故它可能再次犯【把提到当成做到】。
  故它只打印【计数与原文片段】，由人判；且它把这一限制写在输出里。
"""
from __future__ import annotations
import json
import pathlib
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SEAT = pathlib.Path(__file__).resolve().parent.parent
LEDGER = SEAT / "ledger" / "frontier_ledger.jsonl"

DEFER = re.compile(r"待您|需机主|未获授权|等您|须由|只能把接口留出来|等待|在等|"
                   r"本席没有|本席无法|不由本席|请机主|须人工|由人判|交由")
CLOSE = re.compile(r"已修|已完成|已投放|已归位|已入档|已清|已补|PASS|已追加|已钉|已证伪")
AUTH = re.compile(r"授权|许可|机主一句")
SELFDO = re.compile(r"本席能|我能做|本席可|我可以|本席就能")


def main() -> int:
    if not LEDGER.is_file():
        print("ERR 台账不在：%s ⇒ ★ 器具故障" % LEDGER)
        return 2
    rows = [json.loads(l) for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
    arc = [r for r in rows if str(r.get("ts", "")).startswith("2026-10-02T21:")]
    print("═══ 「托辞」审计（只读）═══")
    print("  台账 = %d 条 ｜ 自指性论证时段 = %d 条" % (len(rows), len(arc)))

    def text(r):
        return (r.get("subject", "") or "") + " || " + (r.get("detail", "") or "")

    d_all = [r for r in rows if DEFER.search(text(r))]
    d_arc = [r for r in arc if DEFER.search(text(r))]
    c_arc = [r for r in arc if CLOSE.search(text(r))]
    print()
    print("  ── A · 含「等别人」字样的条目 ──")
    print("     全台账 = %d / %d  (%.0f%%)" % (len(d_all), len(rows), 100.0*len(d_all)/max(1,len(rows))))
    print("     ★ 论证时段 = %d / %d  (%.0f%%)" % (len(d_arc), len(arc), 100.0*len(d_arc)/max(1,len(arc))))
    print("  ── B · 含「已做/已闭」字样的条目（论证时段）──")
    print("     = %d / %d  ⇒ ★ 做与等的比 = %.2f : 1" % (len(c_arc), len(arc), len(c_arc)/max(1,len(d_arc))))

    print()
    print("  ── C · 论证时段里，同时含【等别人】与【授权】字样的（＝自称受授权约束的）──")
    both = [r for r in arc if DEFER.search(text(r)) and AUTH.search(text(r))]
    print("     = %d" % len(both))
    for r in both[:8]:
        print("       %s  %s" % (str(r.get("ts", ""))[:19], str(r.get("subject", ""))[:52]))

    print()
    print("  ── D · ★ 可疑项：含【等别人】但【不含授权字样】的 —— 须人判其是否托辞 ──")
    susp = [r for r in arc if DEFER.search(text(r)) and not AUTH.search(text(r))]
    print("     = %d" % len(susp))
    for r in susp[:10]:
        t = text(r)
        m = DEFER.search(t)
        s = max(0, m.start()-60); e = min(len(t), m.end()+60)
        print("       %s  %s" % (str(r.get("ts", ""))[:19], str(r.get("subject", ""))[:44]))
        print("            …" + t[s:e].replace("\n", " ") + "…")

    print()
    print("  ═══ 判定 ═══")
    ratio = len(c_arc) / max(1, len(d_arc))
    print("     B 的比 = %.2f : 1（做 : 等）" % ratio)
    if ratio >= 1.0:
        print("     ✅ 做 ≥ 等 ⇒ 至少每一条「等」都配了一条「做」。")
    else:
        print("     ★ 等 > 做 ⇒ ★ 形态偏【生成托辞】。")
    print("     ★★ 本器只能按字样分类 ⇒ 可能再次犯【把提到当成做到】；")
    print("        故它【不下「是否是托辞」的定论】，只把可疑项与原文摆出来给人判。")
    print("★ NOVERDICT=1 —— 本器只把可疑项摆出来，★ 不下判词（由设计）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
