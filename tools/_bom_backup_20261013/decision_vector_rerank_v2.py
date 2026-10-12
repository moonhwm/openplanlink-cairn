# -*- coding: utf-8 -*-
"""决策链 v2：修分词器 ＋ 加嵌入缓存（★不重复花费 token）
v1 之缺陷：中文词元用 [\\u4e00-\\u9fff]{2,} ⇒ 整串中文被切成一个词元 ⇒ overlap 恒 0（重排实为余弦＋长度先验）
v2 之修：①先按标点/空白切段 ②每段取 2–3 字滑窗 n-gram ③缓存嵌入（按文本 sha1）
（引号一律用「」）
"""
import hashlib, json, math, pathlib, re, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
SEAT = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"
EX = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"
ARCH = SEAT/"archive"/"docs"
CACHE = SEAT/"exp"/".cache"; CACHE.mkdir(parents=True, exist_ok=True)
env = {}
for line in (HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8-sig", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
K = env.get("DASHSCOPE_API_KEY", "")
WS = "https://ws-ay6o8osb22o9dc3t.cn-beijing.maas.aliyuncs.com"
QUERY = "世界模型之实时交互入口、会话时长与状态持久性"
TAU = 0.05
CALLS = {"n": 0, "tok": 0}


def cache_path(t):
    return CACHE/("emb_" + hashlib.sha1(t.encode("utf-8")).hexdigest()[:20] + ".json")


def embed_cached(texts):
    out, miss, miss_idx = [None]*len(texts), [], []
    for i, t in enumerate(texts):
        p = cache_path(t)
        if p.exists():
            out[i] = json.loads(p.read_text(encoding="utf-8"))["v"]
        else:
            miss.append(t); miss_idx.append(i)
    if miss:
        for s in range(0, len(miss), 8):                     # ★批量 ≤8
            chunk = miss[s:s+8]
            body = {"model": "text-embedding-v4", "input": chunk}
            for att in range(4):
                r = urllib.request.Request(WS + "/compatible-mode/v1/embeddings",
                                           data=json.dumps(body, ensure_ascii=False).encode(), method="POST")
                r.add_header("Authorization", "Bearer " + K); r.add_header("Content-Type", "application/json")
                try:
                    with urllib.request.urlopen(r, timeout=120) as resp:
                        j = json.loads(resp.read().decode("utf-8", "replace"))
                    break
                except urllib.error.HTTPError as _eh:
                    """★墙闸"""
                    try:
                        _wb = _eh.read().decode("utf-8", "replace")
                        import sys as _ws, pathlib as _wp
                        _ws.path.insert(0, str(_wp.Path(__file__).resolve().parent))
                        import wall_guard as _wg
                        if _wg.classify(_wb)[0] == "wall":
                            _wg.record(_wb, source=_wp.Path(__file__).name, channel="wall")
                            print("   ★撞墙即停（零重试）")
                            raise
                    except RuntimeError:
                        raise
                    except Exception:
                        pass
                except Exception:
                    if att == 3: raise
                    time.sleep(2 + 3*att)
            CALLS["n"] += 1; CALLS["tok"] += (j.get("usage") or {}).get("total_tokens", 0)
            for k, (t, d) in enumerate(zip(chunk, j["data"])):
                cache_path(t).write_text(json.dumps({"v": d["embedding"]}, ensure_ascii=False), encoding="utf-8")
                out[miss_idx[s + k]] = d["embedding"]
    return out


def toks(s, n=(2, 3)):
    """★修正之分词：按标点/空白切段，再取 2–3 字滑窗 n-gram（中文）与整词（西文）"""
    out = set()
    for seg in re.split(r"[，。；：、！？（）()\[\]{}<>/\\|·—…\s\"'“”‘’,.;:!?]+", s):
        if not seg:
            continue
        cj = re.findall(r"[\u4e00-\u9fff]+", seg)
        for run in cj:
            for k in n:
                for i in range(0, max(0, len(run)-k+1)):
                    out.add(run[i:i+k])
        for w in re.findall(r"[A-Za-z][A-Za-z0-9_\-]{2,}", seg):
            out.add(w.lower())
    return out


def cos(a, b):
    s = sum(x*y for x, y in zip(a, b)); na = math.sqrt(sum(x*x for x in a)); nb = math.sqrt(sum(y*y for y in b))
    return s/(na*nb) if na and nb else 0.0


cands = []
for d in sorted(ARCH.iterdir()):
    if not d.is_dir(): continue
    vs = sorted(d.glob("v_*.md"))
    if not vs: continue
    t = vs[-1].read_text(encoding="utf-8", errors="replace")
    if len(t) < 200: continue
    cands.append({"key": d.name, "text": t[:1200], "len": len(t)})
print("  ═══ ① 候选池 %d 件 ｜ 缓存目录 %s ═══" % (len(cands), CACHE.name))
t0 = time.time()
qv = embed_cached([QUERY])[0]
cvec = embed_cached([c["text"] for c in cands])
print("  ② 编码完成 %.1f s ｜ 本轮 API 调用 %d 次／%d tokens（其余命中缓存）" % (time.time()-t0, CALLS["n"], CALLS["tok"]))
for c, v in zip(cands, cvec):
    c["vec"] = v; c["cos"] = round(cos(qv, v), 6)
rec = sorted(cands, key=lambda c: -c["cos"])[:12]
qt = toks(QUERY)
print("  ③ 召回 Top-12 ｜ 查询词元 %d 个（修正后）" % len(qt))
for c in rec[:4]:
    print("     %.4f  %-12s（%d 字）" % (c["cos"], c["key"], c["len"]))
for c in rec:
    ct = toks(c["text"])
    c["overlap"] = round(len(qt & ct)/max(1, len(qt)), 4)
    c["score"] = round(0.6*max(0.0, c["cos"]) + 0.3*c["overlap"] + 0.1*min(1.0, c["len"]/20000), 6)
rr = sorted(rec, key=lambda c: -c["score"])
print("  ④ 重排（修正后；词面项已生效）：")
for i, c in enumerate(rr[:6], 1):
    print("     %d) %.4f  %-12s ｜ 余弦 %.4f ｜ ★覆盖 %.3f" % (i, c["score"], c["key"], c["cos"], c["overlap"]))
mx = max(c["score"] for c in rr)
ex = [math.exp((c["score"]-mx)/TAU) for c in rr]; Z = sum(ex)
for c, e in zip(rr, ex): c["p"] = e/Z
H = -sum(c["p"]*math.log(c["p"]) for c in rr if c["p"] > 0); Hmax = math.log(len(rr)); conf = 1-H/Hmax
print("  ⑤ 决策（softmax τ=%.2f）：p₁=%.6f（%s）｜p₂=%.6f｜margin=%.6f" % (
    TAU, rr[0]["p"], rr[0]["key"], rr[1]["p"], rr[0]["p"]-rr[1]["p"]))
print("     归一化熵 %.4f ⇒ ★置信度 = %.4f ｜ 判 = %s" % (H/Hmax, conf, "高" if conf > 0.5 else ("中" if conf > 0.2 else "低（近似并列）")))
print("\n  ═══ ⑥ 与 v1 之对照 ═══")
print("     v1（词面项失效）：top=%s ｜ 置信度 0.1069 ｜ margin 0.079624 ｜ 覆盖恒 0.000" % "kd_sbZsGm")
print("     v2（词面项生效）：top=%s ｜ 置信度 %.4f ｜ margin %.6f" % (rr[0]["key"], conf, rr[0]["p"]-rr[1]["p"]))
R = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "version": 2, "fix": "按标点切段＋2-3 字滑窗 n-gram；嵌入缓存",
     "api_calls": CALLS["n"], "tokens": CALLS["tok"], "query": QUERY, "tau": TAU,
     "top12": [{"key": c["key"], "cos": c["cos"], "overlap": c["overlap"], "score": c["score"], "p": round(c["p"], 8)} for c in rr],
     "decision": {"top": rr[0]["key"], "p_top": round(rr[0]["p"], 8), "margin": round(rr[0]["p"]-rr[1]["p"], 8),
                  "confidence": round(conf, 6), "v1_top": "kd_sbZsGm", "v1_confidence": 0.1069}}
for p in (SEAT/"outbox"/"mem", EX):
    p.mkdir(parents=True, exist_ok=True)
    (p/"decision_vector_rerank_v2_20261011.json").write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("\n  落盘：decision_vector_rerank_v2_20261011.json")
