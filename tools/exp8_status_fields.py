# -*- coding: utf-8 -*-
"""实验⑧：令之去向 —— 读 GET /travels/status 之 userInstructions／chapters／characterActions
设计：同一带标记首帧 → 建世界 → 进房 → 发一条短令（「向左走三步。」）→ 15 s 后读 status
判：(a) 令改潜状态不改画面 ⇒ 字段异动但画面不动；(b) 令仅入日志 ⇒ userInstructions 含令文；
    (c) 须 RTC 在场 ⇒ 三字段皆空
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
CMD = "向左走三步。"
FRAME = SEAT/"exp"/"exp6_persona_firstframe_20261011.jpg"
R = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "exp": "8-status-fields", "cmd": CMD, "steps": []}


def call(method, path, body=None, to=200):
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
        return -1, str(e)[:150]


def od(tx):
    try:
        o = json.loads(tx).get("output") or {}
        return o.get("code"), o.get("message"), (o.get("data") or {})
    except Exception:
        return None, tx[:100], {}


def brief(v, depth=0):
    if isinstance(v, dict):
        return {k: brief(vv, depth+1) for k, vv in list(v.items())[:12]}
    if isinstance(v, list):
        return ["(%d) %s" % (len(v), brief(v[0], depth+1) if v else "空")]
    if isinstance(v, str):
        return v[:160] + ("…" if len(v) > 160 else "")
    return v


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
print("  ① 建/进 ⇒ 世界尾=%s 会话尾=%s ｜ 进房 code=%s" % (str(wid)[-8:], str(tid)[-8:], c))

print("  ═══ ② 发令前之 status（基线）═══")
st, tx = call("GET", "/travels/status?encryptedTravelId=" + str(tid))
c, m, d = od(tx)
print("     HTTP %s ｜ code=%s ｜ 键=%s" % (st, c, list(d.keys())))
base = {"status": d.get("status"), "mode": d.get("mode"), "rtcStatus": d.get("rtcStatus"),
        "userInstructions": brief(d.get("userInstructions")), "chapters": brief(d.get("chapters")),
        "characterActions": brief(d.get("characterActions"))}
print("     userInstructions=%s" % json.dumps(base["userInstructions"], ensure_ascii=False)[:200])
print("     chapters=%s" % json.dumps(base["chapters"], ensure_ascii=False)[:200])
print("     characterActions=%s" % json.dumps(base["characterActions"], ensure_ascii=False)[:200])
print("     status=%s ｜ rtcStatus=%s" % (base["status"], base["rtcStatus"]))
R["baseline"] = base

st, tx = call("POST", "/travels/instruct", {"encryptedTravelId": str(tid), "content": CMD})
c, m, d = od(tx)
print("  ═══ ③ 发令 ⇒ code=%s ｜「%s」═══" % (c, CMD))
R["instruct_code"] = c
time.sleep(15)
st, tx = call("GET", "/travels/status?encryptedTravelId=" + str(tid))
c, m, d = od(tx)
after = {"status": d.get("status"), "mode": d.get("mode"), "rtcStatus": d.get("rtcStatus"),
         "userInstructions": brief(d.get("userInstructions")), "chapters": brief(d.get("chapters")),
         "characterActions": brief(d.get("characterActions"))}
print("  ═══ ④ 发令后之 status（15 s）═══")
print("     userInstructions=%s" % json.dumps(after["userInstructions"], ensure_ascii=False)[:300])
print("     chapters=%s" % json.dumps(after["chapters"], ensure_ascii=False)[:300])
print("     characterActions=%s" % json.dumps(after["characterActions"], ensure_ascii=False)[:300])
print("     status=%s ｜ rtcStatus=%s" % (after["status"], after["rtcStatus"]))
R["after"] = after
# 判据
uj = json.dumps(after["userInstructions"], ensure_ascii=False)
hit = any(k in uj for k in CMD[:-1]) or ("向左" in uj)
print("\n  ═══ ⑤ 判 ═══")
print("     令文是否出现在 userInstructions ⇒ %s" % ("★是" if hit else "否"))
print("     三字段是否为空 ⇒ userInstructions %s ｜ chapters %s ｜ characterActions %s" % (
    "空" if not after["userInstructions"] else "非空",
    "空" if not after["chapters"] else "非空",
    "空" if not after["characterActions"] else "非空"))
(EX/"exp8_status_fields_20261011.json").write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("  落盘：exp8_status_fields_20261011.json")
