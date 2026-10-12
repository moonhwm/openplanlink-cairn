# -*- coding: utf-8 -*-
"""零输入对照（可复现性检验）：对「另一世界」再跑一次无输入会话 ⇒ 取录像 ⇒ 全帧率亮度/MAD 统计
目的：判 `-37` 之"缓升提亮 +14.3%"是**平台系统性渲染行为**抑或**该世界独有**
零回显：不打印 ticket/token；世界 ID 为标识符（可记）
"""
import json, pathlib, sys, time, urllib.request, urllib.error
from urllib.parse import urlparse

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
SEAT = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"
EX = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"
OUT = EX/"travel_artifacts_20261009_CAIRN_B"
OUT.mkdir(exist_ok=True)
env = {}
for line in (HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
K = env.get("DASHSCOPE_API_KEY", "")
B = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1"

def api(path, body=None, method="POST", to=90):
    r = urllib.request.Request(B + path, data=json.dumps(body, ensure_ascii=False).encode() if body else None, method="POST" if body else "GET")
    r.add_header("Authorization", "Bearer " + K)
    if body: r.add_header("Content-Type", "application/json")
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=to) as resp:
            return resp.status, round(time.time()-t0, 2), json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, round(time.time()-t0, 2), {"err": e.read().decode("utf-8", "replace")[:200]}
    except Exception as e:
        return -1, round(time.time()-t0, 2), {"err": str(e)[:140]}

# 选"数据塔"（上轮分幕链之幕二；非 `-25` 所用之世界）
st, dt, j = api("/worlds?page=1&pageSize=20&status=ready")
items = ((j.get("output") or {}).get("data") or {}).get("items") or []
target = next((i for i in items if i.get("name") == "数据塔"), None)
if not target:
    print("  × 未找到「数据塔」"); sys.exit(1)
WID = target["encryptedWorldId"]
print("  对照世界：「数据塔」%s…（%.2fs）" % (str(WID)[-10:], dt))

st, dt, j = api("/worlds/get-travel-credential", {"encryptedWorldId": WID})
tk = ((j.get("output") or {}).get("data") or {}).get("ticket")
print("  ① 换票 ⇒ HTTP %s ｜ %.2fs ｜ 得票=%s" % (st, dt, bool(tk)))
st, dt, j = api("/travels/enter-travel", {"ticket": tk, "maxExperienceTimeSec": 60})
dd = (j.get("output") or {}).get("data") or {}
TID = dd.get("encryptedTravelId")
print("  ② 进房 ⇒ HTTP %s ｜ %.2fs ｜ TravelId=%s… ｜ rtcConfig=%s" % (st, dt, str(TID)[-8:], bool(dd.get("rtcConfig"))))
print("     ★ 本次不推流、不发指令（零输入）⇒ 依平台 noStreamAutoEndTimeoutSec=30 将在 ~30s 后自动结束")

t0 = time.time(); last = None
while time.time() - t0 < 200:
    time.sleep(12)
    s2, d2, j2 = api("/travels/status?encryptedTravelId=" + TID)
    d2d = (j2.get("output") or {}).get("data") or {}
    last = d2d.get("status")
    print("     [%4.0fs] status=%s ｜ rtcStatus=%s" % (time.time()-t0, last, d2d.get("rtcStatus")))
    if last in ("completed", "failed"): break

s3 = d3 = j3 = None; art = {}; v = {}; url = None
for w in range(12):
    s3, d3, j3 = api("/travels/artifacts?encryptedTravelId=" + TID)
    art = ((j3.get("output") or {}).get("data") or {})
    v = ((art.get("video") or {}).get("original") or {})
    url = v.get("url")
    print("  ③ 产物第 %d 询 ⇒ HTTP %s ｜ original.status=%s ｜ url=%s" % (w+1, s3, v.get("status"), bool(url)))
    if url: break
    time.sleep(10)
if url:
    try:
        with urllib.request.urlopen(url, timeout=120) as resp:
            blob = resp.read()
        p = OUT/"travel_b_video_20261009.mp4"
        p.write_bytes(blob)
        print("  ④ 已下载对照录像：%s（%.1f KB）" % (p.name, len(blob)/1024))
    except Exception as e:
        print("  ④ 下载失败：%s" % str(e)[:120])
(EX/"travel_control_b_20261009_CAIRN.json").write_text(json.dumps(
    {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "seat": "a2a-node-local", "arm": "B（另一世界·零输入）",
     "world": "数据塔", "worldId": WID, "travelId": TID, "final_status": last,
     "note": "可复现性对照：检验提亮是否为平台系统性渲染行为；不落 ticket/token"}, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("  落盘：travel_control_b_20261009_CAIRN.json")
