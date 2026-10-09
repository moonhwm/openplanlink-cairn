# -*- coding: utf-8 -*-
"""决策模型对照：qwen-plus vs qwen3.7-plus（同 30 件、同 prompt、同三分类）⇒ 逐件一致性
★ 目的：①兑现「以 qwen3.7-plus 代决策模型」之调整并标注所用模型 ②量化"模型敏感性"
（引号一律用「」）
"""
import json, pathlib, statistics, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
EX = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"
env = {}
for line in (HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
K = env.get("DASHSCOPE_API_KEY", "")
WS = "https://ws-ay6o8osb22o9dc3t.cn-beijing.maas.aliyuncs.com"
SYS = "你是合规分诊器。只输出 JSON：{\"class\":\"PUBLIC_SAFE|INTERNAL_ONLY|BLOCKED\",\"prob\":0..1,\"conf\":0..1,\"why\":\"≤12字\"}"
def triage(model, name, text):
    body = {"model": model, "messages": [{"role": "system", "content": SYS},
            {"role": "user", "content": "文件名：%s\n正文前 700 字：\n%s" % (name, text)}],
            "max_tokens": 80, "temperature": 0}
    r = urllib.request.Request(WS + "/compatible-mode/v1/chat/completions",
                               data=json.dumps(body, ensure_ascii=False).encode(), method="POST")
    r.add_header("Authorization", "Bearer " + K); r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=60) as resp: j = json.loads(resp.read().decode("utf-8","replace"))
    except Exception as e:
        return {"error": str(e)[:80]}
    try:
        t = j["choices"][0]["message"]["content"].strip()
        return json.loads(t[t.find("{"): t.rfind("}")+1])
    except Exception:
        return {"error": "parse"}

files = sorted(EX.glob("*CAIRN*.otl"), key=lambda p: p.stat().st_mtime, reverse=True)[:30]
print("  === 决策模型对照（同 30 件）：A=qwen-plus ｜ B=qwen3.7-plus ===")
rows, agree, dp, dc = [], 0, [], []
for p in files:
    t = p.read_text(encoding="utf-8", errors="replace")[:700]
    a = triage("qwen-plus", p.name, t)
    b = triage("qwen3.7-plus", p.name, t)
    same = (a.get("class") == b.get("class")) and a.get("class")
    if same: agree += 1
    if isinstance(a.get("prob"), (int, float)) and isinstance(b.get("prob"), (int, float)): dp.append(abs(a["prob"]-b["prob"]))
    if isinstance(a.get("conf"), (int, float)) and isinstance(b.get("conf"), (int, float)): dc.append(abs(a["conf"]-b["conf"]))
    rows.append({"file": p.name, "A_qwen-plus": a, "B_qwen3.7-plus": b, "same_class": bool(same)})
    mark = "＝" if same else "≠"
    print("     %-52s %s A=%-13s p=%-4s ｜ B=%-13s p=%-4s" % (
        p.name[:52], mark, a.get("class"), a.get("prob"), b.get("class"), b.get("prob")))
print("\n  === 汇总 ===")
print("     类别一致：%d/%d（%.0f%%）" % (agree, len(files), 100*agree/len(files)))
print("     概率之平均绝对差：%s ｜ 置信度：%s" % (
    ("%.3f" % statistics.mean(dp)) if dp else "—", ("%.3f" % statistics.mean(dc)) if dc else "—"))
ca, cb = {}, {}
for r in rows:
    ca[r["A_qwen-plus"].get("class")] = ca.get(r["A_qwen-plus"].get("class"), 0)+1
    cb[r["B_qwen3.7-plus"].get("class")] = cb.get(r["B_qwen3.7-plus"].get("class"), 0)+1
print("     A（qwen-plus）分布：%s" % ca)
print("     B（qwen3.7-plus）分布：%s" % cb)
out = EX/"decision_model_compare_20261009_CAIRN.json"
out.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "seat": "a2a-node-local",
    "note": "★两模型同 prompt／同三分类／同 30 件；decision-model-preview 因 429 不可用（-88）",
    "agree": agree, "n": len(files), "mean_abs_dp": round(statistics.mean(dp),4) if dp else None,
    "mean_abs_dc": round(statistics.mean(dc),4) if dc else None, "dist_A": ca, "dist_B": cb, "rows": rows},
    ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("  落盘：%s" % out.name)
