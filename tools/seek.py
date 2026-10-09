# -*- coding: utf-8 -*-
"""本席件库检索入口（seek）—— 自助即取即用
用法：python seek.py "查询文字" [topN]
★ 按第八戒：文档表示＝文件名＋正文前 300 字；★ 按第九戒：声明所用模型与端点
（引号一律用「」）
"""
import json, pathlib, sys, urllib.request

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
EX = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"
IDX = EX/"cairn_index_20261009.json"
env = {}
for line in (HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
K = env.get("DASHSCOPE_API_KEY", "")
WS = "https://ws-ay6o8sobx.cn-beijing.maas.aliyuncs.com" if False else "https://ws-ay6o8osb22o9dc3t.cn-beijing.maas.aliyuncs.com"
MODEL = "text-embedding-v4"

def embed_one(text):
    body = {"model": MODEL, "input": text}
    r = urllib.request.Request(WS + "/compatible-mode/v1/embeddings",
                               data=json.dumps(body, ensure_ascii=False).encode(), method="POST")
    r.add_header("Authorization", "Bearer " + K); r.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(r, timeout=60) as resp:
        j = json.loads(resp.read().decode("utf-8", "replace"))
    return j["data"][0]["embedding"] if "data" in j else j["output"]["embeddings"][0]["embedding"]

def cos(a, b):
    s = sum(x*y for x, y in zip(a, b))
    na = sum(x*x for x in a) ** 0.5; nb = sum(x*x for x in b) ** 0.5
    return s/(na*nb) if na and nb else 0.0

def seek(q, topn=8):
    idx = json.loads(IDX.read_text(encoding="utf-8"))
    qv = embed_one(q)
    scored = sorted(((cos(qv, it["vec"]), it) for it in idx["items"]), key=lambda t: -t[0])
    print("  查询：%s" % q)
    print("  索引：%s ｜ %d 件 ｜ 模型 %s ｜ 文档表示：%s" % (IDX.name, idx["count"], idx["model"], idx["doc_repr"]))
    for i, (s, it) in enumerate(scored[:topn], 1):
        print("   %2d. %.4f ｜ %s" % (i, s, it["file"]))
    return [(round(s, 4), it["file"]) for s, it in scored[:topn]]

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python seek.py \"查询文字\" [topN]"); sys.exit(1)
    seek(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 8)
