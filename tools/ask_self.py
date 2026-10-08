#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 本件只读本机台账与出件，不触网。
r"""ask_self.py —— 落笔前先问自己一次：**我碰过这件事吗？** v1.0.0

为什么要有它（今夜两次教训）
──────────────────────────────
轮 123：我准备报"我从没清点过握手对家"——一查，轮 100 已引用过其五面入口、台账第 99 条也记着。
轮 126：我准备写一件针对共同认领者的分工件——一查，`交件单` 早已存在。
⇒ **两次都是同一个形状：我对【自己已做过的事】的记忆，偏向少算了自己。**
⇒ 故修法不是"记得更牢"，而是**一个可查的东西**——落笔前跑一次。

★ 并遵本席硬规 A：**任何"未命中"都【必须带上检索范围与覆盖】**，
  不许给出一句无范围的"从未做过"。

用法:
  ask_self.py <关键词> [更多关键词…]      # 与命中任一即可
  ask_self.py --all-of <词1> <词2> …       # 必须全部命中
  ask_self.py --scope                       # 只打印检索范围
三态判词：`命中` ／ `部分命中` ／ `未命中（范围已列）`
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
LED = SEAT / "ledger" / "frontier_ledger.jsonl"
OUTBOX = SEAT / "outbox"
EXP = SEAT / "exp"


def load_ledger():
    rows = []
    if LED.is_file():
        for i, line in enumerate(LED.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append((i, json.loads(line)))
            except Exception:
                pass
    return rows


def main() -> int:
    argv = [a for a in sys.argv[1:]]
    all_of = False
    if argv and argv[0] == "--all-of":
        all_of = True
        argv = argv[1:]
    if argv and argv[0] == "--scope":
        argv = []
    if not argv:
        print("用法: ask_self.py <关键词…>  ｜ --all-of 词1 词2 …  ｜ --scope")
        # 仍打印范围（--scope 语义）
        argv = []

    rows = load_ledger()
    ob = [p for p in OUTBOX.glob("*") if p.is_file()] if OUTBOX.is_dir() else []
    ex = [p for p in EXP.glob("*") if p.is_file()] if EXP.is_dir() else []
    ob_dirs = [p for p in OUTBOX.glob("*") if p.is_dir()] if OUTBOX.is_dir() else []
    deps = sum(len(list(p.rglob("*"))) for p in ob_dirs)

    print("═══ 自查：我碰过这件事吗 ═══")
    print("  ── 检索范围（★任何「未命中」都必须带这一段）──")
    print("     台账条目        %d 条（%s）" % (len(rows), LED.name))
    print("     本席 outbox     %d 件文件 ＋ %d 个子目录（含 %d 项）" % (len(ob), len(ob_dirs), deps))
    print("     器具 exp/       %d 件" % len(ex))
    print("     ★ 未纳入：共享面、桌面副本、handshake/ 下他人代码（本器只查【我自己的产出】）")
    if not argv:
        return 0

    def hit(text: str) -> bool:
        """★★ 轮137 修：**词序不再决定成败**。

        为何（轮134 的真实事故）
        ──────────────────────────
        轮134 我用 `15 ?(每分钟|条每分)` 去搜，而原文写的是「每分钟 15 条」——
        **词序与我假设的相反** ⇒ 没搜到 ⇒ 我据此写了「我没有任何权威来源」，
        **而来源就在我自己的件里**。
        ⇒ 故本器改为【按词元匹配】：把查询切成词元，**要求全部出现、不论顺序**。
        """
        ts = text.lower()
        if all_of:
            return all(k.lower() in ts for k in argv)
        # 单词查询：原样子串（保持向后兼容）
        if len(argv) == 1:
            return argv[0].lower() in ts
        # 多词查询：**全部词元出现即可，不论顺序**
        return all(k.lower() in ts for k in argv)

    # ★ 轮137：**未命中时必须连【用过的模式】一起打印**，否则未命中无法被复核
    print("  ── 本次用的检索模式（★未命中时，请核这一行，而不只是范围）──")
    print("     词元 = %s ｜ 组合 = %s" % ("、".join(argv), "全部出现（不论顺序）" if all_of or len(argv) > 1 else "原样子串"))
    print("     ★ 若你要搜的是【一句话】或【固定词序】，本器可能漏 —— 请改用单个关键词多跑几次。")

    # ① 台账
    led_hits = []
    for i, e in rows:
        blob = " ".join(str(e.get(k, "")) for k in ("subject", "detail", "evidence", "ev_type"))
        if hit(blob):
            led_hits.append((i, e.get("ev_type", "?"), str(e.get("subject", ""))[:96], str(e.get("ts", ""))[:19]))

    # ② outbox 文件名与正文
    ob_hits, ob_dirs_hits, ob_txt_hits = [], [], []
    for p in ob:
        if hit(p.name):
            ob_hits.append(p.name)
        else:
            try:
                if hit(p.read_text(encoding="utf-8", errors="replace")[:60000]):
                    ob_txt_hits.append(p.name)
            except Exception:
                pass
    for p in ob_dirs:
        if hit(p.name):
            ob_dirs_hits.append(p.name)
        else:
            try:
                for q in p.rglob("*"):
                    if q.is_file() and hit(q.name):
                        ob_dirs_hits.append(p.name + "/" + q.name)
                        break
            except Exception:
                pass

    # ③ 器具名
    ex_hits = [p.name for p in ex if hit(p.name)]

    total = len(led_hits) + len(ob_hits) + len(ob_txt_hits) + len(ob_dirs_hits) + len(ex_hits)
    print()
    print("  ── 命中 ──")
    if led_hits:
        print("     台账 %d 条：" % len(led_hits))
        for i, t, s, ts in led_hits[:12]:
            print("        #%-4d %-18s %s ｜ %s" % (i, t, s, ts))
        if len(led_hits) > 12:
            print("        …（余 %d 条）" % (len(led_hits) - 12))
    if ob_hits:
        print("     ★ 文件名直接命中 %d 件：" % len(ob_hits))
        for n in ob_hits[:10]:
            print("        " + n)
    if ob_dirs_hits:
        print("     ★ 子目录内命中 %d 处：" % len(ob_dirs_hits))
        for n in ob_dirs_hits[:8]:
            print("        " + n)
    if ob_txt_hits:
        print("     正文命中 %d 件（文件名不含关键词）：" % len(ob_txt_hits))
        for n in ob_txt_hits[:8]:
            print("        " + n)
    if ex_hits:
        print("     器具名命中 %d 件：%s" % (len(ex_hits), "、".join(ex_hits[:8])))

    print()
    print("  ── 判词（三态）──")
    if total == 0:
        print("     ★ 未命中 —— **但这不是「我从未做过」**：")
        print("       本器只查【台账 subject/detail/evidence ＋ outbox 文件名与正文 ＋ exp/ 文件名】；")
        print("       ★ 未纳入共享面、桌面副本、handshake/ 下他人代码，亦未做语义检索（只做字面匹配）。")
        print("       ⇒ 准确的说法是：**在我检索到的 %d 条台账与 %d 件出件里，未见此关键词的字面命中。**"
              % (len(rows), len(ob)))
    elif led_hits and (ob_hits or ob_dirs_hits or ob_txt_hits or ex_hits):
        # ★ 2026-10-02 轮 39 收窄判词：原判词为「✅ 命中（台账与出件【两侧都有】）⇒ 此事我【做过】」。
        #   ★ 而本器的判据只是【那边出现过该关键词】——★「提到」不等于「做到」。
        #   ★ 实证：用 dupcheck 试本器 ⇒ 它判「此事我做过」；
        #     而轮 25 已实测：我好几轮只是写着「已跑 dupcheck」，那个器当时路径已不存在、根本没跑。
        #   ⇒ 故判词收窄成它真正证的，并把【要证"做过"还需要什么】当场写出来。
        print("     ✅ 命中（台账与出件【两侧都有该词】）——★ 这只证【提到过】。")
        print("     ★★ 本判词【不含「此事我做过」】：本器只扫字面命中，「提到」≠「做到」。")
        print("        ★ 实证（轮 39）：用 dupcheck 试本器 ⇒ 它报命中；而轮 25 实测那几轮【根本没跑】。")
        print("        ⇒ 要证『做过』须另有痕迹：执行输出、闸的记录、或台账里带数字的结果。")
        print("        ★（本器头注那条担心是反方向的——怕【少算】已做之事；本条补的是【多算】。）")
    else:
        print("     ○ 部分命中（只在单侧出现）⇒ 再做判断前，请先读上列命中件。")
    print()
    print("  ★ 本器能失败吗：**能**——它对任意关键词返回 0 或非 0 命中，且【未命中时强制打印范围】，")
    print("     故它不会给出无范围的「从未」，也不会把未检索到说成不存在。")
    return 0 if total == 0 else 0


if __name__ == "__main__":
    sys.exit(main())
