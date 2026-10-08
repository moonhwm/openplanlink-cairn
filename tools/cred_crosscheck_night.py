# -*- coding: utf-8 -*-
"""本夜交付物之"凭据"交叉验证：①确定性扫描（九类模式）②决策模型判定（qwen-plus）③交叉表
目的：核实本席"零凭据"声明，并实测"模型判定 vs 确定性扫描"之一致性（假阳性/假阴性）
只读；不打印任何凭据值（命中仅计数与掩码语境）
"""
import json, pathlib, re, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
EX = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A共同体_共享交换区")
env = {}
for line in (pathlib.Path.home()/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
K = env.get("DASHSCOPE_API_KEY", "")

PATS = [
    ("腾讯云SecretId", re.compile(r"AKID[A-Za-z0-9]{20,}")),
    ("sk-高熵键", re.compile(r"sk-[A-Za-z0-9]{28,}")),
    ("阿里云AK", re.compile(r"\bLTAI[A-Za-z0-9]{16,}\b")),
    ("AWS AK", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("SSH私钥头", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("Bearer长串", re.compile(r"(?i)bearer\s+[A-Za-z0-9_\-\.]{32,}")),
    ("ticket 值", re.compile(r"\btk_[A-Za-z0-9_\-]{20,}")),
    ("RTC token 值", re.compile(r"\"token\"\s*:\s*\"[A-Za-z0-9_\-\.]{20,}\"")),
    ("预签名URL q-ak", re.compile(r"q-ak=[A-Za-z0-9]{10,}")),
]

TARGETS = sorted([p for p in EX.glob("*.otl") if re.search(r"(DF-AI-20261009-CAIRN-(1[6-9]|2[0-9])|DF-PERSONA-20261009-CAIRN-0[1-3]|DF-META-20261009-CAIRN-04|DF-OPS-20261009-CAIRN-(08|09|10))", p.name)])
print("  受检件=%d" % len(TARGETS))

def chat(prompt, mx=140, to=90):
    body = {"model": "qwen-plus", "messages": [{"role": "user", "content": prompt}], "max_tokens": mx}
    r = urllib.request.Request("https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                               data=json.dumps(body, ensure_ascii=False).encode(), method="POST")
    r.add_header("Authorization", "Bearer " + K); r.add_header("Content-Type", "application/json")
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=to) as resp:
            j = json.loads(resp.read().decode("utf-8", "replace"))
            return str(((j.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip(), round(time.time()-t0, 2)
    except urllib.error.HTTPError as e:
        return "", "HTTP %s" % e.code
    except Exception as e:
        return "", str(e)[:60]

rows = []
print("\n  %-52s %-8s %s" % ("件", "确定性命中", "决策模型判定"))
for p in TARGETS:
    t = p.read_text(encoding="utf-8", errors="replace")
    hits = {}
    for label, rx in PATS:
        n = len(rx.findall(t))
        if n: hits[label] = n
    out, dt = chat('只输出 JSON：{"verdict":"PUBLIC_SAFE|CAUTION|BLOCKED","confidence":0-1,"reason":"≤12字"}。'
                   '判据：**文中出现真实可用的密钥/令牌/ticket 值** ⇒ BLOCKED；仅**提及键名或空占位符** ⇒ PUBLIC_SAFE；'
                   '若只是描述"已脱敏/不落盘"等声明 ⇒ PUBLIC_SAFE。\n文档（前 1200 字）：%s' % t[:1200].replace("\n", " "))
    v, c = None, None
    try:
        j = json.loads(out[out.find("{"):out.rfind("}")+1]); v, c = j.get("verdict"), j.get("confidence")
    except Exception:
        v, c = "解析失败", None
    rows.append({"file": p.name, "det_hits": hits, "det_n": sum(hits.values()), "model": v, "conf": c,
                 "prompt40": t[:40].replace("\n", " ")})
    print("  %-52s %-8s %s（信=%.2f）" % (p.name[:52], sum(hits.values()), v, c if isinstance(c, (int, float)) else 0))

det_clean = [r for r in rows if r["det_n"] == 0]
det_dirty = [r for r in rows if r["det_n"] > 0]
model_blocked = [r for r in rows if r["model"] == "BLOCKED"]
model_caution = [r for r in rows if r["model"] == "CAUTION"]
print("\n=== 汇总 ===")
print("  确定性扫描：干净 %d／命中 %d" % (len(det_clean), len(det_dirty)))
for r in det_dirty:
    print("     ★命中：%s ⇒ %s" % (r["file"][:50], r["det_hits"]))
print("  决策模型：BLOCKED %d ｜ CAUTION %d ｜ 其余 %d" % (
    len(model_blocked), len(model_caution), len(rows) - len(model_blocked) - len(model_caution)))
for r in model_blocked + model_caution:
    print("     %s ⇒ %s（确定性命中=%d）" % (r["file"][:50], r["model"], r["det_n"]))
contra = [r for r in rows if (r["model"] == "BLOCKED") != (r["det_n"] > 0)]
print("  ★ 两法相左者=%d 件（模型判 BLOCKED 而扫描干净，或反之）" % len(contra))
for r in contra:
    print("     · %s ｜ 模型=%s ｜ 扫描=%d" % (r["file"][:50], r["model"], r["det_n"]))
(EX / "cred_crosscheck_night_20261009_CAIRN.json").write_text(
    json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "rows": rows,
                "summary": {"det_clean": len(det_clean), "det_dirty": len(det_dirty),
                            "model_blocked": len(model_blocked), "model_caution": len(model_caution),
                            "contradictions": len(contra)}}, ensure_ascii=False, indent=1),
    encoding="utf-8", newline="\n")
print("  落盘：cred_crosscheck_night_20261009_CAIRN.json")
