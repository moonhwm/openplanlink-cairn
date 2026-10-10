# -*- coding: utf-8 -*-
"""开园实证 v2：合成 16:9 首帧（夜门＋七点环＋分身剪影）⇒ 建世界 → ready → 换票 → 进房 → 指令 → 取物
★ 打印完整业务消息（不再截断）；ticket/token 不落盘
（引号一律用「」）
"""
import base64, json, pathlib, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
SEAT = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"
EX = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"
env = {}
for line in (HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8-sig", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
K = env.get("DASHSCOPE_API_KEY", "")
BASE = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1"

# ── ① 合成 16:9 首帧 ──
from PIL import Image, ImageDraw, ImageFilter
W, H = 1280, 720
im = Image.new("RGB", (W, H), (7, 8, 12)); d = ImageDraw.Draw(im)
# 夜天穹（上暗下微亮）
for y in range(H):
    t = y/H
    d.line([(0, y), (W, y)], fill=(int(7+18*t), int(8+20*t), int(12+26*t)))
# 门（中央偏后）
d.rectangle([W//2-150, 210, W//2+150, 560], outline=(150, 140, 120), width=3)
d.rectangle([W//2-140, 220, W//2+140, 560], fill=(14, 16, 22))
# 门内微光
for i in range(40):
    a = i/40
    d.rectangle([W//2-140+i, 220+i//3, W//2+140-i, 560-i//3], outline=(int(30+40*a), int(34+44*a), int(46+54*a)))
# 七点环（地面）
import math
cx, cy, rx, ry = W//2, 620, 430, 78
for i in range(7):
    a = -math.pi/2 + i*2*math.pi/7
    x, y = cx + rx*math.cos(a), cy + ry*math.sin(a)
    for r, col in ((16, (36, 30, 16)), (9, (120, 96, 40)), (4, (238, 206, 130))):
        d.ellipse([x-r, y-r*0.72, x+r, y+r*0.72], fill=col)
    d.line([(x, y+12), (x, cy+ry+8)], fill=(60, 52, 30), width=2)
# 分身剪影（取自本席行走帧之单格，贴于环心）
try:
    sheet = Image.open(SEAT/"exp"/"CAIRN_avatar_walk_v6b_fixed_14frames_20261009.png").convert("RGB")
    cell = sheet.crop((0, 0, 380, 305)).resize((190, 152), Image.LANCZOS)
    px = cell.load()
    for j in range(cell.height):
        for i in range(cell.width):
            r, g, b = px[i, j]
            if r+g+b > 120:      # 人形为亮色
                px[i, j] = (min(255, int(r*1.15)), min(255, int(g*1.12)), min(255, int(b*1.05)))
            else:
                px[i, j] = (0, 0, 0)
    mask = cell.convert("L").point(lambda v: 255 if v > 45 else 0)
    im.paste(cell, (cx-95, cy-138), mask)
except Exception as e:
    print("   分身贴图失败（不碍）：%s" % str(e)[:60])
im = im.filter(ImageFilter.GaussianBlur(0.4))
first = SEAT/"exp"/"opening_firstframe_16x9_20261011.jpg"
im.save(first, "JPEG", quality=70, optimize=True)
print("  ① 首帧：%s ｜ %d×%d ｜ %.1f KB ｜ 比例 %.3f" % (first.name, W, H, first.stat().st_size/1024, W/H))
b64 = "data:image/jpeg;base64," + base64.b64encode(first.read_bytes()).decode()
R = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "seat": "a2a-node-local",
     "firstframe": {"file": first.name, "w": W, "h": H, "bytes": first.stat().st_size}, "steps": []}


def call(method, path, body=None, to=150):
    url = path if path.startswith("http") else BASE + path
    r = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode() if body else None, method=method)
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
        j = json.loads(tx); o = j.get("output") or {}
        return o.get("code"), o.get("message"), (o.get("data") or {})
    except Exception:
        return None, tx[:200], {}


PROMPT = "第三人称：夜间游乐场的门前，七枚发光节点连成一环，人形分身立于环心，门内是待开的园区。"
print("\n  ② 建世界…")
st, tx, dt = call("POST", "/worlds", {"async": True, "perspective": "third_person", "prompt": PROMPT, "firstFrameImage": {"base64": b64}})
code, msg, data = od(tx)
wid = data.get("encryptedWorldId") or data.get("worldId")
print("     HTTP %s ｜ %.2f s ｜ code=%s ｜ msg=%s" % (st, dt, code, msg))
print("     worldId=%s" % (("…"+str(wid)[-10:]) if wid else "无"))
R["steps"].append({"step": "create", "http": st, "code": code, "msg": str(msg)[:200], "sec": dt, "worldId_tail": str(wid)[-10:] if wid else None})
if not wid:
    p = EX/"opening_proof_20261011.json"; p.write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print("\n  ⇒ 创建未成；已落盘 " + p.name + "（如实记）"); sys.exit(0)

print("\n  ③ 构建状态…")
for i in range(8):
    st2, tx2, dt2 = call("GET", "/worlds/build-status?encryptedWorldId=" + str(wid))
    c2, m2, d2 = od(tx2)
    stat = d2.get("status") or d2.get("buildStatus") or ""
    print("     第%d次 ⇒ HTTP %s ｜ %.2f s ｜ status=%s ｜ %s" % (i+1, st2, dt2, stat, str(m2)[:40]))
    R["steps"].append({"step": "build-%d" % (i+1), "http": st2, "status": stat, "sec": dt2})
    if stat in ("ready", "failed", "error"): break
    time.sleep(10)

print("\n  ④ 换票…")
st3, tx3, dt3 = call("POST", "/worlds/get-travel-credential", {"encryptedWorldId": str(wid)})
c3, m3, d3 = od(tx3); tk = d3.get("ticket")
print("     HTTP %s ｜ %.2f s ｜ code=%s ｜ ticket=%s（值不落盘）" % (st3, dt3, c3, "已取得" if tk else "未含"))
R["steps"].append({"step": "ticket", "http": st3, "code": c3, "has_ticket": bool(tk), "sec": dt3})
if tk:
    print("\n  ⑤ 进房…")
    st4, tx4, dt4 = call("POST", "/travels/enter-travel", {"ticket": tk, "maxExperienceTimeSec": 120})
    c4, m4, d4 = od(tx4); tid = d4.get("encryptedTravelId") or d4.get("travelId")
    print("     HTTP %s ｜ %.2f s ｜ code=%s ｜ travelId=%s" % (st4, dt4, c4, ("…"+str(tid)[-10:]) if tid else "无"))
    R["steps"].append({"step": "enter", "http": st4, "code": c4, "sec": dt4, "travelId_tail": str(tid)[-10:] if tid else None})
    if tid:
        print("\n  ⑥ 指令…")
        st5, tx5, dt5 = call("POST", "/travels/instruct", {"encryptedTravelId": str(tid), "content": "在环心处点亮第八枚光点，并让分身面向园区之门。"})
        c5, m5, d5 = od(tx5)
        print("     HTTP %s ｜ %.2f s ｜ code=%s ｜ %s" % (st5, dt5, c5, str(m5)[:60]))
        R["steps"].append({"step": "instruct", "http": st5, "code": c5, "sec": dt5})
        print("\n  ⑦ 状态／产物…")
        for label, path in (("status", "/travels/status?encryptedTravelId="), ("artifacts", "/travels/artifacts?encryptedTravelId=")):
            stx, txx, dtx = call("GET", path + str(tid))
            cx, mx, dx = od(txx)
            print("     %s ⇒ HTTP %s ｜ %.2f s ｜ code=%s ｜ keys=%s ｜ %s" % (label, stx, dtx, cx, list(dx)[:8], json.dumps(dx, ensure_ascii=False)[:220]))
            R["steps"].append({"step": label, "http": stx, "code": cx, "keys": list(dx)[:8], "brief": json.dumps(dx, ensure_ascii=False)[:400]})

p = EX/"opening_proof_20261011.json"
p.write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("\n  落盘：" + p.name)
