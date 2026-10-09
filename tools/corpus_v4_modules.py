# -*- coding: utf-8 -*-
"""语料 v4 检索复测（百炼专属域 向量 + 异质承载 重排）＋ 决策模型分诊（专属域）
—— 世界模型面受阻期间，以可用通道尽令条之三模块职责
（引号一律用「」；零回显）
"""
import json, pathlib, sys, time, urllib.request, urllib.error
from urllib.parse import urlparse

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
BASE = HOME / "WPSDrive" / "29969771" / "WPS云盘" / "月之暗面的Plasma游乐场"
EX = BASE / "A2A共同体_共享交换区"; DOCX = BASE / "Plan提示词工程" / "openplanlink-docx"
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

# 语料：交换区之本席件（全量）＋ docx 直取件
docs = []
for p in sorted(EX.glob("*CAIRN*.otl")):
    docs.append((p.name[:56], p.read_text(encoding="utf-8", errors="replace")[:700]))
for p in sorted(DOCX.glob("*_正文副本_20261009_CAIRN-DIRECT.md")):
    docs.append(("docx/" + p.name[:46], p.read_text(encoding="utf-8", errors="replace")[:700]))
print("  语料 v4 = %d 件" % len(docs))

# ① 向量（专属域；分批 8）
ok = 0; dim = None; err = None
for i in range(0, len(docs), 8):
    st, dt, tx = post("https://%s/api/v1/services/embeddings/text-embedding/text-embedding" % H, K,
                      {"model": "text-embedding-v4", "input": {"texts": [d[1] for d in docs[i:i+8]]}})
    if st == 200:
        try: dim = len(json.loads(tx)["output"]["embeddings"][0]["embedding"]); ok += len(docs[i:i+8])
        except Exception as e: err = str(e)[:60]
    else:
        err = "HTTP %s %s" % (st, tx[:80]); break
print("  ① 向量（专属域）⇒ 成功 %d/%d ｜ dim=%s ｜ 备注=%s" % (ok, len(docs), dim, err or "—"))

# ② 重排（三查询）
QS = [("命名由构图还是文案决定", "应命中 -58/-59"),
      ("refWorldId 是否继承内容", "应命中 -60"),
      ("是否见过未知道路返回 200 之兜底", "应命中 -64")]
carrier = None; out = []
for q, exp in QS:
    st, dt, tx = post("https://%s/api/v1/services/rerank/text-rerank/text-rerank" % H, K,
                      {"model": "gte-rerank-v2", "input": {"query": q, "documents": [d[1] for d in docs]}})
    if st == 200:
        carrier = "百炼专属域 gte-rerank-v2"; order = [(r["index"], r["relevance_score"]) for r in json.loads(tx)["output"]["results"]]
    else:
        carrier = "异质承载：硅基流动 BAAI/bge-reranker-v2-m3（专属域 %s）" % st
        st2, dt2, tx2 = post("https://api.siliconflow.cn/v1/rerank", SF,
                             {"model": "BAAI/bge-reranker-v2-m3", "query": q, "documents": [d[1] for d in docs], "top_n": 5})
        order = [(r["index"], r["relevance_score"]) for r in (json.loads(tx2).get("results") or [])] if st2 == 200 else []
    order = sorted(order, key=lambda x: -x[1])[:5]
    print("\n  ② 查询：%s（%s）" % (q, exp))
    for i, s in order:
        print("     %.5f ｜ %s" % (s, docs[i][0]))
    out.append({"query": q, "expect": exp, "carrier": carrier,
                "top5": [{"score": round(s, 5), "doc": docs[i][0]} for i, s in order]})

# ③ 决策模型分诊（专属域；取最新 12 件）
newest = sorted(EX.glob("*CAIRN*.otl"), key=lambda p: p.stat().st_mtime, reverse=True)[:12]
print("\n  ③ 决策模型分诊（专属域 qwen-plus，最新 %d 件）" % len(newest))
rows = []
for p in newest:
    t = p.read_text(encoding="utf-8", errors="replace")
    st, dt, tx = post("https://%s/compatible-mode/v1/chat/completions" % H, K,
                      {"model": "qwen-plus", "max_tokens": 90, "messages": [{"role": "user", "content":
                        '只输出 JSON：{"verdict":"PUBLIC_SAFE|CAUTION|BLOCKED","confidence":0-1}。'
                        '含真实可用密钥/令牌/ticket 值 ⇒ BLOCKED；仅提键名或"已脱敏"声明 ⇒ PUBLIC_SAFE。\n文档前 700 字：' + t[:700].replace("\n", " ")}]})
    v = c = None
    try:
        j = json.loads(tx); content = ((j.get("choices") or [{}])[0].get("message") or {}).get("content", "")
        s = content[content.find("{"):content.rfind("}")+1]; q = json.loads(s); v, c = q.get("verdict"), q.get("confidence")
    except Exception:
        v = "HTTP %s" % st if st != 200 else "解析失败"
    rows.append({"file": p.name, "verdict": v, "conf": c, "http": st})
    print("     %-52s ⇒ %s（%.2f）" % (p.name[:52], v, c if isinstance(c, (int, float)) else 0))
    time.sleep(0.2)

safe = sum(1 for r in rows if r["verdict"] == "PUBLIC_SAFE")
blk = [r for r in rows if r["verdict"] == "BLOCKED"]
print("  ③ 汇总：PUBLIC_SAFE %d／%d ｜ BLOCKED %d" % (safe, len(rows), len(blk)))

p = EX / "corpus_v4_retrieval_20261009_CAIRN.json"
p.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "seat": "a2a-node-local",
                         "corpus_n": len(docs), "vector": {"carrier": "百炼专属域", "model": "text-embedding-v4", "ok": ok, "dim": dim},
                         "rerank_carrier": carrier, "rankings": out,
                         "decision": {"carrier": "百炼专属域 qwen-plus", "n": len(rows), "public_safe": safe, "blocked": len(blk), "rows": rows}},
                        ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("\n  落盘：%s（%d B）" % (p.name, p.stat().st_size))
