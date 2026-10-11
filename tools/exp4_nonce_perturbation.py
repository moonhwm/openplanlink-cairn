# -*- coding: utf-8 -*-
"""实验④：首帧微扰（nonce）—— 同 prompt，两世界之差仅在首帧
A：原合成首帧　B：同帧＋确定性 nonce（LCG 32×32 高对比块，右下角）
流程：建两世界 → 各自 ready → 换票 → 进房（同 maxExperienceTimeSec，零指令）→ 候产物 → 取 artifacts
★ ticket/token 不落盘；每步打印 HTTP／业务码／时延
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
PROMPT = "第三人称：夜间游乐场的门前，七枚发光节点连成一环，人形分身立于环心，门内是待开的园区。"
R = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "exp": "4-nonce-perturbation", "seat": "a2a-node-local", "steps": []}

# ── ① 两帧 ──
from PIL import Image, ImageDraw
base = SEAT/"exp"/"opening_firstframe_16x9_20261011.jpg"
im0 = Image.open(base).convert("RGB")
pert = SEAT/"exp"/"exp4_firstframe_nonce_20261011.jpg"
im1 = im0.copy(); d = ImageDraw.Draw(im1)
x0, y0, v = im0.width-56, im0.height-56, 20261011      # 确定性 LCG
white = 0
for i in range(8):
    for k in range(8):
        v = (v*1103515245 + 12345) & 0x7FFFFFFF
        if (v >> 16) & 1:
            d.rectangle([x0+i*4, y0+k*4, x0+i*4+3, y0+k*4+3], fill=(255, 255, 255)); white += 1
im1.save(pert, "JPEG", quality=70, optimize=True)
import numpy as np
a = np.asarray(Image.open(base).convert("L"), dtype=int); b = np.asarray(Image.open(pert).convert("L"), dtype=int)
diff = (a != b).sum()
print("  ① 首帧：原 %s（%.1f KB）｜微扰 %s（%.1f KB）" % (base.name, base.stat().st_size/1024, pert.name, pert.stat().st_size/1024))
print("     ★微扰：%d 像素（%.4f%%）｜白格 %d｜位置 右下 (%d,%d) 起 32×32" % (diff, 100*diff/a.size, white, x0, y0))
R["perturbation"] = {"pixels_changed": int(diff), "pct": round(100*diff/a.size, 4), "white_cells": white, "anchor": [x0, y0]}
B64 = {"A": "data:image/jpeg;base64," + base64.b64encode(base.read_bytes()).decode(),
       "B": "data:image/jpeg;base64," + base64.b64encode(pert.read_bytes()).decode()}


def call(method, path, body=None, to=180):
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
        return None, tx[:120], {}


# ── ② 建两世界 ──
W = {}
for tag in ("A", "B"):
    st, tx, dt = call("POST", "/worlds", {"async": True, "perspective": "third_person", "prompt": PROMPT,
                                         "firstFrameImage": {"base64": B64[tag]}})
    c, m, d = od(tx); wid = d.get("encryptedWorldId") or d.get("worldId")
    W[tag] = wid
    print("  ② 建世界[%s] ⇒ HTTP %s ｜ code=%s ｜ %.2f s ｜ id=%s" % (tag, st, c, dt, ("…"+str(wid)[-8:]) if wid else "无"))
    R["steps"].append({"step": "create-" + tag, "http": st, "code": c, "sec": dt, "id_tail": str(wid)[-8:] if wid else None})

# ── ③ 各大 ready ──
for tag in ("A", "B"):
    if not W.get(tag): continue
    for i in range(12):
        st, tx, dt = call("GET", "/worlds/build-status?encryptedWorldId=" + str(W[tag]))
        c, m, d = od(tx); s = d.get("status") or d.get("buildStatus") or ""
        if i % 3 == 0 or s in ("ready", "failed"): print("  ③ [%s] 第%d次 ⇒ %s ｜ status=%s" % (tag, i+1, st, s))
        if s in ("ready", "failed", "error"): break
        time.sleep(8)
    R["steps"].append({"step": "ready-" + tag, "status": s})

# ── ④ 换票＋进房（零指令；同体验时长）──
T = {}
for tag in ("A", "B"):
    if not W.get(tag): continue
    st, tx, dt = call("POST", "/worlds/get-travel-credential", {"encryptedWorldId": str(W[tag])})
    c, m, d = od(tx); tk = d.get("ticket")
    print("  ④ [%s] 换票 ⇒ HTTP %s ｜ code=%s ｜ ticket=%s" % (tag, st, c, "已得" if tk else "未含"))
    if not tk: continue
    st2, tx2, dt2 = call("POST", "/travels/enter-travel", {"ticket": tk, "maxExperienceTimeSec": 60})
    c2, m2, d2 = od(tx2); tid = d2.get("encryptedTravelId") or d2.get("travelId")
    T[tag] = tid
    print("  ④ [%s] 进房 ⇒ HTTP %s ｜ code=%s ｜ %.2f s ｜ travelId=%s" % (tag, st2, c2, dt2, ("…"+str(tid)[-8:]) if tid else "无"))
    R["steps"].append({"step": "enter-" + tag, "http": st2, "code": c2, "sec": dt2, "id_tail": str(tid)[-8:] if tid else None})

# ── ⑤ 候产物（体验时长 60 s；先候 70 s 再取）──
print("  ⑤ 候产物（70 s，两会话皆然）…")
time.sleep(70)
for tag in ("A", "B"):
    if not T.get(tag): continue
    for attempt in (1, 2, 3):
        st, tx, dt = call("GET", "/travels/artifacts?encryptedTravelId=" + str(T[tag]))
        c, m, d = od(tx)
        print("  ⑤ [%s] artifacts 第%d次 ⇒ HTTP %s ｜ code=%s ｜ keys=%s" % (tag, attempt, st, c, list(d)[:6]))
        R["steps"].append({"step": "artifacts-%s-%d" % (tag, attempt), "http": st, "code": c, "keys": list(d)[:8],
                           "brief": json.dumps(d, ensure_ascii=False)[:400]})
        if c == 0 and d: break
        time.sleep(20)

p = EX/"exp4_nonce_perturbation_20261011.json"
p.write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("\n  落盘：" + p.name)
