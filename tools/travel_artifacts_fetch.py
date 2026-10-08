# -*- coding: utf-8 -*-
"""取 Travel 产物全字段＋探测视频（大小/类型）＋（<40MB 则下载）＋（有 ffmpeg 则抽帧）
- TravelId 完整值在内存保留（不落盘）
- 纪律：不打印凭据；视频为世界演进之录制品（属本席自建世界之产物）
"""
import json, pathlib, shutil, subprocess, sys, time, urllib.request, urllib.error, urllib.parse

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
OUTDIR = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"/"travel_artifacts_20261009_CAIRN"
OUTDIR.mkdir(parents=True, exist_ok=True)
BASE = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1"
WID_V5 = "8rcpnKlw6xp3FtpLvZIGB9mlTipFohD7syfWSOD-bt7vYWx9jdVEIlPMdelwsS6b"
env = {}
for line in (HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
K = env.get("DASHSCOPE_API_KEY", "")

def call(url, body=None, method="GET", to=90):
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

def dat(t):
    try:
        return (json.loads(t).get("output") or {}).get("data") or {}
    except Exception:
        return {}

# 新做一次最小进房（30–60s），再取产物
s, dt, t = call(BASE + "/worlds/get-travel-credential", {"encryptedWorldId": WID_V5}, "POST")
tk = dat(t).get("ticket")
s, dt, t = call(BASE + "/travels/enter-travel", {"ticket": tk, "maxExperienceTimeSec": 60}, "POST")
d = dat(t); tid = d.get("encryptedTravelId")
print("  进房 ⇒ %s ｜ TravelId=★（内存）｜ rtc 字段=%s ｜ noStream=%s" % (
    s, sorted((d.get("rtcConfig") or {}).keys()), d.get("noStreamAutoEndTimeoutSec")))
if not tid:
    print("  × 未取到 TravelId：%s" % t[:160]); sys.exit(1)
print("  等待 50s（无推流自终）…"); time.sleep(50)
s, dt, t = call(BASE + "/travels/artifacts?encryptedTravelId=" + urllib.parse.quote(tid), None, "GET")
j = dat(t); code = (json.loads(t).get("output") or {}).get("code") if s == 200 else s
print("  产物 ⇒ HTTP %s ｜ code=%s" % (s, code))
print("  全字段：%s" % json.dumps(j, ensure_ascii=False)[:900])
(OUTDIR / "travel_artifacts_meta_20261009_CAIRN.json").write_text(
    json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"),
                "note": "TravelId 未落盘（依凭据纪律）；本件仅存产物元数据",
                "code": code, "artifacts": j}, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")

url = (((j.get("video") or {}).get("original") or {}).get("url")) if isinstance(j, dict) else None
if not url:
    print("  × 未取到视频 URL"); sys.exit(0)
print("  视频 URL=%s…" % str(url)[:90])
# HEAD 探大小
try:
    rq = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(rq, timeout=45) as resp:
        size = int(resp.headers.get("Content-Length") or 0)
        print("  HEAD ⇒ %s ｜ 类型=%s ｜ 大小=%.2f MB" % (resp.status, resp.headers.get("Content-Type"), size/1048576))
except Exception as e:
    print("  HEAD 失败：%s" % str(e)[:110]); size = 0
if 0 < size <= 40 * 1048576:
    vp = OUTDIR / "travel_v5_video_20261009.mp4"
    try:
        rq = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(rq, timeout=180) as resp, open(vp, "wb") as f:
            shutil.copyfileobj(resp, f)
        print("  ★ 视频已下载：%s（%.2f MB）" % (vp.name, vp.stat().st_size/1048576))
        ff = shutil.which("ffmpeg")
        print("  ffmpeg=%s" % (ff or "（未安装）"))
        if ff:
            fr = OUTDIR / "travel_v5_frame_01.jpg"
            subprocess.run([ff, "-y", "-i", str(vp), "-vf", "select=eq(n\\,30)", "-vframes", "1", str(fr)],
                           capture_output=True, timeout=120)
            print("  抽帧：%s ⇒ %s" % (fr.name, "OK" if fr.exists() else "失败"))
    except Exception as e:
        print("  × 下载失败：%s" % str(e)[:120])
else:
    print("  ⇒ 大小 %.2f MB 超阈或无 Content-Length ⇒ 仅登记元数据，不下载" % (size/1048576))
