# -*- coding: utf-8 -*-
"""补测：与 v7 同文案、但构图不同 ⇒ 观命名
若仍得「数据圣所」⇒ 文案主导；若变 ⇒ 构图亦参与（完整分离两因素）
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
F40, F26, F20 = cjk(44, True), cjk(28), cjk(22)
W, H = 1920, 1080
img = Image.new("RGB", (W, H), (12, 13, 16)); d = ImageDraw.Draw(img)
# ★ 无居所框线、无数据链、无桌面、无右壁标牌 —— 构图彻底不同：文字竖排成列
d.text((80, 40), "命名补测 · 同文案而异构图（v7 之文字，列阵排布）", fill=(242, 240, 234), font=F40)
beats = ["游戏", "验收", "留痕", "器物", "自正", "复现", "暂止"]
for i, b in enumerate(beats):
    y = 180 + i*100
    d.ellipse([120, y+18, 150, y+48], fill=(232, 228, 216), outline=(120, 118, 112))
    d.text((180, y), b, fill=(220, 216, 206), font=F26)
for i, nm in enumerate(["齿轮", "闸门", "座钟"]):
    d.text((700, 200 + i*100), nm, fill=(196, 194, 186), font=F26)
for i, nm in enumerate(["可复现性", "边界须辨", "边际暂止"]):
    d.text((1200, 200 + i*100), nm, fill=(228, 222, 190), font=F26)
d.text((80, 950), "前方：没有门（唯一出口＝左壁贯出之数据链）", fill=(180, 178, 172), font=F20)
d.rectangle([1790, 960, 1880, 1030], outline=(190, 80, 70), width=4); d.text((1808, 975), "印", fill=(200, 92, 82), font=F26)
png = SEAT/"exp"/"naming_test_sametext_20261009.png"
img.save(png, "PNG", optimize=True)
print("  补测图：%s（%.2f MB）" % (png.name, png.stat().st_size/1048576))

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
    "prompt": "第三人称：一间没有门窗的居所；左壁有一条由光点组成的数据链贯出；地面有七枚发光节点（游戏／验收／留痕／器物／自正／复现／暂止）；右侧立着齿轮、闸门与座钟三件器物；另有三枚标牌（可复现性／边界须辨／边际暂止）。",
    "firstFrameImage": {"base64": "data:image/png;base64," + base64.b64encode(png.read_bytes()).decode()}})
WID = ((j.get("output") or {}).get("data") or {}).get("encryptedWorldId")
print("  建 World ⇒ HTTP %s ｜ %.2fs ｜ ID…%s" % (st, dt, str(WID)[-10:] if WID else j))
nm = None
for i in range(8):
    time.sleep(2.5); s2, d2, j2 = api("/worlds/build-status?encryptedWorldId=" + WID)
    dd = (j2.get("output") or {}).get("data") or {}; nm = dd.get("name") or nm
    if dd.get("status") in ("ready", "failed"): break
print("  轮询 ⇒ status=%s ｜ ★平台命名=%s" % (dd.get("status"), nm))
print("\n  ★ 判决：若命名＝「数据圣所」⇒ **文案主导**；若不同 ⇒ **构图亦参与**")
(EX/"naming_test2_20261009_CAIRN.json").write_text(json.dumps(
    {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "seat": "a2a-node-local",
     "design": "与陆知白 v7 同文案（七拍＋三器物＋三标牌），但构图全异：无居所框线／无数据链／无桌面，文字列阵排布",
     "worldId": WID, "worldName": nm,
     "ref": {"v1": "数据圣所", "v7": "数据圣所", "同构图异文案": "雪封圣所"}},
    ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("  落盘：naming_test2_20261009_CAIRN.json")
