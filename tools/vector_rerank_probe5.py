# -*- coding: utf-8 -*-
"""vector_rerank_probe5.py —— 依 IRS 规范重建评测集之终版检索实证（2026-10-14 立）

规范依据：IRS-20261014-CAIRN-01（四条硬性）
  ① 语料分层：★仅正文件（.md 正文），剔除元数据件与自我指涉件
  ② 查询—真值对：★真值非空；★件数限 2–5；★判据写明（件名含 key 或 正文首 300 字含 key）
     ⇒ 不在区间者★该查询作废并如实报（不擅自补真值、不放宽判据）
  ③ 指标口径：分母＝真值件数；三指标（Recall@3/MRR/nDCG@3）同报；宏平均按查询等权
  ④ 报告义务：切分口径、语料清单、真值判据、可复算脚本 —— 全部随件落盘
方法：A TF-IDF 余弦｜B BM25（b=0.3/0.5/0.75）｜R1 乘性标题｜R2 BM25F(标题×3)｜R3 短语邻近
纪律：★零外呼、纯本地、可复算｜★结果与语料清单、真值表一并落盘
用法：python vector_rerank_probe5.py
"""
import json, math, pathlib, re, sys

sys.stdout.reconfigure(encoding="utf-8")
SEAT = (pathlib.Path.home() / "WPSDrive" / "29969771" / "WPS云盘" / "月之暗面的Plasma游乐场"
        / "A2A新席_石敢当Cairn_20260928")
OUT = SEAT / "outbox" / "mem" / "vector_rerank_run5_20261014.json"
K = 3
CJK = re.compile(r"[\u4e00-\u9fff]+")
SKIP = re.compile(r"^(vector_rerank_run|rerank_diag|decision_model.*_run|decision_rerank_dry|ask_q|seat_facts|paraphrase_|b_spec_|mem_audit|sync_gap|decision_model)")
# ★查询与主题键（真值判据＝件名含 key 或 正文首 300 字含 key）
QUERIES = [
    ("q1", "OTL 格式 元数据 历史版本 审计", "OTL"),
    ("q2", "安全边界 反向攻击 渗透测试 协议", "安全边界"),
    ("q3", "环境 依赖 版本 资源占用 基线", "交付基线"),
    ("q4", "复现 置信度 5σ Brier 校准", "复现"),
    ("q5", "权限矩阵 数据字典 SAP 联调", "权限矩阵"),
    ("q6", "席位注册 数字人员工 合规 追责", "数字人员工"),
    ("q7", "档案运营 SOP 交付标准 校验", "档案运营"),
    ("q8", "A2A 信封 nonce 抗重放 死信", "A2A通信协议"),
    ("q9", "Linux ls 权限 隐藏文件 运行手册", "Linux"),
    ("q10", "跨席核验 共认 回执 归属", "跨席核验"),
    ("q11", "退款 询问 账单 充值", "退款"),
    ("q12", "技能载入 开源协议 匹配 评估", "开源协议"),
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
    docs = []
    for p in sorted((SEAT / "outbox" / "mem").glob("*.md")):
        if SKIP.match(p.name):
            continue
        docs.append({"id": p.name, "text": p.read_text(encoding="utf-8", errors="replace")[:20000]})
    arch = SEAT / "archive" / "docs"
    if arch.exists():
        for kd in sorted(arch.glob("kd_*"))[:80]:
            fs = sorted(kd.glob("v_*.md"))
            if fs:
                docs.append({"id": "arch/%s/%s" % (kd.name, fs[-1].name),
                             "text": fs[-1].read_text(encoding="utf-8", errors="replace")[:8000]})
    return docs


def truth_of(docs, key):
    """★判据（写明可复核）：件名含 key，或 正文首 300 字含 key"""
    k = key.lower()
    return [d["id"] for d in docs if k in d["id"].lower() or k in d["text"][:300].lower()]


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


def bm25(docs, st, qt, b=0.5, k1=1.5, tb=0.0):
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


def r1(docs, st, qt, qraw, b):
    base = bm25(docs, st, qt, b=b)
    return [base[i] * (1 + 0.5 * sum(1 for w in qraw if w and w in d["id"].lower())) for i, d in enumerate(docs)]


def r3(docs, st, qt, qraw, b):
    base = bm25(docs, st, qt, b=b)
    out = []
    for i, d in enumerate(docs):
        body = re.sub(r"\s+", "", d["text"].lower())
        adj = sum(1 for a in qraw for c in qraw if a and c and a != c and (a + c) in body)
        out.append(base[i] * (1 + 0.06 * adj))
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
    print("  === 依 IRS 规范重建评测集之终版检索实证 ===")
    print("  ★语料 %d 件（仅正文件；切分＝对称 n-gram 2/3/4 滑窗）｜平均长度 %.0f 词" % (len(docs), st["avg"]))
    kept, dropped = [], []
    for qid, q, key in QUERIES:
        rel = truth_of(docs, key)
        if 2 <= len(rel) <= 5:
            kept.append((qid, q, key, rel))
        else:
            dropped.append((qid, key, len(rel)))
    print("  ★按 IRS §三.2 筛：保留 %d 条 ｜ ★作废 %d 条（真值不在 2–5 件）%s" % (
        len(kept), len(dropped), "：" + ", ".join("%s(%s)=%d件" % (a, b, c) for a, b, c in dropped) if dropped else ""))
    MACRO = {}
    rows = []
    for qid, q, key, rel in kept:
        qt = toks(q)
        qraw = [w for w in re.findall(r"[\u4e00-\u9fff]{2,}|[a-z0-9_]{2,}", q.lower())]
        r = {"A_tfidf": ev(docs, rel, tfidf(docs, st, qt))}
        for b in (0.3, 0.5, 0.75):
            r["B_bm25_b%.1f" % b] = ev(docs, rel, bm25(docs, st, qt, b=b))
            r["R2_bm25f_b%.1f" % b] = ev(docs, rel, bm25(docs, st, qt, b=b, tb=3.0))
        r["R1_mul_b0.5"] = ev(docs, rel, r1(docs, st, qt, qraw, 0.5))
        r["R3_phrase_b0.5"] = ev(docs, rel, r3(docs, st, qt, qraw, 0.5))
        for n, v in r.items():
            a = MACRO.setdefault(n, {"recall": 0.0, "mrr": 0.0, "ndcg": 0.0})
            for k in ("recall", "mrr", "ndcg"):
                a[k] += v[k] / len(kept)
        rows.append({"qid": qid, "q": q, "key": key, "truth": rel, "res": r})
        print("   %s %-20s 真值%d件 ｜ A=%.2f B=.5=%.2f R2=.5=%.2f R1=%.2f R3=%.2f（nDCG）" % (
            qid, q[:20], len(rel), r["A_tfidf"]["ndcg"], r["B_bm25_b0.5"]["ndcg"],
            r["R2_bm25f_b0.5"]["ndcg"], r["R1_mul_b0.5"]["ndcg"], r["R3_phrase_b0.5"]["ndcg"]))
    print("  ★宏平均（★按查询等权，分母＝真值件数）：")
    for n in sorted(MACRO):
        print("     %-16s Recall@3=%.4f  MRR=%.4f  nDCG@3=%.4f" % (n, MACRO[n]["recall"], MACRO[n]["mrr"], MACRO[n]["ndcg"]))
    base = MACRO.get("B_bm25_b0.5", {})
    print("  ★★相对 B(b=0.5) 之 ΔnDCG：")
    for n in sorted(MACRO):
        if n != "B_bm25_b0.5":
            print("     %-16s %+.4f" % (n, MACRO[n]["ndcg"] - base.get("ndcg", 0.0)))
    best = max(MACRO, key=lambda n: MACRO[n]["ndcg"])
    print("  ★★按 nDCG 之最优：%s（%.4f）" % (best, MACRO[best]["ndcg"]))
    doc = {"doc_id": "VR5-20261014-CAIRN-01", "spec": "IRS-20261014-CAIRN-01", "corpus": len(docs),
           "tokenizer": "对称 n-gram 2/3/4 滑窗", "K": K, "kept": len(kept), "dropped": dropped,
           "truth_rule": "件名含 key 或 正文首 300 字含 key", "macro": MACRO, "best_by_ndcg": best,
           "corpus_list": [d["id"] for d in docs], "rows": rows}
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print("  ★落盘：%s（含语料清单与真值表）" % OUT.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
