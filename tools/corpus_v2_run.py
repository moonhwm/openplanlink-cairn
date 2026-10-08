# -*- coding: utf-8 -*-
"""语料 v2（34 件）四模块复算：向量编码 + 三查询重排序 + 新入件决策分诊
- 语料：游乐场根 17 件 + openplanlink-docx 14 件 + 本席治理/AI 件 9 件
- 零回显：键自 .env；不打印凭据
"""
import json, math, pathlib, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
PLAZA = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场")
ROOT = PLAZA / "Plan提示词工程" / "openplanlink-docx" / "游乐场根_正文副本_20261009_CAIRN"
DOCX = PLAZA / "Plan提示词工程" / "openplanlink-docx"
EX = PLAZA / "A2A共同体_共享交换区"
env = {}
for line in (pathlib.Path.home()/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
KEY = env.get("DASHSCOPE_API_KEY", "")
STATS = {"calls": 0, "ms": 0, "tokens": 0}

def post(url, body, timeout=90):
    r = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode(), method="POST")
    r.add_header("Authorization", "Bearer " + KEY); r.add_header("Content-Type", "application/json")
    t0 = time.time(); STATS["calls"] += 1
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            j = json.loads(resp.read().decode("utf-8", "replace"))
            STATS["ms"] += int((time.time()-t0)*1000)
            STATS["tokens"] += int((j.get("usage") or {}).get("total_tokens") or 0)
            return j
    except Exception as e:
        STATS["ms"] += int((time.time()-t0)*1000); return {"_err": str(e)[:100]}

def embed(texts):
    out = []
    for i in range(0, len(texts), 8):
        j = post("https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding",
                 {"model": "text-embedding-v4", "input": {"texts": texts[i:i+8]}})
        if "_err" in j: return None, j["_err"]
        out += [e["embedding"] for e in j["output"]["embeddings"]]
    return out, None

def rerank(q, docs):
    j = post("https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank",
             {"model": "gte-rerank-v2", "input": {"query": q, "documents": docs}})
    if "_err" in j: return None, j["_err"]
    return [(r["index"], r["relevance_score"]) for r in (j.get("output") or {}).get("results", [])], None

def chat(p, mx=200):
    j = post("https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
             {"model": "qwen-turbo", "messages": [{"role": "user", "content": p}], "max_tokens": mx})
    if "_err" in j: return "ERR " + str(j["_err"])[:60]
    return str(((j.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()

docs = []
for p in sorted(ROOT.glob("*_正文副本_20261009_CAIRN.md")):
    docs.append(("根/" + p.name.replace("_正文副本_20261009_CAIRN.md", ""), p.read_text(encoding="utf-8", errors="replace")[:700]))
for p in sorted(DOCX.glob("*_正文副本_20261009_CAIRN-DIRECT.md")):
    docs.append(("docx/" + p.name.replace("_正文副本_20261009_CAIRN-DIRECT.md", ""), p.read_text(encoding="utf-8", errors="replace")[:700]))
for pat in ["*DF-OPS-20261009-CAIRN-0*.otl", "*DF-AI-20261009-CAIRN-0*.otl", "*DF-GOV-20261009-CAIRN-01.otl"]:
    for p in sorted(EX.glob(pat)):
        docs.append(("gov/" + p.name, p.read_text(encoding="utf-8", errors="replace")[:700]))
print("  语料 v2 = %d 件" % len(docs))

vecs, verr = embed([n + "\n" + t.replace("\n", " ") for n, t in docs])
print("  向量编码：%s" % ("OK %d 条 dim=%d" % (len(vecs), len(vecs[0])) if vecs else "ERR " + str(verr)))

QUERIES = ["开源协议分层、AGPL 与 SSPL 之组合口径", "异质模型通路与超算接入", "尼采 奴隶道德 主人道德 研读"]
ranking = []
for q in QUERIES:
    rr, err = rerank(q, [n + "：" + t.replace("\n", " ")[:280] for n, t in docs])
    top = sorted(rr, key=lambda x: -x[1])[:5] if rr else []
    print("\n  === 查询：%s ===" % q)
    for i, s in top:
        print("     %-52s %.5f" % (docs[i][0][:52], s))
    ranking.append({"query": q, "top5": [{"name": docs[i][0], "score": round(s, 5)} for i, s in top]})

# 新入 17 件之发布就绪分诊
print("\n  === 新入（根目录）件之发布就绪分诊（决策模型）===")
triage = []
for n, t in [(n, t) for n, t in docs if n.startswith("根/")]:
    out = chat('只输出 JSON：{"verdict":"PUBLIC_SAFE|CAUTION|BLOCKED","score":0-100,"confidence":0-1,"reason":"≤16字"}。'
               '判据：含真实凭据/密钥/预签名地址/口令者应 CAUTION 或 BLOCKED；纯治理文本 PUBLIC_SAFE。\n'
               '文档：%s\n摘录：%s' % (n[:70], t.replace("\n", " ")[:400]))
    try:
        j = json.loads(out[out.find("{"):out.rfind("}")+1]); triage.append({"name": n, **j})
        print("     %-52s %-12s %3s ｜ %s" % (n[:52], j.get("verdict"), j.get("score"), str(j.get("reason"))[:16]))
    except Exception:
        triage.append({"name": n, "error": out[:60]})
        print("     %-52s × %s" % (n[:52], out[:50]))

res = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "corpus_n": len(docs),
       "vectors": [{"name": n, "dim": len(v), "head4": [round(x, 5) for x in v[:4]]} for (n, _), v in zip(docs, vecs or [])],
       "rankings": ranking, "triage": triage, "stats": STATS}
p = EX / "corpus_v2_four_modules_20261009.json"
p.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
dist = {}
for r in triage:
    if r.get("verdict"): dist[r["verdict"]] = dist.get(r["verdict"], 0) + 1
print("\n  分诊分布=%s ｜ 调用=%d ｜ 时延=%.1fs ｜ token=%d" % (dist, STATS["calls"], STATS["ms"]/1000, STATS["tokens"]))
print("  落盘：%s（%d B）" % (p.name, p.stat().st_size))
