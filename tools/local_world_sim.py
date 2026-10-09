# -*- coding: utf-8 -*-
"""本地替身世界（surrogate）：本席自产微型场景 ＋ CAIRN_avatar 按七拍行走 ＋ 五态轮转
★ 如实标注：非平台世界模型；一切变化皆由本席代码规定 ⇒ 不含涌现
输出：①N 帧接触表 PNG ②动图 GIF（引号一律用「」）
"""
import json, math, pathlib, struct, sys

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
SEAT = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928")
GLB = SEAT/"exp"/"CAIRN_avatar_v2_LOD1.glb"
raw = GLB.read_bytes()
jlen, _ = struct.unpack_from("<II", raw, 12); js = json.loads(raw[20:20+jlen].decode())
boff = 20+jlen; blen, _ = struct.unpack_from("<II", raw, boff); bn = raw[boff+8:boff+8+blen]
CT = {5123:("H",2), 5125:("I",4), 5126:("f",4)}; NC = {"SCALAR":1,"VEC3":3,"VEC4":4,"MAT4":16}
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
def eval_anim(anim_name, t):
    out = {}
    an = next((a for a in js["animations"] if a["name"] == anim_name), None)
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
                    u = (t-ti[k])/max(1e-9, ti[k+1]-ti[k])
                    q = [qq[k][m]*(1-u)+qq[k+1][m]*u for m in range(4)]; break
        n = math.sqrt(sum(v*v for v in q)) or 1.0
        out[ch["target"]["node"]] = [v/n for v in q]
    return out
def world_all(t, anim, root_extra):
    """全部节点之世界矩阵（含 root 额外平移/旋转）"""
    W, C = {}, {}
    order = sorted(range(len(js["nodes"])), key=lambda i: (lambda f: f(f, i))(lambda f, x: 0 if x not in PARENT else 1+f(f, PARENT[x])))
    for i in order:
        nd = js["nodes"][i]; t0 = list(nd.get("translation", [0, 0, 0])); q = list(nd.get("rotation", [0, 0, 0, 1]))
        if i in anim: q = anim[i]
        if i == 0:
            t0 = [t0[k] + root_extra[0][k] for k in range(3)]
            q = root_extra[1]
        loc = trs(t0, q)
        W[i] = loc if i not in PARENT else mul(W[PARENT[i]], loc)
    return W
def skin(W, translate=(0.0, 0.0, 0.0)):
    M = [mul(W[JN[k]], list(IBM[k])) for k in range(len(JN))]
    out = []
    for vi, v in enumerate(POS):
        acc = [translate[0], translate[1], translate[2]]
        for k in range(4):
            w = WTS[vi][k]
            if w <= 0: continue
            m = M[JTS[vi][k]]
            acc[0] += w*(m[0]*v[0]+m[4]*v[1]+m[8]*v[2]+m[12])
            acc[1] += w*(m[1]*v[0]+m[5]*v[1]+m[9]*v[2]+m[13])
            acc[2] += w*(m[2]*v[0]+m[6]*v[1]+m[10]*v[2]+m[14])
        out.append(tuple(acc))
    return out

# ── 场景：无门窗之居所（左壁数据链）＋地面七拍环＋底部灯带 ──
BEATS = ["游戏", "验收", "留痕", "器物", "自正", "复现", "暂止"]
STATES = ["IDLE_VERIFY", "WEIGH", "INSPECT", "RELAY", "REFUSE", "IDLE_VERIFY", "RELAY"]
R = 1.45
def scene_points():
    ring = [(R*math.cos(-math.pi/2 + i*2*math.pi/7), R*math.sin(-math.pi/2 + i*2*math.pi/7)) for i in range(7)]
    chain = [(-2.4 + k*0.30, -1.35 + k*0.16) for k in range(11)]
    return ring, chain

from PIL import Image, ImageDraw, ImageFont
def cjk(sz):
    for p in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"):
        try: return ImageFont.truetype(p, sz)
        except Exception: pass
    return ImageFont.load_default()
F34, F22, F18 = cjk(38), cjk(26), cjk(20)
W, H = 1280, 960
SCALE = 128.0     # px/m
OX, OY = 640, 780  # 地面原点
def proj(p3, yaw):
    """绕 Y 轴 yaw（度）后正交投影（略斜视以见地面环）"""
    a = math.radians(yaw)
    x, y, z = p3
    xr = x*math.cos(a) - z*math.sin(a); zr = x*math.sin(a) + z*math.cos(a)
    tilt = 0.42
    return (OX + xr*SCALE, OY - y*SCALE + zr*SCALE*tilt), zr
N = 14
frames = []
ring, chain = scene_points()
for fi in range(N):
    u = fi/(N-1)
    seg = u*6.0; si = min(6, int(seg)); lo = seg - si
    x0, y0 = ring[si]; x1, y1 = ring[(si+1) % 7]
    ax = x0 + (x1-x0)*lo; ay = y0 + (y1-y0)*lo
    st = STATES[si]
    tv = min(0.9, 0.2 + 0.7*abs(math.sin(seg*1.3)))
    yaw = math.degrees(math.atan2(ax, ay)) + 90
    anim = eval_anim(st, tv)
    Wm = world_all(tv, anim, ((ax, 0.0, ay), (0.0, 0.0, 0.0, 1.0)))
    verts = skin(Wm, translate=(0.0, 0.0, 0.0))
    img = Image.new("RGB", (W, H), (9, 10, 13)); d = ImageDraw.Draw(img)
    # 居所（无门窗）四面墙（以地面矩形示意）
    for cx, cy in ((-2.6, -2.2), (2.6, -2.2), (2.6, 2.2), (-2.6, 2.2)):
        p, _ = proj((cx, 0, cy), 0); d.ellipse([p[0]-3, p[1]-3, p[0]+3, p[1]+3], outline=(70, 72, 78))
    # 地面七拍环（含七枚节点）
    for i, (rx, ry) in enumerate(ring):
        p, _ = proj((rx, 0.02, ry), 0)
        lit = (i == si)
        rr = 16 if lit else 9
        d.ellipse([p[0]-rr, p[1]-rr, p[0]+rr, p[1]+rr], fill=(240, 226, 160) if lit else (96, 100, 108))
        d.text((p[0]-18, p[1]+rr+2), BEATS[i], fill=(240, 226, 160) if lit else (140, 142, 148), font=F18)
    # 数据链（左壁贯出）
    for (cx, cy) in chain:
        p, _ = proj((cx, 0.05, cy), 0); d.ellipse([p[0]-4, p[1]-4, p[0]+4, p[1]+4], fill=(150, 152, 160))
    # 底部灯带
    for k in range(24):
        xx = -2.8 + k*0.24
        p, _ = proj((xx, 0.0, -2.4), 0)
        g = 120 + int(80*abs(math.sin(k*0.5 + fi*0.7)))
        d.rectangle([p[0]-6, p[1]-3, p[0]+6, p[1]+3], fill=(g, g, min(255, g+10)))
    # 分身（按 z 排序画三角）
    tris = sorted(range(len(IDX)//3), key=lambda n: -(verts[IDX[n*3]][2]+verts[IDX[n*3+1]][2]+verts[IDX[n*3+2]][2]))
    for n in tris:
        pts = []
        for i in range(3):
            v = verts[IDX[n*3+i]]
            p, _ = proj((v[0]+ax, v[1], v[2]+ay), yaw)
            pts.append(p)
        zavg = sum(verts[IDX[n*3+i]][2] for i in range(3))/3
        lum = int(150 + 70*max(0.0, min(1.0, (zavg+0.3)/0.6)))
        d.polygon(pts, fill=(lum, lum, min(255, lum+8)))
    # 题头
    d.text((40, 30), "本地替身世界（surrogate）· 第 %d/%d 帧 ｜ 拍：%s ｜ 态：%s" % (fi+1, N, BEATS[si], st), fill=(244, 242, 236), font=F34)
    d.text((40, 92), "★ 非平台世界模型；场景与分身之全部变化皆由本席代码规定 ⇒ 不含涌现（如实标注）", fill=(196, 170, 150), font=F18)
    d.text((40, 126), "资产：CAIRN_avatar v2_LOD1（1,176 三角／17 关节／4 权重蒙皮／五态）｜世界模型资格受阻期间之本地替身", fill=(168, 172, 178), font=F18)
    d.text((40, H-40), "七拍：游戏→验收→留痕→器物→自正→复现→暂止 ｜ 本席自产、零第三方 3D 库、零付费", fill=(160, 162, 168), font=F18)
    frames.append(img)

# 接触表（3×5）
cols, rows = 5, 3; cw, ch = 384, 288
sheet = Image.new("RGB", (cols*cw, rows*ch), (6, 7, 9))
for i, f in enumerate(frames):
    sheet.paste(f.resize((cw, ch)), ((i % cols)*cw, (i//cols)*ch))
sheet_p = SEAT/"exp"/"local_surrogate_world_14frames_20261009.png"
sheet.save(sheet_p, "PNG", optimize=True)
gif_p = SEAT/"exp"/"local_surrogate_world_20261009.gif"
frames[0].save(gif_p, save_all=True, append_images=frames[1:], duration=420, loop=0, optimize=True)
print("  ★ 接触表：%s（%.2f MB）" % (sheet_p.name, sheet_p.stat().st_size/1048576))
print("  ★ 动图：%s（%.2f MB，%d 帧）" % (gif_p.name, gif_p.stat().st_size/1048576, len(frames)))
print("  ★ 场景：地面七拍环（半径 %.2f m）＋左壁数据链 11 点＋底部灯带 24 段；分身沿环行走、逐拍换态" % R)
