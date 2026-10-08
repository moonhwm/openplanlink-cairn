# -*- coding: utf-8 -*-
"""以"业务空间专属域"（自 .env 之 DASHSCOPE_WS_BASE 解出）测三事：
  ① Directing（simple）② Directing（scriptlist）③ Acting ④ 专属 Key 是否另有预算（qwen-plus）
零回显：只报 HTTP 码与响应摘要；不打印键值、不打印 ticket/token
"""
import base64, json, pathlib, sys, time, urllib.request, urllib.error, urllib.parse

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
PNG = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"/"exp"/"persona_luzhibai_world_20261009.png"
env = {}
for line in (HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
from urllib.parse import urlparse
WS_HOST = urlparse(env["DASHSCOPE_WS_BASE"]).hostname
WS_KEY = env.get("DASHSCOPE_WS_KEY", "")
MAIN_KEY = env.get("DASHSCOPE_API_KEY", "")
FF = "data:image/png;base64," + base64.b64encode(PNG.read_bytes()).decode()
print("  专属域 host=%s ｜ 专属键=%s（len=%d）" % (WS_HOST, "有" if WS_KEY else "无", len(WS_KEY)))

def call(url, key, body=None, method="POST", to=60):
    data = json.dumps(body, ensure_ascii=False).encode() if body else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Authorization", "Bearer " + key)
    if body: r.add_header("Content-Type", "application/json")
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=to) as resp:
            return resp.status, round(time.time()-t0, 2), resp.read().decode("utf-8", "replace")[:260]
    except urllib.error.HTTPError as e:
        return e.code, round(time.time()-t0, 2), e.read().decode("utf-8", "replace")[:260]
    except Exception as e:
        return -1, round(time.time()-t0, 2), str(e)[:150]

APP = "https://%s/api/v2/apps/" % WS_HOST
print("\n=== ① 专属域 · Directing（simple）")
st, dt, tx = call(APP + "happyoyster-1.0-directing/openapi/v1/worlds", WS_KEY,
                  {"async": True, "creationModel": "simple", "resolution": "720p",
                   "prompt": "夜间游乐场，第三人称：镜头缓缓穿过文档塔与光带，停在一枚只读镜片前。",
                   "eventStyle": "normal", "layout": "Calm", "narrative": "Calm",
                   "firstFrameImage": {"base64": FF}})
print("   ⇒ HTTP %s ｜ %.2fs ｜ %s" % (st, dt, tx.replace("\n", " ")))

print("=== ② 专属域 · Directing（scriptlist）")
st2, dt2, tx2 = call(APP + "happyoyster-1.0-directing/openapi/v1/worlds", WS_KEY,
                     {"async": True, "creationModel": "scriptlist", "resolution": "720p",
                      "firstFrameImage": {"base64": FF},
                      "scriptList": {"videoTitle": "夜间游乐场巡场", "synopsis": "一枚只读镜片沿光带巡场，记录文档塔与席位印记。",
                                     "language": "zh", "scene": "夜间的开放式游乐场", "style": "Stable", "speed": "Steady",
                                     "subjects": [{"label": "[character_1]", "name": "只读镜片", "type": "narrator", "voice": "冷静平稳"}],
                                     "acts": [{"turn": 1, "content": "镜头掠过成排文档塔，纸页沿光带滑行。",
                                               "cameraType": "Tracking", "shotSize": "Wide", "cut": "long-take"}]}})
print("   ⇒ HTTP %s ｜ %.2fs ｜ %s" % (st2, dt2, tx2.replace("\n", " ")))

print("=== ③ 专属域 · Acting（邀测）")
st3, dt3, tx3 = call(APP + "happyoyster-1.0-acting/openapi/v1/worlds", WS_KEY,
                     {"async": True, "perspective": "third_person", "prompt": "夜间游乐场（模式探测）", "firstFrameImage": {"base64": FF}})
print("   ⇒ HTTP %s ｜ %.2fs ｜ %s" % (st3, dt3, tx3.replace("\n", " ")))

print("=== ④ 专属 Key 是否另有预算（qwen-plus 单次前向）")
st4, dt4, tx4 = call("https://%s/compatible-mode/v1/chat/completions" % WS_HOST, WS_KEY,
                     {"model": "qwen-plus", "messages": [{"role": "user", "content": "只回复：ok"}], "max_tokens": 8})
print("   ⇒ HTTP %s ｜ %.2fs ｜ %s" % (st4, dt4, tx4.replace("\n", " ")[:200]))
print("=== ⑤ 对照：主键于专属域（qwen-plus）")
st5, dt5, tx5 = call("https://%s/compatible-mode/v1/chat/completions" % WS_HOST, MAIN_KEY,
                     {"model": "qwen-plus", "messages": [{"role": "user", "content": "只回复：ok"}], "max_tokens": 8})
print("   ⇒ HTTP %s ｜ %.2fs ｜ %s" % (st5, dt5, tx5.replace("\n", " ")[:200]))
