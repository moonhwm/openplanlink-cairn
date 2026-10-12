# -*- coding: utf-8 -*-
"""本席件库检索入口：建索引（text-embedding-v4；文档表示＝文件名＋正文前 300 字）
并出查询器具 seek.py 可用之索引文件
★ 按第八戒：文档表示须声明；★ 按第九戒：须声明所用模型
（引号一律用「」）
"""
import json, math, pathlib, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
EX = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"
env = {}
for line in (HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
K = env.get("DASHSCOPE_API_KEY", "")
WS = "https://ws-ay6o8osb22o9dc3t.cn-beijing.maas.aliyuncs.com"
MODEL = "text-embedding-v4"

def embed(texts):
    body = {"model": MODEL, "input": {"texts": texts}}
    r = urllib.request.Request(WS + "/compatible-mode/v1/embeddings",
                               data=json.dumps(body, ensure_ascii=False).encode(), method="POST")
    r.add_header("Authorization", "Bearer " + K); r.add_header("Content-Type", "application/json")
    for attempt in (1, 2):
        try:
            with urllib.request.urlopen(r, timeout=90) as resp:
                j = json.loads(resp.read().decode("utf-8", "replace"))
            if "data" in j: return [d["embedding"] for d in j["data"]]      # 兼容模式（OpenAI 风格）
            return [d["embedding"] for d in j["output"]["embeddings"]]  # 原生路径
        except Exception as e:
            if attempt == 2: raise
            time.sleep(4)

def doc_of(p):
    t = p.read_text(encoding="utf-8", errors="replace")
    t = t.split("<!-- SIG-BLOCK")[0]
    t = " ".join(t.split())
    return p.name + " ｜ " + t[:300]

files = [p for p in sorted(EX.glob("*CAIRN*.otl"))]
print("  待索引件数 = %d" % len(files))
items, ok = [], 0
B = 8
for i in range(0, len(files), B):
    chunk = files[i:i+B]
    try:
        vecs = embed([doc_of(p) for p in chunk])
    except Exception as e:
        print("   批 %d 失败：%s" % (i//B, str(e)[:70])); continue
    for p, v in zip(chunk, vecs):
        items.append({"file": p.name, "bytes": p.stat().st_size,
                      "head": doc_of(p)[:120], "vec": [round(x, 6) for x in v]})
        ok += 1
    if (i//B) % 8 == 0: print("   已索引 %d/%d" % (ok, len(files)))
out = EX/"cairn_index_20261009.json"
out.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "seat": "a2a-node-local",
    "model": MODEL, "domain": "专属域", "endpoint": "/compatible-mode/v1/embeddings（响应为 OpenAI 风格 data[]）",
    "doc_repr": "文件名＋正文前 300 字（按第八戒声明）",
    "count": len(items), "dim": len(items[0]["vec"]) if items else 0, "items": items},
    ensure_ascii=False), encoding="utf-8", newline="\n")
print("  ★ 索引：%s（%d 件，dim=%d，%.2f MB）" % (out.name, len(items), len(items[0]["vec"]) if items else 0,
                                              out.stat().st_size/1048576))
