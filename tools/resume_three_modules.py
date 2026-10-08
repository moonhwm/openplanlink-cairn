# -*- coding: utf-8 -*-
"""续作实跑（域分区修正后）：①专属域 向量 ②专属域 决策 ③重排（专属域 429 ⇒ 试异质承载：硅基流动 bge-reranker-v2-m3，**明确标注承载方**）
零回显；不打印键值
"""
import json, pathlib, sys, time, urllib.request, urllib.error
from urllib.parse import urlparse

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
env = {}
for line in (HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
WS_HOST = urlparse(env["DASHSCOPE_WS_BASE"]).hostname
K = env.get("DASHSCOPE_API_KEY", "")
SF = env.get("SILICONFLOW_API_KEY", "")

def call(url, key, body=None, method="POST", to=60):
    data = json.dumps(body, ensure_ascii=False).encode() if body else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Authorization", "Bearer " + key)
    if body: r.add_header("Content-Type", "application/json")
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=to) as resp:
            return resp.status, round(time.time()-t0, 2), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, round(time.time()-t0, 2), e.read().decode("utf-8", "replace")
    except Exception as e:
        return -1, round(time.time()-t0, 2), str(e)[:140]

TEXTS = ["凭据：见即止、不外显、不落盘；取回即扫描；diff 在脱敏副本上进行",
         "器物强制优于自律：时点行由 stamp_time.py 写入，禁止手写",
         "共享面之礼：先取后推、他席提交不覆盖、签名树冲突必重签"]
print("=== ① 专属域 · 向量编码（text-embedding-v4）")
st, dt, tx = call("https://%s/api/v1/services/embeddings/text-embedding/text-embedding" % WS_HOST, K,
                  {"model": "text-embedding-v4", "input": {"texts": TEXTS}})
dim = None
try:
    dim = len(json.loads(tx)["output"]["embeddings"][0]["embedding"])
except Exception:
    pass
print("   ⇒ HTTP %s ｜ %.2fs ｜ 条数=3 ｜ dim=%s" % (st, dt, dim))

print("=== ② 专属域 · 决策模型（单次前向，JSON 判决）")
st2, dt2, tx2 = call("https://%s/compatible-mode/v1/chat/completions" % WS_HOST, K,
                     {"model": "qwen-plus",
                      "messages": [{"role": "user", "content":
                                    '只输出 JSON：{"label":"通过|复核|否决","probabilities":{"通过":x,"复核":y,"否决":z},"confidence":c}。'
                                    '判定：某件由本席签发、含 SHA3-512 树根与署名块，且经九类凭据模式扫描 0 命中。'}],
                      "max_tokens": 200})
print("   ⇒ HTTP %s ｜ %.2fs ｜ %s" % (st2, dt2, tx2[tx2.find("{"):][:220] if st2 == 200 else tx2[:180].replace("\n", " ")))

print("=== ③ 重排序：先试专属域，再试异质承载（硅基流动）")
st3, dt3, tx3 = call("https://%s/api/v1/services/rerank/text-rerank/text-rerank" % WS_HOST, K,
                     {"model": "gte-rerank-v2", "input": {"query": "器物强制", "documents": TEXTS}})
print("   专属域 ⇒ HTTP %s ｜ %.2fs ｜ %s" % (st3, dt3, tx3[:120].replace("\n", " ")))
st4, dt4, tx4 = call("https://api.siliconflow.cn/v1/rerank", SF,
                     {"model": "BAAI/bge-reranker-v2-m3", "query": "器物强制", "documents": TEXTS, "top_n": 3})
print("   异质承载（硅基流动 BAAI/bge-reranker-v2-m3）⇒ HTTP %s ｜ %.2fs ｜ %s" % (st4, dt4, tx4[:220].replace("\n", " ")))
if st4 == 200:
    try:
        j = json.loads(tx4)
        for r in (j.get("results") or []):
            print("      · idx=%s score=%.5f ｜ %s" % (r.get("index"), float(r.get("relevance_score", 0)), TEXTS[r["index"]][:30]))
    except Exception:
        pass
