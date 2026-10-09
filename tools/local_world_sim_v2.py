# -*- coding: utf-8 -*-
"""本地替身世界 v2：行迹真实数值（七拍）＋分身沿环行走＋逐拍换态＋正视收紧构图
输出：接触表 PNG ＋ GIF（与 v1 同格式，便于并列对照）
★ 三条限制同 v1：非平台世界模型／变化皆本席所写 ⇒ 不含涌现／朝向固定系渲染选择
（引号一律用「」）
"""
import hashlib, json, math, pathlib, struct, sys, time

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
SEAT = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"
EX = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"

# ── 七拍真实数值（承 -15；逐项溯源）──
ledger = SEAT/"ledger"/"frontier_ledger.jsonl"
n_led = sum(1 for _ in ledger.open(encoding="utf-8", errors="replace")) if ledger.exists() else 0
n_tools = len(list((SEAT/"exp").glob("*.py"))) + len(list((SEAT/"exp").glob("*.cs")))
BEATS = [("游戏", 23, "IDLE_VERIFY"), ("验收", 9, "WEIGH"), ("留痕", n_led, "INSPECT"),
         ("器物", n_tools, "RELAY"), ("自正", 70, "REFUSE"), ("复现", 46, "IDLE_VERIFY"),
         ("暂止", 10, "RELAY")]

# ── 蒙皮（LOD1）──
raw = (SEAT/"exp"/"CAIRN_avatar_v2_LOD1.glb").read_bytes()
jlen, _ = struct.unpack_from("<II", raw, 12); js = json.loads(raw[20:20+jlen].decode())
boff = 20+jlen; blen, _ = struct.unpack_from("<II", raw, boff); bn = raw[boff+8:boff+8+blen]
CT = {5123:("H",2),5125:("I",4),5126:("f",4)}; NC = {"SCALAR":1,"VEC3":3,"VEC4":4,"MAT4":16}
def racc(i):
    a = js["accessors"][i]; bv = js["bufferViews"][a["bufferView"]]
    f, s = CT[a["componentType"]]; n = NC[a["type"]]
    off = bv.get("byteOffset",0)+a.get("byteOffset",0)
    return [struct.unpack_from("<%d%s"%(n,f), bn, off+k*n*s) for k in range(a["count"])]
prim = js["meshes"][0]["primitives"][0]
POS = racc(prim["attributes"]["POSITION"]); JTS = racc(prim["attributes"]["JOINTS_0"]); WTS = racc(prim["attributes"]["WEIGHTS_0"])
IDX = [i[0] for i in racc(prim["indices"])]
JN = js["skins"][0]["joints"]; IBM = racc(js["skins"][0]["inverseBindMatrices"])
PARENT = {}
for i, nd in enumerate(js["nodes"]):
    for c in nd.get("children", []): PARENT[c] = i
def mul(a, b):
    r = [0.0]*16
    for c in range(4):
        for row in range(4):
            r[c*4+row] = sum(a[k*4+row]*b[c*4+k] for k in range(4))
    return r
def trs(t, q):
    x, y, z, w = q; xx, yy, zz = x*x, y*y, z*z
    return [1-2*(yy+zz), 2*(x*y+z*w), 2*(x*z-y*w), 0,
            2*(x*y-z*w), 1-2*(xx+zz), 2*(y*z+x*w), 0,
            2*(x*z+y*w), 2*(y*z-x*w), 1-2*(xx+yy), 0, t[0], t[1], t[2], 1]
def eval_anim(name, t):
    out = {}
    an = next((a for a in js["animations"] if a["name"] == name), None)
    if not an: return out
    for ch in an["channels"]:
        if ch["target"]["path"] != "rotation": continue
        s = an["samplers"][ch["sampler"]]
        ti = [v[0] for v in racc(s["input"])]; qq = racc(s["output"])
        if t <= ti[0]: q = list(qq[0])
        elif t >= ti[-1]: q = list(qq[-1])
        else:
            for k in range(len(ti)-1):
                if ti[k] <= t <= ti[k+1]:
                    u = (t-ti[k])/max(1e-9, ti[k+1]-ti[k]); q = [qq[k][m]*(1-u)+qq[k+1][m]*u for m in range(4)]; break
        n = math.sqrt(sum(v*v for v in q)) or 1.0
        out[ch["target"]["node"]] = [v/n for v in q]
    return out
def skin(anim):
    W = {}
    order = sorted(range(len(js["nodes"])), key=lambda i: (lambda f: f(f, i))(lambda f, x: 0 if x not in PARENT else 1+f(f, PARENT[x])))
    for i in order:
        nd = js["nodes"][i]; t0 = list(nd.get("translation", [0,0,0])); q = list(nd.get("rotation", [0,0,0,1]))
        if i in anim: q = anim[i]
        loc = trs(t0, q); W[i] = loc if i not in PARENT else mul(W[PARENT[i]], loc)
    M = [mul(W[JN[k]], list(IBM[k])) for k in range(len(JN))]
    verts = []
    for vi, v in enumerate(POS):
        acc = [0.0, 0.0, 0.0]
        for k in range(4):
            w = WTS[vi][k]
            if w <= 0: continue
            m = M[JTS[vi][k]]
            acc[0] += w*(m[0]*v[0]+m[4]*v[1]+m[8]*v[2]+m[12])
            acc[1] += w*(m[1]*v[0]+m[5]*v[1]+m[9]*v[2]+m[13])
            acc[2] += w*(m[2]*v[0]+m[6]*v[1]+m[10]*v[2]+m[14])
        verts.append(tuple(acc))
    return verts

from PIL import Image, ImageDraw, ImageFont
def cjk(sz):
    for p in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"):
        try: return ImageFont.truetype(p, sz)
        except Exception: pass
    return ImageFont.load_default()
F44, F30, F22, F20 = cjk(46), cjk(30), cjk(24), cjk(20)
SCALE, OX, OY = 156.0, 640, 700   # 收紧构图（承 -13）
def proj(p):
    x, y, z = p
    return (OX + (x - z*0.55) * SCALE, OY - (y + z*0.42) * SCALE)

N = 7; R = 1.45
def node_pos(i):
    a = 2*math.pi*i/N - math.pi/2
    return (R*math.cos(a), 0.0, R*math.sin(a))
FR = 14
frames = []
for fi in range(FR):
    im = Image.new("RGB", (1280, 800), (9, 10, 13)); d = ImageDraw.Draw(im)
    t = fi/(FR-1)
    bi = int(t*N) % N
    ang = 2*math.pi*t - math.pi/2
    ax, az = R*math.cos(ang), R*math.sin(ang)
    d.text((40, 26), "本地替身世界 v2（行迹驱动）· 第 %d/%d 帧 ｜ 拍：%s（%s）" % (
        fi+1, FR, BEATS[bi][0], BEATS[bi][1]), fill=(244,242,236), font=F44)
    d.text((40, 84), "★ 非平台世界模型；变化皆本席所写 ⇒ 不含涌现；朝向固定为正视（渲染选择）", fill=(196,170,150), font=F20)
    # 环与节点
    for i in range(N):
        p = node_pos(i); q = node_pos((i+1) % N)
        d.line([proj(p), proj(q)], fill=(40,44,52), width=2)
    for i, (nm, v, st) in enumerate(BEATS):
        p = node_pos(i); sx, sy = proj(p)
        cur = (i == bi)
        r = 11 if cur else 7
        d.ellipse([sx-r, sy-r, sx+r, sy+r], fill=(255,215,120) if cur else (110,150,175))
        d.text((sx-42, sy+12), "%s %s" % (nm, v), fill=(238,236,230) if cur else (150,152,158), font=F22)
    # 分身（固定正视；仍在环上位置）
    verts = skin(eval_anim(BEATS[bi][2], 0.6))
    xs = [v[0] for v in verts]; ys = [v[1] for v in verts]
    cx = (max(xs)+min(xs))/2
    bx, by = proj((ax, 0, az))
    tris = sorted(range(len(IDX)//3), key=lambda n: -(verts[IDX[n*3]][2]+verts[IDX[n*3+1]][2]+verts[IDX[n*3+2]][2]))
    for n in tris:
        pts = [(bx + (verts[IDX[n*3+j]][0]-cx)*SCALE, by - verts[IDX[n*3+j]][1]*SCALE) for j in range(3)]
        zavg = sum(verts[IDX[n*3+j]][2] for j in range(3))/3
        lum = int(150 + 70*max(0.0, min(1.0, (zavg+0.3)/0.6)))
        d.polygon(pts, fill=(lum, lum, min(255, lum+8)))
    d.text((40, 748), "资产：CAIRN_avatar v2_LOD1（1,176 三角／17 关节／4 权重蒙皮，五态）｜七拍数值取自本席台账（可溯源）", fill=(150,152,158), font=F20)
    frames.append(im)
png = SEAT/"exp"/"local_surrogate_v2_14frames_20261009.png"
cols, rows = 4, 4
tw, th = 320, 200
sheet = Image.new("RGB", (cols*tw, rows*th), (9,10,13))
for i, f in enumerate(frames):
    sheet.paste(f.resize((tw, th), Image.LANCZOS), ((i % cols)*tw, (i//cols)*th))
sheet.save(png, "PNG", optimize=True)
gif = SEAT/"exp"/"local_surrogate_v2_20261009.gif"
sm = [f.resize((640, 400), Image.LANCZOS) for f in frames]
sm[0].save(gif, save_all=True, append_images=sm[1:], duration=260, loop=0, optimize=True)
print("  ★ 接触表：%s（%.2f MB）" % (png.name, png.stat().st_size/1048576))
print("  ★ 动图：%s（%.2f MB，%d 帧）" % (gif.name, gif.stat().st_size/1048576, len(sm)))
print("  ★ 七拍数值：" + "／".join("%s %s" % (b[0], b[1]) for b in BEATS))
