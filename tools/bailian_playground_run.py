# -*- coding: utf-8 -*-
"""百炼四模块 × 游乐场文档库 实战（承目标轮令：强制调用）
- 世界模型（qwen-turbo）：三类运行模式之态势演绎（世界探索／实时导演／角色演绎）
- 决策模型（qwen-turbo）：逐件三态判定 PUBLIC_SAFE / CAUTION / BLOCKED ＋ 置信度
- 向量编码（text-embedding-v4）：逐件向量（维度＋首 4 值）
- 重排序（gte-rerank-v2）：对 14 件作相关性排序
零回显：键自 a2a-bridge/.env 读取；不落盘键值。
"""
import hashlib, json, pathlib, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

BASE = "https://dashscope.aliyuncs.com"
DOCX = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\Plan提示词工程\openplanlink-docx")
OUT = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A共同体_共享交换区")

env = {}
for line in (pathlib.Path.home()/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8", errors="replace").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
KEY = env.get("DASHSCOPE_API_KEY", "")
print("  键长=%d（零回显）｜ 端点=%s" % (len(KEY), BASE))

STATS = {"calls": 0, "ms": 0, "tokens": 0}

def post(path, body, timeout=120):
    r = urllib.request.Request(BASE + path, data=json.dumps(body, ensure_ascii=False).encode("utf-8"), method="POST")
    r.add_header("Authorization", "Bearer " + KEY); r.add_header("Content-Type", "application/json")
    t0 = time.time(); STATS["calls"] += 1
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            j = json.loads(resp.read().decode("utf-8", "replace"))
            STATS["ms"] += int((time.time()-t0)*1000)
            u = j.get("usage") or {}
            STATS["tokens"] += int(u.get("total_tokens") or u.get("input_tokens") or 0)
            return j
    except urllib.error.HTTPError as e:
        STATS["ms"] += int((time.time()-t0)*1000)
        return {"_err": "HTTP %s" % e.code, "_body": e.read().decode("utf-8", "replace")[:200]}
    except Exception as e:
        STATS["ms"] += int((time.time()-t0)*1000)
        return {"_err": str(e)[:120]}

def chat(model, prompt, mx=400):
    j = post("/compatible-mode/v1/chat/completions",
             {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": mx})
    if "_err" in j: return None, j["_err"]
    ch = (j.get("choices") or [{}])[0]
    return ((ch.get("message") or {}).get("content") or "").strip(), None

# ---------- 语料 ----------
docs = []
for p in sorted(DOCX.glob("*_正文副本_20261009_CAIRN-DIRECT.md")):
    t = p.read_text(encoding="utf-8", errors="replace")
    name = p.name.replace("_正文副本_20261009_CAIRN-DIRECT.md", "")
    docs.append({"name": name, "path": str(p), "chars": len(t), "excerpt": t[:600].replace("\n", " ")})
print("  语料件数=%d" % len(docs))

# ---------- ① 向量编码 ----------
print("\n=== ① 向量编码（text-embedding-v4）===")
vecs = []
for d in docs:
    j = post("/api/v1/services/embeddings/text-embedding/text-embedding",
             {"model": "text-embedding-v4", "input": {"texts": [d["name"] + "\n" + d["excerpt"]]}})
    if "_err" in j:
        print("   × %-40s %s" % (d["name"][:40], j["_err"])); continue
    emb = j["output"]["embeddings"][0]["embedding"]
    vecs.append({"name": d["name"], "dim": len(emb), "head4": [round(x, 5) for x in emb[:4]],
                 "sha256_16": hashlib.sha256(json.dumps([round(x,6) for x in emb]).encode()).hexdigest()[:16]})
    print("   ★ %-40s dim=%d ｜ head4=%s" % (d["name"][:40], len(emb), vecs[-1]["head4"]))

# ---------- ② 重排序 ----------
QUERY = "A2A 节点读取便利与故障排查；异质模型通路；凭据纪律与开源分层"
print("\n=== ② 重排序（gte-rerank-v2）｜查询：%s ===" % QUERY)
j = post("/api/v1/services/rerank/text-rerank/text-rerank",
         {"model": "gte-rerank-v2", "input": {"query": QUERY, "documents": [d["name"] + "：" + d["excerpt"][:300] for d in docs]}})
rank = []
if "_err" in j:
    print("   × %s" % j["_err"])
else:
    for it in (j.get("output") or {}).get("results", [])[:6]:
        nm = docs[it["index"]]["name"]
        rank.append({"name": nm, "score": round(it.get("relevance_score", 0), 5), "index": it["index"]})
        print("   ★ %-44s score=%.5f" % (nm[:44], it.get("relevance_score", 0)))

# ---------- ③ 决策模型（逐件三态） ----------
print("\n=== ③ 决策模型（qwen-turbo 三态＋置信度）===")
decisions = []
for d in docs[:8]:                      # 取前 8 件控预算
    prompt = ('就下述文档作为「可公开发布到 GitHub 公共仓库」之对象，作**单次判定**，只输出 JSON：'
              '{"verdict":"PUBLIC_SAFE|CAUTION|BLOCKED","confidence":0-1,"reason":"≤20字"}。'
              '判据：含真实凭据/密钥/口令/设备标识者应 CAUTION 或 BLOCKED；纯治理与研读文本应 PUBLIC_SAFE。\n'
              '文档名：%s\n正文摘录：%s' % (d["name"], d["excerpt"][:400]))
    out, err = chat("qwen-turbo", prompt, 120)
    if err:
        print("   × %-40s %s" % (d["name"][:40], err)); continue
    try:
        jj = json.loads(out[out.find("{"):out.rfind("}")+1])
        decisions.append({"name": d["name"], **jj})
        print("   ★ %-40s %-12s conf=%s ｜ %s" % (d["name"][:40], jj.get("verdict"), jj.get("confidence"), str(jj.get("reason"))[:22]))
    except Exception as e:
        print("   × %-40s JSON 解析失败：%s ｜ %s" % (d["name"][:40], str(e)[:30], out[:60]))

# ---------- ④ 世界模型（三类模式） ----------
print("\n=== ④ 世界模型（qwen-turbo；三类运行模式）===")
world = {}
modes = {
    "世界探索": "以夜间游乐场（A2A 交界）为世界，探索式描述当前可观测态势：在场席位、文档面、通道面。≤70字。",
    "实时导演": "以夜间游乐场为世界，作为导演给出下一步最该发生的一个镜头（谁做什么）。≤70字。",
    "角色演绎": "以夜间游乐场为世界，演绎一个'新来席位'此刻的独白。≤70字。",
}
for mode, ask in modes.items():
    out, err = chat("qwen-turbo", ask, 160)
    world[mode] = out if out else ("ERR: " + str(err)[:60])
    print("   ★ %-8s ｜ %s" % (mode, world[mode][:110].replace("\n", " ")))

# ---------- 落盘 ----------
res = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "corpus": [d["name"] for d in docs],
       "vectors": vecs, "query": QUERY, "rerank_top6": rank, "decisions": decisions, "world": world,
       "stats": STATS, "note": "百炼四模块实战（世界/决策/向量/重排）；键零回显；输入为游乐场文档（已脱敏副本）"}
p = OUT / "bailian_four_modules_playground_20261009.json"
p.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("\n=== 资源效能（本席自计）===")
print("   调用次数=%d ｜ 累计时延=%.1fs ｜ 计量 token=%d" % (STATS["calls"], STATS["ms"]/1000, STATS["tokens"]))
print("   落盘：%s（%d B）" % (p.name, p.stat().st_size))
