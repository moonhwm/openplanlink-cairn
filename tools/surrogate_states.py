# -*- coding: utf-8 -*-
"""本地替身世界 · 五态正视对照图（同场景、同站位、仅换态 ⇒ 使"态"之差可辨）
（引号一律用「」）
"""
import json, math, pathlib, struct, sys

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
SEAT = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928")
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
def world_matrix(anim):
    W = {}
    order = sorted(range(len(js["nodes"])), key=lambda i: (lambda f: f(f, i))(lambda f, x: 0 if x not in PARENT else 1+f(f, PARENT[x])))
    for i in order:
        nd = js["nodes"][i]; t0 = list(nd.get("translation", [0,0,0])); q = list(nd.get("rotation", [0,0,0,1]))
        if i in anim: q = anim[i]
        loc = trs(t0, q)
        W[i] = loc if i not in PARENT else mul(W[PARENT[i]], loc)
    return W
def skin(anim):
    W = world_matrix(anim)
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
F44, F24, F20 = cjk(48), cjk(28), cjk(22)
STATES = [("IDLE_VERIFY", 1.0, "待核态"), ("WEIGH", 0.8, "天平加载"), ("INSPECT", 0.7, "放大镜抬起"),
          ("RELAY", 0.6, "数据流带点亮"), ("REFUSE", 0.5, "动作回弹")]
P, GAP = 356, 24
img = Image.new("RGB", (5*P + 6*GAP, 760), (9, 10, 13)); d = ImageDraw.Draw(img)
d.text((GAP+8, 20), "本地替身世界 · 五态正视对照（同场景、同站位、仅换态）", fill=(244, 242, 236), font=F44)
d.text((GAP+8, 84), "★ 非平台世界模型；全部变化由本席代码规定 ⇒ 不含涌现 ｜ 资产：CAIRN_avatar v2_LOD0（1,512 三角／17 关节／4 权重蒙皮）", fill=(196, 170, 150), font=F20)
for i, (nm, tv, cn) in enumerate(STATES):
    verts = skin(eval_anim(nm, tv))
    px = GAP + i*(P+GAP); py = 150
    d.rectangle([px, py, px+P, py+520], outline=(92, 96, 104), width=2)
    d.text((px+10, py+8), "%s" % nm, fill=(238, 236, 230), font=F20)
    d.text((px+10, py+38), "%s ｜ t=%.1fs" % (cn, tv), fill=(178, 176, 170), font=F20)
    xs = [v[0] for v in verts]; ys = [v[1] for v in verts]
    span = max(max(xs)-min(xs), max(ys)-min(ys)) or 1
    k = 400*0.86/span
    cx = (max(xs)+min(xs))/2; cy = (max(ys)+min(ys))/2
    # 地面参考线
    gy = py + 500
    d.line([px+20, gy, px+P-20, gy], fill=(60, 62, 68), width=2)
    tris = sorted(range(len(IDX)//3), key=lambda n: -(verts[IDX[n*3]][2]+verts[IDX[n*3+1]][2]+verts[IDX[n*3+2]][2]))
    for n in tris:
        pts = [(px+P/2 + (verts[IDX[n*3+j]][0]-cx)*k, py+360 - (verts[IDX[n*3+j]][1]-0.86)*k) for j in range(3)]
        zavg = sum(verts[IDX[n*3+j]][2] for j in range(3))/3
        lum = int(150 + 70*max(0.0, min(1.0, (zavg+0.3)/0.6)))
        d.polygon(pts, fill=(lum, lum, min(255, lum+8)))
    # 该态所挂钩之纪律（承 HY4 规范 §2.6）
    hook = {"IDLE_VERIFY": "默认", "WEIGH": "K-04 多通道判据", "INSPECT": "K-01/K-02",
            "RELAY": "K-03 落盘+短回执", "REFUSE": "B1–B3 边界"}[nm]
    d.text((px+10, py+478), "纪律挂钩：%s" % hook, fill=(200, 196, 190), font=F20)
png = SEAT/"exp"/"local_surrogate_states_20261009.png"
img.save(png, "PNG", optimize=True)
print("  ★ 五态正视对照图：%s（%.2f MB）" % (png.name, png.stat().st_size/1048576))
