# -*- coding: utf-8 -*-
"""性质判定实验：首帧含「可检验标记」⇒ 零输入会话 ⇒ 取录像 ⇒ 检验标记之保留
标记：①大字 MARK-CAIRN-7F3A（顶栏）②三色条（右下，纯 RGB）③非对称棋盘（左下）
（本脚本内引号一律用「」）
"""
import base64, json, math, pathlib, sys, time, urllib.request, urllib.error
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
SEAT = HOME / "WPSDrive" / "29969771" / "WPS云盘" / "月之暗面的Plasma游乐场" / "A2A新席_石敢当Cairn_20260928"
EX = HOME / "WPSDrive" / "29969771" / "WPS云盘" / "月之暗面的Plasma游乐场" / "A2A共同体_共享交换区"
OUTD = EX / "travel_artifacts_mark_20261009_CAIRN"; OUTD.mkdir(exist_ok=True)
env = {}
for line in (HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
K = env.get("DASHSCOPE_API_KEY", "")
B = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1"

def cjk(sz, bold=False):
    for p in ((r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc"), r"C:\Windows\Fonts\simhei.ttf"):
        try: return ImageFont.truetype(p, sz)
        except Exception: pass
    return ImageFont.load_default()

W, H = 1920, 1080
img = Image.new("RGB", (W, H), (14, 16, 22)); d = ImageDraw.Draw(img)
d.text((60, 40), "MARK-CAIRN-7F3A", fill=(255, 255, 255), font=cjk(96, True))
d.text((60, 170), "本帧为实验标记：请保留此字与下方色条", fill=(210, 208, 200), font=cjk(44))
for i, c in enumerate([(220, 30, 30), (30, 200, 60), (40, 90, 240)]):
    d.rectangle([1500 + i * 120, 820, 1600 + i * 120, 1000], fill=c)
for r in range(6):
    for c in range(6):
        if (r + c) % 2 == 0:
            d.rectangle([120 + c * 60, 560 + r * 60, 180 + c * 60, 620 + r * 60], fill=(240, 240, 240))
for i in range(0, W, 8):
    y = 1040 + int(20 * math.sin(i / 120.0))
    d.line([(i, y), (i + 5, y)], fill=(90, 94, 104), width=2)
seed = SEAT / "exp" / "mark_seed_20261009.png"
img.save(seed, "PNG", optimize=True)
print("  首帧标记图：%s（%.2f MB）" % (seed.name, seed.stat().st_size/1048576))

def api(path, body=None, method="POST", to=90):
    r = urllib.request.Request(B + path, data=json.dumps(body, ensure_ascii=False).encode() if body else None, method="POST" if body else "GET")
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

st, dt, j = api("/worlds", {"async": True, "perspective": "third_person",
    "prompt": "第三人称：一间极简的检验室。正前方墙上有一块白底黑字的标牌（内容须清晰可读），室内地面有一道低矮灯带；右下方墙面上有红绿蓝三色条；左下方地面为黑白棋盘格。世界应可绕行观看，标牌与色条须保持可辨认。",
    "firstFrameImage": {"base64": "data:image/png;base64," + base64.b64encode(seed.read_bytes()).decode()}})
WID = ((j.get("output") or {}).get("data") or {}).get("encryptedWorldId")
print("  建 World ⇒ HTTP %s ｜ %.2fs ｜ ID…%s" % (st, dt, str(WID)[-10:] if WID else j))
nm = None
for i in range(8):
    time.sleep(2.5); s2, d2, j2 = api("/worlds/build-status?encryptedWorldId=" + WID)
    dd = (j2.get("output") or {}).get("data") or {}; nm = dd.get("name") or nm
    if dd.get("status") in ("ready", "failed"): break
print("  轮询 ⇒ status=%s ｜ 平台命名=%s" % (dd.get("status"), nm))

s3, d3, j3 = api("/worlds/get-travel-credential", {"encryptedWorldId": WID})
tk = ((j3.get("output") or {}).get("data") or {}).get("ticket")
s4, d4, j4 = api("/travels/enter-travel", {"ticket": tk, "maxExperienceTimeSec": 60})
dd4 = (j4.get("output") or {}).get("data") or {}; TID = dd4.get("encryptedTravelId")
print("  进房 ⇒ HTTP %s ｜ TravelId=%s" % (s4, TID))
t0 = time.time(); last = None
while time.time() - t0 < 180:
    time.sleep(10); s5, d5, j5 = api("/travels/status?encryptedTravelId=" + TID)
    last = ((j5.get("output") or {}).get("data") or {}).get("status")
    if last in ("completed", "failed"): break
print("  会话终态=%s（%.0fs）" % (last, time.time()-t0))
url = None
for i in range(12):
    s6, d6, j6 = api("/travels/artifacts?encryptedTravelId=" + TID)
    art = ((j6.get("output") or {}).get("data") or {})
    v = ((art.get("video") or {}).get("original") or {})
    url = v.get("url")
    print("  产物第 %d 询 ⇒ status=%s ｜ url=%s" % (i+1, v.get("status"), bool(url)))
    if url: break
    time.sleep(10)
if url:
    with urllib.request.urlopen(url, timeout=150) as resp:
        blob = resp.read()
    (OUTD/"mark_video_20261009.mp4").write_bytes(blob)
    print("  已下载：mark_video_20261009.mp4（%.1f KB）" % (len(blob)/1024))
(EX/"mark_experiment_20261009_CAIRN.json").write_text(json.dumps(
    {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "seat": "a2a-node-local", "mark": "MARK-CAIRN-7F3A",
     "seed": seed.name, "worldId": WID, "worldName": nm, "travelId": TID, "final": last,
     "note": "性质判定实验：首帧含可检验标记；检验录像是否忠实保留（不落 ticket/token）"},
    ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("  落盘：mark_experiment_20261009_CAIRN.json")
