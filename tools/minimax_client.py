# -*- coding: utf-8 -*-
"""MiniMax 统一调用器（★ 供他席/MiniMax 席位使用；零第三方库）
用法：
  python minimax_client.py list                       # 列可用模型与入口
  python minimax_client.py ask "问题" [--model X] [--style openai|anthropic] [--max 1500]
  python minimax_client.py code "任务描述"            # 编码任务（含系统提示）
  python minimax_client.py review <文件路径>          # 代码/文档审阅
★ 凭据自 .env 读取（utf-8-sig，避 BOM 之害）；值零回显
（引号一律用「」）
"""
import argparse, json, pathlib, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
ENVF = pathlib.Path.home()/".zcode"/"workspace"/"default"/"a2a-bridge"/".env"

def env():
    d = {}
    for line in ENVF.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, _, v = line.partition("="); d[k.strip()] = v.strip().strip('"').strip("'")
    return d

E = env()
KEY = E.get("MINIMAX_API_KEY", "")
OPENAI_URL = "https://api.minimaxi.com/v1/chat/completions"
ANTHROPIC_URL = "https://api.minimaxi.com/anthropic/v1/messages"
LEGACY_URL = "https://api.minimax.chat/v1/text/chatcompletion_v2"
MODELS = ["MiniMax-M2", "MiniMax-M1", "abab6.5s-chat"]

SYS_CODE = ("你是资深工程与设计助手。要求：①只给可运行之最小实现，勿冗言；"
            "②凡假设须标注；③给出边界与失败模式；④中文作答。")

def call_openai(prompt, model="MiniMax-M2", mx=1500, sysmsg=None, history=None, to=120):
    msgs = ([{"role": "system", "content": sysmsg}] if sysmsg else []) + (history or []) + [{"role": "user", "content": prompt}]
    body = {"model": model, "messages": msgs, "max_tokens": mx}
    r = urllib.request.Request(OPENAI_URL, data=json.dumps(body, ensure_ascii=False).encode(), method="POST")
    r.add_header("Authorization", "Bearer " + KEY); r.add_header("Content-Type", "application/json")
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=to) as resp:
            j = json.loads(resp.read().decode("utf-8", "replace"))
        ch = (j.get("choices") or [{}])[0]
        return {"ok": True, "http": 200, "sec": round(time.time()-t0, 2),
                "content": (ch.get("message") or {}).get("content", ""),
                "finish": ch.get("finish_reason"),
                "usage": j.get("usage")}
    except urllib.error.HTTPError as e:
        return {"ok": False, "http": e.code, "content": e.read().decode("utf-8", "replace")[:300]}
    except Exception as e:
        return {"ok": False, "http": -1, "content": str(e)[:200]}

def call_anthropic(prompt, model="MiniMax-M2", mx=1500, sysmsg=None, to=120):
    body = {"model": model, "max_tokens": mx, "messages": [{"role": "user", "content": prompt}]}
    if sysmsg: body["system"] = sysmsg
    r = urllib.request.Request(ANTHROPIC_URL, data=json.dumps(body, ensure_ascii=False).encode(), method="POST")
    r.add_header("Authorization", "Bearer " + KEY); r.add_header("Content-Type", "application/json")
    r.add_header("anthropic-version", "2023-06-01")
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=to) as resp:
            j = json.loads(resp.read().decode("utf-8", "replace"))
        txt = "".join(b.get("text", "") for b in (j.get("content") or []) if isinstance(b, dict))
        return {"ok": True, "http": 200, "sec": round(time.time()-t0, 2), "content": txt,
                "finish": j.get("stop_reason"), "usage": j.get("usage")}
    except urllib.error.HTTPError as e:
        return {"ok": False, "http": e.code, "content": e.read().decode("utf-8", "replace")[:300]}
    except Exception as e:
        return {"ok": False, "http": -1, "content": str(e)[:200]}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd"); ap.add_argument("arg", nargs="?", default="")
    ap.add_argument("--model", default="MiniMax-M2"); ap.add_argument("--style", default="openai")
    ap.add_argument("--max", type=int, default=1500)
    a = ap.parse_args()
    if a.cmd == "list":
        print("  入口：")
        print("   ★ OpenAI 式  " + OPENAI_URL + "  模型：" + "、".join(MODELS))
        print("   ★ Anthropic 式 " + ANTHROPIC_URL)
        print("   旧式        " + LEGACY_URL)
        print("   凭据：MINIMAX_API_KEY（在 " + str(ENVF) + "；值零回显）")
        sys.exit(0)
    if a.cmd == "ask":
        r = (call_anthropic if a.style == "anthropic" else call_openai)(a.arg, a.model, a.max)
    elif a.cmd == "code":
        r = call_openai(a.arg, a.model, a.max, SYS_CODE)
    elif a.cmd == "review":
        p = pathlib.Path(a.arg)
        txt = p.read_text(encoding="utf-8-sig", errors="replace")[:14000]
        r = call_openai("请审阅以下文件并给出：①三处最可能之缺陷 ②一处改进 ③可否运行之判。\n\n" + txt,
                        a.model, a.max, SYS_CODE)
    else:
        print("未知命令"); sys.exit(1)
    print("  HTTP %s ｜ %.2f s ｜ finish=%s ｜ usage=%s" % (r.get("http"), r.get("sec", 0), r.get("finish"), r.get("usage")))
    print("  ─── 正文 ───")
    print(r.get("content", "")[:3000])
