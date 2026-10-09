# -*- coding: utf-8 -*-
"""行走 v6b：以"数值 IK（直接用 FK 求解）"根除符号之误 ＋ 髋高降至 0.80 m
① 骨架实测：腿长 0.840、Pelvis→Hip 0.050
② 髋高设定 0.80 ⇒ Pelvis 之 y = 0.85（0.80 + 0.05）
③ 数值 IK：在 (髋角, 膝角) 网格上以 FK 求脚位，取与目标最近者（不依赖任何符号约定）
④ 支撑相冻结：支撑期内令"脚之世界 z 恒定"；骨盆随之前进 ⇒ 净前进 2×步长
复核：支撑脚世界 z 偏差（应≈0）｜最低脚 y（应≈0）｜净前进
输出：CAIRN_avatar_v6b_LODk_walk.glb
（引号一律用「」）
"""
import json, math, pathlib, struct, sys

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
EXP = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"/"exp"
NKEY = 14
HIP_GROUND = 0.80     # 目标髋高（离地）
PELVIS_Y = 0.85       # Pelvis 之 y（=0.80+0.05）
STEP = 0.35
T = 1.3

def load(src):
    raw = src.read_bytes()
    jl, _ = struct.unpack_from("<II", raw, 12); j = json.loads(raw[20:20+jl].decode())
    bo = 20+jl; bl, _ = struct.unpack_from("<II", raw, bo); return raw, j, raw[bo+8:bo+8+bl]
def qx(d):
    a = math.radians(d)/2
    return (math.sin(a), 0.0, 0.0, math.cos(a))
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

_, JS, _ = load(EXP/"CAIRN_avatar_v2_LOD1.glb")
NM = {i: JS["nodes"][i].get("name","?") for i in range(len(JS["nodes"]))}
IDX = {v: k for k, v in NM.items()}
PAR = {}
for i, nd in enumerate(JS["nodes"]):
    for c in nd.get("children", []): PAR[c] = i
ORDER = sorted(range(len(JS["nodes"])), key=lambda i: (lambda f: f(f, i))(lambda f, x: 0 if x not in PAR else 1+f(f, PAR[x])))

def fk_foot(side, hip_deg, knee_deg, ankle_deg, pel_y, pel_z):
    """给定关节角与骨盆位移 ⇒ 该侧脚之世界 (y, z) 与髋之世界 y"""
    ov = {"CAIRN_Hip_%s" % side: qx(hip_deg), "CAIRN_Knee_%s" % side: qx(knee_deg),
          "CAIRN_Foot_%s" % side: qx(ankle_deg)}
    W = {}
    for i in ORDER:
        nd = JS["nodes"][i]; t0 = list(nd.get("translation", [0,0,0])); q = list(nd.get("rotation", [0,0,0,1]))
        nm = NM[i]
        if nm in ov: q = list(ov[nm])
        if nm == "CAIRN_Pelvis": t0 = [t0[0], pel_y, t0[2]+pel_z]
        loc = trs(t0, q); W[i] = loc if i not in PAR else mul(W[PAR[i]], loc)
    f = W[IDX["CAIRN_Foot_%s" % side]]; h = W[IDX["CAIRN_Hip_%s" % side]]
    return f[13], f[14], h[13]

# ── 预建查找表（数值 IK；不依赖符号约定）──
GRID_H = [h/2 for h in range(-120, 121)]      # 髋角 −60…+60，步 0.5°
GRID_K = [k/2 for k in range(-170, 1)]        # 膝角 −85…0，步 0.5°
TABLE = []
for h in GRID_H:
    for k in GRID_K:
        y, z, hy = fk_foot("L", h, k, 0.0, PELVIS_Y, 0.0)
        TABLE.append((h, k, y - hy, z))
print("  查找表：%d 项（髋 %g…%g°，膝 %g…%g°）" % (len(TABLE), GRID_H[0], GRID_H[-1], GRID_K[0], GRID_K[-1]))
def ik(dy, dz):
    """目标（相对髋：dy 向下为负、dz 向前为正）⇒ (髋角, 膝角)"""
    best, bd = None, 1e9
    for h, k, ty, tz in TABLE:
        d = (ty-dy)**2 + (tz-dz)**2
        if d < bd: bd, best = d, (h, k)
    return best[0], best[1], math.sqrt(bd)
# 自校：随机 6 个目标，查回代误差
print("  === 数值 IK 自校（回代 FK 之误差）===")
import random
random.seed(20261009)
for _ in range(6):
    dy = -random.uniform(0.70, 0.83); dz = random.uniform(-0.25, 0.25)
    h, k, e = ik(dy, dz)
    y, z, hy = fk_foot("L", h, k, 0.0, PELVIS_Y, 0.0)
    print("   目标 dy %+.3f dz %+.3f ⇒ 髋 %+6.1f° 膝 %+6.1f° ⇒ 实得 dy %+.3f dz %+.3f ｜ 误差 %.4f m" % (
        dy, dz, h, k, y-hy, z, math.hypot((y-hy)-dy, z-dz)))

def gait(ph):
    pel_z = 2*STEP*ph
    out = {}
    for side, off in (("L", 0.0), ("R", 0.5)):
        p = (ph + off) % 1.0
        if p < 0.5:      # 支撑相：脚固定于世界 ⇒ 相对骨盆向后匀速
            u = p/0.5
            z_world = STEP/2 + (0.0 if off == 0 else STEP)
            dz = z_world - pel_z
            dy = -(HIP_GROUND)
            h, k, e = ik(dy, dz); ank = 6.0*(u-0.5); tag = "支撑"
        else:            # 摆动相：由后向前划弧并抬起
            u = (p-0.5)/0.5
            dz = -STEP/2 + STEP*u
            dy = -(HIP_GROUND) + 0.075*math.sin(math.pi*u)
            h, k, e = ik(dy, dz); ank = 10.0*math.sin(math.pi*u); tag = "摆动"
        out[side] = (h, k, ank, tag)
    return out, pel_z

print("\n  === v6b 相位表（支撑脚之世界 z 应恒定）===")
print("   相位  帧 ｜ L(髋,膝,相) ｜ R(髋,膝,相) ｜ 骨盆 z ｜ 脚世界 z（支撑者）")
plant = {"L": None, "R": None}; slip = []
rows = []
for i in range(NKEY):
    ph = i/NKEY
    g, pz = gait(ph)
    st = []
    for side in ("L", "R"):
        h, k, a, tag = g[side]
        y, z, hy = fk_foot(side, h, k, a, PELVIS_Y, pz)
        if tag == "支撑":
            if plant[side] is None: plant[side] = z
            slip.append(abs(z - plant[side]))
            st.append("%s w=%.4f(偏%+.4f) y=%+.4f" % (side, z, z-plant[side], y))
    rows.append((ph, g, pz, st))
    print("   %.3f %3d ｜ (%+6.1f,%+6.1f,%s) ｜ (%+6.1f,%+6.1f,%s) ｜ %+.3f ｜ %s" % (
        ph, i+1, g["L"][0], g["L"][1], g["L"][3], g["R"][0], g["R"][1], g["R"][3], pz,
        "；".join(st) if st else "（皆摆动）"))
print("   ⇒ 支撑脚世界 z 偏差：最大 %.5f m（★应≈0）｜ 最低脚 y：%.5f（应≈0）｜ 净前进 %.2f m" % (
    max(slip) if slip else 0, min(min(fk_foot(s, *g[s][:3], PELVIS_Y, pz)[0] for s in ("L","R")) for _, g, pz, _ in rows), 2*STEP))

def bake(src, dst):
    raw, js, bin0 = load(src)
    NAME = {i: js["nodes"][i].get("name","?") for i in range(len(js["nodes"]))}
    IX = {v: k for k, v in NAME.items()}
    pel = IX["CAIRN_Pelvis"]; t0 = list(js["nodes"][pel].get("translation", [0.0, 0.95, 0.0]))
    times = [round(i*(T/(NKEY-1)), 4) for i in range(NKEY)]
    poses, pzs = [], []
    for i in range(NKEY):
        g, pz = gait(i/NKEY)
        ov = {}
        for side in ("L", "R"):
            h, k, a, _ = g[side]
            ov["CAIRN_Hip_%s" % side] = qx(h); ov["CAIRN_Knee_%s" % side] = qx(k); ov["CAIRN_Foot_%s" % side] = qx(a)
        A = 2*math.pi*(i/NKEY)
        ov["CAIRN_Shoulder_L"] = qx(-16.0*math.sin(A)); ov["CAIRN_Shoulder_R"] = qx(-16.0*math.sin(A+math.pi))
        ov["CAIRN_Elbow_L"] = qx(-16.0); ov["CAIRN_Elbow_R"] = qx(-16.0)
        ov["CAIRN_Spine"] = qx(3.0*math.sin(2*A)); ov["CAIRN_Chest"] = qx(2.0*math.sin(2*A+1.0))
        ov["CAIRN_Head"] = qx(2.0*math.sin(A))
        poses.append(ov); pzs.append(pz)
    add = bytearray()
    def pad4(x):
        while len(x) % 4: x.append(0)
    pad4(add); t_off = len(add)
    for t in times: add += struct.pack("<f", t)
    roff = {}
    for nm in poses[0]:
        pad4(add); roff[nm] = len(add)
        for p in poses: add += struct.pack("<4f", *p[nm])
    pad4(add); toff = len(add)
    for k in range(NKEY): add += struct.pack("<3f", t0[0], PELVIS_Y, t0[2]+pzs[k])
    pad4(add)
    nb = bin0 + bytes(add); base = len(bin0)
    bvs, accs = js["bufferViews"], js["accessors"]
    def bv(o, l):
        bvs.append({"buffer":0,"byteOffset":o,"byteLength":l}); return len(bvs)-1
    def acc(b, c, t, mn, mx):
        accs.append({"bufferView":b,"componentType":5126,"count":c,"type":t,"min":mn,"max":mx}); return len(accs)-1
    ta = acc(bv(base+t_off, 4*NKEY), NKEY, "SCALAR", [min(times)], [max(times)])
    js["animations"] = [a for a in js.get("animations", []) if a["name"] != "WALK"]
    sm, ch = [], []
    for nm in poses[0]:
        a = acc(bv(base+roff[nm], 16*NKEY), NKEY, "VEC4",
                [min(p[nm][k] for p in poses) for k in range(4)],
                [max(p[nm][k] for p in poses) for k in range(4)])
        sm.append({"input": ta, "output": a, "interpolation": "LINEAR"})
        ch.append({"sampler": len(sm)-1, "target": {"node": IX[nm], "path": "rotation"}})
    ys = [PELVIS_Y]*NKEY; zs = [t0[2]+p for p in pzs]
    a2 = acc(bv(base+toff, 12*NKEY), NKEY, "VEC3", [t0[0], min(ys), min(zs)], [t0[0], max(ys), max(zs)])
    sm.append({"input": ta, "output": a2, "interpolation": "LINEAR"})
    ch.append({"sampler": len(sm)-1, "target": {"node": pel, "path": "translation"}})
    js["animations"].append({"name": "WALK", "samplers": sm, "channels": ch})
    js["buffers"] = [{"byteLength": len(nb)}]
    jb = json.dumps(js, separators=(",", ":")).encode()
    while len(jb) % 4: jb += b" "
    bb = nb
    while len(bb) % 4: bb += b"\x00"
    out = struct.pack("<III", 0x46546C67, 2, 12+8+len(jb)+8+len(bb)) + struct.pack("<II", len(jb), 0x4E4F534A) + jb + struct.pack("<II", len(bb), 0x004E4942) + bb
    dst.write_bytes(out)
    return len(out)

print("\n  === 烘焙 v6b（三 LOD）===")
for lod in ("LOD0", "LOD1", "LOD2"):
    s = EXP/("CAIRN_avatar_v2_%s.glb" % lod)
    d = EXP/("CAIRN_avatar_v6b_%s_walk.glb" % lod)
    if s.exists(): print("   %s ⇒ %s（%d B）" % (s.name, d.name, bake(s, d)))
