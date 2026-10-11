# -*- coding: utf-8 -*-
"""实验⑨：以世界自有之动作词表（characterActions）下令
① 建世界＋进房 ⇒ 读 status 取 characterActions 之全部项（名与结构）
② 以其中一项之名下令 ⇒ 20 s 后复读 status
③ 判：userInstructions 之 status 是否转为执行态（非 UNE…）／characterActions 是否变化
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
R = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "exp": "9-character-actions"}


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
print("  ① 建/进 ⇒ 世界尾=%s 会话尾=%s ｜ 进房 code=%s" % (str(wid)[-8:], str(tid)[-8:], c))

st, tx = call("GET", "/travels/status?encryptedTravelId=" + str(tid))
c, m, d = od(tx)
acts = d.get("characterActions") or []
print("  ═══ ② characterActions 全表（%d 项）═══" % len(acts))
names = []
for i, a in enumerate(acts):
    if isinstance(a, dict):
        nm = a.get("name") or a.get("actionName") or a.get("type") or list(a.keys())[0]
        names.append(str(nm))
        print("   %d) name=%-18s ｜ 键=%s ｜ 值=%s" % (i+1, nm, list(a.keys())[:8],
              json.dumps({k: v for k, v in list(a.items())[:6]}, ensure_ascii=False)[:200]))
    else:
        names.append(str(a)); print("   %d) %s" % (i+1, str(a)[:150]))
R["actions"] = acts
R["action_names"] = names
print("     status=%s ｜ rtcStatus=%s ｜ userInstructions=%s" % (
    d.get("status"), d.get("rtcStatus"), json.dumps(d.get("userInstructions"), ensure_ascii=False)[:120]))

if names:
    cmd = names[0]
    st, tx = call("POST", "/travels/instruct", {"encryptedTravelId": str(tid), "content": cmd})
    c, m, d2 = od(tx)
    print("  ═══ ③ 以动作名下令 ⇒ code=%s ｜「%s」═══" % (c, cmd))
    R["cmd"] = cmd; R["cmd_code"] = c
    time.sleep(20)
    st, tx = call("GET", "/travels/status?encryptedTravelId=" + str(tid))
    c2, m2, d3 = od(tx)
    ui = d3.get("userInstructions") or []
    acts2 = d3.get("characterActions") or []
    print("  ═══ ④ 20 s 后之 status ═══")
    print("     userInstructions=%s" % json.dumps(ui, ensure_ascii=False)[:320])
    print("     characterActions 项数：%d ⇒ %d ｜ status=%s ｜ rtcStatus=%s" % (
        len(acts), len(acts2), d3.get("status"), d3.get("rtcStatus")))
    ex = False
    for u in ui:
        if isinstance(u, dict) and u.get("startTime"):
            ex = True
    print("\n  ═══ ⑤ 判 ═══")
    print("     令是否带执行时间戳（startTime 非空）⇒ %s" % ("★是 ⇒ 令被执行" if ex else "否 ⇒ 仍未执行"))
    print("     characterActions 是否变化 ⇒ %s" % ("是" if len(acts) != len(acts2) else "否（项数同）"))
    R["after"] = {"userInstructions": ui, "actions_count": len(acts2), "status": d3.get("status")}
(EX/"exp9_character_actions_20261011.json").write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("  落盘：exp9_character_actions_20261011.json")
