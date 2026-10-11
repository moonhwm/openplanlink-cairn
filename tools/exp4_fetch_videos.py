# -*- coding: utf-8 -*-
"""实验④ 之后半：取录像 URL 并下载（A=原首帧，B=nonce 首帧）
（引号一律用「」）
"""
import json, pathlib, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
EX = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"
TMP = pathlib.Path.home()/"AppData"/"Local"/"Temp"/"exp4"; TMP.mkdir(parents=True, exist_ok=True)
env = {}
for line in (HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8-sig", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
K = env.get("DASHSCOPE_API_KEY", "")
BASE = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1"
R = json.loads((EX/"exp4_nonce_perturbation_20261011.json").read_text(encoding="utf-8"))
TID = {}
for s in R["steps"]:
    if s.get("step") == "artifacts-A-1": TID["A"] = s["brief"]
    if s.get("step") == "artifacts-B-1": TID["B"] = s["brief"]


def call(path, to=120):
    r = urllib.request.Request(BASE + path, method="GET")
    r.add_header("Authorization", "Bearer " + K)
    try:
        with urllib.request.urlopen(r, timeout=to) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return -1, str(e)[:150]


out = {}
for tag in ("A", "B"):
    # 从 brief 里取完整 encryptedTravelId
    try:
        j = json.loads(TID[tag]); tid = j["encryptedTravelId"]
    except Exception:
        print("  ✗ %s：无法取 travelId" % tag); continue
    st, tx = call("/travels/artifacts?encryptedTravelId=" + tid)
    try:
        d = (json.loads(tx).get("output") or {}).get("data") or {}
    except Exception:
        d = {}
    vid = ((d.get("video") or {}).get("original") or {})
    url = vid.get("url")
    print("  %s：HTTP %s ｜ composeStatus=%s ｜ video.keys=%s" % (
        tag, st, d.get("composeStatus"), list(((d.get("video") or {})).keys())))
    if not url:
        print("     无 URL；原始：%s" % json.dumps(d, ensure_ascii=False)[:200]); continue
    dst = TMP/("exp4_%s.mp4" % tag)
    try:
        t0 = time.time()
        req = urllib.request.Request(url); req.add_header("User-Agent", "cairn/1.0")
        with urllib.request.urlopen(req, timeout=240) as resp, open(dst, "wb") as f:
            n = 0
            while True:
                b = resp.read(1 << 20)
                if not b: break
                f.write(b); n += len(b)
        print("     ★已下载 %s：%.2f MB（%.1f s）" % (dst.name, n/1048576, time.time()-t0))
        out[tag] = {"file": str(dst), "bytes": n, "url_host": url.split("/")[2], "duration_hint": vid.get("duration")}
    except Exception as e:
        print("     ✗ 下载失败：%s" % str(e)[:120])
(EX/"exp4_videos_20261011.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("  落盘：exp4_videos_20261011.json")
