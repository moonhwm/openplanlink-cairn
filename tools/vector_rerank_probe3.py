# -*- coding: utf-8 -*-
"""vector_rerank_probe3.py —— 分词修正版：检索精度重测（2026-10-14 立，承 led_1492 之诊断）

修正（★核心）：v1/v2 之 toks() 对汉字用 [\u4e00-\u9fff]{2,} ★贪婪匹配 ⇒ 正文长串被整体吞掉
      ⇒ 查询短词在正文侧从不出现（切分不对称）⇒ 结论受污染。
本版：★查询与正文★同用对称切分 —— 英文/数字按 [a-z0-9_]+；汉字对每个连续串取 ★2/3/4 字滑窗 n-gram
      ⇒ 短词与长串皆成词，切分对称。
对照：A TF-IDF 余弦｜B BM25｜R1 乘性标题｜R2 BM25F(标题×3)｜R3 短语邻近
指标：Recall@3 / MRR / nDCG@3（宏平均）＋ 各法 Δ（vs BM25）
纪律：★零外呼、纯本地、可复算｜★结果落 outbox/mem
用法：python vector_rerank_probe3.py
"""
import json, math, pathlib, re, sys

sys.stdout.reconfigure(encoding="utf-8")
SEAT = (pathlib.Path.home() / "WPSDrive" / "29969771" / "WPS云盘" / "月之暗面的Plasma游乐场"
        / "A2A新席_石敢当Cairn_20260928")
OUT = SEAT / "outbox" / "mem" / "vector_rerank_run3_20261014.json"
K = 3
CJK = re.compile(r"[\u4e00-\u9fff]+")
QUERIES = [
    ("q1", "决策模型 概率分布 置信度 校准", ["decision_model_run_20261014.json", "decision_model3_run_20261014.json"]),
    ("q2", "OTL 格式 元数据 历史版本 审计", ["OTL格式与元数据完整性规范_OTL-SPEC-20261014-CAIRN-01.md"]),
    ("q3", "台账 hash 链 快照 对账 缺口", ["sync_gap_20261014.md"]),
    ("q4", "A2A 信封 nonce 抗重放 死信", ["A2A通信协议与接口规范_PROTO-A2A-20261014-CAIRN-01.md"]),
    ("q5", "安全边界 反向攻击 渗透测试 协议", ["三仓评估与安全边界声明_SEC-20261014-CAIRN-01.md"]),
    ("q6", "环境 依赖 版本 资源占用 基线", ["环境与依赖交付基线_ENV-BASELINE-20261014-CAIRN-01.md"]),
    ("q7", "复现 置信度 5σ Brier 校准", ["独立复现校验报告_REPRO-20261014-CAIRN-01.md"]),
    ("q8", "权限矩阵 数据字典 SAP OA 联调", ["权限矩阵与数据字典_RBAC-DICT-20261014-CAIRN-01.md"]),
    ("q9", "席位注册 数字人员工 合规 追责", ["数字人员工注册规范_SEAT-REG-20261014-CAIRN-01.md"]),
    ("q10", "档案运营 SOP 交付标准 校验", ["档案运营管理SOP_SOP-20261014-CAIRN-01.md"]),
    ("q11", "Linux ls 权限 隐藏文件 运行手册", ["Linux命令实作runbook_LS-RUNBOOK-20261014-CAIRN-01.md"]),
    ("q12", "技能载入 开源协议 匹配 评估", ["开源项目引入评估与协议匹配表_OSS-20261014-CAIRN-01.md", "技能载入清单_SKILLS-20261014-CAIRN-01.md"]),
]


def toks(s: str):
    """★对称切分：英数按词；汉字按 2/3/4 字滑窗 n-gram"""
    s = s.lower()
    out = re.findall(r"[a-z0-9_]+", s)
    for run in CJK.findall(s):
        L = len(run)
        for n in (2, 3, 4):
            if L >= n:
                out.extend(run[i:i + n] for i in range(L - n + 1))
        if L == 1:
            out.append(run)
    return out


def load_corpus():
    docs = []
    for p in sorted((SEAT / "outbox" / "mem").glob("*")):
        if p.is_file() and p.suffix.lower() in (".md", ".json"):
            try:
                t = p.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            docs.append({"id": p.name, "title": p.name, "text": t[:20000]})
    led = SEAT / "ledger" / "frontier_ledger.jsonl"
    if led.exists():
        lines = led.read_text(encoding="utf-8", errors="replace").splitlines()
        for i, ln in enumerate(lines[-40:] if len(lines) > 40 else lines):
            try:
                sub = str(json.loads(ln).get("subject") or "")
            except Exception:
                continue
            if sub:
                docs.append({"id": "led_%d" % i, "title": sub[:60], "text": sub[:4000]})
    return docs


def prep(docs):
    df = {}
    for d in docs:
        d["tok"] = toks(d["title"] + " " + d["text"])
        d["ttok"] = toks(d["title"])
        f = {}
        for t in d["tok"]:
            f[t] = f.get(t, 0) + 1
        d["f"] = f
        tf = {}
        for t in d["ttok"]:
            tf[t] = tf.get(t, 0) + 1
        d["tf"] = tf
        for t in set(d["tok"]):
            df[t] = df.get(t, 0) + 1
    N = len(docs)
    dls = [len(d["tok"]) for d in docs]
    return {"df": df, "N": N, "avg": sum(dls) / max(1, N), "dls": dls}


def bm25(docs, st, qt, k1=1.5, b=0.75, tb=0.0):
    N, df, avg, dls = st["N"], st["df"], st["avg"], st["dls"]
    sc = []
    for i, d in enumerate(docs):
        s = 0.0
        for t in qt:
            if t not in d["f"]:
                continue
            idf = math.log(1 + (N - df.get(t, 0) + 0.5) / (df.get(t, 0) + 0.5))
            w = d["f"][t] + tb * d["tf"].get(t, 0)
            s += idf * w * (k1 + 1) / (w + k1 * (1 - b + b * dls[i] / avg))
        sc.append(s)
    return sc


def tfidf(docs, st, qt):
    N, df = st["N"], st["df"]
    qv = {t: math.log(N / (1 + df.get(t, 0))) for t in qt}
    qn = math.sqrt(sum(v * v for v in qv.values())) or 1.0
    out = []
    for d in docs:
        dv = {t: d["f"][t] * math.log(N / (1 + df.get(t, 0))) for t in set(qt) if t in d["f"]}
        dn = math.sqrt(sum(v * v for v in dv.values())) or 1.0
        out.append(sum(qv[t] * dv.get(t, 0.0) for t in qv) / (qn * dn))
    return out


def r1(docs, st, qt, qraw):
    base = bm25(docs, st, qt)
    return [base[i] * (1.0 + 0.5 * sum(1 for w in qraw if w and w in d["title"].lower())) for i, d in enumerate(docs)]


def r3(docs, st, qt, qraw):
    base = bm25(docs, st, qt)
    out = []
    for i, d in enumerate(docs):
        body = re.sub(r"\s+", "", d["text"].lower())
        adj = sum(1 for a in qraw for b in qraw if a and b and a != b and (a + b) in body)
        out.append(base[i] * (1.0 + 0.06 * adj))
    return out


def ndcg(order, rel, k):
    dcg = sum((1.0 if order[i] in rel else 0.0) / math.log2(i + 2) for i in range(min(k, len(order))))
    ideal = sum(1.0 / math.log2(i + 2) for i in range(min(k, len(rel))))
    return dcg / ideal if ideal else 0.0


def ev(docs, rel, sc):
    idx = sorted(range(len(docs)), key=lambda i: -sc[i])[:K]
    order = [docs[i]["id"] for i in idx]
    rr = 0.0
    for r, did in enumerate(order):
        if did in rel:
            rr = 1.0 / (r + 1); break
    return {"top": order, "recall": len(set(order) & set(rel)) / max(1, len(rel)), "mrr": rr, "ndcg": ndcg(order, set(rel), K)}


def main() -> int:
    docs = load_corpus()
    st = prep(docs)
    print("  === 分词修正版：检索精度重测（对称 n-gram 切分）===")
    print("  ★语料 %d 件｜平均长度 %.0f 词（修正后）｜K=%d｜查询 %d 条" % (len(docs), st["avg"], K, len(QUERIES)))
    names = ["A_tfidf", "B_bm25", "R1乘性标题", "R2 BM25F(×3)", "R3短语邻近"]
    agg = {n: {"recall": 0.0, "mrr": 0.0, "ndcg": 0.0} for n in names}
    rows = []
    zero = []
    for qid, q, rel in QUERIES:
        qt = toks(q)
        qraw = [w for w in re.findall(r"[\u4e00-\u9fff]{2,}|[a-z0-9_]{2,}", q.lower())]
        res = {
            "A_tfidf": ev(docs, rel, tfidf(docs, st, qt)),
            "B_bm25": ev(docs, rel, bm25(docs, st, qt)),
            "R1乘性标题": ev(docs, rel, r1(docs, st, qt, qraw)),
            "R2 BM25F(×3)": ev(docs, rel, bm25(docs, st, qt, tb=3.0)),
            "R3短语邻近": ev(docs, rel, r3(docs, st, qt, qraw)),
        }
        for n in names:
            for k in ("recall", "mrr", "ndcg"):
                agg[n][k] += res[n][k] / len(QUERIES)
        if res["A_tfidf"]["recall"] == 0 and res["B_bm25"]["recall"] == 0:
            zero.append(qid)
        rows.append({"qid": qid, "q": q, "rel": rel, "res": res})
        print("   %s %-22s R@3 A=%.2f B=%.2f R1=%.2f R2=%.2f R3=%.2f ｜ nDCG A=%.2f B=%.2f R2=%.2f" % (
            qid, q[:22], res["A_tfidf"]["recall"], res["B_bm25"]["recall"], res["R1乘性标题"]["recall"],
            res["R2 BM25F(×3)"]["recall"], res["R3短语邻近"]["recall"],
            res["A_tfidf"]["ndcg"], res["B_bm25"]["ndcg"], res["R2 BM25F(×3)"]["ndcg"]))
    print("  ★宏平均：")
    for n in names:
        print("     %-14s Recall@3=%.4f  MRR=%.4f  nDCG@3=%.4f" % (n, agg[n]["recall"], agg[n]["mrr"], agg[n]["ndcg"]))
    print("  ★★相对 BM25 之增益：")
    for n in [x for x in names if x not in ("B_bm25",)]:
        print("     %-14s ΔRecall=%+.4f  ΔMRR=%+.4f  ΔnDCG=%+.4f" % (
            n, agg[n]["recall"] - agg["B_bm25"]["recall"], agg[n]["mrr"] - agg["B_bm25"]["mrr"],
            agg[n]["ndcg"] - agg["B_bm25"]["ndcg"]))
    best = max(names, key=lambda n: agg[n]["ndcg"])
    print("  ★★按 nDCG 之最优：%s（%.4f）" % (best, agg[best]["ndcg"]))
    print("  ★★仍零召回之查询：%s" % (", ".join(zero) if zero else "无"))
    doc = {"doc_id": "VR3-20261014-CAIRN-01", "fix": "对称 n-gram 切分（2/3/4 字滑窗）", "corpus": len(docs),
           "K": K, "queries": len(QUERIES), "macro": agg, "best_by_ndcg": best, "still_zero_recall": zero, "rows": rows}
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print("  ★落盘：%s" % OUT.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
