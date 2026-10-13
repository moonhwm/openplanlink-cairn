# -*- coding: utf-8 -*-
"""bailian_four_probe.py —— 百炼四腿复探（2026-10-14 立；承 -1437／-1438 之 429，今节省计划）
缘由：昨夜百炼 429（budget exhausted）＋账户欠费；今令条载"已购 250 抵 500 节省计划"，
      且 qwen-plus 实测 200 ⇒ ★须逐腿复探：①chat ②embedding ③rerank ④多模态嵌入。
本器（★各一次极小调用；★零凭据回显；★带退避）：
  ① POST {base}/chat/completions  model=qwen-plus
  ② POST {base}/embeddings        model=text-embedding-v4        ⇒ 报维度
  ③ POST {base}/rerank（compatible）与 /api/v1/services/rerank/text-rerank/text-rerank（原生）
  ④ POST {base}/embeddings        model=multimodal-embedding-v1（传 data URI 图）
判据：逐腿给 HTTP 与体内 code ⇒ 判"可用／受限"
用法：python bailian_four_probe.py [--dry]
（中文串一律用「」）
"""
import argparse, base64, json, pathlib, sys, time, urllib.request, urllib.error

ENVF = pathlib.Path.home()/".zcode"/"workspace"/"default"/"a2a-bridge"/".env"
IMG = (pathlib.Path.home()/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"
       /"A2A新席_石敢当Cairn_20260928"/"assets"/"firstframe_20261013_0044.jpg")


def env():
    d = {}
    for l in ENVF.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if "=" in l and not l.strip().startswith("#"):
            k, _, v = l.partition("="); d[k.strip()] = v.strip().strip('"').strip("'")
    return d


def post(url, body, key, to=90, tries=3):
    for i in range(tries):
        r = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode(),
                                   headers={"Authorization": "Bearer " + key,
                                            "Content-Type": "application/json"}, method="POST")
        t0 = time.time()
        try:
            with urllib.request.urlopen(r, timeout=to) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8", "replace")), round(time.time()-t0, 2)
        except urllib.error.HTTPError as e:
            try: j = json.loads(e.read().decode("utf-8", "replace"))
            except Exception: j = {}
            if e.code in (429, 500, 503) and i < tries-1:
                time.sleep(4); continue
            return e.code, j, round(time.time()-t0, 2)
        except Exception as e:
            if i < tries-1:
                time.sleep(4); continue
            return -1, {"err": str(e)[:110]}, round(time.time()-t0, 2)
    return -1, {}, 0.0


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry", action="store_true"); a = ap.parse_args()
    E = env(); K = E.get("DASHSCOPE_API_KEY", "")
    base = E.get("DASHSCOPE_WS_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1").rstrip("/")
    print("  ═══ 百炼四腿复探（★各一次极小调用；节省计划后）═══")
    print("   base = %s" % base)
    if a.dry: return 0
    rows = []

    def rec(tag, st, j, dt, extra=""):
        code = ""
        if isinstance(j, dict):
            code = str(j.get("code") or (j.get("output") or {}).get("code") or "")
        msg = str(j)[:120].replace("\n", " ")
        print("   ★%-22s HTTP %-5s ｜ %5.2fs ｜ code=%s %s" % (tag, st, dt, code, extra))
        if st != 200 or (code and code not in ("0", "200")):
            print("        %s" % msg)
        rows.append({"tag": tag, "http": st, "code": code, "ok": bool(st == 200 and code in ("0", "200", ""))})

    # ① chat
    st, j, dt = post(base+"/chat/completions", {"model": "qwen-plus", "max_tokens": 8,
        "messages": [{"role": "user", "content": "reply with: OK"}]}, K)
    txt = ""
    try: txt = str(j["choices"][0]["message"]["content"])[:20]
    except Exception: pass
    rec("① chat(qwen-plus)", st, j, dt, "｜" + txt)

    # ② embedding
    st, j, dt = post(base+"/embeddings", {"model": "text-embedding-v4", "input": "夜间游乐场开园"}, K)
    dim = None
    try: dim = len(j["data"][0]["embedding"])
    except Exception: pass
    rec("② embedding(v4)", st, j, dt, "｜维度 %s" % dim)

    # ③ rerank（compatible 与原生）
    st, j, dt = post(base+"/rerank", {"model": "gte-rerank-v2", "query": "总线可否事后补录",
        "documents": ["总线 emit 不可事后补录（行为之历史不可伪造）", "夜间游乐场开园：以首帧为条件之重绘"]}, K)
    rec("③a rerank(compatible)", st, j, dt)
    st, j, dt = post("https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank",
        {"model": "gte-rerank-v2", "input": {"query": "总线可否事后补录",
         "documents": ["总线 emit 不可事后补录", "夜间游乐场开园"]}, "parameters": {"return_documents": False}}, K)
    rec("③b rerank(原生 api/v1)", st, j, dt)

    # ④ 多模态嵌入
    if IMG.exists():
        b64 = base64.b64encode(IMG.read_bytes()).decode()
        st, j, dt = post(base+"/embeddings", {"model": "multimodal-embedding-v1", "input": [
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64[:1500]}}]}, K)
        dim = None
        try: dim = len(j["data"][0]["embedding"])
        except Exception: pass
        rec("④ 多模态嵌入", st, j, dt, "｜维度 %s" % dim)
    else:
        print("   ★④ 跳：图不在 %s" % IMG.name)

    print("   ── 判 ──")
    good = [r["tag"] for r in rows if r["ok"]]
    print("   ★可用：%s" % ("、".join(good) if good else "★皆不可用（如实）"))
    print("   ★受限：%s" % ("、".join(r["tag"] for r in rows if not r["ok"]) or "无"))
    out = pathlib.Path(__file__).resolve().parent.parent/"outbox"/"mem"/("bailian_four_probe_%s.json" % time.strftime("%Y%m%d_%H%M"))
    out.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "base": base, "rows": rows,
        "good": good}, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print("   ⇒ 已写：%s" % out.name)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True); sys.exit(main())
