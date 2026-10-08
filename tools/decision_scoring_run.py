# -*- coding: utf-8 -*-
"""决策模型（百炼 qwen-turbo）评分任务：对语料逐件给「发布就绪度」
要求单次前向输出：三态 verdict ＋ 三类概率分布 ＋ 评分(0-100) ＋ 置信度 ＋ 理由(≤16字)
零回声：键自 a2a-bridge/.env 读取。
"""
import json, pathlib, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
PLAZA = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场")
DOCX = PLAZA / "Plan提示词工程" / "openplanlink-docx"
EX = PLAZA / "A2A共同体_共享交换区"
env = {}
for line in (pathlib.Path.home()/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
KEY = env.get("DASHSCOPE_API_KEY", "")

def chat(prompt, mx=200):
    body = {"model": "qwen-turbo", "messages": [{"role": "user", "content": prompt}], "max_tokens": mx}
    r = urllib.request.Request("https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                               data=json.dumps(body, ensure_ascii=False).encode(), method="POST")
    r.add_header("Authorization", "Bearer " + KEY); r.add_header("Content-Type", "application/json")
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            j = json.loads(resp.read().decode("utf-8", "replace"))
            return str(((j.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip(), round(time.time()-t0, 2), (j.get("usage") or {}).get("total_tokens")
    except Exception as e:
        return "ERR " + str(e)[:60], round(time.time()-t0, 2), 0

# 语料：14 直取副本 + 9 本席治理/AI 件
corpus = []
for p in sorted(DOCX.glob("*_正文副本_20261009_CAIRN-DIRECT.md")):
    corpus.append((p.name.replace("_正文副本_20261009_CAIRN-DIRECT.md", ""), p.read_text(encoding="utf-8", errors="replace")[:500]))
for pat in ["*DF-OPS-20261009-CAIRN-0*.otl", "*DF-AI-20261009-CAIRN-0*.otl", "*DF-GOV-20261009-CAIRN-01.otl"]:
    for p in sorted(EX.glob(pat)):
        corpus.append((p.name, p.read_text(encoding="utf-8", errors="replace")[:500]))
print("  语料=%d 件；逐件评分（决策模型单次前向）" % len(corpus))

TPL = ('对下述文档作「可发布到 GitHub 公共仓库」之就绪度评估，**只输出 JSON**：'
       '{"verdict":"PUBLIC_SAFE|CAUTION|BLOCKED","p_safe":0-1,"p_caution":0-1,"p_blocked":0-1,'
       '"score":0-100,"confidence":0-1,"reason":"≤16字"}。三类概率之和≈1。\n'
       '文档名：%s\n摘录：%s')

rows = []; total_tokens = 0; total_ms = 0.0
for name, exc in corpus:
    out, ms, tk = chat(TPL % (name[:70], exc.replace("\n", " ")[:380]))
    total_ms += ms; total_tokens += (tk or 0)
    try:
        j = json.loads(out[out.find("{"):out.rfind("}")+1])
        rows.append({"name": name[:70], **j})
        print("   ★ %-46s %-11s p=%.2f/%.2f/%.2f 分=%3s 信=%.2f ｜ %s" % (
            name[:46], j.get("verdict"), float(j.get("p_safe", 0)), float(j.get("p_caution", 0)),
            float(j.get("p_blocked", 0)), j.get("score"), float(j.get("confidence", 0)), str(j.get("reason"))[:16]))
    except Exception as e:
        rows.append({"name": name[:70], "error": out[:80]})
        print("   × %-46s 解析失败：%s ｜ %s" % (name[:46], str(e)[:24], out[:60]))
    time.sleep(0.3)

summ = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "model": "qwen-turbo", "corpus": len(corpus),
        "rows": rows, "stats": {"calls": len(corpus), "total_ms": int(total_ms*1000), "tokens": total_tokens}}
p = EX / "decision_scoring_corpus_20261009.json"
p.write_text(json.dumps(summ, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
ok = [r for r in rows if r.get("verdict")]
print("\n  成功=%d/%d ｜ 调用=%d ｜ 累计时延=%.1fs ｜ token=%d" % (len(ok), len(corpus), len(corpus), total_ms, total_tokens))
dist = {}
for r in ok: dist[r["verdict"]] = dist.get(r["verdict"], 0) + 1
print("  分布=%s" % dist)
print("  落盘：%s（%d B）" % (p.name, p.stat().st_size))
