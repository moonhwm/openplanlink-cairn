# -*- coding: utf-8 -*-
"""通用建 World 器（Adventure；trial 域）——供人设迭代反复使用
用法：
  python wm_create_generic.py --png <图片> --prompt-file <txt|缺失则用内联> [--label v3]
行为：轻档闸 350 MB → 创建 → 轮询至 ready → 下载平台首帧 → 打印平台命名
"""
import argparse, base64, json, pathlib, subprocess, sys, time, urllib.request, urllib.error, urllib.parse

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
BASE = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1"
HOME = pathlib.Path.home()

def free_mb():
    try:
        o = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory"],
                           capture_output=True, timeout=30)
        return int((o.stdout or b"0").decode().strip() or 0) // 1024
    except Exception:
        return -1

def key():
    env = {}
    for line in (HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
    return env.get("DASHSCOPE_API_KEY", "")

def call(url, K, body=None, method="GET", to=60):
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
        return -1, round(time.time()-t0, 2), str(e)[:150]

ap = argparse.ArgumentParser()
ap.add_argument("--png", required=True)
ap.add_argument("--prompt", required=True)
ap.add_argument("--out", default="world_firstframe_20261009.png")
a = ap.parse_args()

fm = free_mb()
print("  资源闸（轻档 350 MB）：可用=%s MB ⇒ %s" % (fm, "放行" if fm < 0 or fm >= 350 else "拒绝"))
if 0 <= fm < 350:
    sys.exit(3)

png = pathlib.Path(a.png)
print("  首帧：%s（%.2f MB）" % (png.name, png.stat().st_size/1048576))
K = key()
body = {"async": True, "perspective": "third_person", "prompt": a.prompt,
        "firstFrameImage": {"base64": "data:image/png;base64," + base64.b64encode(png.read_bytes()).decode()}}
st, dt, txt = call(BASE + "/worlds", K, body, "POST")
print("=== ① 创建 ⇒ HTTP %s ｜ %.2fs" % (st, dt))
wid = None
try:
    data = ((json.loads(txt).get("output") or {}).get("data") or {})
    wid = data.get("encryptedWorldId")
    print("   World ID=%s ｜ status=%s" % ((str(wid)[:20] + "…") if wid else "(未取到)", data.get("status")))
except Exception:
    print("   原始：%s" % txt[:240])

if wid:
    for i in range(4):
        time.sleep(8)
        s2, d2, t2 = call(BASE + "/worlds/build-status?encryptedWorldId=" + urllib.parse.quote(str(wid)), K, None, "GET")
        try:
            dd = json.loads(t2).get("output", {}).get("data", {})
        except Exception:
            dd = {}
        print("=== ② 轮询 %d ⇒ HTTP %s ｜ %.2fs ｜ status=%s ｜ 平台命名=%s" % (i+1, s2, d2, dd.get("status"), dd.get("name")))
        if dd.get("status") == "ready":
            ff = dd.get("firstFrame")
            print("   ★★ ready（平台命名：%s）" % dd.get("name"))
            print("   ★ World ID（完整）：%s" % wid)
            if ff:
                out = png.parent / a.out
                try:
                    req = urllib.request.Request(ff, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=60) as resp:
                        out.write_bytes(resp.read())
                    print("   ★ 首帧已下载：%s" % out.name)
                except Exception as e:
                    print("   × 首帧下载失败：%s" % str(e)[:100])
            break
        if dd.get("status") == "failed":
            print("   × 构建失败"); break
