import json, pathlib, sys, urllib.request, urllib.error
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
env = {}
for line in (pathlib.Path.home()/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k,_,v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
K = env.get("DASHSCOPE_API_KEY","")
def call(url, body=None, to=40, key=None):
    r = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode() if body else None, method="POST" if body else "GET")
    r.add_header("Authorization", "Bearer " + (key or K))
    if body: r.add_header("Content-Type","application/json")
    try:
        with urllib.request.urlopen(r, timeout=to) as resp: return resp.status, resp.read().decode("utf-8","replace")[:120]
    except urllib.error.HTTPError as e: return e.code, e.read().decode("utf-8","replace")[:120]
    except Exception as e: return -1, str(e)[:90]
for app, mode in (("happyoyster-1.0-adventure","世界探索"), ("happyoyster-1.0-directing","实时导演"), ("happyoyster-1.0-acting","角色演绎")):
    st, tx = call("https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/%s/openapi/v1/worlds?page=1&pageSize=1&status=ready" % app)
    print("   %s %-22s ⇒ HTTP %-4s ｜ %s" % (mode, app.split("-")[-1], st, ("★门已开！" if st==200 else tx[:70].replace("\n"," "))))
WS = "https://ws-ay6o8osb22o9dc3t.cn-beijing.maas.aliyuncs.com"
for m in ("qwen-plus","qwen3.7-plus","decision-model-preview","qwen3.8-max"):
    st, _ = call(WS + "/compatible-mode/v1/chat/completions", {"model": m, "messages":[{"role":"user","content":"回一字：可"}], "max_tokens": 8})
    print("   模型 %-24s ⇒ HTTP %-4s ｜ %s" % (m, st, {200:"可用", 429:"预算墙", 403:"无资格"}.get(st, str(st))))
k2 = env.get("AI302_API_KEY","")
st, _ = call("https://api.302ai.cn/v1/chat/completions", {"model":"gpt-5","messages":[{"role":"user","content":"回一字：可"}],"max_tokens":4000}, key=k2)
print("   第三通道 302.AI gpt-5 ⇒ HTTP %s" % st)
