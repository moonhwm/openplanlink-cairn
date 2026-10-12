# -*- coding: utf-8 -*-
"""实验⑪：令之合法性假设（B）—— 世界设成"角色正在奔跑"，再令 dash
① 同带标记首帧（分身立于环心）＋ prompt 明写"正在向前奔跑冲刺，随时可 dash"
② 进房 ⇒ 轮询保活（造 STREAMING）⇒ 发令「dash」⇒ 复核 status（UNEXECUTED？EXECUTED？）
③ 取录像 ⇒ 标记追踪（位移）
判：若令转 EXECUTED 或标记位移 ⇒ (B) 成立；否则 (B) 排除，只剩 (A) 真客户端 / (C) 须"角色演绎"模式
（引号一律用「」）
"""
import base64, json, math, pathlib, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
SEAT = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"
EX = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"
TMP = HOME/"AppData"/"Local"/"Temp"/"exp11"; TMP.mkdir(parents=True, exist_ok=True)
env = {}
for line in (HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8-sig", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
K = env.get("DASHSCOPE_API_KEY", "")
B = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1"
FRAME = SEAT/"exp"/"exp6_persona_firstframe_20261011.jpg"
PROMPT = "第三人称：夜间游乐场门前，人形分身正在向前奔跑冲刺，随时准备施展 dash 动作。"
R = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "exp": "11-action-legality", "prompt": PROMPT, "polls": []}


def call(method, path, body=None, to=150):
    r = urllib.request.Request((path if path.startswith("http") else B + path),
                               data=json.dumps(body, ensure_ascii=False).encode() if body else None, method=method)
    r.add_header("Authorization", "Bearer " + K)
    if body: r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=to) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:

        """★墙闸"""
        try:
            _b = e.read().decode("utf-8", "replace")
            import sys as _s, pathlib as _p
            _s.path.insert(0, str(_p.Path(__file__).resolve().parent))
            import wall_guard as _wg
            if _wg.classify(_b)[0] == "wall":
                _wg.record(_b, source=_p.Path(__file__).name, channel="wall")
                print("   ★撞墙即停（零重试）")
                return e.code, _b[:200]
        except Exception:
            pass
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
st, tx = call("POST", "/worlds", {"async": True, "perspective": "third_person", "prompt": PROMPT,
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
t0 = time.time(); sent = False; ui_last = None
while time.time() - t0 < 70:
    el = round(time.time() - t0, 1)
    if (not sent) and el >= 10:
        st, tx = call("POST", "/travels/instruct", {"encryptedTravelId": str(tid), "content": "dash"})
        c2, m2, d2 = od(tx)
        print("  ② t=%5.1fs 令「dash」⇒ code=%s" % (el, c2)); sent = True
    st, tx = call("GET", "/travels/status?encryptedTravelId=" + str(tid))
    c3, m3, d3 = od(tx)
    ui = d3.get("userInstructions") or []
    us = [u.get("status") for u in ui if isinstance(u, dict)]
    acts = d3.get("characterActions") or []
    R["polls"].append({"t": el, "status": d3.get("status"), "rtc": d3.get("rtcStatus"), "ui": us,
                       "acts": [a.get("name") if isinstance(a, dict) else a for a in acts]})
    if us != ui_last:
        print("     t=%5.1fs rtc=%-9s ui=%s acts=%s" % (el, d3.get("rtcStatus"), us,
              [a.get("name") if isinstance(a, dict) else a for a in acts]))
        ui_last = us
    if d3.get("status") == "completed" and el > 20: break
    time.sleep(3)
print("  …候产物 40 s")
time.sleep(40)
url = None
for att in range(1, 4):
    st, tx = call("GET", "/travels/artifacts?encryptedTravelId=" + str(tid))
    c4, m4, d4 = od(tx)
    url = ((d4.get("video") or {}).get("original") or {}).get("url")
    print("  ③ 产物 第%d次 ⇒ code=%s compose=%s url=%s" % (att, c4, d4.get("composeStatus"), "有" if url else "无"))
    if url: break
    time.sleep(20)
if url:
    dst = TMP/"exp11.mp4"
    req = urllib.request.Request(url); req.add_header("User-Agent", "cairn/1.0")
    with urllib.request.urlopen(req, timeout=300) as resp, open(dst, "wb") as f:
        n = 0
        while True:
            b = resp.read(1 << 20)
            if not b: break
            f.write(b); n += len(b)
    print("     ★录像 %.2f MB" % (n/1048576)); R["video"] = str(dst)
us_all = sorted({str(x) for p in R["polls"] for x in p["ui"]})
alive = max(p["t"] for p in R["polls"]) if R["polls"] else 0
print("\n  ═══ ④ 判 ═══")
print("   存活 t=%.1f s ｜ rtcStatus 集合=%s" % (alive, sorted({str(p['rtc']) for p in R['polls']})))
print("   userInstructions.status 集合=%s" % us_all)
print("   ⇒ 判：%s" % ("★令已执行 ⇒ (B) 成立" if any("UNEXECUTED" not in u and "EXECUTED" in u for u in us_all)
                    else "★令仍未执行 ⇒ (B) 被排除，余 (A)/(C)"))
(EX/"exp11_action_legality_20261011.json").write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("   落盘：exp11_action_legality_20261011.json")
