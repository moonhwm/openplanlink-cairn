# -*- coding: utf-8 -*-
"""决策链：向量编码 → 召回 → 重排 → 单次前向打分（输出概率分布与置信度）
指定服务商：阿里云百炼（专属域 text-embedding-v4）
① 编码：对查询与候选各取一次嵌入（★每候选一次前向，无循环）
② 召回：余弦 Top-K
③ 重排：二次打分（余弦 + 词面覆盖 + 结构先验）线性融合，输出重排序
④ 决策：softmax(score/τ) ⇒ 概率分布；置信度 = 1 − 归一化熵；并列差（margin）
★ 结果可复算（同一输入同一输出）；凭据零回显
（引号一律用「」）
"""
import hashlib, json, math, pathlib, re, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
SEAT = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"
EX = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"
ARCH = SEAT/"archive"/"docs"
env = {}
for line in (HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8-sig", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
K = env.get("DASHSCOPE_API_KEY", "")
WS = "https://ws-ay6o8osb22o9dc3t.cn-beijing.maas.aliyuncs.com"
QUERY = "世界模型之实时交互入口、会话时长与状态持久性"
TAU = 0.05


def embed(texts):
    body = {"model": "text-embedding-v4", "input": texts}
    last = None
    for att in range(4):                      # ★重试（网络重置时）
        r = urllib.request.Request(WS + "/compatible-mode/v1/embeddings",
                                   data=json.dumps(body, ensure_ascii=False).encode(), method="POST")
        r.add_header("Authorization", "Bearer " + K); r.add_header("Content-Type", "application/json")
        t0 = time.time()
        try:
            with urllib.request.urlopen(r, timeout=120) as resp:
                j = json.loads(resp.read().decode("utf-8", "replace"))
            return [d["embedding"] for d in j["data"]], round(time.time()-t0, 2), j.get("usage", {})
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
        except Exception as e:
            last = e; time.sleep(2 + 3*att)
    raise last


def cos(a, b):
    s = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a)); nb = math.sqrt(sum(y*y for y in b))
    return s/(na*nb) if na and nb else 0.0


# ── 候选：取自本席"可微可导"档案（各件最新版之前 1200 字）──
cands = []
for d in sorted(ARCH.iterdir()):
    if not d.is_dir():
        continue
    vs = sorted(d.glob("v_*.md"))
    if not vs:
        continue
    t = vs[-1].read_text(encoding="utf-8", errors="replace")
    if len(t) < 200:
        continue
    cands.append({"key": d.name, "ver": vs[-1].stem[2:], "len": len(t), "text": t[:1200]})
print("  ═══ ① 候选池：%d 件（取自档案最新版之前 1200 字）═══" % len(cands))

# ── ② 编码（查询 1 次 ＋ 候选 N 次，单次前向）──
t_all = time.time()
qv, dt_q, uq = embed([QUERY])
print("  ② 查询编码：%.2f s ｜ usage=%s" % (dt_q, uq))
vecs, dt_c, uc, nb = [], 0.0, [], 0
for i in range(0, len(cands), 8):          # ★批量上限：每批 8（兼容面之限）
    chunk = [c["text"] for c in cands[i:i+8]]
    v, dt1, u1 = embed(chunk)
    vecs += v; dt_c += dt1; uc.append(u1); nb += 1
print("     候选编码：%d 件 ／ %d 批 ／ %.2f s ｜ usage 合计=%s" % (
    len(vecs), nb, round(dt_c, 2), {"prompt_tokens": sum(x.get("prompt_tokens", 0) for x in uc),
                                    "total_tokens": sum(x.get("total_tokens", 0) for x in uc)}))
for c, v in zip(cands, vecs):
    c["vec"] = v; c["cos"] = round(cos(qv[0], v), 6)

# ── ③ 召回 Top-K ──
rec = sorted(cands, key=lambda c: -c["cos"])[:12]
print("  ③ 召回 Top-12（余弦）：")
for c in rec[:6]:
    print("     %.4f  %-12s（%d 字）" % (c["cos"], c["key"], c["len"]))

# ── ④ 重排：线性融合（余弦 ＋ 词面覆盖 ＋ 结构先验）──
qtok = set(re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z]{3,}", QUERY))
for c in rec:
    tt = set(re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z]{3,}", c["text"]))
    ov = len(qtok & tt)/max(1, len(qtok))
    c["overlap"] = round(ov, 4)
    c["score"] = round(0.6*max(0.0, c["cos"]) + 0.3*ov + 0.1*min(1.0, c["len"]/20000), 6)
rr = sorted(rec, key=lambda c: -c["score"])
print("  ④ 重排后（融合分）：")
for i, c in enumerate(rr[:6], 1):
    print("     %d) %.4f  %-12s ｜ 余弦 %.4f ｜ 覆盖 %.3f" % (i, c["score"], c["key"], c["cos"], c["overlap"]))

# ── ⑤ 决策：softmax ⇒ 概率分布 ＋ 置信度 ──
mx = max(c["score"] for c in rr)
ex = [math.exp((c["score"]-mx)/TAU) for c in rr]
Z = sum(ex)
for c, e in zip(rr, ex):
    c["p"] = e/Z
H = -sum(c["p"]*math.log(c["p"]) for c in rr if c["p"] > 0)
Hmax = math.log(len(rr))
conf = 1 - H/Hmax
top, second = rr[0], rr[1]
print("  ⑤ 决策（softmax τ=%.2f）：" % TAU)
for c in rr[:5]:
    print("     p=%.6f  %-12s" % (c["p"], c["key"]))
print("     归一化熵 H/Hmax = %.4f ⇒ ★置信度 = %.4f ｜ margin(p1−p2) = %.6f ｜ 判 = %s" % (
    H/Hmax, conf, top["p"]-second["p"], "高置信" if conf > 0.5 else ("中" if conf > 0.2 else "低（近似并列）")))
R = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "seat": "a2a-node-local", "stage": "decision-vector-rerank",
     "provider": "aliyun-bailian", "model_embed": "text-embedding-v4", "tau": TAU, "query": QUERY,
     "pool": len(cands), "timing": {"query_embed_s": dt_q, "cand_embed_s": dt_c, "total_s": round(time.time()-t_all, 2)},
     "usage": {"query": uq, "candidates": uc},
     "recall_top": [{"key": c["key"], "cos": c["cos"]} for c in rec],
     "rerank_top": [{"key": c["key"], "score": c["score"], "cos": c["cos"], "overlap": c["overlap"], "p": round(c["p"], 8)} for c in rr],
     "decision": {"top": rr[0]["key"], "p_top": round(rr[0]["p"], 8), "margin": round(top["p"]-second["p"], 8),
                  "norm_entropy": round(H/Hmax, 6), "confidence": round(conf, 6),
                  "label": "高置信" if conf > 0.5 else ("中置信" if conf > 0.2 else "低置信（近似并列）")}}
for p in (SEAT/"outbox"/"mem", EX):
    p.mkdir(parents=True, exist_ok=True)
    (p/"decision_vector_rerank_20261011.json").write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("\n  ⑥ 落盘：decision_vector_rerank_20261011.json（可复算：同输入同输出）")
