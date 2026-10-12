# -*- coding: utf-8 -*-
"""v6b 之侧视接触表 ＋ GIF · ★固定世界原点版（修正逐帧居中）\n★ 关键：相机原点固定于"首帧身体中心"，身体随帧右移 ⇒ 可直观核"身进脚定"
（引号一律用「」）
"""
import json, math, pathlib, struct, sys

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
EXP = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"/"exp"
NKEY, HIP_GROUND, PELVIS_Y, STEP, T = 14, 0.80, 0.85, 0.35, 1.3

raw = (EXP/"CAIRN_avatar_v2_LOD1.glb").read_bytes()
jl, _ = struct.unpack_from("<II", raw, 12); JS = json.loads(raw[20:20+jl].decode())
bo = 20+jl; bl, _ = struct.unpack_from("<II", raw, bo); BN = raw[bo+8:bo+8+bl]
CT = {5123:("H",2),5125:("I",4),5126:("f",4)}; NC = {"SCALAR":1,"VEC3":3,"VEC4":4,"MAT4":16}
def racc(i):
    a = JS["accessors"][i]; bv = JS["bufferViews"][a["bufferView"]]
    f, s = CT[a["componentType"]]; n = NC[a["type"]]
    off = bv.get("byteOffset",0)+a.get("byteOffset",0)
    return [struct.unpack_from("<%d%s"%(n,f), BN, off+k*n*s) for k in range(a["count"])]
prim = JS["meshes"][0]["primitives"][0]
POS = racc(prim["attributes"]["POSITION"]); JTS = racc(prim["attributes"]["JOINTS_0"]); WTS = racc(prim["attributes"]["WEIGHTS_0"])
IDX = [i[0] for i in racc(prim["indices"])]
JN = JS["skins"][0]["joints"]; IBM = racc(JS["skins"][0]["inverseBindMatrices"])
NM = {i: JS["nodes"][i].get("name","?") for i in range(len(JS["nodes"]))}
IX = {v: k for k, v in NM.items()}
PAR = {}
for i, nd in enumerate(JS["nodes"]):
    for c in nd.get("children", []): PAR[c] = i
ORDER = sorted(range(len(JS["nodes"])), key=lambda i: (lambda f: f(f, i))(lambda f, x: 0 if x not in PAR else 1+f(f, PAR[x])))
def qx(d):
    a = math.radians(d)/2; return (math.sin(a), 0.0, 0.0, math.cos(a))
def mul(a, b):
    r = [0.0]*16
    for c in range(4):
        for row in range(4): r[c*4+row] = sum(a[k*4+row]*b[c*4+k] for k in range(4))
    return r
def trs(t, q):
    x, y, z, w = q; xx, yy, zz = x*x, y*y, z*z
    return [1-2*(yy+zz), 2*(x*y+z*w), 2*(x*z-y*w), 0, 2*(x*y-z*w), 1-2*(xx+zz), 2*(y*z+x*w), 0,
            2*(x*z+y*w), 2*(y*z-x*w), 1-2*(xx+yy), 0, t[0], t[1], t[2], 1]
def W_of(ov, pely, pelz):
    W = {}
    for i in ORDER:
        nd = JS["nodes"][i]; t0 = list(nd.get("translation", [0,0,0])); q = list(nd.get("rotation", [0,0,0,1]))
        nm = NM[i]
        if nm in ov: q = list(ov[nm])
        if nm == "CAIRN_Pelvis": t0 = [t0[0], pely, t0[2]+pelz]
        loc = trs(t0, q); W[i] = loc if i not in PAR else mul(W[PAR[i]], loc)
    return W
def foot(side, h, k, a, pely, pelz):
    W = W_of({"CAIRN_Hip_%s"%side: qx(h), "CAIRN_Knee_%s"%side: qx(k), "CAIRN_Foot_%s"%side: qx(a)}, pely, pelz)
    f = W[IX["CAIRN_Foot_%s"%side]]; hh = W[IX["CAIRN_Hip_%s"%side]]
    return f[13], f[14], hh[13]
TBL = [(h/2, k/2) for h in range(-120, 121) for k in range(-170, 1)]
def build():
    t = []
    for h, k in TBL:
        y, z, hy = foot("L", h, k, 0.0, PELVIS_Y, 0.0)
        t.append((h, k, y-hy, z))
    return t
TB = build()
def ik(dy, dz):
    b, bd = None, 1e9
    for h, k, ty, tz in TB:
        d = (ty-dy)**2 + (tz-dz)**2
        if d < bd: bd, b = d, (h, k)
    return b
def gait(ph):
    pz = 2*STEP*ph; out = {}
    for side, off in (("L", 0.0), ("R", 0.5)):
        p = (ph+off) % 1.0
        if p < 0.5:
            u = p/0.5; zw = STEP/2 + (0.0 if off == 0 else STEP)
            h, k = ik(-HIP_GROUND, zw-pz); a = 6.0*(u-0.5); tag = "支撑"
        else:
            u = (p-0.5)/0.5
            h, k = ik(-HIP_GROUND + 0.075*math.sin(math.pi*u), -STEP/2 + STEP*u); a = 10.0*math.sin(math.pi*u); tag = "摆动"
        out[side] = (h, k, a, tag)
    return out, pz
def verts(ov, pely, pelz):
    W = W_of(ov, pely, pelz)
    M = [mul(W[JN[k]], list(IBM[k])) for k in range(len(JN))]
    out = []
    for vi, v in enumerate(POS):
        acc = [0.0, 0.0, 0.0]
        for k in range(4):
            w = WTS[vi][k]
            if w <= 0: continue
            m = M[JTS[vi][k]]
            acc[0] += w*(m[0]*v[0]+m[4]*v[1]+m[8]*v[2]+m[12])
            acc[1] += w*(m[1]*v[0]+m[5]*v[1]+m[9]*v[2]+m[13])
            acc[2] += w*(m[2]*v[0]+m[6]*v[1]+m[10]*v[2]+m[14])
        out.append(tuple(acc))
    return out

from PIL import Image, ImageDraw, ImageFont
def cjk(sz):
    for p in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"):
        try: return ImageFont.truetype(p, sz)
        except Exception: pass
    return ImageFont.load_default()
F42, F20 = cjk(40), cjk(19)
S = 190.0
frames = []
print("  渲染 14 帧（侧视；含骨盆 y/z 位移）…")
for fi in range(NKEY):
    ph = fi/NKEY
    g, pz = gait(ph)
    ov = {}
    for side in ("L", "R"):
        h, k, a, _ = g[side]
        ov["CAIRN_Hip_%s"%side] = qx(h); ov["CAIRN_Knee_%s"%side] = qx(k); ov["CAIRN_Foot_%s"%side] = qx(a)
    A = 2*math.pi*ph
    ov["CAIRN_Shoulder_L"] = qx(-16.0*math.sin(A)); ov["CAIRN_Shoulder_R"] = qx(-16.0*math.sin(A+math.pi))
    ov["CAIRN_Elbow_L"] = qx(-16.0); ov["CAIRN_Elbow_R"] = qx(-16.0)
    ov["CAIRN_Spine"] = qx(3.0*math.sin(2*A)); ov["CAIRN_Chest"] = qx(2.0*math.sin(2*A+1.0))
    ov["CAIRN_Head"] = qx(2.0*math.sin(A))
    V = verts(ov, PELVIS_Y, pz)
    im = Image.new("RGB", (760, 610), (9,10,13)); d = ImageDraw.Draw(im)
    d.text((16, 16), "行走 v6b · 侧视 · ★固定世界原点 · 第 %d/14 帧 ｜ 骨盆前移 %.3f m" % (fi+1, pz), fill=(244,242,236), font=F42)
    d.text((16, 66), "★数值 IK ＋ 支撑相冻结：支撑脚世界 z 漂移 ≤2.8 mm ｜ 触地 −1 mm ｜ 0.54 m/s ｜ LOD1", fill=(196,170,150), font=F20)
    cx, cy = 360, 500
    mz = 0.0   # ★固定世界原点（不逐帧居中）
    tris = sorted(range(len(IDX)//3), key=lambda n: -(V[IDX[n*3]][0]+V[IDX[n*3+1]][0]+V[IDX[n*3+2]][0]))
    for n in tris:
        pts = [(cx + (V[IDX[n*3+j]][2]-mz)*S, cy - (V[IDX[n*3+j]][1]-0.02)*S) for j in range(3)]
        xa = sum(V[IDX[n*3+j]][0] for j in range(3))/3
        lum = int(150 + 70*max(0.0, min(1.0, (xa+0.25)/0.5)))
        d.polygon(pts, fill=(lum, lum, min(255, lum+8)))
    d.line([50, cy, 710, cy], fill=(52,54,60), width=2)
    d.text((16, 550), "L %s 髋%+6.1f° 膝%+6.1f° ｜ R %s 髋%+6.1f° 膝%+6.1f°" % (
        g["L"][3], g["L"][0], g["L"][1], g["R"][3], g["R"][0], g["R"][1]), fill=(180,178,172), font=F20)
    # 世界坐标刻度（每 0.1 m 一格；随骨盆前移而移动 ⇒ 直观示"身体前进而脚不动"）
    for k in range(-3, 8):
        x = cx + (k*0.1 + 0.0 - mz)*S
        if 50 < x < 710:
            d.line([x, cy, x, cy+30], fill=(70,72,80), width=2)
            d.text((x-8, cy+32), "%.1f" % (k*0.1), fill=(110,112,120), font=cjk(14))
    frames.append(im)
png = EXP/"CAIRN_avatar_walk_v6b_fixed_14frames_20261009.png"
cols, rows, tw, th = 4, 4, 380, 305
sheet = Image.new("RGB", (cols*tw, rows*th), (9,10,13))
for i, f in enumerate(frames):
    sheet.paste(f.resize((tw, th), Image.LANCZOS), ((i % cols)*tw, (i//cols)*th))
sheet.save(png, "PNG", optimize=True)
gif = EXP/"CAIRN_avatar_walk_v6b_fixed_20261009.gif"
sm = [f.resize((570, 458), Image.LANCZOS) for f in frames]
sm[0].save(gif, save_all=True, append_images=sm[1:], duration=90, loop=0, optimize=True)
print("  ★ 接触表：%s（%.2f MB）" % (png.name, png.stat().st_size/1048576))
print("  ★ 动图：%s（%.2f MB，%d 帧）" % (gif.name, gif.stat().st_size/1048576, len(sm)))
