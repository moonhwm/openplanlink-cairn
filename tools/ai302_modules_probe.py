# -*- coding: utf-8 -*-
"""ai302_modules_probe.py —— 测 302.AI 三模块（chat／embedding／rerank）（2026-10-13 立）
缘由：-1438 定论 —— 百炼账户欠费（−8.44 CNY，信控 0）⇒ 其付费模型全受限（429 budget exhausted）。
      而令条★另点名 302.AI（https://api.302ai.cn ＋ sk-5982…，★独立账户）⇒ 本器测其是否可补位。
本器（★三模块各一次极小调用；★零凭据回显；★读体内）：
  ① chat：POST /v1/chat/completions（★模型 gpt-5，单句）⇒ 判其可用否（可作「实时导演」之近似承载）
  ② embedding：POST /v1/embeddings（text-embedding-3-small）⇒ 报维度
  ③ rerank：POST /v1/rerank（jina-reranker-v2-base-multilingual）⇒ 报前二条与分数
判据（可失败）：①三模块皆有 HTTP 与体内状态；②★至少一模块通（否则如实报）
用法：python ai302_modules_probe.py [--dry]
（中文串一律用「」）
"""
import argparse, json, pathlib, sys, time, urllib.request, urllib.error

ENVF = pathlib.Path.home()/".zcode"/"workspace"/"default"/"a2a-bridge"/".env"
BASE = "https://api.302ai.cn/v1"
PROXY = "http://127.0.0.1:10081"


def env(k):
    for l in ENVF.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if l.strip().startswith(k):
            return l.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def post(path, body, key, to=90):
    op = urllib.request.build_opener(urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
    r = urllib.request.Request(BASE + path, data=json.dumps(body, ensure_ascii=False).encode(),
                               headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
                               method="POST")
    t0 = time.time()
    try:
        with op.open(r, timeout=to) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8", "replace")), time.time()-t0
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read().decode("utf-8", "replace")), time.time()-t0
        except Exception: return e.code, {}, time.time()-t0
    except Exception as e:
        return -1, {"err": str(e)[:110]}, time.time()-t0


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry", action="store_true"); a = ap.parse_args()
    K = env("AI302_API_KEY") or env("API302_API_KEY") or env("AI302_KEY")
    if not K:
        # ★令条给了 key，但不回显；从 .env 取不到则如实报
        print("   ★未在 .env 找到 AI302 之键（键名试 AI302_API_KEY／API302_API_KEY／AI302_KEY）⇒ 止"); return 2
    print("  ═══ 302.AI 三模块之探（★独立账户；三模块各一次极小调用）═══")
    if a.dry:
        print("   DRY：将试 /chat/completions ／ /embeddings ／ /rerank"); return 0
    rows = []
    # ① chat（可作「实时导演」之近似承载）
    st, j, dt = post("/chat/completions", {"model": "gpt-5", "messages": [
        {"role": "user", "content": "只回四字：夜场已开"}], "max_tokens": 24}, K)
    txt = ""
    try: txt = str(j["choices"][0]["message"]["content"])[:60]
    except Exception: txt = str(j)[:90]
    ok1 = (st == 200 and txt)
    print("   ① chat(gpt-5) ⇒ HTTP %-4s ｜ %.2fs ｜ 回复「%s」" % (st, dt, txt.replace("\n", " ")[:40]))
    rows.append({"m": "chat", "http": st, "ok": bool(ok1), "sample": txt[:60]})
    # ② embedding
    st, j, dt = post("/embeddings", {"model": "text-embedding-3-small", "input": "夜间游乐场开园"}, K)
    dim = None
    try: dim = len(j["data"][0]["embedding"])
    except Exception: pass
    ok2 = (st == 200 and dim)
    print("   ② embedding(text-embedding-3-small) ⇒ HTTP %-4s ｜ %.2fs ｜ ★维度 %s" % (st, dt, dim))
    rows.append({"m": "embedding", "http": st, "ok": bool(ok2), "dim": dim})
    # ③ rerank
    st, j, dt = post("/rerank", {"model": "jina-reranker-v2-base-multilingual",
        "query": "总线可否事后补录",
        "documents": ["总线 emit 不可事后补录（行为之历史不可伪造）", "夜间游乐场开园：以首帧为条件之重绘"],
        "top_n": 2}, K)
    top = []
    try: top = [(round(float(r.get("relevance_score") or 0), 5), str(r.get("index"))) for r in (j.get("results") or [])]
    except Exception: pass
    ok3 = (st == 200 and top)
    print("   ③ rerank(jina-reranker-v2) ⇒ HTTP %-4s ｜ %.2fs ｜ ★前二 %s" % (st, dt, top))
    rows.append({"m": "rerank", "http": st, "ok": bool(ok3), "top": top})
    print("   ── 判 ──")
    good = [r["m"] for r in rows if r["ok"]]
    print("   ★可用模块：%s" % ("、".join(good) if good else "★无一可用（如实报）"))
    crit = {"①三模块皆有 HTTP 与体内状态": len(rows) == 3, "②★至少一模块通": bool(good)}
    for k, v in crit.items(): print("   %s ⇒ %s" % (k, "✓" if v else "✗（如实）"))
    out = pathlib.Path(__file__).resolve().parent.parent/"outbox"/"mem"/"ai302_modules_probe_20261013.json"
    out.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "rows": rows, "good": good,
        "criteria": crit}, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print("   ⇒ 已写：%s" % out.name)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True); sys.exit(main())
