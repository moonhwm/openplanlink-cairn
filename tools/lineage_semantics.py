# -*- coding: utf-8 -*-
"""检验 `refWorldId` 之语义：以【异首帧】衍生自「数据塔」
若命名/外观随【新帧】⇒ 衍生＝血缘记录（不继承内容）；若随【父世界】⇒ 继承内容
（引号一律用「」）
"""
import base64, json, pathlib, sys, time, urllib.request, urllib.error
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
SEAT = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"
EX = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"
env = {}
for line in (HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
K = env.get("DASHSCOPE_API_KEY", "")
B = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1"

def cjk(sz, bold=False):
    for p in ((r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc"), r"C:\Windows\Fonts\simhei.ttf"):
        try: return ImageFont.truetype(p, sz)
        except Exception: pass
    return ImageFont.load_default()
F44, F24 = cjk(48, True), cjk(26)
W, H = 1920, 1080
img = Image.new("RGB", (W, H), (14, 10, 10)); d = ImageDraw.Draw(img)
# 鲜明异于「数据塔」之新帧：红色荒漠＋三块石碑
d.rectangle([0, 700, W, H], fill=(60, 20, 16))
for i in range(3):
    x = 400 + i*400
    d.rectangle([x, 330, x+180, 700], fill=(90, 30, 22), outline=(220, 160, 120), width=4)
    d.text((x+16, 380), "碑%d" % (i+1), fill=(240, 220, 200), font=F24)
d.text((80, 60), "血缘检验帧 · 赤色荒漠与三碑（与「数据塔」全然不同）", fill=(250, 230, 220), font=F44)
png = SEAT/"exp"/"lineage_test_frame_20261009.png"
img.save(png, "PNG", optimize=True)
print("  异首帧：%s（%.2f MB）" % (png.name, png.stat().st_size/1048576))

def api(path, body=None, to=90):
    r = urllib.request.Request(B + path, data=json.dumps(body, ensure_ascii=False).encode() if body else None,
                               method="POST" if body else "GET")
    r.add_header("Authorization", "Bearer " + K)
    if body: r.add_header("Content-Type", "application/json")
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=to) as resp:
            return resp.status, round(time.time()-t0, 2), json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, round(time.time()-t0, 2), {"err": e.read().decode("utf-8", "replace")[:200]}
    except Exception as e:
        return -1, round(time.time()-t0, 2), {"err": str(e)[:130]}

# 取「数据塔」之 ID 作为父
st, dt, j = api("/worlds?page=1&pageSize=30&status=ready")
items = ((j.get("output") or {}).get("data") or {}).get("items") or []
parent = next((i for i in items if i.get("name") == "数据塔"), None)
if not parent:
    print("  × 未找到父世界「数据塔」"); sys.exit(1)
PID = parent["encryptedWorldId"]
print("  父世界：「数据塔」%s…" % str(PID)[-10:])
st, dt, j = api("/worlds", {"async": True, "perspective": "third_person",
    "prompt": "第三人称：一片赤色荒漠，矗立三块刻字的石碑；天空暗红，地面有细砂纹。",
    "firstFrameImage": {"base64": "data:image/png;base64," + base64.b64encode(png.read_bytes()).decode()},
    "refWorldId": PID})
WID = ((j.get("output") or {}).get("data") or {}).get("encryptedWorldId")
print("  衍生建 World ⇒ HTTP %s ｜ %.2fs ｜ ID…%s" % (st, dt, str(WID)[-10:] if WID else j))
nm = None
for i in range(8):
    time.sleep(2.5); s2, d2, j2 = api("/worlds/build-status?encryptedWorldId=" + WID)
    dd = (j2.get("output") or {}).get("data") or {}; nm = dd.get("name") or nm
    if dd.get("status") in ("ready", "failed"): break
print("  轮询 ⇒ status=%s ｜ ★平台命名=%s" % (dd.get("status"), nm))
# 详情：核 refWorldId 回显
s3, d3, j3 = api("/worlds/detail?encryptedWorldId=" + WID)
dd3 = (j3.get("output") or {}).get("data") or {}
print("  详情 ⇒ refWorldId 回显=%s ｜ 命名=%s ｜ 首帧URL=%s" % (
    (str(dd3.get("refWorldId"))[-10:] if dd3.get("refWorldId") else "null"), dd3.get("name"), bool(dd3.get("firstFrameImage") or dd3.get("firstFrameUrl"))))
print("\n  ★ 判决：若命名随【新帧】（如赤色/荒漠/碑）⇒ **衍生不继承外观内容，仅记血缘**")
print("     若命名仍为「数据塔」⇒ **衍生继承父世界之内容/命名**")
(EX/"lineage_semantics_test_20261009_CAIRN.json").write_text(json.dumps(
    {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "seat": "a2a-node-local",
     "design": "以『赤色荒漠三碑』为异首帧，refWorldId 指向「数据塔」",
     "parent": {"name": "数据塔", "id": PID}, "child": {"id": WID, "name": nm},
     "detail_ref": bool(dd3.get("refWorldId"))}, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("  落盘：lineage_semantics_test_20261009_CAIRN.json")
