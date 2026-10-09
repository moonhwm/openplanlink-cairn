# -*- coding: utf-8 -*-
"""知识单点依赖盘点：对 14 个关键主题重排，按"首名分／次名分"判"单点承载"抑或"多点承载"
并对单点者核查其在 交换区／正本仓／镜像 三处是否皆有副本（冗余）
（引号一律用「」；零回显）
"""
import json, pathlib, sys, time, urllib.request, urllib.error
from urllib.parse import urlparse

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
BASE = HOME / "WPSDrive" / "29969771" / "WPS云盘" / "月之暗面的Plasma游乐场"
EX = BASE / "A2A共同体_共享交换区"; DOCX = BASE / "Plan提示词工程" / "openplanlink-docx"
CAIRN = HOME / "openplanlink-cairn"; MIRROR = HOME / "openplanlink-mirror"
env = {}
for line in (HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
K = env.get("DASHSCOPE_API_KEY", ""); SF = env.get("SILICONFLOW_API_KEY", "")
H = urlparse(env["DASHSCOPE_WS_BASE"]).hostname

def post(url, key, body, to=120):
    r = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode(), method="POST")
    r.add_header("Authorization", "Bearer " + key); r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=to) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return -1, str(e)[:110]

docs = []
for p in sorted(EX.glob("*CAIRN*.otl")):
    docs.append((p.name, p.read_text(encoding="utf-8", errors="replace")[:700]))
print("  语料 %d 件" % len(docs))

TOPICS = [
    ("噪声地板与信号底之测定口径", "floor"),
    ("提亮是否为管线行为", "bright"),
    ("GOP 关键帧间隔之证据", "gop"),
    ("产物录像是否为首帧条件渲染", "firstframe"),
    ("命名由构图与文案共同决定", "naming"),
    ("refWorldId 是血缘还是继承", "lineage"),
    ("未知路径之兜底 200 响应", "fallback"),
    ("跨会话复现性检验之判据", "repro"),
    ("去趋势后自相关之处置", "detrend"),
    ("功率谱边界峰之辨识", "spectral"),
    ("隔帧现象之空间分布", "zones"),
    ("世界模型访问失效与配额", "quota"),
    ("进房作业包与十拍序列", "entrypack"),
    ("真 3D 双向量产（glTF）", "gltf"),
]
rows = []
for q, key in TOPICS:
    st, tx = post("https://api.siliconflow.cn/v1/rerank", SF,
                  {"model": "BAAI/bge-reranker-v2-m3", "query": q, "documents": [d[1] for d in docs], "top_n": 3})
    res = (json.loads(tx).get("results") or []) if st == 200 else []
    res = sorted(res, key=lambda r: -r["relevance_score"])[:3]
    s1 = res[0]["relevance_score"] if res else 0.0
    s2 = res[1]["relevance_score"] if len(res) > 1 else 0.0
    gap = (s1 / s2) if s2 > 0.001 else float("inf")
    d1 = docs[res[0]["index"]][0] if res else "—"
    kind = "**单点承载**" if (gap > 3 and s1 > 0.5) else ("多点承载" if s1 > 0.3 else "弱承载")
    rows.append({"topic": q, "key": key, "top1": round(s1, 5), "top2": round(s2, 5),
                 "gap": (round(gap, 2) if gap != float("inf") else "∞"), "top1_doc": d1, "kind": kind})
    print("  %-30s ⇒ %-12s ｜ 首=%.5f 次=%.5f ｜ 断层=%-6s ｜ 首名件=%s" % (
        q, kind, s1, s2, (round(gap, 2) if gap != float("inf") else "∞"), d1[:46]))
    time.sleep(0.3)

print("\n  === 单点承载者之三处副本核查 ===")
def has_copy(name):
    n = pathlib.Path(name).stem
    hits = []
    if (EX / name).exists(): hits.append("交换区")
    for root in (CAIRN, MIRROR):
        try:
            if any(p.name.startswith(n[:20]) for p in root.rglob("*.otl")): hits.append(root.name)
        except Exception: pass
    return hits
single = [r for r in rows if r["kind"] == "**单点承载**"]
for r in single:
    h = has_copy(r["top1_doc"])
    print("  %-44s ⇒ 副本：%s %s" % (r["top1_doc"][:44], "、".join(h) if h else "（未在双仓检索到）",
                                   "✓" if len(h) >= 2 else "⚠ 冗余不足"))
print("\n  单点承载主题数 = %d／%d" % (len(single), len(rows)))
p = EX / "knowledge_singlepoint_audit_20261009_CAIRN.json"
p.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "seat": "a2a-node-local",
                         "corpus_n": len(docs), "carrier": "硅基流动 BAAI/bge-reranker-v2-m3",
                         "topics": rows, "single_point_count": len(single)},
                        ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("  落盘：%s（%d B）" % (p.name, p.stat().st_size))
