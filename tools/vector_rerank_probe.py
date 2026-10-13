# -*- coding: utf-8 -*-
"""vector_rerank_probe.py —— 向量编码与重排序模块：检索精度实证（2026-10-14 立）

依据：令条「向量编码与重排序模块（对文本或图文数据进行向量化处理，结合重排序机制提升检索精度）」
实作：★三级对照 —— (A) TF-IDF 余弦（词袋向量）｜(B) BM25（稀疏检索基线）｜(C) B + 重排（重排器＝
      查询词覆盖 + 词邻近 + 标题命中加权之交叉打分）⇒ ★以 Recall@3 / MRR / nDCG@3 量化"重排是否提升"
语料：★本席自辖件（outbox/mem 全目录 ＋ ledger 台账 subject 抽样）—— 零外呼、可复算
可选：★302.AI embedding 端点探活（只报状态，不作主链）
纪律：★凭据零回显零落盘｜★零外呼为主链
用法：python vector_rerank_probe.py
"""
import json, math, os, pathlib, re, sys, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8")
SEAT = (pathlib.Path.home() / "WPSDrive" / "29969771" / "WPS云盘" / "月之暗面的Plasma游乐场"
        / "A2A新席_石敢当Cairn_20260928")
OUT = SEAT / "outbox" / "mem" / "vector_rerank_run_20261014.json"
K = 3
QUERIES = [
    ("q1", "决策模型 概率分布 置信度 校准", ["decision_model_run_20261014.md", "decision_model3_run_20261014.json"]),
    ("q2", "OTL 格式 元数据 历史版本 审计", ["OTL格式与元数据完整性规范_OTL-SPEC-20261014-CAIRN-01.md"]),
    ("q3", "台账 hash 链 快照 对账", ["sync_gap_20261014.md", "mem_audit_20261005T214028Z.md"]),
    ("q4", "A2A 信封 nonce 抗重放 死信", ["A2A通信协议与接口规范_PROTO-A2A-20261014-CAIRN-01.md"]),
    ("q5", "安全边界 反向攻击 渗透测试 协议", ["三仓评估与安全边界声明_SEC-20261014-CAIRN-01.md"]),
    ("q6", "环境 依赖 版本 资源占用 基线", ["环境与依赖交付基线_ENV-BASELINE-20261014-CAIRN-01.md"]),
    ("q7", "复现 置信度 5σ Brier 校准", ["独立复现校验报告_REPRO-20261014-CAIRN-01.md"]),
    ("q8", "权限矩阵 数据字典 SAP OA 联调", ["权限矩阵与数据字典_RBAC-DICT-20261014-CAIRN-01.md"]),
]


def toks(s: str):
    s = s.lower()
    en = re.findall(r"[a-z0-9_]+", s)
    zh = re.findall(r"[\u4e00-\u9fff]{2,}", s)
    zh2 = [z[i:i + 2] for z in zh for i in range(max(1, len(z) - 1))]
    return en + zh + zh2


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
                d = json.loads(ln)
            except Exception:
                continue
            sub = str(d.get("subject") or "")
            if sub:
                docs.append({"id": "led_%d" % i, "title": sub[:60], "text": sub[:4000]})
    return docs


def bm25(docs, q, k1=1.5, b=0.75):
    N = len(docs)
    dls = [len(d["tok"]) for d in docs]
    avg = sum(dls) / max(1, N)
    df = {}
    for d in docs:
        for t in set(d["tok"]):
            df[t] = df.get(t, 0) + 1
    qt = [t for t in toks(q)]
    sc = []
    for i, d in enumerate(docs):
        f = {}
        for t in d["tok"]:
            f[t] = f.get(t, 0) + 1
        s = 0.0
        for t in qt:
            if t not in f:
                continue
            idf = math.log(1 + (N - df.get(t, 0) + 0.5) / (df.get(t, 0) + 0.5))
            s += idf * f[t] * (k1 + 1) / (f[t] + k1 * (1 - b + b * dls[i] / avg))
        sc.append(s)
    return sc


def tfidf_cos(docs, q):
    # 以 BM25 之词频向量近似（余弦归一），与 A 组作"纯向量"对照
    N = len(docs)
    df = {}
    for d in docs:
        for t in set(d["tok"]):
            df[t] = df.get(t, 0) + 1
    qt = set(toks(q))
    qv = {t: math.log(N / (1 + df.get(t, 0))) for t in qt}
    qn = math.sqrt(sum(v * v for v in qv.values())) or 1.0
    out = []
    for d in docs:
        f = {}
        for t in d["tok"]:
            f[t] = f.get(t, 0) + 1
        dv = {t: f[t] * math.log(N / (1 + df.get(t, 0))) for t in f if t in df}
        dn = math.sqrt(sum(v * v for v in dv.values())) or 1.0
        dot = sum(qv.get(t, 0.0) * dv.get(t, 0.0) for t in qt)
        out.append(dot / (qn * dn))
    return out


def rerank(docs, q, base):
    """重排器：BM25 分 + 标题命中加权 + 查询词覆盖 + 词邻近（同段共现）"""
    qt = set(toks(q))
    qraw = [w for w in re.findall(r"[\u4e00-\u9fff]{2,}|[a-z0-9_]{2,}", q.lower())]
    out = []
    for i, d in enumerate(docs):
        tl = d["title"].lower()
        t_hit = sum(1.0 for w in qraw if w and w in tl)
        cov = len(qt & set(d["tok"])) / max(1, len(qt))
        prox = 0.0
        body = d["text"].lower()
        for w in qraw[:6]:
            if w and w in body:
                prox += 1.0
        out.append(base[i] + 1.2 * t_hit + 0.8 * cov + 0.3 * prox)
    return out


def ndcg(order, rel, k):
    dcg = sum((1.0 if order[i] in rel else 0.0) / math.log2(i + 2) for i in range(min(k, len(order))))
    ideal = sum(1.0 / math.log2(i + 2) for i in range(min(k, len(rel))))
    return dcg / ideal if ideal else 0.0


def evalset(docs, q, rel, scorer):
    sc = scorer(docs, q)
    idx = sorted(range(len(docs)), key=lambda i: -sc[i])[:K]
    order = [docs[i]["id"] for i in idx]
    hit = len(set(order) & set(rel))
    rr = 0.0
    for r, did in enumerate(order):
        if did in rel:
            rr = 1.0 / (r + 1); break
    return {"top": order, "recall": hit / max(1, len(rel)), "mrr": rr, "ndcg": ndcg(order, set(rel), K)}


def main() -> int:
    docs = load_corpus()
    for d in docs:
        d["tok"] = toks(d["title"] + " " + d["text"])
    print("  === 向量编码与重排序：检索精度实证 ===")
    print("  ★语料：%d 件（outbox/mem ＋ ledger 抽样）｜★K=%d ｜★查询 %d 条" % (len(docs), K, len(QUERIES)))
    agg = {name: {"recall": 0.0, "mrr": 0.0, "ndcg": 0.0} for name in ("A_tfidf", "B_bm25", "C_bm25+rerank")}
    rows = []
    for qid, q, rel in QUERIES:
        a = evalset(docs, q, rel, tfidf_cos)
        b = evalset(docs, q, rel, bm25)
        c = evalset(docs, q, rel, lambda D, Q: rerank(D, Q, bm25(D, Q)))
        for n, r in (("A_tfidf", a), ("B_bm25", b), ("C_bm25+rerank", c)):
            for k in ("recall", "mrr", "ndcg"):
                agg[n][k] += r[k] / len(QUERIES)
        rows.append({"qid": qid, "q": q, "rel": rel, "A": a, "B": b, "C": c})
        print("   %s %-24s R@%d  A=%.2f B=%.2f ★C=%.2f ｜ MRR A=%.2f B=%.2f ★C=%.2f" % (
            qid, q[:24], K, a["recall"], b["recall"], c["recall"], a["mrr"], b["mrr"], c["mrr"]))
    print("  ★宏平均：")
    for n in ("A_tfidf", "B_bm25", "C_bm25+rerank"):
        print("     %-14s Recall@%d=%.4f  MRR=%.4f  nDCG@%d=%.4f" % (n, K, agg[n]["recall"], agg[n]["mrr"], K, agg[n]["ndcg"]))
    d_rec = agg["C_bm25+rerank"]["recall"] - agg["B_bm25"]["recall"]
    d_nd = agg["C_bm25+rerank"]["ndcg"] - agg["B_bm25"]["ndcg"]
    print("  ★★重排相对 BM25 之增益：ΔRecall@%d=%+.4f ｜ ΔnDCG@%d=%+.4f ｜ ΔMRR=%+.4f" % (
        K, d_rec, K, d_nd, agg["C_bm25+rerank"]["mrr"] - agg["B_bm25"]["mrr"]))
    # 可选：302.AI embedding 探活（只报状态）
    st = "未测（无密钥）"
    key = os.environ.get("AI302_KEY", "").strip()
    if key:
        try:
            req = urllib.request.Request("https://api.302.ai/v1/embeddings",
                                         data=json.dumps({"model": "text-embedding-3-small", "input": "探活"}).encode(),
                                         headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
            op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with op.open(req, timeout=45) as r:
                j = json.loads(r.read().decode("utf-8", "replace"))
                dim = len((j.get("data") or [{}])[0].get("embedding") or [])
                st = "HTTP 200 ｜ 维度 %s" % dim
        except urllib.error.HTTPError as e:
            st = "HTTP %s" % e.code
        except Exception as e:
            st = "ERR %s" % str(e)[:40]
    print("  ★302.AI embedding 探活：%s" % st)
    doc = {"doc_id": "VR-20261014-CAIRN-01", "corpus": len(docs), "K": K, "queries": len(QUERIES),
           "macro": agg, "delta_rerank_vs_bm25": {"recall": d_rec, "ndcg": d_nd,
                                                   "mrr": agg["C_bm25+rerank"]["mrr"] - agg["B_bm25"]["mrr"]},
           "rows": rows, "embed_probe_302ai": st}
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print("  ★落盘：%s" % OUT.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
