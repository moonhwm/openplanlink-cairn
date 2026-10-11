# -*- coding: utf-8 -*-
"""人设入世实验：把本席 3D 分身放进世界，并令其行动；自录像定量追踪其"标记色"质心
① 合成 16:9 首帧：夜场门前 ＋ 分身（取自本席行走渲染之单格）＋ 躯干专属标记色（品红）
② 建世界 → ready → 换票 → 进房 → 下指令（令分身行走并抬手）→ 候产物 → 取录像
③ 抽帧：检测标记色之像素数与其质心轨迹（有位移 ⇒ 它确实在世界里动）
★ ticket/token 不落盘；每步打印 HTTP／业务码／时延
（引号一律用「」）
"""
import base64, json, math, pathlib, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
SEAT = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"
EX = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"
TMP = HOME/"AppData"/"Local"/"Temp"/"exp6"; TMP.mkdir(parents=True, exist_ok=True)
env = {}
for line in (HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8-sig", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
K = env.get("DASHSCOPE_API_KEY", "")
B = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1"
INSTRUCT = "让环心的人形分身先向左行走三步，然后举起左手并原地转身面向镜头。"
R = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "exp": "6-persona-in-world", "instruct": INSTRUCT, "steps": []}

# ── ① 首帧：分身 ＋ 标记色 ──
from PIL import Image, ImageDraw, ImageFilter
import numpy as np
W, H = 1280, 720
im = Image.new("RGB", (W, H), (7, 8, 12)); d = ImageDraw.Draw(im)
for y in range(H):
    t = y/H
    d.line([(0, y), (W, y)], fill=(int(7+18*t), int(8+20*t), int(12+26*t)))
d.rectangle([W//2-150, 200, W//2+150, 560], outline=(150, 140, 120), width=3)
d.rectangle([W//2-140, 210, W//2+140, 560], fill=(14, 16, 22))
cx, cy, rx, ry = W//2, 620, 430, 78
for i in range(7):
    a = -math.pi/2 + i*2*math.pi/7
    x, y = cx + rx*math.cos(a), cy + ry*math.sin(a)
    for r, col in ((16, (36, 30, 16)), (9, (120, 96, 40)), (4, (238, 206, 130))):
        d.ellipse([x-r, y-r*0.72, x+r, y+r*0.72], fill=col)
# 分身（取本席行走渲染之单格）
sheet = Image.open(SEAT/"exp"/"CAIRN_avatar_walk_v6b_fixed_14frames_20261009.png").convert("RGB")
cell = sheet.crop((0, 0, 380, 305)).resize((200, 160), Image.LANCZOS)
px = cell.load()
for j in range(cell.height):
    for i in range(cell.width):
        r, g, b = px[i, j]
        px[i, j] = (0, 0, 0) if r+g+b <= 120 else (min(255, int(r*1.15)), min(255, int(g*1.12)), min(255, int(b*1.05)))
ax, ay = cx-100, cy-165
im.paste(cell, (ax, ay), cell.convert("L").point(lambda v: 255 if v > 45 else 0))
# ★躯干标记色（品红）：画在分身中段，便于事后在录像里追踪
d.rectangle([ax+86, ay+72, ax+114, ay+100], fill=(255, 0, 200))
im = im.filter(ImageFilter.GaussianBlur(0.4))
first = SEAT/"exp"/"exp6_persona_firstframe_20261011.jpg"
im.save(first, "JPEG", quality=72, optimize=True)
arr = np.asarray(im.convert("RGB"), dtype=int)
mk = (np.abs(arr[:, :, 0]-255) < 60) & (arr[:, :, 1] < 70) & (np.abs(arr[:, :, 2]-200) < 70)
print("  ① 首帧：%s（%.1f KB）｜★标记色像素 %d ｜ 标记质心 (%.1f, %.1f)" % (
    first.name, first.stat().st_size/1024, mk.sum(), np.argwhere(mk)[:, 1].mean(), np.argwhere(mk)[:, 0].mean()))
R["firstframe"] = {"file": first.name, "marker_px": int(mk.sum()),
                   "marker_centroid": [round(float(np.argwhere(mk)[:, 1].mean()), 1), round(float(np.argwhere(mk)[:, 0].mean()), 1)]}
b64 = "data:image/jpeg;base64," + base64.b64encode(first.read_bytes()).decode()


def call(method, path, body=None, to=200):
    r = urllib.request.Request((path if path.startswith("http") else B + path),
                               data=json.dumps(body, ensure_ascii=False).encode() if body else None, method=method)
    r.add_header("Authorization", "Bearer " + K)
    if body: r.add_header("Content-Type", "application/json")
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=to) as resp:
            return resp.status, resp.read().decode("utf-8", "replace"), round(time.time()-t0, 2)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), round(time.time()-t0, 2)
    except Exception as e:
        return -1, str(e)[:150], round(time.time()-t0, 2)


def od(tx):
    try:
        o = json.loads(tx).get("output") or {}
        return o.get("code"), o.get("message"), (o.get("data") or {})
    except Exception:
        return None, tx[:100], {}


st, tx, dt = call("POST", "/worlds", {"async": True, "perspective": "third_person",
                                      "prompt": "第三人称：夜间游乐场门前，七枚发光节点连成一环，人形分身立于环心。",
                                      "firstFrameImage": {"base64": b64}})
c, m, d = od(tx); wid = d.get("encryptedWorldId")
print("  ② 建世界 ⇒ HTTP %s ｜ code=%s ｜ %.2f s ｜ 尾=%s" % (st, c, dt, str(wid)[-8:]))
for i in range(12):
    st, tx, dt = call("GET", "/worlds/build-status?encryptedWorldId=" + str(wid))
    c, m, d = od(tx); s = d.get("status")
    if s in ("ready", "failed"): break
    time.sleep(7)
print("     ready ⇒ status=%s" % s)
st, tx, dt = call("POST", "/worlds/get-travel-credential", {"encryptedWorldId": str(wid)})
c, m, d = od(tx); tk = d.get("ticket")
st, tx, dt = call("POST", "/travels/enter-travel", {"ticket": tk, "maxExperienceTimeSec": 120})
c, m, d = od(tx); tid = d.get("encryptedTravelId")
R["steps"].append({"step": "enter", "code": c, "sec": dt, "travel": str(tid), "world": str(wid)})
print("  ③ 进房 ⇒ code=%s ｜ %.2f s ｜ 尾=%s" % (c, dt, str(tid)[-8:]))
st, tx, dt = call("POST", "/travels/instruct", {"encryptedTravelId": str(tid), "content": INSTRUCT})
c, m, d = od(tx)
print("  ④ 指令 ⇒ code=%s ｜ %.2f s ｜「%s」" % (c, dt, INSTRUCT))
R["steps"].append({"step": "instruct", "code": c, "sec": dt})
print("  …候产物（无流 30 s 自动收束 ⇒ 候 45 s）")
time.sleep(45)
url = None
for att in range(1, 5):                      # ★重试取产物
    st, tx, dt = call("GET", "/travels/artifacts?encryptedTravelId=" + str(tid))
    c, m, d = od(tx)
    url = ((d.get("video") or {}).get("original") or {}).get("url")
    print("  ⑤ 产物 第%d次 ⇒ HTTP %s ｜ code=%s ｜ compose=%s ｜ url=%s" % (att, st, c, d.get("composeStatus"), "有" if url else "无"))
    R["steps"].append({"step": "artifacts-%d" % att, "http": st, "code": c, "has_url": bool(url),
                       "compose": d.get("composeStatus")})
    if url: break
    time.sleep(20)
if url:
    dst = TMP/"exp6.mp4"
    req = urllib.request.Request(url); req.add_header("User-Agent", "cairn/1.0")
    with urllib.request.urlopen(req, timeout=300) as resp, open(dst, "wb") as f:
        n = 0
        while True:
            b = resp.read(1 << 20)
            if not b: break
            f.write(b); n += len(b)
    print("     ★录像 %s：%.2f MB" % (dst.name, n/1048576))
    R["video"] = {"file": str(dst), "bytes": n}
(EX/"exp6_persona_in_world_20261011.json").write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("\n  落盘：exp6_persona_in_world_20261011.json")
