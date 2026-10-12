# -*- coding: utf-8 -*-
"""分身之行走循环 v3 · 侧视图：程序化骨骼动画（同一相位式，改相机沿 X 轴投影）（髋/膝/踝/肩/脊柱相位摆动 ＋ 骨盆起伏）
★ 承「个人基于人设的动态完善 3D 建模」：现仅五静态态 ⇒ 本件加"动态步态"
输出：14 帧接触表 ＋ GIF ＋ 相位核查表（独立复核）
（引号一律用「」）
"""
import json, math, pathlib, struct, sys

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
SEAT = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"
GLB = SEAT/"exp"/"CAIRN_avatar_v2_LOD1.glb"
raw = GLB.read_bytes()
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
NAME = {i: js["nodes"][i].get("name","?") for i in range(len(js["nodes"]))}
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
def qx(deg):
    a = math.radians(deg)/2
    return (math.sin(a), 0.0, 0.0, math.cos(a))
def qz(deg):
    a = math.radians(deg)/2
    return (0.0, 0.0, math.sin(a), math.cos(a))
def qmul(q1, q2):
    x1,y1,z1,w1 = q1; x2,y2,z2,w2 = q2
    return (w1*x2+x1*w2+y1*z2-z1*y2, w1*y2-x1*z2+y1*w2+z1*x2,
            w1*z2+x1*y2-y1*x2+z1*w2, w1*w2-x1*x2-y1*y2-z1*z2)

def walk_pose(ph):
    """ph∈[0,1)：一步周期。返回 {关节名: 四元数} 与骨盆纵向偏移（米）"""
    A = 2*math.pi*ph
    hipL = 26.0*math.sin(A)             # 左髋：前摆为正
    hipR = 26.0*math.sin(A + math.pi)
    kneeL = -max(0.0, 34.0*math.sin(A - 0.9))    # 膝：单向屈（负角）
    kneeR = -max(0.0, 34.0*math.sin(A + math.pi - 0.9))
    footL = 8.0*math.sin(A + 1.6)
    footR = 8.0*math.sin(A + math.pi + 1.6)
    shoL = -18.0*math.sin(A)            # 左肩与左腿反相（自然对侧摆）
    shoR = -18.0*math.sin(A + math.pi)
    elbL = -14.0 - 8.0*math.sin(A + 0.6)
    elbR = -14.0 - 8.0*math.sin(A + math.pi + 0.6)
    spine = 3.0*math.sin(2*A)           # 脊柱：双频微摆
    chest = 2.0*math.sin(2*A + 1.0)
    head = 2.0*math.sin(A)              # 头部：单频轻点
    bob = 0.022*abs(math.cos(A)) - 0.011   # 骨盆起伏（双频，±1.1 cm）
    return {
        "CAIRN_Hip_L": qx(hipL), "CAIRN_Hip_R": qx(hipR),
        "CAIRN_Knee_L": qx(kneeL), "CAIRN_Knee_R": qx(kneeR),
        "CAIRN_Foot_L": qx(footL), "CAIRN_Foot_R": qx(footR),
        "CAIRN_Shoulder_L": qx(shoL), "CAIRN_Shoulder_R": qx(shoR),
        "CAIRN_Elbow_L": qx(elbL), "CAIRN_Elbow_R": qx(elbR),
        "CAIRN_Spine": qx(spine), "CAIRN_Chest": qx(chest), "CAIRN_Head": qx(head),
    }, bob, {"hipL": hipL, "hipR": hipR, "kneeL": kneeL, "kneeR": kneeR, "bob_mm": bob*1000}

def skin(overrides, bob):
    W = {}
    order = sorted(range(len(js["nodes"])), key=lambda i: (lambda f: f(f, i))(lambda f, x: 0 if x not in PARENT else 1+f(f, PARENT[x])))
    for i in order:
        nd = js["nodes"][i]; t0 = list(nd.get("translation", [0,0,0])); q = list(nd.get("rotation", [0,0,0,1]))
        nm = NAME[i]
        if nm in overrides:
            q = list(overrides[nm])
        if nm == "CAIRN_Pelvis":
            t0 = [t0[0], t0[1] + bob, t0[2]]
        loc = trs(t0, q); W[i] = loc if i not in PARENT else mul(W[PARENT[i]], loc)
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
F42, F20 = cjk(44), cjk(20)
S = 200.0
frames, phases = [], []
for fi in range(14):
    ph = fi/14.0
    ov, bob, rec = walk_pose(ph)
    verts = skin(ov, bob)
    phases.append(rec)
    im = Image.new("RGB", (760, 620), (9,10,13)); d = ImageDraw.Draw(im)
    d.text((18, 18), "分身行走循环 v3 · ★侧视图 · 第 %d/14 帧 ｜ 相位 %.3f" % (fi+1, ph), fill=(244,242,236), font=F42)
    d.text((18, 74), "★侧视（沿 X 轴投影）：步态最可辨 ｜ 髋±26°/膝单向屈/骨盆±1.1cm ｜ 资产 CAIRN_avatar v2_LOD1（低模）", fill=(196,170,150), font=F20)
    cx, cy = 380, 470
    xs = [v[0] for v in verts]; ys = [v[1] for v in verts]
    mz = (max(v[2] for v in verts)+min(v[2] for v in verts))/2
    tris = sorted(range(len(IDX)//3), key=lambda n: -(verts[IDX[n*3]][2]+verts[IDX[n*3+1]][2]+verts[IDX[n*3+2]][2]))
    for n in tris:
        pts = [(cx + (verts[IDX[n*3+j]][2]-mz)*S, cy - (verts[IDX[n*3+j]][1]-0.05)*S) for j in range(3)]
        zavg = sum(-verts[IDX[n*3+j]][0] for j in range(3))/3
        lum = int(150 + 70*max(0.0, min(1.0, (zavg+0.3)/0.6)))
        d.polygon(pts, fill=(lum, lum, min(255, lum+8)))
    d.line([60, cy, 700, cy], fill=(52,54,60), width=2)
    d.text((18, 560), "髋 L/R %+6.1f°/%+6.1f° ｜ 膝 L/R %+6.1f°/%+6.1f° ｜ 骨盆 %+5.1f mm" % (
        rec["hipL"], rec["hipR"], rec["kneeL"], rec["kneeR"], rec["bob_mm"]), fill=(180,178,172), font=F20)
    frames.append(im)
png = SEAT/"exp"/"CAIRN_avatar_walk_side_v3_14frames_20261009.png"
cols, rows, tw, th = 4, 4, 380, 310
sheet = Image.new("RGB", (cols*tw, rows*th), (9,10,13))
for i, f in enumerate(frames):
    sheet.paste(f.resize((tw, th), Image.LANCZOS), ((i % cols)*tw, (i//cols)*th))
sheet.save(png, "PNG", optimize=True)
gif = SEAT/"exp"/"CAIRN_avatar_walk_side_v3_20261009.gif"
sm = [f.resize((570, 465), Image.LANCZOS) for f in frames]
sm[0].save(gif, save_all=True, append_images=sm[1:], duration=90, loop=0, optimize=True)
print("  ★ 接触表：%s（%.2f MB）" % (png.name, png.stat().st_size/1048576))
print("  ★ 动图：%s（%.2f MB，%d 帧）" % (gif.name, gif.stat().st_size/1048576, len(sm)))
print("  === 相位核查（独立复核：跨度为整周期、膝只单向屈、骨盆双频）===")
for i, r in enumerate(phases):
    print("   帧 %2d ｜ 髋 L %+6.1f° R %+6.1f° ｜ 膝 L %+6.1f° R %+6.1f° ｜ 骨盆 %+5.1f mm" % (
        i+1, r["hipL"], r["hipR"], r["kneeL"], r["kneeR"], r["bob_mm"]))
hipL = [r["hipL"] for r in phases]; kneeL = [r["kneeL"] for r in phases]
print("   ⇒ 髋 L 之范围 %.1f°–%.1f°（应为 ±26）｜ 膝 L 之范围 %.1f°–%.1f°（应为 −34–0，只单向屈）｜ 骨盆范围 %+.1f–%+.1f mm" % (
    min(hipL), max(hipL), min(kneeL), max(kneeL), min(r["bob_mm"] for r in phases), max(r["bob_mm"] for r in phases)))
