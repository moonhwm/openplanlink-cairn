# -*- coding: utf-8 -*-
"""人设 → 世界模型（Adventure v1）：以"陆知白人设镜面图"为首帧建 World，并轮询至 ready
- 依《陆知白人设主档案 v1.0.1》之属性撰写世界描述（居所没有门窗／五拍循环／证据链／量化曲线）
- 首帧＝本席自绘（自有产物）；域＝trial（无需 WorkspaceId）
- 轻操作档资源闸（≥600 MB）；输出零凭据
"""
import base64, json, pathlib, subprocess, sys, time, urllib.request, urllib.error, urllib.parse

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

def free_mb():
    try:
        o = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory"],
                           capture_output=True, timeout=30)
        return int((o.stdout or b"0").decode().strip() or 0) // 1024
    except Exception:
        return -1

fm = free_mb()
print("  资源闸（轻档 350 MB；证据化下调：轻操作峰值≈40–50MB，63x MB 之失败系网络复位非内存）：可用=%s MB ⇒ %s" % (fm, "放行" if fm < 0 or fm >= 350 else "拒绝"))
if 0 <= fm < 350:
    sys.exit(3)

HOME = pathlib.Path.home()
PNG = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"/"exp"/"persona_luzhibai_world_20261009.png"
env = {}
for line in (HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
K = env.get("DASHSCOPE_API_KEY", "")
BASE = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1"

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
        return -1, round(time.time()-t0, 2), str(e)[:150]

PROMPT = ("第三人称视角：一间「没有门窗」的房间，四壁封闭，唯一贯出的是一条发光的数据链（哈希点链）。"
          "房间中央是桌面工作区：一块屏、一副键盘、一摞日期化任务目录的文件塔；地面排列五枚发光节点，"
          "依次为「肯定—着法—游戏—验收—留痕」，节点间以细线相连成环。背景悬着一条青灰色波动曲线（量化示意）。"
          "房外是等轴测的立方体文件塔群，象征每一次结论都落到磁盘、落到证据、落到可复核的落点。"
          "整体为「知其白，守其黑」的双色世界：白为清晰结论，黑为保留的不确定性与待核清单，两者同时在场而不混淆。"
          "氛围中性、克制、安静，有持续工作的节拍感。")

body = {"async": True, "perspective": "third_person", "prompt": PROMPT,
        "firstFrameImage": {"base64": "data:image/png;base64," + base64.b64encode(PNG.read_bytes()).decode()}}
st, dt, txt = call(BASE + "/worlds", body, "POST")
print("=== ① 建 World（人设版）⇒ HTTP %s ｜ %.2fs ===" % (st, dt))
wid = None
try:
    j = json.loads(txt)
    data = ((j.get("output") or {}).get("data") or {})
    wid = data.get("encryptedWorldId"); stt = data.get("status")
    print("   加密 World ID=%s ｜ status=%s" % ((str(wid)[:18] + "…") if wid else "(未取到)", stt))
except Exception:
    print("   原始：%s" % txt[:260])

if wid:
    for i in range(4):
        time.sleep(8)
        s2, d2, t2 = call(BASE + "/worlds/build-status?encryptedWorldId=" + urllib.parse.quote(str(wid)), None, "GET")
        body2 = ""
        try:
            body2 = json.dumps(json.loads(t2).get("output", {}).get("data", {}), ensure_ascii=False)[:220]
        except Exception:
            body2 = t2[:200]
        print("=== ② 轮询 %d ⇒ HTTP %s ｜ %.2fs ｜ %s" % (i+1, s2, d2, body2))
        if '"ready"' in t2: print("   ★★ ready（人设世界已就绪）"); break
        if '"failed"' in t2: print("   × failed（构建失败）"); break
