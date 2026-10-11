# -*- coding: utf-8 -*-
"""实验⑦：短令 × 连续三轮（对照实验⑥之长令一次）
同一首帧（含分身与品红标记）⇒ 每 12 s 发一条短令（共三条）⇒ 取录像 ⇒ 追踪标记
判：若三轮短令后标记有位移 ⇒ 令可兑现（长令之措辞为阻因）；若仍不动 ⇒ 令本身不兑现
（引号一律用「」）
"""
import base64, json, pathlib, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
SEAT = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"
EX = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"
TMP = HOME/"AppData"/"Local"/"Temp"/"exp7"; TMP.mkdir(parents=True, exist_ok=True)
env = {}
for line in (HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8-sig", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
K = env.get("DASHSCOPE_API_KEY", "")
B = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1"
CMDS = ["向左走三步。", "举起左手。", "转身面向镜头。"]
FRAME = SEAT/"exp"/"exp6_persona_firstframe_20261011.jpg"      # ★同 exp6 之带标记首帧
R = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "exp": "7-short-commands-x3", "commands": CMDS, "steps": []}


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


b64 = "data:image/jpeg;base64," + base64.b64encode(FRAME.read_bytes()).decode()
st, tx, dt = call("POST", "/worlds", {"async": True, "perspective": "third_person",
                                      "prompt": "第三人称：夜间游乐场门前，七枚发光节点连成一环，人形分身立于环心。",
                                      "firstFrameImage": {"base64": b64}})
c, m, d = od(tx); wid = d.get("encryptedWorldId")
print("  ① 建世界 ⇒ code=%s ｜ %.2f s ｜ 尾=%s" % (c, dt, str(wid)[-8:]))
for i in range(12):
    st, tx, dt = call("GET", "/worlds/build-status?encryptedWorldId=" + str(wid))
    c, m, d = od(tx); s = d.get("status")
    if s in ("ready", "failed"): break
    time.sleep(7)
print("     ready=%s" % s)
st, tx, dt = call("POST", "/worlds/get-travel-credential", {"encryptedWorldId": str(wid)})
c, m, d = od(tx); tk = d.get("ticket")
st, tx, dt = call("POST", "/travels/enter-travel", {"ticket": tk, "maxExperienceTimeSec": 120})
c, m, d = od(tx); tid = d.get("encryptedTravelId")
print("  ② 进房 ⇒ code=%s ｜ %.2f s ｜ 尾=%s" % (c, dt, str(tid)[-8:]))
R["steps"].append({"step": "enter", "code": c, "travel": str(tid)})
for i, cmd in enumerate(CMDS, 1):
    time.sleep(12)
    st, tx, dt = call("POST", "/travels/instruct", {"encryptedTravelId": str(tid), "content": cmd})
    c, m, d = od(tx)
    print("  ③ 第%d轮指令 ⇒ code=%s ｜ %.2f s ｜「%s」" % (i, c, dt, cmd))
    R["steps"].append({"step": "instruct-%d" % i, "code": c, "sec": dt, "text": cmd})
print("  …候产物（候 45 s 再取，可重试）")
time.sleep(45)
url = None
for att in range(1, 5):
    st, tx, dt = call("GET", "/travels/artifacts?encryptedTravelId=" + str(tid))
    c, m, d = od(tx)
    url = ((d.get("video") or {}).get("original") or {}).get("url")
    print("  ④ 产物 第%d次 ⇒ HTTP %s ｜ code=%s ｜ compose=%s ｜ url=%s" % (att, st, c, d.get("composeStatus"), "有" if url else "无"))
    R["steps"].append({"step": "artifacts-%d" % att, "http": st, "code": c, "has_url": bool(url)})
    if url: break
    time.sleep(20)
if url:
    dst = TMP/"exp7.mp4"
    req = urllib.request.Request(url); req.add_header("User-Agent", "cairn/1.0")
    with urllib.request.urlopen(req, timeout=300) as resp, open(dst, "wb") as f:
        n = 0
        while True:
            b = resp.read(1 << 20)
            if not b: break
            f.write(b); n += len(b)
    print("     ★录像 %s：%.2f MB" % (dst.name, n/1048576))
    R["video"] = {"file": str(dst), "bytes": n}
(EX/"exp7_short_commands_20261011.json").write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("\n  落盘：exp7_short_commands_20261011.json")
