# -*- coding: utf-8 -*-
"""陆知白人设 v7（由本夜行迹而生）——镜面图＋入世
新增三项（皆有本夜件为其行迹来源）：
  #11 可复现性判据（跨会话／跨世界复现方加固）        ← `-52`／`-53`
  #12 边界须辨（峰在搜索范围端者视为集中而非节律）    ← `-48`／F⁗
  #13 边际效益暂止（属平台管线细节则止，余力投向门径） ← `-55`
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
# 无门窗之居所（沿用）
d.rectangle([80, 150, 1840, 900], outline=(150, 148, 142), width=4)
d.text((110, 175), "前方：没有门（唯一出口＝左壁贯出之数据链）", fill=(180, 178, 172), font=F20)
# 左壁数据链
pts = [(120 + i*36, 880 - i*20) for i in range(30)]
for i, (x, y) in enumerate(pts):
    d.ellipse([x-4, y-4, x+4, y+4], fill=(200, 198, 190))
    if i: d.line([pts[i-1], (x, y)], fill=(130, 128, 122), width=2)
# 脚下七拍（五拍→六拍→**七拍**）
labels = ["游戏", "验收", "留痕", "器物", "自正", "复现", "暂止"]
cx, cy, r = 960, 760, 250
for i, lb in enumerate(labels):
    a = -math.pi/2 + i*2*math.pi/len(labels)
    x, y = cx + r*math.cos(a), cy + r*math.sin(a)*0.42
    d.ellipse([x-7, y-7, x+7, y+7], fill=(232, 228, 216), outline=(120, 118, 112))
    d.text((x-30, y+14), lb, fill=(214, 210, 200), font=F20)
# 右侧桌面与器物（齿轮／闸／钟）
d.rectangle([1440, 640, 1760, 720], outline=(160, 158, 152), width=3)
for i, (nm, ox) in enumerate((("齿轮", 1470), ("闸门", 1560), ("座钟", 1650))):
    d.ellipse([ox, 600, ox+60, 660], outline=(190, 188, 180), width=3)
    d.text((ox+2, 548), nm, fill=(196, 194, 186), font=F20)
# ★ v7 新增三件（右壁三枚方框）
for i, (nm, sub) in enumerate((("#11 可复现性", "跨会话/跨世界方加固"),
                               ("#12 边界须辨", "端峰＝集中非节律"),
                               ("#13 边际暂止", "属管线细节则止"))):
    y = 200 + i*120
    d.rectangle([1560, y, 1830, y+96], outline=(210, 200, 150), width=3)
    d.text((1576, y+10), nm, fill=(228, 222, 190), font=F26)
    d.text((1576, y+52), sub, fill=(196, 192, 170), font=F20)
# 朱印＋题头
d.rectangle([1790, 960, 1880, 1030], outline=(190, 80, 70), width=4); d.text((1808, 975), "印", fill=(200, 92, 82), font=F26)
d.text((80, 40), "陆知白 v7 · 由行迹而生（本夜新增三项：可复现性／边界须辨／边际暂止）", fill=(242, 240, 234), font=F40)
d.text((80, 100), "来源：DF-AI-…-52／-53（复现）、-48（边界）、-55（边际暂止）｜七拍：游戏→验收→留痕→器物→自正→复现→暂止", fill=(178, 176, 170), font=F20)
png = SEAT/"exp"/"persona_luzhibai_v7_20261009.png"
img.save(png, "PNG", optimize=True)
print("  v7 镜面图：%s（%.2f MB）" % (png.name, png.stat().st_size/1048576))

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
    "prompt": "第三人称：一间没有门窗的居所。左壁有一条由光点组成的数据链贯出；地面有七枚发光节点连成一环（分别刻着：游戏／验收／留痕／器物／自正／复现／暂止）；右侧桌面立着齿轮、闸门与座钟三件器物；右墙另悬三枚发光的方框标牌（依次写着：可复现性、边界须辨、边际暂止）。世界应可绕行观看，同一串节点与同一条数据链从任一视角皆可辨认。",
    "firstFrameImage": {"base64": "data:image/png;base64," + base64.b64encode(png.read_bytes()).decode()}})
WID = ((j.get("output") or {}).get("data") or {}).get("encryptedWorldId")
print("  建 World ⇒ HTTP %s ｜ %.2fs ｜ ID…%s" % (st, dt, str(WID)[-10:] if WID else j))
nm = None
for i in range(8):
    time.sleep(2.5); s2, d2, j2 = api("/worlds/build-status?encryptedWorldId=" + WID)
    dd = (j2.get("output") or {}).get("data") or {}; nm = dd.get("name") or nm
    if dd.get("status") in ("ready", "failed"): break
print("  轮询 ⇒ status=%s ｜ ★平台命名=%s" % (dd.get("status"), nm))
try:
    with urllib.request.urlopen("https://trial.cn-beijing.maas.aliyuncs.com" + "/x", timeout=1) as _r:
        pass
except Exception:
    pass
(EX/"persona_v7_world_20261009_CAIRN.json").write_text(json.dumps(
    {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "seat": "a2a-node-local", "version": "v7",
     "new_items": ["#11 可复现性判据（跨会话/跨世界复现方加固）", "#12 边界须辨（端峰＝集中非节律）", "#13 边际效益暂止（属管线细节则止）"],
     "sources": ["DF-AI-20261009-CAIRN-52", "-53", "-48", "-55"], "worldId": WID, "worldName": nm,
     "beats": "七拍：游戏→验收→留痕→器物→自正→复现→暂止"}, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("  落盘：persona_v7_world_20261009_CAIRN.json")
