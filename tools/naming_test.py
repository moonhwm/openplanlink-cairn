# -*- coding: utf-8 -*-
"""命名判决实验：与 v7 同构图、但文字全异 ⇒ 观平台命名
若仍得「数据圣所」⇒ 命名由构图主导；若得新名 ⇒ 文字/内容亦有影响
（引号一律用「」）
"""
import base64, json, math, pathlib, sys, time, urllib.request, urllib.error
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
F40, F26, F20 = cjk(44, True), cjk(28), cjk(22)
W, H = 1920, 1080
img = Image.new("RGB", (W, H), (10, 11, 14)); d = ImageDraw.Draw(img)
d.rectangle([80, 150, 1840, 900], outline=(150, 148, 142), width=4)
d.text((110, 175), "前方：一扇窗（窗外是雪原）", fill=(180, 178, 172), font=F20)     # ← 唯一文字差异之一
pts = [(120 + i*36, 880 - i*20) for i in range(30)]
for i, (x, y) in enumerate(pts):
    d.ellipse([x-4, y-4, x+4, y+4], fill=(200, 198, 190))
    if i: d.line([pts[i-1], (x, y)], fill=(130, 128, 122), width=2)
labels = ["甲", "乙", "丙", "丁", "戊", "己", "庚"]                                   # ← 与 v7 之文字全异
cx, cy, r = 960, 760, 250
for i, lb in enumerate(labels):
    a = -math.pi/2 + i*2*math.pi/len(labels)
    x, y = cx + r*math.cos(a), cy + r*math.sin(a)*0.42
    d.ellipse([x-7, y-7, x+7, y+7], fill=(232, 228, 216), outline=(120, 118, 112))
    d.text((x-14, y+14), lb, fill=(214, 210, 200), font=F20)
d.rectangle([1440, 640, 1760, 720], outline=(160, 158, 152), width=3)
for nm, ox in (("一", 1470), ("二", 1560), ("三", 1650)):                              # ← 器物名亦异
    d.ellipse([ox, 600, ox+60, 660], outline=(190, 188, 180), width=3)
    d.text((ox+16, 548), nm, fill=(196, 194, 186), font=F20)
for i, (nm, sub) in enumerate((("壹", "子"), ("贰", "丑"), ("叁", "寅"))):               # ← 右壁标牌亦异
    y = 200 + i*120
    d.rectangle([1560, y, 1830, y+96], outline=(210, 200, 150), width=3)
    d.text((1576, y+10), nm, fill=(228, 222, 190), font=F26)
    d.text((1576, y+52), sub, fill=(196, 192, 170), font=F20)
d.rectangle([1790, 960, 1880, 1030], outline=(190, 80, 70), width=4); d.text((1808, 975), "印", fill=(200, 92, 82), font=F26)
d.text((80, 40), "命名判决实验 · 同构图而文字全异", fill=(242, 240, 234), font=F40)
d.text((80, 100), "与陆知白 v7 同布局、同器物、同七节点环；唯将全部文字改作甲／乙／丙…与一／二／三", fill=(178, 176, 170), font=F20)
png = SEAT/"exp"/"naming_test_samecomp_20261009.png"
img.save(png, "PNG", optimize=True)
print("  实验图：%s（%.2f MB）" % (png.name, png.stat().st_size/1048576))

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
        return e.code, round(time.time()-t0, 2), {"err": e.read().decode("utf-8", "replace")[:180]}
    except Exception as e:
        return -1, round(time.time()-t0, 2), {"err": str(e)[:130]}

st, dt, j = api("/worlds", {"async": True, "perspective": "third_person",
    "prompt": "第三人称：一间封闭的居所，前方有一扇窗，窗外是雪原；地面有七枚光点连成一环；右侧桌面立着三件器物；右墙悬挂三枚发光标牌。室内有一串光点沿左壁延伸至地面。",
    "firstFrameImage": {"base64": "data:image/png;base64," + base64.b64encode(png.read_bytes()).decode()}})
WID = ((j.get("output") or {}).get("data") or {}).get("encryptedWorldId")
print("  建 World ⇒ HTTP %s ｜ %.2fs ｜ ID…%s" % (st, dt, str(WID)[-10:] if WID else j))
nm = None
for i in range(8):
    time.sleep(2.5); s2, d2, j2 = api("/worlds/build-status?encryptedWorldId=" + WID)
    dd = (j2.get("output") or {}).get("data") or {}; nm = dd.get("name") or nm
    if dd.get("status") in ("ready", "failed"): break
print("  轮询 ⇒ status=%s ｜ ★平台命名=%s" % (dd.get("status"), nm))
print("\n  ★ 判决：若命名＝「数据圣所」⇒ 与 v1/v7 同 ⇒ **命名由构图主导（文字无影响）**")
print("     若命名不同 ⇒ 文字/内容亦参与命名")
(EX/"naming_test_20261009_CAIRN.json").write_text(json.dumps(
    {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "seat": "a2a-node-local",
     "design": "与陆知白 v7 同构图、文字全异（甲/乙/丙…、一/二/三、壹/贰/叁；文案改为『一扇窗·雪原』）",
     "worldId": WID, "worldName": nm, "ref": {"v1_name": "数据圣所", "v7_name": "数据圣所"}},
    ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("  落盘：naming_test_20261009_CAIRN.json")
