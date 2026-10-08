# -*- coding: utf-8 -*-
"""语料 v3 检索复测（令条之向量／重排模块）：
 语料＝本席夜班件（DF-AI/DF-OPS/DF-PERSONA/DF-META 之 .otl）＋两册 ＋ docx 直取件
 ①向量：专属域 text-embedding-v4（dim=1024）——逐件首 700 字
 ②重排：专属域 gte-rerank-v2（若 429 则异质承载 硅基流动 bge-reranker-v2-m3，标注承载方）
 ③三查询 top-5 ＋ ★语料缺口探针（取一"应无命中"之题，看首位分值是否显著低）
③′顺带一测：Directing 是否已开通（1 次调用）
"""
import json, pathlib, sys, time, urllib.request, urllib.error
from urllib.parse import urlparse

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
PLAZA = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"
EX = PLAZA/"A2A共同体_共享交换区"; DOCX = PLAZA/"Plan提示词工程"/"openplanlink-docx"
env = {}
for line in (HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
H = urlparse(env["DASHSCOPE_WS_BASE"]).hostname
K = env.get("DASHSCOPE_API_KEY", ""); SF = env.get("SILICONFLOW_API_KEY", "")

def post(url, key, body, to=120):
    r = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode(), method="POST")
    r.add_header("Authorization", "Bearer " + key); r.add_header("Content-Type", "application/json")
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=to) as resp:
            return resp.status, round(time.time()-t0, 2), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, round(time.time()-t0, 2), e.read().decode("utf-8", "replace")
    except Exception as e:
        return -1, round(time.time()-t0, 2), str(e)[:120]

docs = []
for pat, tag in [("*DF-AI-20261009-CAIRN-*.otl", "ai"), ("*DF-OPS-20261009-CAIRN-*.otl", "ops"),
                 ("*DF-PERSONA-20261009-CAIRN-*.otl", "persona"), ("*DF-META-20261009-CAIRN-*.otl", "meta")]:
    for p in sorted(EX.glob(pat)):
        docs.append(("%s/%s" % (tag, p.name[:46]), p.read_text(encoding="utf-8", errors="replace")[:700]))
for p in sorted(DOCX.glob("*_正文副本_20261009_CAIRN-DIRECT.md")):
    docs.append(("docx/%s" % p.name[:44], p.read_text(encoding="utf-8", errors="replace")[:700]))
print("  语料 v3 = %d 件" % len(docs))

# ① 向量（分批 8）
ok = 0; dim = None; emb_err = None
for i in range(0, len(docs), 8):
    st, dt, tx = post("https://%s/api/v1/services/embeddings/text-embedding/text-embedding" % H, K,
                      {"model": "text-embedding-v4", "input": {"texts": [d[1] for d in docs[i:i+8]]}})
    if st == 200:
        try:
            dim = len(json.loads(tx)["output"]["embeddings"][0]["embedding"]); ok += len(docs[i:i+8])
        except Exception as e:
            emb_err = str(e)[:60]
    else:
        emb_err = "HTTP %s" % st
        break
print("  ① 向量（专属域）：成功 %d/%d ｜ dim=%s ｜ 备注=%s" % (ok, len(docs), dim, emb_err or "—"))

# ② 重排 + ③ 三查询
QUERIES = [("器物强制与凭据纪律", "应命中 ai/ops 之纪律件"),
           ("真 3D 资产与 glTF 入世", "应命中 AI-28/29"),
           ("涌现判定与判官重推导", "应命中 AI-27/30/31")]
rerank_carrier = None
res = []
for q, expect in QUERIES:
    st, dt, tx = post("https://%s/api/v1/services/rerank/text-rerank/text-rerank" % H, K,
                      {"model": "gte-rerank-v2", "input": {"query": q, "documents": [d[1] for d in docs]}})
    if st == 200:
        rerank_carrier = "百炼专属域 gte-rerank-v2"
        order = [(r["index"], r["relevance_score"]) for r in json.loads(tx)["output"]["results"]]
    else:
        rerank_carrier = "异质承载：硅基流动 BAAI/bge-reranker-v2-m3（专属域 %s）" % st
        st2, dt2, tx2 = post("https://api.siliconflow.cn/v1/rerank", SF,
                             {"model": "BAAI/bge-reranker-v2-m3", "query": q,
                              "documents": [d[1] for d in docs], "top_n": 5})
        order = [(r["index"], r["relevance_score"]) for r in (json.loads(tx2).get("results") or [])] if st2 == 200 else []
    order = sorted(order, key=lambda x: -x[1])[:5]
    print("\n  ② 查询：%s（%s）" % (q, expect))
    for i, s in order:
        print("     %.5f ｜ %s" % (s, docs[i][0]))
    res.append({"query": q, "expect": expect, "carrier": rerank_carrier,
                "top5": [{"score": round(s, 5), "doc": docs[i][0]} for i, s in order]})

# ③′ Directing 一测
st, dt, tx = post("https://%s/api/v2/apps/happyoyster-1.0-directing/openapi/v1/worlds" % H, K,
                  {"async": True, "creationModel": "simple", "resolution": "720p",
                   "prompt": "夜间游乐场（开通性探测）",
                   "firstFrameImage": {"base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg=="}})
print("\n  ③′ Directing 开通性一测 ⇒ HTTP %s ｜ %.2fs ｜ %s" % (st, dt, tx[:120].replace("\n", " ")))

out = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "seat": "a2a-node-local",
       "corpus_n": len(docs), "vector": {"carrier": "百炼专属域", "model": "text-embedding-v4", "ok": ok, "dim": dim},
       "rerank_carrier": rerank_carrier, "rankings": res,
       "directing_probe": {"http": st, "sec": dt}}
p = EX/"corpus_v3_retrieval_20261009_CAIRN.json"
p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("\n  落盘：%s（%d B）" % (p.name, p.stat().st_size))
