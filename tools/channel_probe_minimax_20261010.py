import json, pathlib, sys, urllib.request, urllib.error
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
env = {}
for line in (pathlib.Path.home()/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k,_,v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
MK = env.get("MINIMAX_API_KEY","")
def probe(url, model, style, to=45):
    if style == "openai":
        body = {"model": model, "messages":[{"role":"user","content":"回一字：可"}], "max_tokens": 16}
    elif style == "anthropic":
        body = {"model": model, "messages":[{"role":"user","content":"回一字：可"}], "max_tokens": 16}
    else:
        body = {"model": model, "messages":[{"role":"user","content":"回一字：可"}], "max_tokens": 16}
    r = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST")
    r.add_header("Authorization", "Bearer " + MK); r.add_header("Content-Type","application/json")
    if style == "anthropic": r.add_header("anthropic-version","2023-06-01"); r.add_header("x-api-key", MK)
    try:
        with urllib.request.urlopen(r, timeout=to) as resp:
            tx = resp.read().decode("utf-8","replace")
            return resp.status, tx[:200].replace("\n"," ")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8","replace")[:200].replace("\n"," ")
    except Exception as e:
        return -1, str(e)[:120]
print("  === ① MiniMax 端点勘察（先定位正确入口）===")
tries = [
  ("https://api.minimaxi.com/v1/chat/completions", "MiniMax-M2", "openai"),
  ("https://api.minimaxi.com/v1/chat/completions", "MiniMax-M1", "openai"),
  ("https://api.minimaxi.com/v1/chat/completions", "abab6.5s-chat", "openai"),
  ("https://api.minimax.chat/v1/text/chatcompletion_v2", "abab6.5s-chat", "openai"),
  ("https://api.minimaxi.com/v1/text/chatcompletion_v2", "abab6.5s-chat", "openai"),
  ("https://api.minimax.io/v1/chat/completions", "MiniMax-M2", "openai"),
  ("https://api.minimaxi.com/anthropic/v1/messages", "MiniMax-M2", "anthropic"),
]
for url, model, style in tries:
    st, tx = probe(url, model, style)
    host = url.split("/")[2]; path = "/" + "/".join(url.split("/")[3:])
    print("   %-22s %-16s %-9s ⇒ %-5s ｜ %s" % (host, model, style, st, tx[:96]))
print("\n  === ② 门径复探（10-10 新日）===")
K = env.get("DASHSCOPE_API_KEY","")
def call(url, body=None, to=40, key=None):
    r = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode() if body else None, method="POST" if body else "GET")
    r.add_header("Authorization","Bearer " + (key or K))
    if body: r.add_header("Content-Type","application/json")
    try:
        with urllib.request.urlopen(r, timeout=to) as resp: return resp.status, resp.read().decode("utf-8","replace")[:110]
    except urllib.error.HTTPError as e: return e.code, e.read().decode("utf-8","replace")[:110]
    except Exception as e: return -1, str(e)[:90]
for app, mode in (("happyoyster-1.0-adventure","世界探索"), ("happyoyster-1.0-directing","实时导演"), ("happyoyster-1.0-acting","角色演绎")):
    st, tx = call("https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/%s/openapi/v1/worlds?page=1&pageSize=1&status=ready" % app)
    print("   %s ⇒ HTTP %-4s ｜ %s" % (mode, st, ("★门已开！" if st==200 else tx[:70])))
WS = "https://ws-ay6o8osb22o9dc3t.cn-beijing.maas.aliyuncs.com"
for m in ("qwen-plus","qwen3.7-plus","decision-model-preview","qwen3.8-max","text-embedding-v4"):
    if m.startswith("text-"):
        st, _ = call(WS + "/compatible-mode/v1/embeddings", {"model": m, "input": "试"})
    else:
        st, _ = call(WS + "/compatible-mode/v1/chat/completions", {"model": m, "messages":[{"role":"user","content":"回一字：可"}], "max_tokens": 8})
    print("   模型 %-24s ⇒ HTTP %-4s ｜ %s" % (m, st, {200:"可用",429:"预算墙",403:"无资格"}.get(st,str(st))))
