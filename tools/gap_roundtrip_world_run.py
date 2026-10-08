# -*- coding: utf-8 -*-
"""① 语料扩充后之检索复测（验证"重排低分＝语料缺口"判断是否成立）
   ② 纲要云件往返校验（kdocs 直取 vs 既有副本，检测夜间漂移）
   ③ 世界模型多步交互（世界探索→实时导演→角色演绎→世界探索·第2步）
零回显：键自 a2a-bridge/.env 读取。
"""
import hashlib, json, math, pathlib, subprocess, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
DOCX = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\Plan提示词工程\openplanlink-docx")
EX = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A共同体_共享交换区")
CLI = str(pathlib.Path.home() / ".kimi-work" / "bin" / "kdocs-cli.exe")
env = {}
for line in (pathlib.Path.home()/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
DS = env.get("DASHSCOPE_API_KEY", "")

def post(url, body, timeout=120):
    r = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode(), method="POST")
    r.add_header("Authorization", "Bearer " + DS); r.add_header("Content-Type", "application/json")
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8","replace")), time.time()-t0
    except urllib.error.HTTPError as e:
        return {"_err": "HTTP %s: %s" % (e.code, e.read().decode("utf-8","replace")[:120])}, time.time()-t0
    except Exception as e:
        return {"_err": str(e)[:110]}, time.time()-t0

def embed(texts):
    out = []
    for i in range(0, len(texts), 8):
        j, _ = post("https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding",
                    {"model": "text-embedding-v4", "input": {"texts": texts[i:i+8]}})
        if "_err" in j: return None, j["_err"]
        out += [e["embedding"] for e in j["output"]["embeddings"]]
    return out, None

def rerank(query, docs):
    j, _ = post("https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank",
                {"model": "gte-rerank-v2", "input": {"query": query, "documents": docs}})
    if "_err" in j: return None, j["_err"]
    return [(r["index"], r["relevance_score"]) for r in (j.get("output") or {}).get("results", [])], None

def chat(prompt, mx=200):
    j, _ = post("https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                {"model": "qwen-turbo", "messages": [{"role": "user", "content": prompt}], "max_tokens": mx})
    if "_err" in j: return "ERR " + str(j["_err"])[:80]
    return str(((j.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()

Q2 = "异质模型通路与超算通道之接入要点与实测结论？"
report = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800")}

# ---------- ① 补语料前后复测 ----------
base = []
for p in sorted(DOCX.glob("*_正文副本_20261009_CAIRN-DIRECT.md")):
    base.append((p.name.replace("_正文副本_20261009_CAIRN-DIRECT.md", ""), p.read_text(encoding="utf-8", errors="replace")[:800]))
rr0, e0 = rerank(Q2, [n + "：" + t.replace("\n", " ")[:300] for n, t in base])
s0 = sorted(rr0, key=lambda x: -x[1])[:3] if rr0 else []
print("=== ① 补语料前（14 件）===")
print("   top3：" + " ｜ ".join("%s(%.4f)" % (base[i][0][:26], s) for i, s in s0))

add = []
for pat in ["*DF-OPS-20261009-CAIRN-0*.otl", "*DF-AI-20261009-CAIRN-0*.otl", "*DF-GOV-20261009-CAIRN-01.otl",
            "*DF-NIETZ-20261008-CAIRN-41.otl"]:
    for p in sorted(EX.glob(pat)):
        add.append((p.name, p.read_text(encoding="utf-8", errors="replace")[:800]))
print("   新增语料=%d 件：%s" % (len(add), [n[:26] for n, _ in add]))
allc = base + add
rr1, e1 = rerank(Q2, [n + "：" + t.replace("\n", " ")[:300] for n, t in allc])
s1 = sorted(rr1, key=lambda x: -x[1])[:5] if rr1 else []
print("=== ① 补语料后（%d 件）===" % len(allc))
print("   top5：" + " ｜ ".join("%s(%.4f)" % (allc[i][0][:28], s) for i, s in s1))
if s0 and s1:
    print("   ★ 最高分：补前 %.4f → 补后 %.4f（%s）" % (s0[0][1], s1[0][1], "提升" if s1[0][1] > s0[0][1] else "未提升"))
report["corpus_gap_test"] = {"before": [{"name": base[i][0], "score": round(s, 5)} for i, s in s0],
                             "after": [{"name": allc[i][0], "score": round(s, 5)} for i, s in s1],
                             "added": [n for n, _ in add]}

# ---------- ② 纲要云件往返校验 ----------
print("\n=== ② 纲要云件往返校验（link_id=ci2ybbMcccFi）===")
try:
    r = subprocess.run([CLI, "drive", "read-file", "--args", json.dumps({"link_id": "ci2ybbMcccFi"})],
                       capture_output=True, timeout=120)
    j = json.loads((r.stdout or b"").decode("utf-8", "replace"))
    fresh = ((j.get("data") or {}).get("content") or "")
except Exception as e:
    fresh = ""
    print("   × 直取失败：%s" % str(e)[:80])
prev = DOCX / "OpenPlanLink全局声明与Agent-to-Agent网络建设纲要.otl_正文副本_20261009_CAIRN-DIRECT.md"
if fresh and prev.exists():
    old = prev.read_text(encoding="utf-8", errors="replace")
    def norm(s):
        s = s.split("> 提取席", 1)[-1] if s.startswith(">") else s
        return s.replace("\r\n", "\n").strip()
    def norm(s):
        """归一：丢弃文件头（行首 '>' 之引言块与空行）后，CRLF→LF、首尾去白"""
        lines = s.replace("\r\n", "\n").split("\n")
        i = 0
        while i < len(lines) and (lines[i].startswith(">") or lines[i].strip() == ""):
            i += 1
        return "\n".join(lines[i:]).strip()
    h_new = hashlib.sha3_512(norm(fresh).encode()).hexdigest()[:32]
    h_old = hashlib.sha3_512(norm(old).encode()).hexdigest()[:32]
    print("   新拉字符=%d ｜ 既有字符=%d" % (len(fresh), len(old)))
    print("   新拉 SHA3-512 前32=%s" % h_new)
    print("   既有 SHA3-512 前32=%s" % h_old)
    print("   ★ 判定：%s" % ("一致（夜间无漂移）" if h_new == h_old else "★不一致（云端已变更或提取口径差异）——须核"))
    report["roundtrip"] = {"link_id": "ci2ybbMcccFi", "fresh_chars": len(fresh), "prev_chars": len(old),
                           "fresh_sha3_32": h_new, "prev_sha3_32": h_old, "identical": h_new == h_old}

# ---------- ③ 世界模型多步交互 ----------
print("\n=== ③ 世界模型多步交互（三类模式轮转）===")
STATE = ("已知事实：夜间游乐场已开园；在场＝Cairn 席（本席）与 Moon／Trae 席之近时件；"
         "文档面＝14 桩可本机秒级直取（kdocs link_id 法）、全量目录 25 件；"
         "通道面＝百炼四模块在役、异质四通道（302ai.cn／硅基／华为／超算）全绿；"
         "风险面＝《四件套·中》含腾讯云 Secret ID（待轮换）。")
steps = [
    ("世界探索·第1步", STATE + " 请以探索口吻描述当前态势要害（≤50字）。"),
    ("实时导演", STATE + " 请以导演口吻给出「此刻最该发生的一个动作」（谁做什么，≤50字）。"),
    ("角色演绎", STATE + " 请以「一枚新入库之只读镜片」的角色作一句独白（≤50字）。"),
    ("世界探索·第2步", STATE + " 若上一步之动作已发生，态势有何变化？以探索口吻（≤50字）。"),
]
world = {}
for tag, ask in steps:
    out = chat(ask, 160)
    world[tag] = out
    print("   ★ %-12s ｜ %s" % (tag, out[:110].replace("\n", " ")))
report["world_interaction"] = world

p = EX / "corpus_gap_roundtrip_world_20261009.json"
p.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("\n  落盘：%s（%d B）" % (p.name, p.stat().st_size))
