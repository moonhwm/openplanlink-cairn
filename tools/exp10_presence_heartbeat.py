# -*- coding: utf-8 -*-
"""实验⑩：在场假设 —— 以"心跳轮询"充当在场者，看令是否转 EXECUTED
设计：建世界＋进房（120 s）⇒ 每 3 s 轮询 status（共 ~75 s）⇒ t≈12 s 发一令「dash」
判：①会话是否活过 30 s（先前皆 30 s 收束）②rtcStatus 是否变化 ③userInstructions[].status 是否转 EXECUTED
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
B = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1"
FRAME = SEAT/"exp"/"exp6_persona_firstframe_20261011.jpg"
R = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "exp": "10-presence-heartbeat", "polls": []}


def call(method, path, body=None, to=120):
    r = urllib.request.Request((path if path.startswith("http") else B + path),
                               data=json.dumps(body, ensure_ascii=False).encode() if body else None, method=method)
    r.add_header("Authorization", "Bearer " + K)
    if body: r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=to) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return -1, str(e)[:140]


def od(tx):
    try:
        o = json.loads(tx).get("output") or {}
        return o.get("code"), o.get("message"), (o.get("data") or {})
    except Exception:
        return None, tx[:90], {}


b64 = "data:image/jpeg;base64," + base64.b64encode(FRAME.read_bytes()).decode()
st, tx = call("POST", "/worlds", {"async": True, "perspective": "third_person",
                                 "prompt": "第三人称：夜间游乐场门前，七枚发光节点连成一环，人形分身立于环心。",
                                 "firstFrameImage": {"base64": b64}})
c, m, d = od(tx); wid = d.get("encryptedWorldId")
for i in range(12):
    st, tx = call("GET", "/worlds/build-status?encryptedWorldId=" + str(wid))
    c, m, d = od(tx); s = d.get("status")
    if s in ("ready", "failed"): break
    time.sleep(7)
st, tx = call("POST", "/worlds/get-travel-credential", {"encryptedWorldId": str(wid)})
c, m, d = od(tx); tk = d.get("ticket")
st, tx = call("POST", "/travels/enter-travel", {"ticket": tk, "maxExperienceTimeSec": 120})
c, m, d = od(tx); tid = d.get("encryptedTravelId")
print("  ① 建/进 ⇒ 世界尾=%s 会话尾=%s ｜ 进房 code=%s ｜ noStreamAutoEnd=%s" % (
    str(wid)[-8:], str(tid)[-8:], c, d.get("noStreamAutoEndTimeoutSec")))
t0 = time.time()
sent = False
last = None
while time.time() - t0 < 78:
    el = round(time.time() - t0, 1)
    if (not sent) and el >= 12:
        st, tx = call("POST", "/travels/instruct", {"encryptedTravelId": str(tid), "content": "dash"})
        c2, m2, d2 = od(tx)
        print("  ② t=%5.1fs 发令「dash」⇒ code=%s" % (el, c2))
        R["instruct_code"] = c2; sent = True
    st, tx = call("GET", "/travels/status?encryptedTravelId=" + str(tid))
    c3, m3, d3 = od(tx)
    ui = d3.get("userInstructions") or []
    ustat = [u.get("status") for u in ui if isinstance(u, dict)]
    row = {"t": el, "code": c3, "status": d3.get("status"), "rtc": d3.get("rtcStatus"),
           "ui_status": ustat, "acts": len(d3.get("characterActions") or [])}
    R["polls"].append(row)
    if row["status"] != last or el % 15 < 3:
        print("     t=%5.1fs status=%-9s rtc=%-10s ui=%s acts=%d" % (el, row["status"], row["rtc"], ustat, row["acts"]))
        last = row["status"]
    if d3.get("status") == "completed" and el > 20:
        print("     ⇒ 会话于 t=%.1fs 结束" % el)
        break
    time.sleep(3)
print("\n  ═══ ③ 判 ═══")
alive = max(p["t"] for p in R["polls"])
print("   轮询 %d 次 ｜ 会话存活至 t=%.1f s（先前无在场者时约 30 s 收束）" % (len(R["polls"]), alive))
rtcs = sorted({str(p["rtc"]) for p in R["polls"]})
uis = sorted({str(x) for p in R["polls"] for x in p["ui_status"]})
print("   rtcStatus 取值集合 = %s" % rtcs)
print("   userInstructions.status 取值集合 = %s" % uis)
print("   ⇒ 判：%s" % ("★令已执行（转 EXECUTED）" if any("EXECUTED" in u and "UN" not in u for u in uis)
                    else ("★令仍未执行（UNEXECUTED）" if any("UNEXECUTED" in u for u in uis) else "（尚无令状态）")))
(EX/"exp10_presence_heartbeat_20261011.json").write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("  落盘：exp10_presence_heartbeat_20261011.json")
