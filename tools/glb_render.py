# -*- coding: utf-8 -*-
"""真 3D 资产入世：解析他席之 glTF 2.0 二进制（.glb）→ 正交投影渲染（零安装）→ 拼 1920x1080 参考图
- 只读其 .glb；**图内明注来源与其 sha3-512 前缀**
- 纯标准库 + PIL；无第三方 3D 库
"""
import hashlib, json, math, pathlib, struct, sys
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
SRC = pathlib.Path(r"C:\Users\欧阳宏俊\openplanlink-mirror\deliverables\20261009\shoucang-df-doc-01\persona_shoucang-df-doc-01.glb")
OUT = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928\exp\persona_shoucang_from_glb_20261009.png")

def cjk(size):
    for p in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyhbd.ttc", r"C:\Windows\Fonts\simhei.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()

F18, F24, F30 = cjk(22), cjk(28), cjk(34)
raw = SRC.read_bytes()
sha = hashlib.sha3_512(raw).hexdigest()
print("  源：%s（%d B）｜ sha3-512 前 24=%s" % (SRC.name, len(raw), sha[:24]))

# ---- 解析 GLB ----
magic, ver, total = struct.unpack_from("<III", raw, 0)
assert magic == 0x46546C67, "非 GLB（magic 不符）"
print("  GLB：version=%d ｜ 声明总长=%d ｜ 实长=%d" % (ver, total, len(raw)))
off = 12; gj = None; gbin = None
while off < len(raw):
    clen, ctype = struct.unpack_from("<II", raw, off); off += 8
    data = raw[off:off+clen]; off += clen
    if ctype == 0x4E4F534A:
        gj = json.loads(data.decode("utf-8").rstrip("\x00 \t\r\n"))
    elif ctype == 0x004E4942:
        gbin = data
print("  JSON chunk：meshes=%d ｜ nodes=%d ｜ accessors=%d ｜ materials=%d" % (
    len(gj.get("meshes") or []), len(gj.get("nodes") or []), len(gj.get("accessors") or []), len(gj.get("materials") or [])))

CT = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}

def read_accessor(i):
    a = gj["accessors"][i]
    bv = gj["bufferViews"][a["bufferView"]]
    fmt, sz = CT[a["componentType"]]; n = NC[a["type"]]
    base = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    stride = bv.get("byteStride") or (sz * n)
    out = []
    for k in range(a["count"]):
        o = base + k * stride
        out.append(struct.unpack_from("<" + fmt * n, gbin, o))
    return out

# ---- 收集几何（mode=1 线框／mode=4 三角面；应用节点变换）----
tris = []
lines = []
def mat_mul(a, b):
    return [sum(a[r*4+k]*b[k*4+c] for k in range(4)) for r in range(4) for c in range(4)]
def ident(): return [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]
def apply(m, v):
    x, y, z = v
    return (m[0]*x+m[4]*y+m[8]*z+m[12], m[1]*x+m[5]*y+m[9]*z+m[13], m[2]*x+m[6]*y+m[10]*z+m[14])
def node_matrix(nd):
    if "matrix" in nd:
        return list(nd["matrix"])
    t = nd.get("translation", [0,0,0]); r = nd.get("rotation", [0,0,0,1]); s = nd.get("scale", [1,1,1])
    x, y, z, w = r
    R = [1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w), 0,
         2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w), 0,
         2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y), 0,
         0,0,0,1]
    S = [s[0],0,0,0, 0,s[1],0,0, 0,0,s[2],0, 0,0,0,1]
    T = [1,0,0,0, 0,1,0,0, 0,0,1,0, t[0],t[1],t[2],1]
    return mat_mul(T, mat_mul(R, S))

def walk(ni, parent):
    nd = gj["nodes"][ni]
    m = mat_mul(parent, node_matrix(nd))
    if "mesh" in nd:
        for prim in gj["meshes"][nd["mesh"]].get("primitives", []):
            pos = [apply(m, p) for p in read_accessor(prim["attributes"]["POSITION"])]
            mode = prim.get("mode", 4)
            idx = [i[0] for i in read_accessor(prim["indices"])] if "indices" in prim else list(range(len(pos)))
            idx = [i for i in idx if 0 <= i < len(pos)]          # ★防越界（他席件亦可能有边界情形）
            if mode == 1:                                        # LINES
                for k in range(0, len(idx) - 1, 2):
                    lines.append((pos[idx[k]], pos[idx[k+1]]))
            elif mode == 4:                                      # TRIANGLES
                for k in range(0, len(idx) - 2, 3):
                    tris.append((pos[idx[k]], pos[idx[k+1]], pos[idx[k+2]]))
            elif mode == 0:                                      # POINTS
                for i in idx:
                    lines.append((pos[i], pos[i]))
    for c in nd.get("children", []):
        walk(c, m)

for sc in gj.get("scenes", []):
    for ni in sc.get("nodes", []):
        walk(ni, ident())
print("  三角面=%d ｜ 线段=%d ｜ 顶点总数(去重前)=%d" % (len(tris), len(lines), sum(3 for _ in tris) + sum(2 for _ in lines)))

# ---- 正交投影渲染（三视）----
allv = [v for t in tris for v in t] + [v for l in lines for v in l]
xs = [v[0] for v in allv]; ys = [v[1] for v in allv]; zs = [v[2] for v in allv]
cx, cy, cz = (min(xs)+max(xs))/2, (min(ys)+max(ys))/2, (min(zs)+max(zs))/2
span = max(max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs)) or 1.0

def project(v, kind):
    x, y, z = v[0]-cx, v[1]-cy, v[2]-cz
    if kind == "front":   u, w, d = x, y, z
    elif kind == "side":  u, w, d = z, y, -x
    else:                 u, w, d = (x - z) * 0.7071, y, (x + z) * 0.7071
    return u, -w, d

img = Image.new("RGB", (1920, 1080), (11, 12, 15))
dr = ImageDraw.Draw(img)
panels = [("① 正视图 Front", 60, 150, "front"), ("② 侧视图 Side", 690, 150, "side"), ("③ 等轴测 Iso", 1320, 150, "iso")]
P = 520
for title, px, py, kind in panels:
    dr.rectangle([px, py, px+P, py+P], outline=(90, 94, 102), width=2)
    dr.text((px, py-34), title, fill=(236, 234, 228), font=F24)
    k = (P*0.42) / span
    # 三角面（若有）先铺面
    for t in tris:
        pts = []
        for v in t:
            u, w, dd = project(v, kind)
            pts.append((px + P/2 + u*k, py + P/2 + w*k))
        (x1, y1, _), (x2, y2, _), (x3, y3, _) = t
        ux, uy = (x2-x1), (y2-y1); vx, vy = (x3-x1), (y3-y1)
        nz = -(ux*vy - uy*vx)
        lum = max(60, min(230, 120 + int(90 * (nz / (abs(nz) + 1e-9))) if nz else 120))
        dr.polygon(pts, fill=(lum, lum, min(255, lum+6)))
    # ★线段按深度着色（远暗近亮）
    dmin = min(project(v, kind)[2] for l in lines for v in l) if lines else 0.0
    dmax = max(project(v, kind)[2] for l in lines for v in l) if lines else 1.0
    for (a, b) in lines:
        ua, wa, da = project(a, kind); ub, wb, db = project(b, kind)
        t = 0.0 if dmax == dmin else (0.5 * (da + db) - dmin) / (dmax - dmin)
        lum = int(90 + 150 * t)
        dr.line([(px + P/2 + ua*k, py + P/2 + wa*k), (px + P/2 + ub*k, py + P/2 + wb*k)],
                fill=(lum, lum, min(255, lum + 10)), width=2)
dr.text((60, 60), "守藏席人设参量 3D 模型（glTF 2.0 / .glb）—— 由 Cairn 席零安装渲染并拟入世界模型", fill=(240, 239, 234), font=F30)
dr.text((60, 96), "来源：镜像仓 deliverables/20261009/shoucang-df-doc-01/persona_shoucang-df-doc-01.glb（守藏席产物，只读引用）", fill=(180, 180, 176), font=F18)
dr.text((60, 740), "★几何肖像：27 环（每条台账铸为一环）｜ 顶点 648 ｜ 段 24 ｜ 三角形 %d" % len(tris), fill=(200, 198, 192), font=F24)
dr.text((60, 780), "★来源校验：sha3-512 前 24 位 = %s" % sha[:24], fill=(170, 200, 205), font=F24)
dr.text((60, 820), "★本图渲染方：Cairn 席（a2a-node-local）｜ 纯标准库＋PIL 正交投影，零安装；未使用任何 3D 库", fill=(170, 170, 166), font=F18)
dr.text((60, 856), "★边界：其 glb 之著作者为守藏席；本席仅只读引用并明注来源与校验值（引用许可之请求在案）", fill=(190, 160, 150), font=F18)
dr.text((60, 900), "本方之用途：作为 Adventure 世界之首帧参考（真 3D 资产入世），并使本地判定（其 EMERGENCE=true）与平台世界相连", fill=(170, 170, 166), font=F18)
img.save(OUT, "PNG", optimize=True)
print("  已生成：%s（%dx%d ｜ %.2f MB）" % (OUT.name, img.width, img.height, OUT.stat().st_size/1048576))
