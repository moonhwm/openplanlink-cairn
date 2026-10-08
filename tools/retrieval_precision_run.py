# -*- coding: utf-8 -*-
"""① 检索精度对比：向量检索（text-embedding-v4 + 余弦） vs 向量＋重排序（gte-rerank-v2）
   ② 302.AI 交叉复核：以非国内最先进模型复核百炼决策模型之 CAUTION 判定
零回显：键自 a2a-bridge/.env 读取；不落盘键值。
"""
import json, math, pathlib, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
DOCX = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\Plan提示词工程\openplanlink-docx")
OUT = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A共同体_共享交换区")
env = {}
for line in (pathlib.Path.home()/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
DS, AI302 = env.get("DASHSCOPE_API_KEY", ""), env.get("AI302_API_KEY", "")
STATS = {"calls": 0, "ms": 0}

def post(url, body, key, timeout=120):
    r = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode("utf-8"), method="POST")
    r.add_header("Authorization", "Bearer " + key); r.add_header("Content-Type", "application/json")
    t0 = time.time(); STATS["calls"] += 1
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            j = json.loads(resp.read().decode("utf-8", "replace")); STATS["ms"] += int((time.time()-t0)*1000)
            return j
    except urllib.error.HTTPError as e:
        STATS["ms"] += int((time.time()-t0)*1000)
        return {"_err": "HTTP %s: %s" % (e.code, e.read().decode("utf-8", "replace")[:140])}
    except Exception as e:
        STATS["ms"] += int((time.time()-t0)*1000); return {"_err": str(e)[:120]}

def embed(texts):
    j = post("https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding",
             {"model": "text-embedding-v4", "input": {"texts": texts}}, DS)
    if "_err" in j: return None, j["_err"]
    return [e["embedding"] for e in j["output"]["embeddings"]], None

def cos(a, b):
    s = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a)); nb = math.sqrt(sum(y*y for y in b))
    return s/(na*nb) if na and nb else 0.0

def rerank(query, docs):
    j = post("https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank",
             {"model": "gte-rerank-v2", "input": {"query": query, "documents": docs}}, DS)
    if "_err" in j: return None, j["_err"]
    return [(r["index"], r["relevance_score"]) for r in (j.get("output") or {}).get("results", [])], None

docs = []
for p in sorted(DOCX.glob("*_正文副本_20261009_CAIRN-DIRECT.md")):
    t = p.read_text(encoding="utf-8", errors="replace")
    docs.append({"name": p.name.replace("_正文副本_20261009_CAIRN-DIRECT.md", ""), "excerpt": t[:800].replace("\n", " ")})
print("  语料=%d 件" % len(docs))

texts = [d["name"] + "\n" + d["excerpt"] for d in docs]
dfull = []
for i in range(0, len(texts), 8):          # DashScope 单请求文本数上限：分批 8
    part, perr = embed(texts[i:i+8])
    if part: dfull.extend(part)
    else: print("   × 批 %d 失败：%s" % (i//8+1, str(perr)[:90]))
print("  文档向量：%s" % ("OK %d 条 dim=%d" % (len(dfull), len(dfull[0])) if dfull else "ERR"))

QUERIES = ["凭据纪律、密钥脱敏与开源协议分层如何落在文档流程上？",
           "异质模型通路与超算通道之接入要点与实测结论？"]
report = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "corpus": len(docs), "compare": [], "ai302_crosscheck": None}
for q in QUERIES:
    qv, err = embed([q])
    vec_top = []
    if qv:
        sims = [(i, cos(qv[0], dfull[i])) for i in range(len(docs))]
        sims.sort(key=lambda x: -x[1]); vec_top = sims[:6]
    rr, rerr = rerank(q, [d["name"] + "：" + d["excerpt"][:300] for d in docs])
    rr_top = sorted(rr, key=lambda x: -x[1])[:6] if rr else []
    vnames = [docs[i]["name"] for i, _ in vec_top]
    rnames = [docs[i]["name"] for i, _ in rr_top]
    print("\n=== 查询：%s ===" % q)
    print("   向量-only top6：%s" % " ｜ ".join("%s(%.4f)" % (n[:22], s) for (i, s), n in zip(vec_top, vnames)))
    if rr_top: print("   向量+重排 top6：%s" % " ｜ ".join("%s(%.4f)" % (docs[i]["name"][:22], s) for i, s in rr_top))
    moved = [(n, vnames.index(n), rnames.index(n)) for n in vnames if n in rnames]
    report["compare"].append({"query": q, "vector_top6": [{"name": n, "score": round(s, 5)} for (i, s), n in zip(vec_top, vnames)],
                              "rerank_top6": [{"name": docs[i]["name"], "score": round(s, 5)} for i, s in rr_top],
                              "rank_changes": [{"name": n[:40], "vec_rank": a+1, "rr_rank": b+1} for n, a, b in moved],
                              "only_in_vector": [n for n in vnames if n not in rnames],
                              "only_in_rerank": [n for n in rnames if n not in vnames]})
    print("   仅在向量榜：%s ｜ 仅在重排榜：%s" % ([n[:18] for n in report["compare"][-1]["only_in_vector"]] or "—",
                                                  [n[:18] for n in report["compare"][-1]["only_in_rerank"]] or "—"))

# ---------- 302.AI 交叉复核（非国内、最先进） ----------
print("\n=== 302.AI 交叉复核（claude-opus-5）===")
verdicts = [{"doc": "A2A项目四件套完整文字记录_中.otl", "bailian": "CAUTION 0.85", "reason": "含凭据信息（腾讯云 Secret ID 等 24 处，运行中实测被 GitHub Push Protection 拦截，现已脱敏）"},
            {"doc": "OpenPlanLink全局声明与Agent-to-Agent网络建设纲要.otl", "bailian": "CAUTION 0.80", "reason": "含凭据形态（4 处 sk- 形态；主权人 164 号裁定称系有意共享）"},
            {"doc": "A2A算力分配与分布式协同深化案_v0.1.otl", "bailian": "CAUTION 0.90", "reason": "含云直取链接及凭据信息"}]
prompt = ("请对下列三份文档的「可公开发布到 GitHub 公共仓库」判定作**独立复核**。已知百炼决策模型给出如下判定与理由：\n"
          + "\n".join("- %s：%s（%s）" % (v["doc"], v["bailian"], v["reason"]) for v in verdicts)
          + "\n请只输出 JSON：{\"concur\":true|false,\"confidence\":0-1,\"note\":\"≤40字\"}。")
j = post("https://api.302ai.cn/v1/chat/completions",
         {"model": "claude-opus-5", "messages": [{"role": "user", "content": prompt}], "max_tokens": 600}, AI302)
if "_err" in j:
    print("   × %s" % j["_err"]); report["ai302_crosscheck"] = {"error": j["_err"]}
else:
    ch = (j.get("choices") or [{}])[0]; msg = ch.get("message") or {}
    txt = (msg.get("content") or msg.get("reasoning_content") or "").strip()
    print("   ★ claude-opus-5 ⇒ 200 ｜ finish=%s ｜ tokens=%s" % (ch.get("finish_reason"), (j.get("usage") or {}).get("total_tokens")))
    print("   " + txt[:300].replace("\n", " "))
    report["ai302_crosscheck"] = {"model": "claude-opus-5", "finish": ch.get("finish_reason"),
                                  "tokens": (j.get("usage") or {}).get("total_tokens"), "text": txt[:600]}

report["stats"] = STATS
p = OUT / "retrieval_precision_and_crosscheck_20261009.json"
p.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("\n  调用=%d ｜ 累计时延=%.1fs ｜ 落盘=%s（%d B）" % (STATS["calls"], STATS["ms"]/1000, p.name, p.stat().st_size))
