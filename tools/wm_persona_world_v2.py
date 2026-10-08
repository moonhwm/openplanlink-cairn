# -*- coding: utf-8 -*-
"""人设 v2 → 世界模型（Adventure v2）：以 v2 镜面图为首帧建 World 并轮询至 ready，取首帧供对比
- 轻档闸 350 MB（证据化下调后）
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
print("  资源闸（轻档 350 MB）：可用=%s MB ⇒ %s" % (fm, "放行" if fm < 0 or fm >= 350 else "拒绝"))
if 0 <= fm < 350:
    sys.exit(3)

HOME = pathlib.Path.home()
BASE_DIR = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"/"exp"
PNG = BASE_DIR/"persona_luzhibai_v2_world_20261009.png"
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

PROMPT = ("第三人称视角：同一间「没有门窗」的房间，但世界已随行迹**动态完善**——右壁多出三件「器物」："
          "一枚齿轮（打钟）、一道闸门（发布闸）、一座座钟（审计）；地面节拍由五枚增为六枚，末节为「器物」。"
          "左侧有两条检验路径——「实跑取钟」与「审计比对」——各自延伸后交汇于同一枚结论点，"
          "表示单路径自证不足、须两路交叉。房间下部有一道双刻度的水位线（轻 350／重 2000），示资源之分档闸。"
          "数据链上新增一对「核名」方框，用于防止名称模糊匹配造成的错拉。房间外一枚探针以**虚线**射向世界边界，"
          "虚线**未闭合**——表示涌现尚待交互验证，**不预称已涌现**。整体仍为「知其白，守其黑」的双色世界，"
          "中性、克制，但比初版多了一层「以器物约束自身」的秩序感。")

body = {"async": True, "perspective": "third_person", "prompt": PROMPT,
        "firstFrameImage": {"base64": "data:image/png;base64," + base64.b64encode(PNG.read_bytes()).decode()}}
st, dt, txt = call(BASE + "/worlds", body, "POST")
print("=== ① 建 World v2 ⇒ HTTP %s ｜ %.2fs ===" % (st, dt))
wid = None
try:
    j = json.loads(txt); data = ((j.get("output") or {}).get("data") or {})
    wid = data.get("encryptedWorldId")
    print("   World ID=%s ｜ status=%s" % ((str(wid)[:20] + "…") if wid else "(未取到)", data.get("status")))
except Exception:
    print("   原始：%s" % txt[:260])

ff_url = None
if wid:
    for i in range(4):
        time.sleep(8)
        s2, d2, t2 = call(BASE + "/worlds/build-status?encryptedWorldId=" + urllib.parse.quote(str(wid)), None, "GET")
        try:
            dd = json.loads(t2).get("output", {}).get("data", {})
        except Exception:
            dd = {}
        print("=== ② 轮询 %d ⇒ HTTP %s ｜ %.2fs ｜ status=%s ｜ name=%s ｜ firstFrame=%s" % (
            i+1, s2, d2, dd.get("status"), dd.get("name"), str(dd.get("firstFrame"))[:60]))
        if dd.get("status") == "ready":
            ff_url = dd.get("firstFrame")
            print("   ★★ v2 世界已就绪（平台命名：%s）" % dd.get("name"))
            break
        if dd.get("status") == "failed":
            print("   × 构建失败"); break

if ff_url:
    out = BASE_DIR/"persona_v2_world_firstframe_20261009.png"
    try:
        req = urllib.request.Request(ff_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            b = resp.read()
        out.write_bytes(b)
        print("   ★ v2 首帧已下载：%s（%d KB）" % (out.name, len(b)//1024))
    except Exception as e:
        print("   × 首帧下载失败：%s" % str(e)[:120])
