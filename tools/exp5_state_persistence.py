# -*- coding: utf-8 -*-
"""实验⑤：跨会话状态持久性 —— A1 基线 → B 永久改变 → A2 复验（同一世界）
判：A2 与 A1 显著不同 ⇒ 状态持久（倾向记忆/涌现）；A2≈A1 ⇒ 程序化重置
★ ticket/token 不落盘；每步打印 HTTP／业务码／时延
（引号一律用「」）
"""
import base64, json, pathlib, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
SEAT = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"
EX = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"
TMP = HOME/"AppData"/"Local"/"Temp"/"exp5"; TMP.mkdir(parents=True, exist_ok=True)
env = {}
for line in (HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8-sig", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
K = env.get("DASHSCOPE_API_KEY", "")
BASE = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1"
PROMPT = "第三人称：夜间游乐场的门前，七枚发光节点连成一环，人形分身立于环心，门内是待开的园区。"
FRAME = SEAT/"exp"/"opening_firstframe_16x9_20261011.jpg"
INSTRUCT = "在地上放一块不会消失的石头，位置固定在环心左侧三米处。"
EXP_SEC = 60   # ★实测：45 ⇒ code=400000；60 ⇒ code=0（该参有最小值约束）
R = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "exp": "5-state-persistence", "instruct": INSTRUCT,
     "experience_sec": EXP_SEC, "seat": "a2a-node-local", "steps": []}


def call(method, path, body=None, to=200):
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
        return None, tx[:100], {}


# ① 建世界（标准首帧）
b64 = "data:image/jpeg;base64," + base64.b64encode(FRAME.read_bytes()).decode()
st, tx, dt = call("POST", "/worlds", {"async": True, "perspective": "third_person", "prompt": PROMPT,
                                     "firstFrameImage": {"base64": b64}})
c, m, d = od(tx); WID = d.get("encryptedWorldId") or d.get("worldId")
print("  ① 建世界 ⇒ HTTP %s ｜ code=%s ｜ %.2f s ｜ id=%s" % (st, c, dt, ("…"+str(WID)[-8:]) if WID else "无"))
R["steps"].append({"step": "create", "http": st, "code": c, "sec": dt, "id_tail": str(WID)[-8:] if WID else None})
if not WID: sys.exit(1)
for i in range(12):
    st, tx, dt = call("GET", "/worlds/build-status?encryptedWorldId=" + str(WID))
    c, m, d = od(tx); s = d.get("status") or ""
    if s in ("ready", "failed", "error") or i >= 11: print("  ① ready ⇒ 第%d次 status=%s" % (i+1, s)); break
    time.sleep(8)


def session(tag, instruct=None):
    st, tx, dt = call("POST", "/worlds/get-travel-credential", {"encryptedWorldId": str(WID)})
    c, m, d = od(tx); tk = d.get("ticket")
    if not tk: print("  [%s] 换票失败 code=%s" % (tag, c)); return None
    st2, tx2, dt2 = call("POST", "/travels/enter-travel", {"ticket": tk, "maxExperienceTimeSec": EXP_SEC})
    c2, m2, d2 = od(tx2); tid = d2.get("encryptedTravelId") or d2.get("travelId")
    print("  [%s] 进房 ⇒ code=%s ｜ %.2f s ｜ id=%s" % (tag, c2, dt2, ("…"+str(tid)[-8:]) if tid else "无"))
    R["steps"].append({"step": "enter-" + tag, "http": st2, "code": c2, "sec": dt2, "id_tail": str(tid)[-8:] if tid else None})
    if instruct and tid:
        st3, tx3, dt3 = call("POST", "/travels/instruct", {"encryptedTravelId": str(tid), "content": instruct})
        c3, m3, d3 = od(tx3)
        print("  [%s] 指令 ⇒ code=%s ｜ %.2f s" % (tag, c3, dt3))
        R["steps"].append({"step": "instruct-" + tag, "http": st3, "code": c3, "sec": dt3})
    return tid


T = {}
T["A1"] = session("A1")
print("  …A1 体验 %d s" % EXP_SEC); time.sleep(EXP_SEC + 10)
T["B"] = session("B", INSTRUCT)
print("  …B 体验 %d s" % EXP_SEC); time.sleep(EXP_SEC + 10)
T["A2"] = session("A2")
print("  …A2 体验 %d s" % EXP_SEC); time.sleep(EXP_SEC + 10)

# ② 取产物并下载
VID = {}
for tag, tid in T.items():
    if not tid: continue
    for att in (1, 2, 3):
        st, tx, dt = call("GET", "/travels/artifacts?encryptedTravelId=" + str(tid))
        c, m, d = od(tx)
        v = (d.get("video") or {}).get("original") or {}
        url = v.get("url")
        print("  [%s] artifacts 第%d次 ⇒ code=%s ｜ compose=%s ｜ url=%s" % (
            tag, att, c, d.get("composeStatus"), "有" if url else "无"))
        if url:
            dst = TMP/("exp5_%s.mp4" % tag)
            try:
                req = urllib.request.Request(url); req.add_header("User-Agent", "cairn/1.0")
                with urllib.request.urlopen(req, timeout=300) as resp, open(dst, "wb") as f:
                    n = 0
                    while True:
                        b = resp.read(1 << 20)
                        if not b: break
                        f.write(b); n += len(b)
                VID[tag] = {"file": str(dst), "bytes": n}
                print("      ★已下载 %s：%.2f MB" % (dst.name, n/1048576))
                R["steps"].append({"step": "video-" + tag, "bytes": n, "code": c})
            except Exception as e:
                print("      ✗ 下载失败：%s" % str(e)[:100])
            break
        time.sleep(20)

(EX/"exp5_state_persistence_20261011.json").write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
(EX/"exp5_videos_20261011.json").write_text(json.dumps(VID, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("\n  落盘：exp5_state_persistence_20261011.json ｜ exp5_videos_20261011.json（%d 段）" % len(VID))
