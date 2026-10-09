# -*- coding: utf-8 -*-
"""本席自产【动态 glTF 2.0 · v2】：多网格／多节点／两段动画
结构：① 主环串（41 环×24 段＋12 立方塔＋中轴）② 七拍节点（环上七枚，各一网格）
      ③ 数据链（自左壁贯出之小立方串）④ 三器物（齿轮/闸门/座钟之近似体）
动画：`spin`（主环串绕 Y 轴 0/90/180/270°）＋`pulse`（七拍节点依次点亮：缩放 1→1.35→1，相位错开）
并自渲染四时相（t=0/2/4/6）以证两段动画（引号一律用「」）
"""
import hashlib, json, math, pathlib, struct, sys, time

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
SEAT = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928")
OUT = SEAT/"exp"/"persona_cairn-dsh-anim-v2.glb"
SEAT_ID = "cairn-dsh"
seed = hashlib.sha3_512(SEAT_ID.encode()).hexdigest()
N_RING, SEG, R_BASE, TWIST, Z_STEP = 41, 24, 1.6, 0.54, 4.2/41

# ── 各部之几何 ──
parts = []   # (name, positions, indices)
def mk_ring_stack():
    pos, idx = [], []
    def add_ring(zc, r, phase):
        b = len(pos)
        for k in range(SEG):
            a = phase + 2*math.pi*k/SEG
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
    return pos, idx

def mk_cube(s):
    pos, idx = [], []
    for dz in (-s, s):
        for dx, dy in ((-s,-s), (s,-s), (s,s), (-s,s)): pos.append((dx, dy, dz))
    for t in [(0,1,2),(0,2,3),(4,6,5),(4,7,6),(0,4,5),(0,5,1),(1,5,6),(1,6,2),(2,6,7),(2,7,3),(3,7,4),(3,4,0)]:
        idx.extend(list(t))
    return pos, idx

parts.append(("ring_stack",) + mk_ring_stack())
BEATS = ["游戏", "验收", "留痕", "器物", "自正", "复现", "暂止"]
beat_xy = []
for i in range(7):
    a = -math.pi/2 + i*2*math.pi/7
    x, y = 3.6*math.cos(a), 3.6*math.sin(a)
    beat_xy.append((x, y, 0.0))
    parts.append(("beat_%d" % i,) + mk_cube(0.26))
# 数据链（自左壁贯出之小立方串，置于 -x 侧）
chain_pos, chain_idx = [], []
for k in range(14):
    b = len(chain_pos); s = 0.09; cx, cy, cz = -5.0 + k*0.34, -3.0 + k*0.22, -1.2
    for dz in (-s, s):
        for dx, dy in ((-s,-s), (s,-s), (s,s), (-s,s)): chain_pos.append((cx+dx, cy+dy, cz+dz))
    for t in [(0,1,2),(0,2,3),(4,6,5),(4,7,6),(0,4,5),(0,5,1),(1,5,6),(1,6,2),(2,6,7),(2,7,3),(3,7,4),(3,4,0)]:
        chain_idx.extend([b+x for x in t])
parts.append(("data_chain", chain_pos, chain_idx))
# 三器物（齿轮/闸门/座钟之近似）
for nm, s in (("gear", 0.5), ("gate", 0.62), ("clock", 0.42)):
    parts.append((nm,) + mk_cube(s))

# ── 组装二进制：positions 区 / indices 区 / 动画区 ──
pos_all, idx_all, pv, iv = [], [], [], []
pos_off, idx_off = 0, 0
for name, p, ix in parts:
    pv.append((name, pos_off, len(p))); pos_all += p; pos_off += len(p)
for name, p, ix in parts:
    iv.append((name, idx_off, len(ix))); idx_all += ix; idx_off += len(ix)
pos_b = b"".join(struct.pack("<3f", *p) for p in pos_all)
idx_b = b"".join(struct.pack("<H", i) for i in idx_all); idx_b += b"\x00" * ((-len(idx_b)) % 4)

# 动画 1：spin —— 主环串绕 Y 轴
times = [0.0, 2.0, 4.0, 6.0]
quats = []
for deg in (0, 90, 180, 270):
    h = math.radians(deg)/2.0
    quats += [0.0, math.sin(h), 0.0, math.cos(h)]
t_b = struct.pack("<4f", *times); q_b = struct.pack("<16f", *quats)
# 动画 2：pulse —— 七拍依次点亮（共用时间轴 0..7s，每 0.5s 一帧；相位错开）
pt = [round(0.5*k, 2) for k in range(15)]
pt_b = struct.pack("<%df" % len(pt), *pt)
pulse_bufs = []
for i in range(7):
    scales = []
    for k in range(len(pt)):
        t = pt[k]; center = i*1.0
        d = abs(t - center)
        s = 1.35 if d < 0.51 else 1.0
        scales += [s, s, s]
    pulse_bufs.append(struct.pack("<%df" % len(scales), *scales))

blob = pos_b + idx_b + t_b + q_b + pt_b + b"".join(pulse_bufs)
o_pos, o_idx, o_t, o_q, o_pt = 0, len(pos_b), len(pos_b)+len(idx_b), len(pos_b)+len(idx_b)+len(t_b), len(pos_b)+len(idx_b)+len(t_b)+len(q_b)
o_pulse = [o_pt + len(pt_b) + sum(len(b) for b in pulse_bufs[:i]) for i in range(7)]

nodes, meshes, accessors, bviews = [], [], [], []
bviews.append({"buffer": 0, "byteOffset": o_pos, "byteLength": len(pos_b), "target": 34962})
bviews.append({"buffer": 0, "byteOffset": o_idx, "byteLength": len(idx_b), "target": 34963})
bviews.append({"buffer": 0, "byteOffset": o_t, "byteLength": len(t_b)})
bviews.append({"buffer": 0, "byteOffset": o_q, "byteLength": len(q_b)})
bviews.append({"buffer": 0, "byteOffset": o_pt, "byteLength": len(pt_b)})
mi = {}
for name, off, cnt in pv:
    sub = pos_all[off:off+cnt]
    mins = [min(p[i] for p in sub) for i in range(3)]; maxs = [max(p[i] for p in sub) for i in range(3)]
    accessors.append({"bufferView": 0, "byteOffset": off*12, "componentType": 5126, "count": cnt, "type": "VEC3", "min": mins, "max": maxs})
    mi[name] = len(accessors)-1
ii = {}
for name, off, cnt in iv:
    accessors.append({"bufferView": 1, "byteOffset": off*2, "componentType": 5123, "count": cnt, "type": "SCALAR"})
    ii[name] = len(accessors)-1
acc_t = len(accessors); accessors.append({"bufferView": 2, "componentType": 5126, "count": len(times), "type": "SCALAR", "min": [0.0], "max": [6.0]})
acc_q = len(accessors); accessors.append({"bufferView": 3, "componentType": 5126, "count": len(times), "type": "VEC4"})
acc_pt = len(accessors); accessors.append({"bufferView": 4, "componentType": 5126, "count": len(pt), "type": "SCALAR", "min": [0.0], "max": [7.0]})
acc_pulse = []
for i in range(7):
    bviews.append({"buffer": 0, "byteOffset": o_pulse[i], "byteLength": len(pulse_bufs[i])})
    accessors.append({"bufferView": len(bviews)-1, "componentType": 5126, "count": len(pt), "type": "VEC3"})
    acc_pulse.append(len(accessors)-1)

node_names = []
for name, p, ix in parts:
    meshes.append({"name": name, "primitives": [{"attributes": {"POSITION": mi[name]}, "indices": ii[name], "mode": 4}]})
    node_names.append(name)
for idx, name in enumerate(node_names):
    n = {"name": name, "mesh": idx, "rotation": [0, 0, 0, 1]}
    if name.startswith("beat_"):
        b = int(name.split("_")[1]); n["translation"] = list(beat_xy[b]); n["scale"] = [1, 1, 1]
    elif name == "gear": n["translation"] = [5.0, 4.2, 0.0]
    elif name == "gate": n["translation"] = [5.0, 0.6, 0.0]
    elif name == "clock": n["translation"] = [5.0, -3.0, 0.0]
    nodes.append(n)

channels = [{"sampler": 0, "target": {"node": 0, "path": "rotation"}}]
samplers = [{"input": acc_t, "output": acc_q, "interpolation": "LINEAR"}]
for i in range(7):
    node_i = node_names.index("beat_%d" % i)
    samplers.append({"input": acc_pt, "output": acc_pulse[i], "interpolation": "STEP"})
    channels.append({"sampler": len(samplers)-1, "target": {"node": node_i, "path": "scale"}})

gltf = {
 "asset": {"version": "2.0", "generator": "cairn-dsh/glb_make_cairn_anim_v2.py (self-made, zero-3rd-party)"},
 "scene": 0, "scenes": [{"name": "cairn-luzhibai-v2", "nodes": list(range(len(nodes)))}],
 "nodes": nodes, "meshes": meshes, "accessors": accessors, "bufferViews": bviews,
 "buffers": [{"byteLength": len(blob)}],
 "animations": [
   {"name": "spin", "samplers": [samplers[0]], "channels": [channels[0]]},
   {"name": "pulse", "samplers": samplers[1:], "channels": channels[1:]}],
 "extras": {"by": "a2a-node-local", "version": "v2", "parts": len(parts), "nodes": len(nodes),
            "animations": 2, "beats": BEATS,
            "note": "多网格/多节点/两段动画：spin（主环串绕 Y 轴）＋ pulse（七拍依次点亮，STEP 插值）"},
}
js = json.dumps(gltf, ensure_ascii=False, separators=(",", ":")).encode("utf-8"); js += b" " * ((-len(js)) % 4)
glb = b"glTF" + struct.pack("<II", 2, 12+8+len(js)+8+len(blob)) + struct.pack("<II", len(js), 0x4E4F534A) + js + struct.pack("<II", len(blob), 0x004E4942) + blob
OUT.write_bytes(glb)
sha = hashlib.sha3_512(glb).hexdigest()
tri = len(idx_all)//3
print("  ★ glTF v2：%s（%d B）｜ 网格 %d ｜ 节点 %d ｜ 顶点 %d ｜ 三角 %d ｜ ★animations=2（spin 4 帧／pulse 7×15 帧）" % (
    OUT.name, len(glb), len(parts), len(nodes), len(pos_all), tri))
print("  ★ sha3-512 前 24=%s" % sha[:24])
print("  ★ 七拍：%s" % "／".join(BEATS))

# ── 四时相自渲染（按四元数旋转主环串；并标出当刻点亮之拍）──
from PIL import Image, ImageDraw, ImageFont
def cjk(sz):
    for p in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"):
        try: return ImageFont.truetype(p, sz)
        except Exception: pass
    return ImageFont.load_default()
def quat_rot(q, v):
    x, y, z, w = q; vx, vy, vz = v
    cx = y*vz - z*vy; cy = z*vx - x*vz; cz = x*vy - y*vx
    c2x = y*cz - z*cy; c2y = z*cx - x*cz; c2z = x*cy - y*cx
    return (vx + 2*w*cx + 2*c2x, vy + 2*w*cy + 2*c2y, vz + 2*w*cz + 2*c2z)
ring_pos = pos_all[:pv[0][2]]; ring_idx = idx_all[:iv[0][2]]
tris = [(ring_pos[ring_idx[k]], ring_pos[ring_idx[k+1]], ring_pos[ring_idx[k+2]]) for k in range(0, len(ring_idx)-2, 3)]
img = Image.new("RGB", (1920, 1080), (10, 11, 14)); d = ImageDraw.Draw(img)
F42, F24, F20 = cjk(46), cjk(27), cjk(22)
P = 400
for pi, (t, deg) in enumerate(zip(times, (0, 90, 180, 270))):
    q = quats[pi*4:pi*4+4]
    px = 70 + pi*455; py = 230
    d.rectangle([px, py, px+P, py+P], outline=(92, 96, 104), width=2)
    lit = int(t) % 7
    d.text((px, py-74), "t=%ds ｜ spin %d° ｜ pulse 亮「%s」" % (int(t), deg, BEATS[lit]), fill=(238, 236, 230), font=F20)
    rot = [quat_rot(q, v) for v in [p for tri in tris for p in tri]]
    xs = [v[0] for v in rot]; ys = [v[1] for v in rot]
    span = max(max(xs)-min(xs), max(ys)-min(ys)) or 1
    k = P*0.40/span
    for n in range(0, len(rot), 3):
        pts = [(px+P/2 + rot[n+i][0]*k, py+P/2 - rot[n+i][1]*k) for i in range(3)]
        lum = 88 + int(60 * ((n*37) % 100)/100)
        d.polygon(pts, fill=(lum, lum, min(255, lum+8)))
    for b, (bx, by, _) in enumerate(beat_xy):
        cx2, cy2 = px+P/2 + bx*k, py+P/2 - by*k
        r = 9 if b == lit else 6
        col = (250, 240, 180) if b == lit else (120, 124, 130)
        d.ellipse([cx2-r, cy2-r, cx2+r, cy2+r], fill=col)
        d.text((cx2-16, cy2+r+3), BEATS[b], fill=col, font=F20)
d.text((70, 60), "本席自产 glTF v2（多网格／多节点／两段动画）：spin ＋ pulse 七拍依次点亮", fill=(242, 240, 234), font=F42)
d.text((70, 130), "结构：主环串＋七拍节点（游戏/验收/留痕/器物/自正/复现/暂止）＋数据链＋三器物 ｜ 零第三方 3D 库", fill=(178, 176, 170), font=F24)
d.text((70, 180), "资料：persona_cairn-dsh-anim-v2.glb ｜ 网格 %d ｜ 节点 %d ｜ 顶点 %d ｜ 三角 %d ｜ animations=2" % (len(parts), len(nodes), len(pos_all), tri), fill=(176, 176, 172), font=F20)
d.text((70, 700), "★ sha3-512 前 24 位 = %s" % sha[:24], fill=(172, 202, 206), font=F24)
d.text((70, 750), "★ 边界：本席自有产物（非他席资产）；生成器与渲染器皆本席自写；测试件属性如实标注", fill=(190, 162, 152), font=F20)
d.text((70, 795), "★ 用途：平台面受阻期间，仍推进「基于人设的动态完善 3D 建模」之本地半（静态＋动画＋多节点）", fill=(170, 170, 166), font=F20)
png = SEAT/"exp"/"persona_luzhibai_gltf_v2_4phases_20261009.png"
img.save(png, "PNG", optimize=True)
print("  ★ 四时相渲染：%s（%.2f MB）" % (png.name, png.stat().st_size/1048576))
(SEAT/"exp"/"persona_cairn-dsh-anim-v2.glb.json").write_text(json.dumps(
 {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "seat": SEAT_ID, "glb": OUT.name, "bytes": len(glb),
  "meshes": len(parts), "nodes": len(nodes), "vertices": len(pos_all), "triangles": tri,
  "animations": ["spin(4 keyframes, LINEAR)", "pulse(7 channels × 15 keyframes, STEP)"],
  "beats": BEATS, "sha3_512_24": sha[:24]}, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
