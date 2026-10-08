# -*- coding: utf-8 -*-
"""**亲验一次服务端进房**（v5「数据虚空」first_person）——取 RTC 配置、状态序列、动作池、产物
流程：换票 → enter-travel(60s) → 轮询 travels/status ×3 → 待无推流自终(30s) → 再查状态 → 查产物
纪律：①ticket 不落盘、不打印 ②RTC token 不打印（只报字段是否存在）③如实登记此为一"最小进房"
"""
import json, pathlib, sys, time, urllib.request, urllib.error, urllib.parse

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
WID_V5 = "8rcpnKlw6xp3FtpLvZIGB9mlTipFohD7syfWSOD-bt7vYWx9jdVEIlPMdelwsS6b"
BASE = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1"
env = {}
for line in (HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
K = env.get("DASHSCOPE_API_KEY", "")

def call(url, body=None, method="GET", to=60):
    data = json.dumps(body, ensure_ascii=False).encode() if body else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Authorization", "Bearer " + K)
    if body: r.add_header("Content-Type", "application/json")
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=to) as resp:
            return resp.status, round(time.time()-t0, 2), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, round(time.time()-t0, 2), e.read().decode("utf-8", "replace")[:300]
    except Exception as e:
        return -1, round(time.time()-t0, 2), str(e)[:160]

def data_of(txt):
    try:
        return (json.loads(txt).get("output") or {}).get("data") or {}
    except Exception:
        return {}

# ① 换票（主 Key）
st, dt, txt = call(BASE + "/worlds/get-travel-credential", {"encryptedWorldId": WID_V5}, "POST")
d = data_of(txt)
ticket = d.get("ticket") or ""
print("① 换票 ⇒ HTTP %s ｜ %.2fs ｜ code=%s ｜ ticket=%s（前缀 %s／长 %d／expiresIn=%s）" % (
    st, dt, (json.loads(txt).get("output") or {}).get("code") if st == 200 else "?", "★有" if ticket else "无",
    ticket[:3], len(ticket), d.get("expiresIn")))
if not ticket:
    print("   票未取到，终止。原始：%s" % txt[:200]); sys.exit(1)

# ② 进房
st, dt, txt = call(BASE + "/travels/enter-travel", {"ticket": ticket, "maxExperienceTimeSec": 60}, "POST")
d = data_of(txt)
tid = d.get("encryptedTravelId") or ""
rtc = d.get("rtcConfig") or {}
print("② 进房 ⇒ HTTP %s ｜ %.2fs ｜ code=%s ｜ TravelId=%s ｜ version=%s" % (
    st, dt, (json.loads(txt).get("output") or {}).get("code") if st == 200 else "?",
    (str(tid)[:22] + "…") if tid else "无", d.get("version")))
print("   rtcConfig：%s ｜ 字段=%s" % ("★有" if rtc else "null",
      sorted(rtc.keys()) if isinstance(rtc, dict) and rtc else "—"))
for kk in ("noStreamAutoEndTimeoutSec", "maxExperienceTimeSec"):
    if kk in d: print("   %s=%s" % (kk, d.get(kk)))
if not tid:
    print("   未取到 TravelId，终止。原始：%s" % txt[:200]); sys.exit(1)

# ③ 轮询状态 ×3（间隔 5s）
for i in range(3):
    time.sleep(5)
    s, dd, t = call(BASE + "/travels/status?encryptedTravelId=" + urllib.parse.quote(str(tid)), None, "GET")
    j = data_of(t)
    print("③ 状态%d ⇒ HTTP %s ｜ %.2fs ｜ status=%s ｜ rtcStatus=%s ｜ 角色动作=%s ｜ 环境动作=%s ｜ chapters=%s" % (
        i + 1, s, dd, j.get("status"), j.get("rtcStatus"),
        j.get("characterActions"), j.get("environmentActions"),
        (len(j.get("chapters")) if isinstance(j.get("chapters"), list) else j.get("chapters"))))

# ④ 待无推流自终（30s）后再查
print("④ 待 35s（无客户端推流 ⇒ 预期自终）…")
time.sleep(35)
s, dd, t = call(BASE + "/travels/status?encryptedTravelId=" + urllib.parse.quote(str(tid)), None, "GET")
j = data_of(t)
print("   终态 ⇒ HTTP %s ｜ %.2fs ｜ status=%s ｜ rtcStatus=%s" % (s, dd, j.get("status"), j.get("rtcStatus")))

# ⑤ 查产物（试官档命名族：travels/artifacts）
for path in ("/travels/artifacts?encryptedTravelId=", "/travels/artifact?encryptedTravelId="):
    s, dd, t = call(BASE + path + urllib.parse.quote(str(tid)), None, "GET")
    ok = (s == 200 and '"error"' not in t)
    print("⑤ 产物探测 %-38s ⇒ HTTP %s ｜ %s ｜ %s" % (path.split("?")[0], s, "★有效" if ok else "无效", t[:180].replace("\n", " ")))
    if ok:
        break
print("\n★ 本席亲验结论：①换票＝%s ②进房＝%s ③TravelId 已得（不落盘）④终态已观测 ⑤产物接口探测见上" % (
    "成" if ticket else "败", "成" if tid else "败"))
