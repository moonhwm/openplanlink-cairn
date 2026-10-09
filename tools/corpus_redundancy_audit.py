# -*- coding: utf-8 -*-
"""件库冗余度自审：两两余弦相似度 ⇒ 近重复对（≥0.90／≥0.95）与整体冗余指标
★ 文档表示为「文件名＋正文前 300 字」（承 -99 之索引）
★ 目的：以己为镜——若本席产出高度重复，则如实报之
（引号一律用「」）
"""
import json, pathlib, statistics, sys

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
EX = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"
idx = json.loads((EX/"cairn_index_20261009.json").read_text(encoding="utf-8"))
items = idx["items"]
vecs = [it["vec"] for it in items]
n = len(vecs)
print("  件数 = %d ｜ dim = %d ｜ 模型 = %s" % (n, idx["dim"], idx["model"]))

# 归一化（避免用 numpy 之外之依赖；numpy 已有）
try:
    import numpy as np
    A = np.asarray(vecs, dtype=np.float32)
    A /= np.linalg.norm(A, axis=1, keepdims=True) + 1e-12
    S = A @ A.T
    np.fill_diagonal(S, -1.0)
    iu = np.triu_indices(n, k=1)
    vals = S[iu]
    order = np.argsort(-vals)
    pairs = [(float(vals[k]), iu[0][k], iu[1][k]) for k in order[:25]]
    mean_sim = float(vals.mean()); med = float(np.median(vals))
    ge90 = int((vals >= 0.90).sum()); ge95 = int((vals >= 0.95).sum()); ge80 = int((vals >= 0.80).sum())
except Exception as e:
    print("  numpy 失败：%s" % e); sys.exit(1)

print("\n  === 冗余指标 ===")
print("   两两相似度：均 %.4f ｜ 中位 %.4f ｜ 最大 %.4f" % (mean_sim, med, float(vals.max())))
print("   对数分布：≥0.95 ⇒ %d 对 ｜ ≥0.90 ⇒ %d 对 ｜ ≥0.80 ⇒ %d 对（总对 %d）" % (ge95, ge90, ge80, vals.size))

print("\n  === 最相似之 20 对 ===")
for v, i, j in pairs[:20]:
    print("   %.4f ｜ %s  ⇔  %s" % (v, items[i]["file"][:52], items[j]["file"][:52]))

out = EX/"corpus_redundancy_audit_20261009_CAIRN.json"
out.write_text(json.dumps({"ts": __import__("time").strftime("%Y-%m-%dT%H:%M:%S+0800"),
    "seat": "a2a-node-local", "n": n, "doc_repr": idx["doc_repr"], "model": idx["model"],
    "mean": round(mean_sim,4), "median": round(med,4), "max": round(float(vals.max()),4),
    "pairs_ge_095": ge95, "pairs_ge_090": ge90, "pairs_ge_080": ge80, "total_pairs": int(vals.size),
    "top25": [{"sim": round(v,4), "a": items[i]["file"], "b": items[j]["file"]} for v, i, j in pairs]},
    ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("\n  落盘：%s" % out.name)
