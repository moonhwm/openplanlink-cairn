# -*- coding: utf-8 -*-
"""virtue_audit.py —— **德性自审**（承则二十三·§41 第 6 条：「不粘连于自己的德性」）

## 缘起
JGB §41 列"六不依"，其第六为：**「Nicht an unsern eignen Tugenden hängen bleiben」**（不粘连于自己的德性）。
**本席自审（诚实）**：本席历轮**大量增器、增栏、增链**（术语表、方法论诸则、多道闸门、多种索引）
⇒ 须检验：**其中哪些真正改变了决定，哪些只是累积**（**"严谨"是否已自成目的**）。

## 方法（**代理指标，如实标注**）
- **对象**：`exp/*.py`（本席自建工具）；
- **代理**：该工具在 **台账（`ledger/frontier_ledger.jsonl`）＋ 事件链（`ops/ops_event.jsonl`）** 中被**提及**之次数与轮次跨度；
- **★口径声明**：**"被提及"≠"被调用"**，本器**不测调用**（无埋点）⇒ 结论**仅为候选**，**不构成处置**；
- **判定**：**0–1 次 ⇒ ★候选（并入或废止）**｜**2–4 次 ⇒ 观察**｜**≥5 次 ⇒ 在用**。

用法：
    python virtue_audit.py            # 审计并输出表
    python virtue_audit.py --json <p> # 另存机读结果
性质：**只读**；**不删不并**（处置须候批，承"候选≠判据"）。
"""
import argparse
import collections
import json
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
SEAT = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928")
LEDGER = SEAT / "ledger" / "frontier_ledger.jsonl"
EVENTS = SEAT / "ops" / "ops_event.jsonl"
EXP = SEAT / "exp"
OUT = SEAT / "outbox" / "mem" / "virtue_audit.json"


def read_all():
    txt = []
    for p in (LEDGER, EVENTS):
        if p.exists():
            txt.append(p.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(txt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    tools = sorted([p.name for p in EXP.glob("*.py") if not p.name.startswith("__")])
    if not tools:
        print("★ 未检出工具 ⇒ 未测")
        return 2
    corpus = read_all()
    if not corpus:
        print("★ 台账/事件链不可读 ⇒ **未测**（不以 0 次代「未用」）")
        return 2

    rows = []
    for name in tools:
        stem = name[:-3]
        n = len(re.findall(re.escape(stem), corpus))
        rows.append({"tool": name, "mentions": n,
                     "verdict": "在用" if n >= 5 else ("观察" if n >= 2 else "★候选（并入或废止）")})
    rows.sort(key=lambda r: (-r["mentions"], r["tool"]))
    print("★ 德性自审（§41 第 6 条：不粘连于自己的德性）")
    print("  对象：`exp/*.py` 共 **%d** 件 ｜ 依据：台账＋事件链（**代理指标：被提及次数**）" % len(rows))
    print("  ── 工具 ｜ 提及数 ｜ 判定")
    for r in rows:
        print("   %-26s %4d ｜ %s" % (r["tool"], r["mentions"], r["verdict"]))
    cand = [r for r in rows if r["verdict"].startswith("★")]
    watch = [r for r in rows if r["verdict"] == "观察"]
    print("  ⇒ 在用 %d ｜ 观察 %d ｜ **★候选 %d**" % (len(rows) - len(cand) - len(watch), len(watch), len(cand)))
    print("  ★口径：**「被提及」≠「被调用」**；本器**不测调用** ⇒ 判定**仅为候选**，**处置须候批**")
    rec = {"audited_at": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S +08"),
           "scope": "exp/*.py", "metric": "mentions-in-ledger+events(proxy)", "rows": rows,
           "counts": {"in_use": len(rows) - len(cand) - len(watch), "watch": len(watch), "candidates": len(cand)},
           "caveat": "被提及≠被调用；判定为候选，非处置"}
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        print("  JSON：%s" % a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
