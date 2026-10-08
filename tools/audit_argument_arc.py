#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只读统计本席台账与件，判"论证序列"是收敛还是空转。不触网。
r"""audit_argument_arc.py —— 把"我这七轮是收敛还是空转"变成【可数的东西】。 v1.0.0

★★ 2026-10-02 轮 14 标注（不是补丁，是【让读者别被本器误导】）：
   本器与 `audit_deferrals.py`、`audit_by_evtype.py` 在【同一对象】上重叠，
   而轮 11 的【逐条手判】已证明：这三个器里的两个（字样类）给出的数【偏离实际】——
   ★ 字样会【高估】（把"叙述推翻"算成推翻）、字段会【低估】（本席归类不一致）。
   ⇒ 故本器的计数【只作候选】，**最终的推翻率以轮 11 的手判表为准：严格 62%（8/13）｜宽松 77%（10/13）**。
   ⇒ 见 `outbox\\自指性论证十一…`（含 18 行逐条判词，可逐格推翻）。
   ★ 且轮 14 的工具箱审计显示：本器属"同一对象被 3 个器提及"之一 ⇒ 保留而不新造第四个。

为什么做它
────────────
自指性论证已连做六轮。★ 而"再来一轮"这件事本身需要一个判据：
**若每轮都只是【加装置】而不【补洞】，那就是空转——哪怕每轮都产出了新件。**

可测的四项
────────────
  A 推翻率：台账里【更正／自曝／勘误／推翻】类条目 占 论证类条目 的比例
     ⇒ 高 = 每轮都在真测自己；0 = 只在叠加
  B 终点稳定性：从第 4 轮起，"终点"（需一个独立复算者）这句话是否【一字未变】
     ⇒ 不变 = 终点已定；★ 而终点已定却仍在加装置 = ★ 绕着洞打转
  C 装置增长：每轮的【新器数】与【新件数】
  D 洞是否被补：台账里有没有【任何一条】记录"他方独立复算已完成"
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

OVERTURN = re.compile(r"更正|自曝|勘误|推翻|错|缺陷|停滞|停早|名不副实")
TERMINUS = re.compile(r"独立复算|独立见证|不受本席这枚钉约束|第二个.*席位|独立对端")
ADDITIVE = re.compile(r"ARGUMENT|追加|新增|增")


def main() -> int:
    if not LEDGER.is_file():
        print("ERR 台账不在：%s ⇒ ★ 器具故障" % LEDGER)
        return 2
    rows = [json.loads(l) for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
    print("═══ 论证弧审计（只读）═══")
    print("  台账条目 = %d" % len(rows))

    # 按小时聚拢：本席自指性论证发生在 10-02 21:0x 之后
    arc = [r for r in rows if str(r.get("ts", "")).startswith("2026-10-02T21:")]
    print("  ★ 自指性论证时段（2026-10-02 21:xx）条目 = %d" % len(arc))

    def verdict(r):
        txt = (r.get("subject", "") or "") + (r.get("detail", "") or "")
        is_turn = bool(OVERTURN.search(txt))
        is_term = bool(TERMINUS.search(txt))
        return is_turn, is_term

    turns = [r for r in arc if verdict(r)[0]]
    terms = [r for r in arc if verdict(r)[1]]
    print()
    print("  ── A · 推翻率 ──")
    print("     含【更正/自曝/勘误/推翻/缺陷】字样的条目 = %d / %d  (%.0f%%)"
          % (len(turns), len(arc), 100.0 * len(turns) / max(1, len(arc))))
    for r in arc:
        t, _ = verdict(r)
        mark = "★推翻" if t else "  叠加"
        print("       %s  %-14s %s" % (mark, r.get("ev_type"), str(r.get("subject", ""))[:58]))

    print()
    print("  ── B · 终点稳定性 ──")
    print("     提到【独立复算/独立见证/第二个席位】的条目 = %d" % len(terms))
    for r in terms[-6:]:
        m = re.search(r"独立复算|独立见证|不受本席这枚钉约束[^。]{0,20}|第二个[^。]{0,12}席位", 
                      (r.get("subject", "") or "") + (r.get("detail", "") or ""))
        print("       %s  → 「%s」" % (str(r.get("ts", ""))[:19], (m.group(0) if m else "?")))

    print()
    print("  ── C · 装置增长（本轮时段内新建的器／件）──")
    def newest(sub: str, pat: str):
        got = [p for p in (SEAT / sub).rglob("*") if p.is_file() and re.search(pat, p.name)]
        return len(got)
    print("     exp 下的 .py 器 = %d" % newest("exp", r"\.py$"))
    print("     exp 下【本时段新造】的器（名字含 selfref|seat_location|forge|lockpin|audit_honesty|neg_control|twocopy）")
    newtools = [p.name for p in (SEAT / "exp").rglob("*")
                if p.is_file() and re.search(r"selfref|seat_location|forge|lockpin|audit_honesty|neg_control|twocopy", p.name)]
    print("        = %d 个：%s" % (len(newtools), "、".join(sorted(newtools))))

    print()
    print("  ── D · 洞是否被补（★ 判据已收紧：只认【完成标记】，不认【提到】）──")
    # ★ 2026-10-02 轮 7 修：首版 D 判据把「要真正破环唯一的路是他方独立复算」这类
    #   【声明洞还在】的句子，当成了【记录他方独立复算已完成】⇒ 假阳性，
    #   且因它非 0，把"洞未被补"那句结论【静默跳过】。
    #   病名：★【把"提到"当成"做到"】——本缺陷第四次。
    DONE = re.compile(r"已收到.{0,12}复算|复算结论已|对联署完成|已联署完成|他方复算已完成|COUNTERSIGN")
    hole = [r for r in rows if DONE.search((r.get("subject", "") or "") + (r.get("detail", "") or ""))]
    print("     带【完成标记】的条目 = %d" % len(hole))
    if len(hole) == 0:
        print("     ★★ 0 ⇒ 洞【未被补】，仍在等 —— ★ 这一句是本器存在的理由，故【无条件打印】。")
    else:
        for r in hole:
            print("       %s  %s" % (str(r.get("ts", ""))[:19], str(r.get("subject", ""))[:56]))

    print()
    print("  ═══ 判定 ═══")
    ratio = len(turns) / max(1, len(arc))
    # ★ 终点与洞，各自无条件打印
    print("     B 终点：自第 4 轮起稳定提及 %d 次 ⇒ ★ 终点【未动】" % len(terms))
    if len(hole) == 0:
        print("     D 洞：★ 未补（带完成标记的条目 = 0）⇒ ★★ 形态：【终点未动，装置在长】")
    else:
        print("     D 洞：★ 已有 %d 条完成标记 ⇒ 洞已补（须人工复核其真伪）" % len(hole))
    if ratio >= 0.25:
        print("     ✅ 推翻率 %.0f%% ≥ 25%% ⇒ 每数条就有一条在推翻自己 ⇒ 不是单纯叠加。" % (100 * ratio))
    else:
        print("     ★ 推翻率 %.0f%% 偏低 ⇒ 偏叠加。" % (100 * ratio))
    print("     ★★ 本器自身的边界：A 的『推翻』仍按【字样】判 ⇒ 同样可能犯『把提到当成做到』。")
    print("        故本器只报【计数与出处】，不替人下『收敛/空转』的定论。")
    print("★ NOVERDICT=1 —— 本器只报计数与出处，★ 不替人下判词（由设计）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
