# -*- coding: utf-8 -*-
"""r6 标准作业（验收实证）：
① 16:9 带标记首帧 ⇒ 建世界（验 firstFrameImage 必需与比例）② ready ⇒ ③ 进房 120 s
④ 保活：每 3 s 轮询 status（验 INIT→STREAMING）⑤ 一令（验"一会话一令"）
⑥ 取产物（重试至 ready）⇒ 下载 ⑦ 报：存活时长／rtcStatus／录像大小（对照 r6 之"大 7 倍"）
（引号一律用「」）
"""
import base64, json, pathlib, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
SEAT = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"
EX = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"
TMP = HOME/"AppData"/"Local"/"Temp"/"r6std"; TMP.mkdir(parents=True, exist_ok=True)
env = {}
for line in (HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8-sig", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
K = env.get("DASHSCOPE_API_KEY", "")
B = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1"
FRAME = SEAT/"exp"/"exp6_persona_firstframe_20261011.jpg"
R = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "op": "r6-standard-operation", "checks": {}}


def call(method, path, body=None, to=150):
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


# ① 口径 1 之反证：不带首帧
st, tx = call("POST", "/worlds", {"async": True, "perspective": "third_person", "prompt": "试。"})
c, m, d = od(tx)
print("  ① 反证（不带首帧）⇒ HTTP %s ｜ code=%s ｜ msg=%s" % (st, c, str(m)[:60]))
R["checks"]["no_firstframe"] = {"http": st, "code": c, "msg": str(m)[:80]}
# ② 正证：16:9 带首帧
b64 = "data:image/jpeg;base64," + base64.b64encode(FRAME.read_bytes()).decode()
st, tx = call("POST", "/worlds", {"async": True, "perspective": "third_person",
                                 "prompt": "第三人称：夜间游乐场门前，七枚发光节点连成一环，人形分身立于环心。",
                                 "firstFrameImage": {"base64": b64}})
c, m, d = od(tx); wid = d.get("encryptedWorldId")
print("  ② 建世界（16:9 带首帧）⇒ code=%s ｜ 世界尾=%s" % (c, str(wid)[-8:]))
for i in range(12):
    st, tx = call("GET", "/worlds/build-status?encryptedWorldId=" + str(wid))
    c2, m2, d2 = od(tx); s = d2.get("status")
    if s in ("ready", "failed"): break
    time.sleep(7)
print("     ready ⇒ %s" % s)
st, tx = call("POST", "/worlds/get-travel-credential", {"encryptedWorldId": str(wid)})
c3, m3, d3 = od(tx); tk = d3.get("ticket")
st, tx = call("POST", "/travels/enter-travel", {"ticket": tk, "maxExperienceTimeSec": 120})
c4, m4, d4 = od(tx); tid = d4.get("encryptedTravelId")
print("  ③ 进房 ⇒ code=%s ｜ 会话尾=%s ｜ noStream=%s" % (c4, str(tid)[-8:], d4.get("noStreamAutoEndTimeoutSec")))
# ④ 保活 + 一令
t0 = time.time(); sent = False; rtcs = []; stat = []
while time.time() - t0 < 110:
    el = round(time.time() - t0, 1)
    if (not sent) and el >= 8:
        st, tx = call("POST", "/travels/instruct", {"encryptedTravelId": str(tid), "content": "dash"})
        c5, m5, d5 = od(tx)
        print("  ④ t=%5.1fs 令「dash」⇒ code=%s" % (el, c5))
        R["checks"]["instruct"] = c5; sent = True
        st, tx = call("POST", "/travels/instruct", {"encryptedTravelId": str(tid), "content": "jump"})
        c6, m6, d6 = od(tx)
        print("     再令「jump」（验会話一令）⇒ code=%s" % c6)
        R["checks"]["second_instruct"] = c6
    st, tx = call("GET", "/travels/status?encryptedTravelId=" + str(tid))
    c7, m7, d7 = od(tx)
    rtcs.append(str(d7.get("rtcStatus"))); stat.append(str(d7.get("status")))
    if d7.get("status") == "completed" and el > 20:
        print("     会话于 t=%.1f s 结束" % el); break
    time.sleep(3)
alive = round(time.time() - t0, 1)
print("  ⑤ 保活结果 ⇒ 存活 %.1f s ｜ rtcStatus 集合=%s ｜ status 集合=%s" % (alive, sorted(set(rtcs)), sorted(set(stat))))
R["checks"]["alive_s"] = alive; R["checks"]["rtc"] = sorted(set(rtcs)); R["checks"]["status"] = sorted(set(stat))
# ⑥ 产物
time.sleep(20)
url = None
for att in range(1, 5):
    st, tx = call("GET", "/travels/artifacts?encryptedTravelId=" + str(tid))
    c8, m8, d8 = od(tx)
    url = ((d8.get("video") or {}).get("original") or {}).get("url")
    print("  ⑥ 产物 第%d次 ⇒ code=%s ｜ compose=%s ｜ url=%s" % (att, c8, d8.get("composeStatus"), "有" if url else "无"))
    R["checks"]["compose_%d" % att] = str(d8.get("composeStatus"))
    if url: break
    time.sleep(20)
if url:
    dst = TMP/"r6std.mp4"
    req = urllib.request.Request(url); req.add_header("User-Agent", "cairn/1.0")
    with urllib.request.urlopen(req, timeout=300) as resp, open(dst, "wb") as f:
        n = 0
        while True:
            b = resp.read(1 << 20)
            if not b: break
            f.write(b); n += len(b)
    print("     ★录像 %.2f MB（r6 记：未保活约 0.83 MB；保活 5.83 MB）" % (n/1048576))
    R["checks"]["video_mb"] = round(n/1048576, 2); R["video"] = str(dst)
(EX/"r6_standard_op_20261011.json").write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("\n  落盘：r6_standard_op_20261011.json")
