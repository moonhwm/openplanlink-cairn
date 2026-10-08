# -*- coding: utf-8 -*-
"""分幕世界链（以 Adventure 之 refWorldId 承载"分幕/镜头"，为 Directing 之近似——件中必标）
生成三张分镜首帧（1920x1080，横屏）→ 建三幕世界（幕二、幕三带 refWorldId）→ 记录谱系
零凭据；只在可用能力内
"""
import base64, hashlib, json, math, pathlib, sys, time, urllib.request, urllib.error
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

def cjk(sz):
    for p in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"):
        try: return ImageFont.truetype(p, sz)
        except Exception: pass
    return ImageFont.load_default()
F28, F20, F16 = cjk(40), cjk(28), cjk(22)

def frame(path, title, shot, desc, seed):
    img = Image.new("RGB", (1920, 1080), (8, 9, 12)); d = ImageDraw.Draw(img)
    h = int(hashlib.sha3_512(seed.encode()).hexdigest()[:8], 16)
    # 灯带与地面
    for i in range(0, 1920, 6):
        y = 700 + int(60 * math.sin(i / 190.0))
        d.line([(i, y), (i + 4, y)], fill=(70, 74, 84), width=2)
    d.line([(0, 880), (1920, 860)], fill=(52, 56, 64), width=3)
    # 文档塔（数量随幕次）
    n = 5 + (h % 5)
    for i in range(n):
        x = 200 + i * (1500 // max(1, n)); w = 70 + (h >> i) % 40
        ytop = 430 - (h >> (i % 8)) % 90
        d.rectangle([x, ytop, x + w, 860], outline=(150, 146, 138), width=3)
        for k in range(6):
            yy = ytop + 24 + k * 20
            if yy < 856: d.line([(x + 8, yy), (x + w - 8, yy)], fill=(96, 94, 90), width=1)
    # 数据链
    for i in range(28):
        px = 120 + i * 58; py = 820 - i * 16
        d.ellipse([px - 4, py - 4, px + 4, py + 4], fill=(190, 188, 180))
        if i: d.line([(px - 58, py + 16), (px, py)], fill=(120, 118, 112), width=2)
    # 灯环（幕三特写：大环）
    if "Close" in shot:
        d.ellipse([1080, 300, 1720, 780], outline=(210, 206, 196), width=5)
        d.ellipse([1180, 380, 1620, 700], outline=(150, 148, 142), width=3)
        d.text((1250, 500), "只读镜片", fill=(225, 222, 214), font=F28)
    elif "Medium" in shot:
        d.ellipse([1280, 380, 1680, 700], outline=(180, 176, 168), width=4)
    # 朱印（每幕一枚）
    d.rectangle([1740, 940, 1860, 1030], outline=(190, 80, 70), width=4)
    d.text((1762, 962), "印", fill=(200, 92, 82), font=F28)
    d.text((60, 50), title, fill=(240, 238, 232), font=F28)
    d.text((60, 108), shot, fill=(200, 190, 150), font=F20)
    d.text((60, 150), desc, fill=(170, 170, 166), font=F16)
    img.save(path, "PNG", optimize=True)
    return path

shots = [
    ("幕一", "Wide · Tracking（全景横移）", "夜间游乐场入口：灯带横贯画面，两侧文档塔林立，数据链自左下延伸入景；镜头自左向右缓移。", "act1"),
    ("幕二", "Medium · Dolly-in（中景推近）", "中景：文档塔与数据链成为主体，镜片轮廓在右前方渐显；镜头向塔群缓推。", "act2"),
    ("幕三", "Close-up · Static（特写固定）", "特写：只读镜片占画面主体，环内可见完整环串；镜头固定不动，唯光影微移。", "act3"),
]
outs = []
for tag, shot, desc, seed in shots:
    p = SEAT/"exp"/("storyboard_%s_20261009.png" % seed)
    frame(p, "夜间游乐场 · 分幕链 · %s（以 Adventure 之 refWorldId 承载分幕，Directing 之近似）" % tag, shot, desc, seed)
    outs.append((tag, shot, desc, seed, p))
    print("  分镜：%s（%.2f MB）" % (p.name, p.stat().st_size/1048576))

def api(path, body, method="POST", to=90):
    r = urllib.request.Request(B + path, data=json.dumps(body, ensure_ascii=False).encode() if body else None, method=method)
    r.add_header("Authorization", "Bearer " + K)
    if body: r.add_header("Content-Type", "application/json")
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=to) as resp:
            return resp.status, round(time.time()-t0, 2), json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, round(time.time()-t0, 2), {"err": e.read().decode("utf-8", "replace")[:160]}
    except Exception as e:
        return -1, round(time.time()-t0, 2), {"err": str(e)[:140]}

chain = []
prev = None
for tag, shot, desc, seed, p in outs:
    body = {"async": True, "perspective": "third_person",
            "prompt": "第三人称：%s。本幕镜头设定＝%s。整体为墨黑底、灯带与文档塔构成之夜间游乐场；镜头语言清晰、可绕行观看。" % (desc, shot),
            "firstFrameImage": {"base64": "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()}}
    if prev: body["refWorldId"] = prev
    st, dt, j = api("/worlds", body)
    wid = ((j.get("output") or {}).get("data") or {}).get("encryptedWorldId")
    print("  %s 建 World ⇒ HTTP %s ｜ %.2fs ｜ %s" % (tag, st, dt, "ID…" + str(wid)[-10:] if wid else j))
    if not wid: break
    name = None
    for i in range(6):
        time.sleep(2.2)
        s2, d2, j2 = api("/worlds/build-status?encryptedWorldId=" + wid, None, "GET")
        dd = (j2.get("output") or {}).get("data") or {}
        name = dd.get("name") or name
        if dd.get("status") in ("ready", "failed"): break
    chain.append({"act": tag, "shot": shot, "worldId": wid, "name": name, "refWorldId": prev, "create_sec": dt, "status": dd.get("status")})
    print("     轮询 ⇒ status=%s ｜ 平台命名=%s" % (dd.get("status"), name))
    prev = wid

(EX/"storyboard_chain_20261009_CAIRN.json").write_text(json.dumps(
    {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "seat": "a2a-node-local",
     "note": "以 Adventure 之 refWorldId 承载分幕与镜头设定——系 Directing（实时导演）之近似，非其本身",
     "chain": chain}, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("\n  ★ 分幕链：%s" % " → ".join(["%s(%s)" % (c["act"], c["name"]) for c in chain]))
