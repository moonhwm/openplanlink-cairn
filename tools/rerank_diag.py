# -*- coding: utf-8 -*-
"""rerank_diag.py —— q1/q7 零召回之专项诊断（2026-10-14 立）

问题（承 led_1491）：查询 q1"决策模型 概率分布 置信度 校准"与 q7"复现 置信度 5σ Brier 校准"
在 BM25 下对真值件召回全失。本器逐层定位：
 ① 真值件是否在语料中（含名称精确匹配）
 ② 真值件之命中词（与查询词之交集）与 BM25 得分
 ③ 实际 Top-10 之件名与得分
 ④ 查询词之 IDF 与在真值件中之词频（判是否"查询词不在真值件中"）
纪律：★零外呼、纯本地、只读语料｜★不改任何件
用法：python rerank_diag.py
"""
import json, math, pathlib, re, sys

sys.stdout.reconfigure(encoding="utf-8")
SEAT = (pathlib.Path.home() / "WPSDrive" / "29969771" / "WPS云盘" / "月之暗面的Plasma游乐场"
        / "A2A新席_石敢当Cairn_20260928")
CASES = [
    ("q1", "决策模型 概率分布 置信度 校准", ["decision_model_run_20261014.json", "decision_model3_run_20261014.json"]),
    ("q7", "复现 置信度 5σ Brier 校准", ["独立复现校验报告_REPRO-20261014-CAIRN-01.md"]),
]


def toks(s: str):
    s = s.lower()
    return (re.findall(r"[a-z0-9_]+", s)
            + re.findall(r"[\u4e00-\u9fff]{2,}", s)
            + [z[i:i + 2] for z in re.findall(r"[\u4e00-\u9fff]{2,}", s) for i in range(max(1, len(z) - 1))])


def main() -> int:
    docs = []
    for p in sorted((SEAT / "outbox" / "mem").glob("*")):
        if p.is_file() and p.suffix.lower() in (".md", ".json"):
            docs.append({"id": p.name, "text": p.read_text(encoding="utf-8", errors="replace")[:20000]})
    led = SEAT / "ledger" / "frontier_ledger.jsonl"
    if led.exists():
        for i, ln in enumerate(led.read_text(encoding="utf-8", errors="replace").splitlines()[-40:]):
            try:
                sub = str(json.loads(ln).get("subject") or "")
            except Exception:
                continue
            if sub:
                docs.append({"id": "led_%d" % i, "text": sub[:4000]})
    N = len(docs)
    for d in docs:
        d["tok"] = toks(d["id"] + " " + d["text"])
        f = {}
        for t in d["tok"]:
            f[t] = f.get(t, 0) + 1
        d["f"] = f
    df = {}
    for d in docs:
        for t in set(d["tok"]):
            df[t] = df.get(t, 0) + 1
    dls = [len(d["tok"]) for d in docs]
    avg = sum(dls) / N
    print("  === q1/q7 零召回专项诊断 === ｜ 语料 %d 件 ｜ 平均长度 %.0f 词" % (N, avg))
    for qid, q, rel in CASES:
        qt = toks(q)
        print("  ── %s：%s ──" % (qid, q))
        for r in rel:
            hit = [d for d in docs if d["id"] == r]
            if not hit:
                print("     ★真值件不在语料：%s" % r); continue
            d = hit[0]
            inter = sorted(set(qt) & set(d["tok"]))
            print("     真值件 %s ｜ 长度 %d 词 ｜ ★查询词命中 %d 个：%s" % (r, len(d["tok"]), len(inter), ", ".join(inter[:12]) or "（无）"))
            for t in sorted(set(qt))[:12]:
                print("        %-10s IDF=%.2f  件内词频=%d" % (t, math.log(1 + (N - df.get(t, 0) + 0.5) / (df.get(t, 0) + 0.5)), d["f"].get(t, 0)))
        sc = []
        for i, d in enumerate(docs):
            s = 0.0
            for t in qt:
                if t not in d["f"]:
                    continue
                idf = math.log(1 + (N - df.get(t, 0) + 0.5) / (df.get(t, 0) + 0.5))
                s += idf * d["f"][t] * 2.5 / (d["f"][t] + 1.5 * (1 - 0.75 + 0.75 * dls[i] / avg))
            sc.append((s, d["id"]))
        sc.sort(reverse=True)
        print("     ★BM25 Top-10：")
        for s, i in sc[:10]:
            mark = "★真值" if i in rel else ""
            print("        %7.3f  %s %s" % (s, i[:60], mark))
        rank = next((k + 1 for k, (_, i) in enumerate(sc) if i in rel), None)
        print("     ★真值件排名：%s" % (rank if rank else "★未入榜（在 %d 件中）" % N))
    return 0


if __name__ == "__main__":
    sys.exit(main())
