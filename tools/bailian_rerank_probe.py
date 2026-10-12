# -*- coding: utf-8 -*-
"""bailian_rerank_probe.py —— 复探百炼之 rerank 端点是否已开通（2026-10-13 立，应 -1405 之请）
由来：-1405 见 provider_rerank_probe.py 曾探三组合而★产物未见（疑皆未通）⇒ 今复探，判其是否已开通。
本器（★极小调用：三组合各一次；★零凭据回显；★读体内 code/message 而非只看 HTTP）：
  ① 组合 A：/compatible-mode/v1/rerank ＋ gte-rerank-v2（兼容模式）
  ② 组合 B：/api/v1/services/rerank/text-rerank/text-rerank ＋ gte-rerank-v2（DashScope 原生）
  ③ 组合 C：/compatible-mode/v1/rerank ＋ qwen3-rerank
判据（可失败）：①三组合皆有 HTTP 与体内状态；②★至少一组合通（否则如实报"皆未通"）
用法：python bailian_rerank_probe.py [--dry]
（中文串一律用「」）
"""
import argparse, json, pathlib, sys, time, urllib.request, urllib.error

ENVF = pathlib.Path.home()/".zcode"/"workspace"/"default"/"a2a-bridge"/".env"
PROXY = "http://127.0.0.1:10081"
WS = "https://ws-ay6o8osb22o9dc3t.cn-beijing.maas.aliyuncs.com"


def key():
    for l in ENVF.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if l.strip().startswith("DASHSCOPE_API_KEY"):
            return l.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def post(url, body, to=60):
    k = key()
    op = urllib.request.build_opener(urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
    r = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode(), method="POST")
    r.add_header("Authorization", "Bearer " + k); r.add_header("Content-Type", "application/json")
    t0 = time.time()
    try:
        with op.open(r, timeout=to) as resp:
            return resp.status, resp.read().decode("utf-8", "replace"), time.time()-t0
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), time.time()-t0
    except Exception as e:
        return -1, str(e)[:130], time.time()-t0


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry", action="store_true"); a = ap.parse_args()
    Q = "清单互认：哪些交付物最应提交 A2A 跨席互认"
    DOCS = ["总线 emit 不可事后补录（行为之历史不可伪造）", "夜间游乐场开园：以首帧为条件之重绘"]
    combos = [
        ("A 兼容模式·gte-rerank-v2", WS + "/compatible-mode/v1/rerank",
         {"model": "gte-rerank-v2", "query": Q, "documents": DOCS, "top_n": 2}),
        ("B 原生服务·gte-rerank-v2", WS + "/api/v1/services/rerank/text-rerank/text-rerank",
         {"model": "gte-rerank-v2", "input": {"query": Q, "documents": DOCS}, "parameters": {"top_n": 2}}),
        ("C 兼容模式·qwen3-rerank", WS + "/compatible-mode/v1/rerank",
         {"model": "qwen3-rerank", "query": Q, "documents": DOCS, "top_n": 2}),
    ]
    print("  ═══ 复探百炼 rerank 端点（★三组合各一次；★读体内）═══")
    if a.dry:
        for n, u, b in combos: print("   DRY ｜ %-24s ⇒ %s" % (n, u.split("maas.aliyuncs.com")[-1]))
        return 0
    rows = []; any_ok = False
    for n, u, b in combos:
        st, tx, dt = post(u, b)
        code = msg = None; nres = None
        try:
            j = json.loads(tx)
            if isinstance(j.get("output"), dict):
                code = j["output"].get("code"); msg = str(j["output"].get("message") or "")[:60]
            elif "code" in j:
                code = j.get("code"); msg = str(j.get("message") or j.get("error") or "")[:60]
            res = j.get("results") or ((j.get("output") or {}).get("results") if isinstance(j.get("output"), dict) else None)
            nres = len(res) if isinstance(res, list) else None
        except Exception:
            msg = tx[:70]
        ok = (st == 200 and nres)
        if ok: any_ok = True
        print("   ★%-24s ⇒ HTTP %-4s ｜ %.2fs ｜ 体内 code=%s ｜ msg=%s ｜ 结果 %s"
              % (n, st, dt, code, msg, ("%d 条" % nres) if nres else "无"))
        rows.append({"combo": n, "url": u.split("maas.aliyuncs.com")[-1], "http": st, "code": code,
                     "msg": msg, "n_results": nres, "ok": bool(ok)})
    print("   ── 判 ──")
    print("   ★可用组合：%s" % ("、".join(r["combo"] for r in rows if r["ok"]) if any_ok else "★无一可用（皆未通）"))
    crit = {"①三组合皆有 HTTP 与体内状态": len(rows) == 3, "②★至少一组合通": any_ok}
    for k, v in crit.items(): print("   %s ⇒ %s" % (k, "✓" if v else "✗（如实）"))
    out = pathlib.Path(__file__).resolve().parent.parent/"outbox"/"mem"/"bailian_rerank_probe_20261013.json"
    out.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "rows": rows,
        "any_ok": any_ok, "criteria": crit}, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print("   ⇒ 已写：%s" % out.name)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True); sys.exit(main())
