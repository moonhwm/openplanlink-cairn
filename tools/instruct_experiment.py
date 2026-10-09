# -*- coding: utf-8 -*-
"""★B 组自办尝试：开会话 ⇒（running 期间）调 `/travels/instruct` 带 content ⇒ 取录像与零输入基线比对
判：若画面出现结构性位移/变化 ⇒ 指令生效 ⇒ **B 组可自办**（与官档之"不支持 instruct"出入须如实标注）
（引号一律用「」；零回显）
"""
import json, pathlib, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
EX = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"
OUT = EX/"travel_artifacts_instruct_20261009_CAIRN"; OUT.mkdir(exist_ok=True)
env = {}
for line in (HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
K = env.get("DASHSCOPE_API_KEY", "")
B = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1"

def call(path, body=None, method="POST", to=60):
    r = urllib.request.Request(B + path, data=json.dumps(body, ensure_ascii=False).encode() if body else None, method=method)
    r.add_header("Authorization", "Bearer " + K)
    if body: r.add_header("Content-Type", "application/json")
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=to) as resp:
            return resp.status, round(time.time()-t0, 2), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, round(time.time()-t0, 2), e.read().decode("utf-8", "replace")
    except Exception as e:
        return -1, round(time.time()-t0, 2), str(e)[:120]

st, dt, tx = call("/worlds?page=1&pageSize=20&status=ready", None, "GET")
items = ((json.loads(tx).get("output") or {}).get("data") or {}).get("items") or []
tgt = next((i for i in items if i.get("name") == "极简检验室"), None)
if not tgt: print("  × 未找到世界"); sys.exit(1)
WID = tgt["encryptedWorldId"]
st, dt, tx = call("/worlds/get-travel-credential", {"encryptedWorldId": WID})
tk = ((json.loads(tx).get("output") or {}).get("data") or {}).get("ticket")
st, dt, tx = call("/travels/enter-travel", {"ticket": tk, "maxExperienceTimeSec": 90})
TID = ((json.loads(tx).get("output") or {}).get("data") or {}).get("encryptedTravelId")
print("  会话已开：TravelId 尾 %s" % str(TID)[-8:])

INSTR = ["请向前走两步", "向左转 90 度", "跳一下", "向前走并环顾四周"]
log = []
for i, c in enumerate(INSTR):
    st, dt, tx = call("/travels/instruct", {"encryptedTravelId": TID, "content": c})
    code = None
    try: code = (json.loads(tx).get("output") or {}).get("code")
    except Exception: pass
    print("  第%d 次 instruct（%s）⇒ HTTP %s ｜ %.2fs ｜ code=%s ｜ %s" % (
        i+1, c, st, dt, code, tx.replace("\n", " ")[:110]))
    log.append({"i": i+1, "content": c, "http": st, "code": code, "resp": tx[:160]})
    time.sleep(6)
    st2, dt2, tx2 = call("/travels/status?encryptedTravelId=" + TID, None, "GET")
    try:
        d2 = (json.loads(tx2).get("output") or {}).get("data") or {}
        print("     状态 ⇒ status=%s ｜ rtcStatus=%s" % (d2.get("status"), d2.get("rtcStatus")))
    except Exception: pass

print("\n  等会话结束…")
t0 = time.time(); last = None
while time.time() - t0 < 150:
    time.sleep(10)
    st, dt, tx = call("/travels/status?encryptedTravelId=" + TID, None, "GET")
    try: last = ((json.loads(tx).get("output") or {}).get("data") or {}).get("status")
    except Exception: pass
    if last in ("completed", "failed"): break
print("  终态=%s" % last)
url = None
for i in range(12):
    st, dt, tx = call("/travels/artifacts?encryptedTravelId=" + TID, None, "GET")
    try:
        v = ((((json.loads(tx).get("output") or {}).get("data") or {}).get("video") or {}).get("original")) or {}
        url = v.get("url")
        print("  产物第 %d 询 ⇒ %s" % (i+1, "ready" if url else v.get("status")))
        if url: break
    except Exception: pass
    time.sleep(10)
if url:
    with urllib.request.urlopen(url, timeout=150) as resp:
        blob = resp.read()
    (OUT/"instruct_video_20261009.mp4").write_bytes(blob)
    print("  已下载：%.1f KB" % (len(blob)/1024))
(EX/"instruct_experiment_20261009_CAIRN.json").write_text(json.dumps(
    {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "seat": "a2a-node-local",
     "purpose": "B 组自办尝试：running 期间以 /travels/instruct 下发 content",
     "world": "极简检验室", "travelId": TID, "instructions": log, "final": last,
     "note": "★与官档『不支持 instruct』之出入须如实标注；结果以录像比对为准"},
    ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("  落盘：instruct_experiment_20261009_CAIRN.json")
