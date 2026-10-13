# -*- coding: utf-8 -*-
"""vector_rerank_probe2.py —— 重排器重设计版：检索精度实证（2026-10-14 立，承 v1 之否证）

v1 否证：以 BM25 分为基作★线性加项之"重排"零增益（Δ三项皆 0），因其未改变排序。
v2 改法（★皆能改变排序）：R1 乘性标题加权（BM25×(1+α·标题命中)）｜R2 BM25F 多字段（标题词频×3）｜
      R3 短语邻近加分（查询词在文中相邻出现者加乘）⇒ 与 BM25 基线逐一对照 Δ。
修正：★q1 真值 .md→.json（v1 标注误）；★查询集 8→12 条。
指标：Recall@3 / MRR / nDCG@3（宏平均）＋ 逐法 Δ。
纪律：★零外呼、纯本地、可复算｜★结果落 outbox/mem
用法：python vector_rerank_probe2.py
"""
import json, math, pathlib, re, sys

sys.stdout.reconfigure(encoding="utf-8")
SEAT = (pathlib.Path.home() / "WPSDrive" / "29969771" / "WPS云盘" / "月之暗面的Plasma游乐场"
        / "A2A新席_石敢当Cairn_20260928")
OUT = SEAT / "outbox" / "mem" / "vector_rerank_run2_20261014.json"
K = 3
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
    s = s.lower()
    return (re.findall(r"[a-z0-9_]+", s)
            + re.findall(r"[\u4e00-\u9fff]{2,}", s)
            + [z[i:i + 2] for z in re.findall(r"[\u4e00-\u9fff]{2,}", s) for i in range(max(1, len(z) - 1))])


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
        for t in set(d["tok"]):
            df[t] = df.get(t, 0) + 1
    N = len(docs)
    dls = [len(d["tok"]) for d in docs]
    return {"df": df, "N": N, "avg": sum(dls) / max(1, N), "dls": dls}


def bm25(docs, st, qt, k1=1.5, b=0.75, title_boost=0.0):
    N, df, avg, dls = st["N"], st["df"], st["avg"], st["dls"]
    sc = []
    for i, d in enumerate(docs):
        f = d["_f"] if "_f" in d else None
        if f is None:
            f = {}
            for t in d["tok"]:
                f[t] = f.get(t, 0) + 1
            d["_f"] = f
        tf_t = d["_tf"] if "_tf" in d else None
        if tf_t is None:
            tf_t = {}
            for t in d["ttok"]:
                tf_t[t] = tf_t.get(t, 0) + 1
            d["_tf"] = tf_t
        s = 0.0
        for t in qt:
            if t not in f:
                continue
            idf = math.log(1 + (N - df.get(t, 0) + 0.5) / (df.get(t, 0) + 0.5))
            w = f[t] + title_boost * tf_t.get(t, 0)
            s += idf * w * (k1 + 1) / (w + k1 * (1 - b + b * dls[i] / avg))
        sc.append(s)
    return sc


def r1_mul(docs, st, qt, qraw):
    base = bm25(docs, st, qt)
    out = []
    for i, d in enumerate(docs):
        hits = sum(1 for w in qraw if w and w in d["title"].lower())
        out.append(base[i] * (1.0 + 0.5 * hits))
    return out


def r2_bm25f(docs, st, qt):
    return bm25(docs, st, qt, title_boost=3.0)


def r3_phrase(docs, st, qt, qraw):
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
    print("  === 重排器重设计版：检索精度实证 ===")
    print("  ★语料 %d 件｜K=%d｜查询 %d 条（v1 为 8 条）" % (len(docs), K, len(QUERIES)))
    names = ["BM25(v1基线)", "R1乘性标题", "R2 BM25F(标题×3)", "R3短语邻近"]
    agg = {n: {"recall": 0.0, "mrr": 0.0, "ndcg": 0.0} for n in names}
    rows = []
    for qid, q, rel in QUERIES:
        qt = toks(q)
        qraw = [w for w in re.findall(r"[\u4e00-\u9fff]{2,}|[a-z0-9_]{2,}", q.lower())]
        res = {
            "BM25(v1基线)": ev(docs, rel, bm25(docs, st, qt)),
            "R1乘性标题": ev(docs, rel, r1_mul(docs, st, qt, qraw)),
            "R2 BM25F(标题×3)": ev(docs, rel, r2_bm25f(docs, st, qt)),
            "R3短语邻近": ev(docs, rel, r3_phrase(docs, st, qt, qraw)),
        }
        for n in names:
            for k in ("recall", "mrr", "ndcg"):
                agg[n][k] += res[n][k] / len(QUERIES)
        rows.append({"qid": qid, "q": q, "rel": rel, "res": res})
        print("   %s %-22s R@3 基线=%.2f R1=%.2f R2=%.2f R3=%.2f ｜ nDCG 基线=%.2f R1=%.2f R2=%.2f R3=%.2f" % (
            qid, q[:22], res[names[0]]["recall"], res[names[1]]["recall"], res[names[2]]["recall"], res[names[3]]["recall"],
            res[names[0]]["ndcg"], res[names[1]]["ndcg"], res[names[2]]["ndcg"], res[names[3]]["ndcg"]))
    print("  ★宏平均：")
    for n in names:
        print("     %-16s Recall@3=%.4f  MRR=%.4f  nDCG@3=%.4f" % (n, agg[n]["recall"], agg[n]["mrr"], agg[n]["ndcg"]))
    print("  ★★各重排相对 BM25 之增益：")
    for n in names[1:]:
        print("     %-16s ΔRecall=%+.4f  ΔMRR=%+.4f  ΔnDCG=%+.4f" % (
            n, agg[n]["recall"] - agg[names[0]]["recall"], agg[n]["mrr"] - agg[names[0]]["mrr"],
            agg[n]["ndcg"] - agg[names[0]]["ndcg"]))
    best = max(names, key=lambda n: agg[n]["ndcg"])
    print("  ★★按 nDCG 之最优法：%s（%.4f）" % (best, agg[best]["ndcg"]))
    doc = {"doc_id": "VR2-20261014-CAIRN-01", "corpus": len(docs), "K": K, "queries": len(QUERIES),
           "macro": agg, "best_by_ndcg": best, "rows": rows}
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print("  ★落盘：%s" % OUT.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
