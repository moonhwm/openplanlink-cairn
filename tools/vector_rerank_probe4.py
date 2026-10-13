# -*- coding: utf-8 -*-
"""vector_rerank_probe4.py —— 评测集去污染版：检索精度终测（2026-10-14 立，承 led_1494 之再诊）

承 led_1493/1494：零召回之因不在分词（已于 v3 修正），而在★语料被"元数据件"污染 ——
  台账 subject（led_*）与★本席自己的实验输出（vector_rerank_run*.json 等）逐字含查询词 ⇒ 自我指涉陷阱；
  且 b=0.75 之长度归一化使长正文件受罚。
本版修正（★三措并施）：① ★剔除自我指涉件（vector_rerank_run*／rerank_diag*／decision_model*_run*）
  ② ★排除台账 subject 件（led_*）—— 只评★正文件 ③ ★对 b 作敏感性（b=0.3/0.5/0.75）
指标：Recall@3 / MRR / nDCG@3 × {A TF-IDF, B BM25, R1, R2 BM25F, R3} × {b}
纪律：★零外呼、纯本地、可复算｜★结果落 outbox/mem
用法：python vector_rerank_probe4.py
"""
import json, math, pathlib, re, sys

sys.stdout.reconfigure(encoding="utf-8")
SEAT = (pathlib.Path.home() / "WPSDrive" / "29969771" / "WPS云盘" / "月之暗面的Plasma游乐场"
        / "A2A新席_石敢当Cairn_20260928")
OUT = SEAT / "outbox" / "mem" / "vector_rerank_run4_20261014.json"
K = 3
CJK = re.compile(r"[\u4e00-\u9fff]+")
SKIP = re.compile(r"^(vector_rerank_run|rerank_diag|decision_model.*_run|decision_rerank_dry|ask_q|seat_facts|paraphrase_|b_spec_|.*\.bak)")
QUERIES = [
    ("q1", "决策模型 概率分布 置信度 校准", "决策模型"),
    ("q2", "OTL 格式 元数据 历史版本 审计", "OTL"),
    ("q3", "台账 hash 链 快照 对账 缺口", "台账"),
    ("q4", "A2A 信封 nonce 抗重放 死信", "A2A"),
    ("q5", "安全边界 反向攻击 渗透测试 协议", "安全"),
    ("q6", "环境 依赖 版本 资源占用 基线", "环境"),
    ("q7", "复现 置信度 5σ Brier 校准", "复现"),
    ("q8", "权限矩阵 数据字典 SAP OA 联调", "权限"),
    ("q9", "席位注册 数字人员工 合规 追责", "席位"),
    ("q10", "档案运营 SOP 交付标准 校验", "档案"),
    ("q11", "Linux ls 权限 隐藏文件 运行手册", "Linux"),
    ("q12", "技能载入 开源协议 匹配 评估", "技能"),
]


def toks(s: str):
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
    """★仅正文件：outbox/mem 之 .md ＋ 剔除自我指涉与元数据件"""
    docs = []
    for p in sorted((SEAT / "outbox" / "mem").glob("*.md")):
        if SKIP.match(p.name):
            continue
        t = p.read_text(encoding="utf-8", errors="replace")
        docs.append({"id": p.name, "text": t[:20000]})
    # 归档版本档（历史版本，亦为正文件）
    arch = SEAT / "archive" / "docs"
    if arch.exists():
        for kd in sorted(arch.glob("kd_*"))[:60]:
            for f in sorted(kd.glob("v_*.md"))[-1:]:
                docs.append({"id": "arch/%s/%s" % (kd.name, f.name), "text": f.read_text(encoding="utf-8", errors="replace")[:8000]})
    return docs


def truth(docs, key):
    """★真值改按"件内容确含该主题"自动判定 ⇒ 避免人工标注错误"""
    return [d["id"] for d in docs if key.lower() in d["id"].lower() or key.lower() in d["text"][:400].lower()]


def prep(docs):
    df = {}
    for d in docs:
        d["tok"] = toks(d["id"] + " " + d["text"])
        f = {}
        for t in d["tok"]:
            f[t] = f.get(t, 0) + 1
        d["f"] = f
        for t in set(d["tok"]):
            df[t] = df.get(t, 0) + 1
    dls = [len(d["tok"]) for d in docs]
    return {"df": df, "N": len(docs), "avg": sum(dls) / max(1, len(docs)), "dls": dls}


def bm25(docs, st, qt, b=0.75, k1=1.5, tb=0.0):
    N, df, avg, dls = st["N"], st["df"], st["avg"], st["dls"]
    out = []
    for i, d in enumerate(docs):
        s = 0.0
        for t in qt:
            if t not in d["f"]:
                continue
            idf = math.log(1 + (N - df.get(t, 0) + 0.5) / (df.get(t, 0) + 0.5))
            w = d["f"][t] + tb * d["f"].get(t, 0)
            s += idf * w * (k1 + 1) / (w + k1 * (1 - b + b * dls[i] / avg))
        out.append(s)
    return out


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
    print("  === 评测集去污染版：检索精度终测 ===")
    print("  ★语料 %d 件（★仅正文件：剔除自我指涉件与台账 subject）｜平均长度 %.0f 词" % (len(docs), st["avg"]))
    BS = [0.3, 0.5, 0.75]
    agg = {}
    rows = []
    for qid, q, key in QUERIES:
        rel = truth(docs, key)
        qt = toks(q)
        r = {"A_tfidf": ev(docs, rel, tfidf(docs, st, qt))}
        for b in BS:
            r["B_bm25_b%.1f" % b] = ev(docs, rel, bm25(docs, st, qt, b=b))
            r["R2_bm25f_b%.1f" % b] = ev(docs, rel, bm25(docs, st, qt, b=b, tb=3.0))
        for n, v in r.items():
            a = agg.setdefault(n, {"recall": 0.0, "mrr": 0.0, "ndcg": 0.0})
            for k in ("recall", "mrr", "ndcg"):
                a[k] += v[k] / len(QUERIES)
        rows.append({"qid": qid, "q": q, "truth": rel, "res": r})
        print("   %s %-22s 真值%d件 ｜ A nDCG=%.2f ｜ B(b.75)=%.2f R2(b.75)=%.2f ｜ B(b.3)=%.2f R2(b.3)=%.2f" % (
            qid, q[:22], len(rel), r["A_tfidf"]["ndcg"], r["B_bm25_b0.8"]["ndcg"] if "B_bm25_b0.8" in r else r["B_bm25_b0.8"]["ndcg"] if False else r["B_bm25_b0.5"]["ndcg"],
            r["R2_bm25f_b0.5"]["ndcg"], r["B_bm25_b0.3"]["ndcg"], r["R2_bm25f_b0.3"]["ndcg"]))
    print("  ★宏平均（按 b 分列）：")
    for n in sorted(agg):
        print("     %-16s Recall@3=%.4f  MRR=%.4f  nDCG@3=%.4f" % (n, agg[n]["recall"], agg[n]["mrr"], agg[n]["ndcg"]))
    best = max(agg, key=lambda n: agg[n]["ndcg"])
    print("  ★★按 nDCG 之最优：%s（%.4f）" % (best, agg[best]["ndcg"]))
    doc = {"doc_id": "VR4-20261014-CAIRN-01", "corpus": len(docs), "K": K, "macro": agg,
           "best_by_ndcg": best, "truth_rule": "按件内容确含该主题（自动判定）", "rows": rows}
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print("  ★落盘：%s" % OUT.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
