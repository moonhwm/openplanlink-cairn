# -*- coding: utf-8 -*-
"""渲染层可复现性检验：对「极简检验室」第二次零输入会话 ⇒ 取录像 ⇒ RunStats ⇒ 比第一次之 T=2 隔帧结构
判：若复现 ⇒ 倾向渲染器固有节律；若不复现 ⇒ 会话随机
（引号一律用「」；零回显）
"""
import json, pathlib, sys, time, urllib.request, urllib.error
from urllib.parse import urlparse

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
SEAT = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"
EX = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"
OUT = EX/"travel_artifacts_mark2_20261009_CAIRN"; OUT.mkdir(exist_ok=True)
env = {}
for line in (HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
K = env.get("DASHSCOPE_API_KEY", "")
B = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1"

def api(path, body=None, to=90):
    r = urllib.request.Request(B + path, data=json.dumps(body, ensure_ascii=False).encode() if body else None,
                               method="POST" if body else "GET")
    r.add_header("Authorization", "Bearer " + K)
    if body: r.add_header("Content-Type", "application/json")
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=to) as resp:
            return resp.status, round(time.time()-t0, 2), json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, round(time.time()-t0, 2), {"err": e.read().decode("utf-8", "replace")[:180]}
    except Exception as e:
        return -1, round(time.time()-t0, 2), {"err": str(e)[:130]}

st, dt, j = api("/worlds?page=1&pageSize=20&status=ready")
items = ((j.get("output") or {}).get("data") or {}).get("items") or []
tgt = next((i for i in items if i.get("name") == "极简检验室"), None)
if not tgt:
    print("  × 未找到「极简检验室」"); sys.exit(1)
WID = tgt["encryptedWorldId"]
print("  同一世界：「极简检验室」%s…" % str(WID)[-10:])
st, dt, j = api("/worlds/get-travel-credential", {"encryptedWorldId": WID})
tk = ((j.get("output") or {}).get("data") or {}).get("ticket")
st, dt, j = api("/travels/enter-travel", {"ticket": tk, "maxExperienceTimeSec": 60})
TID = ((j.get("output") or {}).get("data") or {}).get("encryptedTravelId")
print("  第二次进房 ⇒ HTTP %s ｜ TravelId=%s（零输入）" % (st, TID))
t0 = time.time(); last = None
while time.time() - t0 < 200:
    time.sleep(10)
    s2, d2, j2 = api("/travels/status?encryptedTravelId=" + TID)
    last = ((j2.get("output") or {}).get("data") or {}).get("status")
    if last in ("completed", "failed"): break
print("  终态=%s（%.0fs）" % (last, time.time()-t0))
url = None
for i in range(12):
    s3, d3, j3 = api("/travels/artifacts?encryptedTravelId=" + TID)
    v = (((j3.get("output") or {}).get("data") or {}).get("video") or {}).get("original") or {}
    url = v.get("url")
    print("  产物第 %d 询 ⇒ %s" % (i+1, "ready" if url else v.get("status")))
    if url: break
    time.sleep(10)
if url:
    with urllib.request.urlopen(url, timeout=150) as resp:
        blob = resp.read()
    (OUT/"mark2_video_20261009.mp4").write_bytes(blob)
    print("  已下载：%.1f KB" % (len(blob)/1024))
(EX/"mark2_experiment_20261009_CAIRN.json").write_text(json.dumps(
    {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "seat": "a2a-node-local", "world": "极简检验室",
     "worldId": WID, "travelId": TID, "final": last, "purpose": "渲染层可复现性检验（第二次零输入会话）",
     "note": "不落 ticket/token"}, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("  落盘：mark2_experiment_20261009_CAIRN.json")
