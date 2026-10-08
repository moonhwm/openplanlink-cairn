# -*- coding: utf-8 -*-
"""三模块齐动（域分区修正后）：
 ①决策模型（专属域 qwen-plus，单次前向）→ 对本夜 18 件作凭据分诊（补齐此前因墙未竟之交叉验证）
 ②向量编码（专属域 text-embedding-v4）
 ③重排序（专属域 gte-rerank-v2 → 若 429 则异质承载 硅基流动 bge-reranker-v2-m3，标注承载方）
零回显：不打印键值
"""
import json, pathlib, re, sys, time, urllib.request, urllib.error
from urllib.parse import urlparse

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
EX = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"
env = {}
for line in (HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
WS_HOST = urlparse(env["DASHSCOPE_WS_BASE"]).hostname
K = env.get("DASHSCOPE_API_KEY", ""); SF = env.get("SILICONFLOW_API_KEY", "")
COMPAT = "https://%s/compatible-mode/v1/chat/completions" % WS_HOST
EMBED = "https://%s/api/v1/services/embeddings/text-embedding/text-embedding" % WS_HOST
RERANK_WS = "https://%s/api/v1/services/rerank/text-rerank/text-rerank" % WS_HOST
RERANK_SF = "https://api.siliconflow.cn/v1/rerank"

PATS = [("腾讯云SecretId", re.compile(r"AKID[A-Za-z0-9]{20,}")), ("sk-高熵键", re.compile(r"sk-[A-Za-z0-9]{28,}")),
        ("阿里云AK", re.compile(r"\bLTAI[A-Za-z0-9]{16,}\b")), ("Bearer长串", re.compile(r"(?i)bearer\s+[A-Za-z0-9_\-\.]{32,}")),
        ("ticket 值", re.compile(r"\btk_[A-Za-z0-9_\-]{20,}")), ("RTC token 值", re.compile(r"\"token\"\s*:\s*\"[A-Za-z0-9_\-\.]{20,}\"")),
        ("预签名URL q-ak", re.compile(r"q-ak=[A-Za-z0-9]{10,}"))]

def call(url, key, body=None, to=90):
    data = json.dumps(body, ensure_ascii=False).encode() if body else None
    r = urllib.request.Request(url, data=data, method="POST" if body else "GET")
    r.add_header("Authorization", "Bearer " + key)
    if body: r.add_header("Content-Type", "application/json")
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=to) as resp:
            return resp.status, round(time.time()-t0, 2), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, round(time.time()-t0, 2), e.read().decode("utf-8", "replace")
    except Exception as e:
        return -1, round(time.time()-t0, 2), str(e)[:130]

targets = sorted([p for p in EX.glob("*.otl") if re.search(r"(DF-AI-20261009-CAIRN-(1[6-9]|2[0-9])|DF-PERSONA-20261009-CAIRN-0[1-3]|DF-META-20261009-CAIRN-04|DF-OPS-20261009-CAIRN-(0[89]|1[0-3]))", p.name)])
print("  受检件=%d" % len(targets))

print("\n=== ① 决策模型（专属域）· 凭据分诊（单次前向，逐件）")
rows = []
for p in targets:
    t = p.read_text(encoding="utf-8", errors="replace")
    det = sum(len(rx.findall(t)) for _, rx in PATS)
    st, dt, tx = call(COMPAT, K, {"model": "qwen-plus", "max_tokens": 120,
        "messages": [{"role": "user", "content":
            '只输出 JSON：{"verdict":"PUBLIC_SAFE|CAUTION|BLOCKED","confidence":0-1}。'
            '含真实可用密钥/token/ticket 值 ⇒ BLOCKED；仅提及键名、占位符或"已脱敏/不落盘"声明 ⇒ PUBLIC_SAFE。\n'
            '文档前 900 字：' + t[:900].replace("\n", " ")}]})
    v = c = None
    try:
        s = tx[tx.find("{"):][:400]
        j = json.loads(s[s.find("{"):s.rfind("}")+1]); v, c = j.get("verdict"), j.get("confidence")
    except Exception:
        v = "HTTP %s" % st if st != 200 else "解析失败"
    rows.append({"file": p.name, "det": det, "model": v, "conf": c, "http": st})
    print("   %-52s 扫描=%d ｜ 模型=%s（%.2f）" % (p.name[:52], det, v, c if isinstance(c, (int, float)) else 0))
    time.sleep(0.2)
det_dirty = [r for r in rows if r["det"] > 0]
blk = [r for r in rows if r["model"] == "BLOCKED"]
caution = [r for r in rows if r["model"] == "CAUTION"]
contra = [r for r in rows if (r["model"] == "BLOCKED") != (r["det"] > 0)]
print("  汇总：确定性命中 %d／%d ｜ 模型 BLOCKED %d ｜ CAUTION %d ｜ 两法相左 %d" % (
    len(det_dirty), len(rows), len(blk), len(caution), len(contra)))

print("\n=== ② 向量编码（专属域 text-embedding-v4）")
texts = ["凭据见即止不外显不落盘", "器物强制优于自律：时点行由器物写入", "共享面之礼：先取后推不覆盖重签",
         "台账几何：参量取自台账实测的真 glTF 资产", "预算墙之分域实测：公共域 429 专属域 200"]
st, dt, tx = call(EMBED, K, {"model": "text-embedding-v4", "input": {"texts": texts}})
dim = None
try: dim = len(json.loads(tx)["output"]["embeddings"][0]["embedding"])
except Exception: pass
print("   ⇒ HTTP %s ｜ %.2fs ｜ 条数=%d ｜ dim=%s" % (st, dt, len(texts), dim))

print("\n=== ③ 重排序（先专属域，429 则异质承载）")
q = "器物强制与凭据纪律"
st3, dt3, tx3 = call(RERANK_WS, K, {"model": "gte-rerank-v2", "input": {"query": q, "documents": texts}})
print("   专属域 ⇒ HTTP %s ｜ %.2fs" % (st3, dt3))
carrier = "百炼专属域"
if st3 == 200:
    order = json.loads(tx3)["output"]["results"]
else:
    carrier = "异质承载：硅基流动 BAAI/bge-reranker-v2-m3"
    st4, dt4, tx4 = call(RERANK_SF, SF, {"model": "BAAI/bge-reranker-v2-m3", "query": q, "documents": texts, "top_n": 5})
    print("   异质 ⇒ HTTP %s ｜ %.2fs" % (st4, dt4))
    order = (json.loads(tx4).get("results") or []) if st4 == 200 else []
print("   承载方=%s" % carrier)
for r in order:
    i = r.get("index"); sc = r.get("relevance_score")
    print("      · %.5f ｜ %s" % (float(sc), texts[i][:32]))

out = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "seat": "a2a-node-local",
       "decision_model": {"carrier": "百炼专属域 (ws-ay6o8osb22o9dc3t)", "model": "qwen-plus", "files": rows,
                          "summary": {"det_dirty": len(det_dirty), "total": len(rows), "blocked": len(blk),
                                      "caution": len(caution), "contradictions": len(contra)}},
       "vector": {"carrier": "百炼专属域", "model": "text-embedding-v4", "http": st, "n": len(texts), "dim": dim},
       "rerank": {"carrier": carrier, "query": q,
                  "top": [{"score": r.get("relevance_score"), "text": texts[r.get("index")]} for r in order]}}
p = EX/"three_modules_resume_20261009_CAIRN.json"
p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("\n  落盘：%s（%d B）" % (p.name, p.stat().st_size))
