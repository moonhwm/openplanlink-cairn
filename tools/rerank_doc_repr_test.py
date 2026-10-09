# -*- coding: utf-8 -*-
"""第八戒之验证：重排之"文档表示"效应
对照：A 组＝仅文件名；B 组＝文件名＋正文前 400 字
四查询：三旧＋一曾未命中者（资格墙）
（引号一律用「」）
"""
import json, pathlib, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
EX = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"
env = {}
for line in (HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
SF = env.get("SILICONFLOW_API_KEY", "")

def post(url, key, body, to=120):
    r = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode(), method="POST")
    r.add_header("Authorization", "Bearer " + key); r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=to) as resp: return resp.status, json.loads(resp.read().decode("utf-8","replace"))
    except urllib.error.HTTPError as e: return e.code, {"err": e.read().decode("utf-8","replace")[:160]}
    except Exception as e: return -1, {"err": str(e)[:120]}

files = sorted(EX.glob("*CAIRN*.otl"), key=lambda p: p.stat().st_mtime, reverse=True)[:60]
names = [p.name for p in files]
bodies = []
for p in files:
    t = p.read_text(encoding="utf-8", errors="replace")
    # 去签名块，取前 400 字之有效正文
    t = t.split("<!-- SIG-BLOCK")[0]
    t = " ".join(t.split())
    bodies.append((p.name + " ｜ " + t[:400]))

QUERIES = [
    ("命名由构图还是文案决定", "-58", ["-58", "-59"]),
    ("refWorldId 是否继承内容", "-60", ["-60", "-61"]),
    ("未知道路兜底 200", "-64", ["-64"]),
    ("世界模型资格墙与解耦问法", "-71", ["-71"]),
]
print("  === 第八戒验证：A 组（仅文件名）vs B 组（文件名＋正文前 400 字）===")
res = []
for q, want, alts in QUERIES:
    row = {"query": q, "expect": want}
    for tag, docs in (("A_filename", names), ("B_name_plus_body", bodies)):
        st, j = post("https://api.siliconflow.cn/v1/rerank", SF,
                     {"model": "BAAI/bge-reranker-v2-m3", "query": q, "documents": docs, "top_n": 3})
        if st == 200 and j.get("results"):
            top = [(round(r["relevance_score"], 5), docs[r["index"]].split(" ｜ ")[0]) for r in j["results"][:3]]
            hit = any(want in t[1] for t in top)
            row[tag] = {"top3": top, "hit": hit}
        else:
            row[tag] = {"error": str(j)[:120]}
    a = row.get("A_filename", {}); b = row.get("B_name_plus_body", {})
    print("\n  「%s」（期望 %s）" % (q, want))
    print("     A 仅文件名 ：%s ⇒ 命中=%s" % (" ｜ ".join("%.5f %s" % t for t in a.get("top3", [])) or a.get("error"), a.get("hit")))
    print("     B 名＋正文 ：%s ⇒ 命中=%s" % (" ｜ ".join("%.5f %s" % t for t in b.get("top3", [])) or b.get("error"), b.get("hit")))
    print("     ⇒ 首名分数 %s → %s" % (a.get("top3", [[None]])[0][0], b.get("top3", [[None]])[0][0]))
    res.append(row)

out = EX/"rerank_doc_repr_test_20261009_CAIRN.json"
out.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "seat": "a2a-node-local",
    "purpose": "第八戒之验证：重排之文档表示（文件名 vs 名＋正文）", "rows": res},
    ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("\n  落盘：%s" % out.name)
