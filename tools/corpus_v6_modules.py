# -*- coding: utf-8 -*-
"""语料 v6 三模块复测 ＋ 决策模型分诊总表（输出类别/概率/置信度）
① 向量：百炼专属域（text-embedding-v4）② 重排：硅基流动 bge-reranker-v2-m3（专属域 429）
③ 决策：百炼专属域（qwen-plus），对最新 N 件逐件分诊 ⇒ 表
（引号一律用「」）
"""
import json, os, pathlib, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
EX = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"
env = {}
for line in (HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
K = env.get("DASHSCOPE_API_KEY", ""); SF = env.get("SILICONFLOW_API_KEY", "")
WS = "https://ws-ay6o8osb22o9dc3t.cn-beijing.maas.aliyuncs.com"
def post(url, key, body, to=90):
    r = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode(), method="POST")
    r.add_header("Authorization", "Bearer " + key); r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=to) as resp: return resp.status, json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e: return e.code, {"err": e.read().decode("utf-8","replace")[:160]}
    except Exception as e: return -1, {"err": str(e)[:120]}

files = sorted(EX.glob("*CAIRN*.otl"), key=lambda p: p.stat().st_mtime, reverse=True)
print("  语料件数 = %d" % len(files))

# ── ① 向量（抽样 40 件以省调用；余者沿用 v5 之结果）──
sample = files[:40]
ok = 0
for p in sample:
    st, j = post(WS + "/compatible-mode/v1/embeddings", K, {"model": "text-embedding-v4", "input": p.name})
    if st == 200 and j.get("data"): ok += 1
print("  ① 向量（专属域 text-embedding-v4）⇒ 成功 %d/%d ｜ dim=%s" % (
    ok, len(sample), len(j["data"][0]["embedding"]) if st == 200 and j.get("data") else "—"))

# ── ② 重排（含新查询）──
QUERIES = ["确定性程序之判与跨会话复现", "音频通道之开与静音头", "论据戒七条与自查", "世界模型资格墙与解耦问法"]
print("  ② 重排（硅基流动 bge-reranker-v2-m3，专属域 429 之异质承载）")
rerank_rows = []
for q in QUERIES:
    docs = [p.name for p in files[:60]]
    st, j = post("https://api.siliconflow.cn/v1/rerank", SF,
                 {"model": "BAAI/bge-reranker-v2-m3", "query": q, "documents": docs, "top_n": 3})
    if st == 200 and j.get("results"):
        top = [(round(r["relevance_score"], 5), docs[r["index"]]) for r in j["results"][:3]]
        print("     「%s」⇒ %s" % (q, " ｜ ".join("%.5f %s" % t for t in top)))
        rerank_rows.append({"query": q, "top3": top})
    else:
        print("     「%s」⇒ 失败 %s" % (q, j)); rerank_rows.append({"query": q, "error": str(j)[:120]})

# ── ③ 决策分诊总表（最新 30 件；要求输出类别/概率/置信度）──
print("  ③ 决策模型分诊（专属域 qwen-plus）：最新 30 件")
rows = []
for p in files[:30]:
    body = {"model": "qwen-plus", "messages": [
        {"role": "system", "content": "你是合规分诊器。只输出 JSON：{\"class\":\"PUBLIC_SAFE|INTERNAL_ONLY|BLOCKED\",\"prob\":0..1,\"conf\":0..1,\"why\":\"≤12字\"}"},
        {"role": "user", "content": ("文件名：%s\n正文前 700 字：\n%s" % (p.name, p.read_text(encoding="utf-8", errors="replace")[:700]))}],
        "max_tokens": 80, "temperature": 0}
    st, j = post(WS + "/compatible-mode/v1/chat/completions", K, body)
    if st != 200:
        rows.append({"file": p.name, "error": str(j)[:100]}); print("     %-56s ⇒ 失败 %s" % (p.name[:56], str(j)[:60])); continue
    try:
        txt = j["choices"][0]["message"]["content"].strip()
        s = txt[txt.find("{"): txt.rfind("}")+1]
        d = json.loads(s)
        rows.append({"file": p.name, "class": d.get("class"), "prob": d.get("prob"), "conf": d.get("conf"), "why": d.get("why")})
        print("     %-56s ⇒ %-13s p=%s c=%s" % (p.name[:56], d.get("class"), d.get("prob"), d.get("conf")))
    except Exception as e:
        rows.append({"file": p.name, "raw": txt[:80]}); print("     %-56s ⇒ 解析失败" % p.name[:56])

cnt = {}
for r in rows:
    if r.get("class"): cnt[r["class"]] = cnt.get(r["class"], 0) + 1
print("  ③ 汇总：%s" % "／".join("%s %d" % (k, v) for k, v in sorted(cnt.items())))
out = EX/"corpus_v6_retrieval_20261009_CAIRN.json"
out.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "seat": "a2a-node-local",
    "corpus": len(files), "embed_ok": "%d/%d" % (ok, len(sample)), "rerank": rerank_rows,
    "decision": rows, "summary": cnt}, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("  落盘：%s" % out.name)
