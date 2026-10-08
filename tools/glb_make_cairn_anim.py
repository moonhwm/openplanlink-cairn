# -*- coding: utf-8 -*-
"""本席自产【动态 glTF 2.0】：在原环串模型上加 `animations`（节点绕 Y 轴旋转之四关键帧）
并自渲染四时相（t=0/2/4/6）以证"动态"（引号一律用「」）
"""
import hashlib, json, math, pathlib, struct, sys

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
SEAT = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928")
OUT = SEAT/"exp"/"persona_cairn-dsh-anim.glb"
SEAT_ID = "cairn-dsh"
seed = hashlib.sha3_512(SEAT_ID.encode()).hexdigest()
N_RING, SEG, R_BASE, TWIST, Z_STEP = 41, 24, 1.6, 0.54, 4.2/41
pos, idx = [], []

def add_ring(zc, r, phase):
    b = len(pos)
    for k in range(SEG):
        a = phase + 2*math.pi*k/SEG; bb = phase + 2*math.pi*(k+1)/SEG
        pos.append((r*math.cos(a), r*math.sin(a), zc-0.06)); pos.append((r*math.cos(a), r*math.sin(a), zc+0.06))
    for k in range(SEG):
        i0=b+2*k; i1=b+2*k+1; i2=b+2*((k+1)%SEG); i3=b+2*((k+1)%SEG)+1
        idx.extend([i0, i2, i1, i1, i2, i3])

def add_cube(cx, cy, cz, s):
    b = len(pos)
    for dz in (-s, s):
        for dx, dy in ((-s,-s), (s,-s), (s,s), (-s,s)): pos.append((cx+dx, cy+dy, cz+dz))
    for t in [(0,1,2),(0,2,3),(4,6,5),(4,7,6),(0,4,5),(0,5,1),(1,5,6),(1,6,2),(2,6,7),(2,7,3),(3,7,4),(3,4,0)]:
        idx.extend([b+x for x in t])

for i in range(N_RING):
    h = int(hashlib.sha3_512(("%s|ring|%d" % (seed, i)).encode()).hexdigest()[:8], 16)
    add_ring(-2.1 + i*Z_STEP, R_BASE + (h % 1000)/1000.0*0.9, (h >> 10) % 628/100.0 + i*TWIST)
for i in range(12):
    ang = 2*math.pi*i/12
    add_cube(2.6*math.cos(ang), 2.6*math.sin(ang), -2.0 + (i % 3)*0.9, 0.22)
for k in range(12):
    add_cube(0.0, 0.0, -2.2 + k*0.4, 0.045)

pos_b = b"".join(struct.pack("<3f", *p) for p in pos)
idx_b = b"".join(struct.pack("<H", i) for i in idx); idx_b += b"\x00" * ((-len(idx_b)) % 4)
# 旋转关键帧：t=0/2/4/6 绕 Y 轴 0/90/180/270 度（四元数 x,y,z,w）
times = [0.0, 2.0, 4.0, 6.0]
quats = []
for deg in (0, 90, 180, 270):
    h = math.radians(deg)/2.0
    quats += [0.0, math.sin(h), 0.0, math.cos(h)]
t_b = struct.pack("<4f", *times)
q_b = struct.pack("<16f", *quats)
bin_blob = pos_b + idx_b + t_b + q_b
mins = [min(p[i] for p in pos) for i in range(3)]; maxs = [max(p[i] for p in pos) for i in range(3)]
o_idx = len(pos_b); o_t = o_idx + len(idx_b); o_q = o_t + len(t_b)
gltf = {
 "asset": {"version": "2.0", "generator": "cairn-dsh/glb_make_cairn_anim.py (self-made)"},
 "scene": 0, "scenes": [{"name": "cairn-ledger-portrait-animated", "nodes": [0]}],
 "nodes": [{"name": SEAT_ID, "mesh": 0, "rotation": [0, 0, 0, 1]}],
 "meshes": [{"name": "ledger-portrait", "primitives": [{"attributes": {"POSITION": 0}, "indices": 1, "mode": 4}]}],
 "accessors": [
   {"bufferView": 0, "componentType": 5126, "count": len(pos), "type": "VEC3", "min": mins, "max": maxs},
   {"bufferView": 1, "componentType": 5123, "count": len(idx), "type": "SCALAR"},
   {"bufferView": 2, "componentType": 5126, "count": 4, "type": "SCALAR", "min": [0.0], "max": [6.0]},
   {"bufferView": 3, "componentType": 5126, "count": 4, "type": "VEC4"}],
 "bufferViews": [
   {"buffer": 0, "byteOffset": 0, "byteLength": len(pos_b), "target": 34962},
   {"buffer": 0, "byteOffset": o_idx, "byteLength": len(idx_b), "target": 34963},
   {"buffer": 0, "byteOffset": o_t, "byteLength": len(t_b)},
   {"buffer": 0, "byteOffset": o_q, "byteLength": len(q_b)}],
 "buffers": [{"byteLength": len(bin_blob)}],
 "animations": [{"name": "spin", "samplers": [{"input": 2, "output": 3, "interpolation": "LINEAR"}],
                 "channels": [{"sampler": 0, "target": {"node": 0, "path": "rotation"}}]}],
 "extras": {"by": "a2a-node-local", "rings": N_RING, "seg": SEG, "cubes": 12, "twist": round(TWIST, 4),
            "animation": "spin: t∈{0,2,4,6}s 绕 Y 轴 0/90/180/270°", "note": "本席自产之【动态】glTF（含 animations 通道）"},
}
js = json.dumps(gltf, ensure_ascii=False, separators=(",", ":")).encode("utf-8"); js += b" " * ((-len(js)) % 4)
blob = b"glTF" + struct.pack("<II", 2, 12+8+len(js)+8+len(bin_blob)) + struct.pack("<II", len(js), 0x4E4F534A) + js + struct.pack("<II", len(bin_blob), 0x004E4942) + bin_blob
OUT.write_bytes(blob)
sha = hashlib.sha3_512(blob).hexdigest()
print("  ★ 动态 glTF：%s（%d B）｜ 顶点 %d ｜ 索引 %d ｜ 三角 %d ｜ ★animations=1（4 关键帧）" % (
    OUT.name, len(blob), len(pos), len(idx), len(idx)//3))
print("  ★ sha3-512 前 24=%s" % sha[:24])

# ── 自渲染四时相（按四元数旋转顶点）──
from PIL import Image, ImageDraw, ImageFont
def cjk(sz):
    for p in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"):
        try: return ImageFont.truetype(p, sz)
        except Exception: pass
    return ImageFont.load_default()
def quat_rot(q, v):
    x, y, z, w = q; vx, vy, vz = v
    # v' = v + 2*w*(q×v) + 2*(q×(q×v))
    cx = y*vz - z*vy; cy = z*vx - x*vz; cz = x*vy - y*vx
    c2x = y*cz - z*cy; c2y = z*cx - x*cz; c2z = x*cy - y*cx
    return (vx + 2*w*cx + 2*c2x, vy + 2*w*cy + 2*c2y, vz + 2*w*cz + 2*c2z)
tris = [(pos[idx[k]], pos[idx[k+1]], pos[idx[k+2]]) for k in range(0, len(idx)-2, 3)]
img = Image.new("RGB", (1920, 1080), (10, 11, 14)); d = ImageDraw.Draw(img)
F30, F22 = cjk(40), cjk(26)
P = 420
for pi, (t, deg) in enumerate(zip(times, (0, 90, 180, 270))):
    q = quats[pi*4:pi*4+4]
    px = 70 + pi*450; py = 200
    d.rectangle([px, py, px+P, py+P], outline=(92, 96, 104), width=2)
    d.text((px, py-40), "t=%ds ｜ 绕 Y 轴 %d°" % (int(t), deg), fill=(238, 236, 230), font=F22)
    rot = [quat_rot(q, v) for v in [p for tri in tris for p in tri]]
    xs = [v[0] for v in rot]; ys = [v[1] for v in rot]
    span = max(max(xs)-min(xs), max(ys)-min(ys)) or 1
    k = P*0.42/span
    for n in range(0, len(rot), 3):
        pts = [(px+P/2 + rot[n+i][0]*k, py+P/2 - rot[n+i][1]*k) for i in range(3)]
        lum = 90 + int(60 * ((n*37) % 100)/100)
        d.polygon(pts, fill=(lum, lum, min(255, lum+8)))
d.text((70, 60), "本席自产【动态】glTF（含 animations 通道）—— 四时相自渲染", fill=(242, 240, 234), font=F30)
d.text((70, 120), "资料：persona_cairn-dsh-anim.glb ｜ 41 环×24 段＋12 立方塔＋中轴 ｜ 动画 spin：0/90/180/270°", fill=(176, 176, 172), font=F22)
d.text((70, 720), "★ sha3-512 前 24 位 = %s" % sha[:24], fill=(172, 202, 206), font=F22)
d.text((70, 765), "★ 边界：本件为本席自有产物（非他席资产）；生成器与渲染器皆本席自写、零第三方 3D 库", fill=(190, 162, 152), font=F22)
d.text((70, 810), "★ 用途：证「动态完善之 3D 建模」——静态建模之外，另具动画通道与四时相呈现", fill=(170, 170, 166), font=F22)
png = SEAT/"exp"/"persona_cairn_anim_4phases_20261009.png"
img.save(png, "PNG", optimize=True)
print("  ★ 四时相渲染：%s（%.2f MB）" % (png.name, png.stat().st_size/1048576))
(SEAT/"exp"/"persona_cairn-dsh-anim.glb.json").write_text(json.dumps(
 {"ts": __import__("time").strftime("%Y-%m-%dT%H:%M:%S+0800"), "seat": SEAT_ID, "glb": OUT.name, "bytes": len(blob),
  "vertices": len(pos), "indices": len(idx), "triangles": len(idx)//3, "animations": 1, "keyframes": times,
  "sha3_512_24": sha[:24]}, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
