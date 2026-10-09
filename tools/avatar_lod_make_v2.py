# -*- coding: utf-8 -*-
"""CAIRN_avatar v2 —— 承 v1 之三缺陷（部件缝隙／符号不显／积木感）而改：
① 体量连接：四肢加长并加肩/肘/髋/膝/踝关节球，消除缝隙 ② 符号件放大 1.6 倍且位置外移
③ LOD0 段数 16（更圆）④ 补足其规范 §2.6 之五态：IDLE_VERIFY／WEIGH／INSPECT／RELAY／REFUSE
仍是：米／Y-up／+Z／身高 1.72 m／命名 CAIRN_<Bone>_<Side>／4 权重蒙皮／零第三方 3D 库／零付费
（引号一律用「」）
"""
import hashlib, json, math, pathlib, struct, sys, time

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
SEAT = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928")
OUTD = SEAT/"exp"; H = 1.72

def box(cx, cy, cz, sx, sy, sz):
    p, i = [], []
    for dz in (-sz, sz):
        for dx, dy in ((-sx,-sy), (sx,-sy), (sx,sy), (-sx,sy)):
            p.append((cx+dx, cy+dy, cz+dz))
    for t in [(0,1,2),(0,2,3),(4,6,5),(4,7,6),(0,4,5),(0,5,1),(1,5,6),(1,6,2),(2,6,7),(2,7,3),(3,7,4),(3,4,0)]:
        i += list(t)
    return p, i

def prism(cx, cy, cz, r, h, ns, axis="y"):
    p, i = [], []
    for k in range(ns):
        a = 2*math.pi*k/ns
        for dz in (-h/2, h/2):
            if axis == "y": p.append((cx+r*math.cos(a), cy+dz, cz+r*math.sin(a)))
            else:           p.append((cx+dz, cy+r*math.cos(a), cz+r*math.sin(a)))
    for k in range(ns):
        k2 = (k+1) % ns
        i += [2*k, 2*k2, 2*k+1, 2*k+1, 2*k2, 2*k2+1]
    for k in range(1, ns-1):
        i += [0, 2*k+2, 2*k]; i += [1, 2*k+1, 2*k+3]
    return p, i

def sphere(cx, cy, cz, r, rings=4, segs=8):
    """低模球（关节球，用于体量连接）"""
    p, i = [], []
    p.append((cx, cy+r, cz))
    for a in range(1, rings):
        th = math.pi*a/rings
        for k in range(segs):
            ph = 2*math.pi*k/segs
            p.append((cx+r*math.sin(th)*math.cos(ph), cy+r*math.cos(th), cz+r*math.sin(th)*math.sin(ph)))
    p.append((cx, cy-r, cz))
    bot = len(p)-1
    for k in range(segs):
        i += [0, 1+(k+1) % segs, 1+k]
    for a in range(rings-2):
        b0 = 1+a*segs; b1 = 1+(a+1)*segs
        for k in range(segs):
            k2 = (k+1) % segs
            i += [b0+k, b1+k, b1+k2, b0+k, b1+k2, b0+k2]
    b = 1+(rings-2)*segs
    for k in range(segs):
        i += [bot, b+k, b+(k+1) % segs]
    return p, i

def parts_for(ns, lite=False):
    P = []
    # 腿（加长以入躯干；并加关节球：髋/膝/踝）
    P.append(("leg_up_L", *prism(-0.11, 0.70, 0.0, 0.082, 0.48, ns)))
    P.append(("leg_up_R", *prism( 0.11, 0.70, 0.0, 0.082, 0.48, ns)))
    P.append(("leg_lo_L", *prism(-0.11, 0.28, 0.0, 0.068, 0.50, ns)))
    P.append(("leg_lo_R", *prism( 0.11, 0.28, 0.0, 0.068, 0.50, ns)))
    P.append(("foot_L", *box(-0.11, 0.045, 0.07, 0.072, 0.045, 0.15)))
    P.append(("foot_R", *box( 0.11, 0.045, 0.07, 0.072, 0.045, 0.15)))
    if not lite:
        for sgn, sd in ((-1, "L"), (1, "R")):
            P.append(("j_hip_%s" % sd,  *sphere(sgn*0.11, 0.92, 0.0, 0.085)))
            P.append(("j_knee_%s" % sd, *sphere(sgn*0.11, 0.50, 0.0, 0.072)))
            P.append(("j_ankle_%s" % sd, *sphere(sgn*0.11, 0.09, 0.0, 0.062)))
            P.append(("j_sh_%s" % sd,   *sphere(sgn*0.205, 1.40, 0.0, 0.075)))
            P.append(("j_el_%s" % sd,   *sphere(sgn*0.205, 1.16, 0.0, 0.062)))
    # 躯干（加长并相互重叠）
    P.append(("pelvis", *prism(0.0, 1.00, 0.0, 0.145, 0.26, ns)))
    P.append(("spine",  *prism(0.0, 1.18, 0.0, 0.150, 0.26, ns)))
    P.append(("chest",  *prism(0.0, 1.36, 0.0, 0.160, 0.28, ns)))
    P.append(("neck",   *prism(0.0, 1.495, 0.0, 0.048, 0.10, ns)))
    P.append(("head",   *box(0.0, 1.615, 0.01, 0.095, 0.11, 0.095)))
    # 臂（加长入躯干）
    for side, sx in (("L", -1), ("R", 1)):
        P.append(("arm_up_%s" % side, *prism(sx*0.205, 1.28, 0.0, 0.058, 0.34, ns)))
        P.append(("arm_lo_%s" % side, *prism(sx*0.205, 1.01, 0.0, 0.050, 0.32, ns)))
        P.append(("hand_%s" % side, *box(sx*0.205, 0.845, 0.0, 0.050, 0.060, 0.035)))
    # 符号件（放大 1.6 倍、外移）
    P.append(("symbol_gate_L", *box(-0.33, 0.845, 0.04, 0.032, 0.115, 0.115)))
    P.append(("symbol_clock_R", *prism(0.33, 0.845, 0.04, 0.082, 0.045, ns, axis="z")))
    P.append(("symbol_gear", *prism(0.0, 1.05, 0.22, 0.075, 0.03, ns, axis="z")))
    for k in range(9):
        a = -math.pi*0.85 + k*(2*math.pi*0.85/8)
        P.append(("symbol_dash_%d" % k, *box(0.36*math.sin(a), 1.20, -0.24 - 0.10*math.cos(a), 0.032, 0.032, 0.032)))
    return P

JOINTS = [
    ("CAIRN_Pelvis", None, (0.00, 0.95, 0.0)), ("CAIRN_Spine", "CAIRN_Pelvis", (0.00, 1.10, 0.0)),
    ("CAIRN_Chest", "CAIRN_Spine", (0.00, 1.26, 0.0)), ("CAIRN_Neck", "CAIRN_Chest", (0.00, 1.44, 0.0)),
    ("CAIRN_Head", "CAIRN_Neck", (0.00, 1.50, 0.0)),
    ("CAIRN_Shoulder_L", "CAIRN_Chest", (-0.18, 1.42, 0.0)), ("CAIRN_Elbow_L", "CAIRN_Shoulder_L", (-0.205, 1.16, 0.0)),
    ("CAIRN_Hand_L", "CAIRN_Elbow_L", (-0.205, 0.90, 0.0)),
    ("CAIRN_Shoulder_R", "CAIRN_Chest", ( 0.18, 1.42, 0.0)), ("CAIRN_Elbow_R", "CAIRN_Shoulder_R", ( 0.205, 1.16, 0.0)),
    ("CAIRN_Hand_R", "CAIRN_Elbow_R", ( 0.205, 0.90, 0.0)),
    ("CAIRN_Hip_L", "CAIRN_Pelvis", (-0.11, 0.90, 0.0)), ("CAIRN_Knee_L", "CAIRN_Hip_L", (-0.11, 0.48, 0.0)),
    ("CAIRN_Foot_L", "CAIRN_Knee_L", (-0.11, 0.06, 0.0)),
    ("CAIRN_Hip_R", "CAIRN_Pelvis", ( 0.11, 0.90, 0.0)), ("CAIRN_Knee_R", "CAIRN_Hip_R", ( 0.11, 0.48, 0.0)),
    ("CAIRN_Foot_R", "CAIRN_Knee_R", ( 0.11, 0.06, 0.0)),
]
JIDX = {n: i for i, (n, _, _) in enumerate(JOINTS)}
PART_JOINT = {"leg_up_L":"CAIRN_Hip_L","leg_lo_L":"CAIRN_Knee_L","foot_L":"CAIRN_Foot_L",
              "leg_up_R":"CAIRN_Hip_R","leg_lo_R":"CAIRN_Knee_R","foot_R":"CAIRN_Foot_R",
              "pelvis":"CAIRN_Pelvis","spine":"CAIRN_Spine","chest":"CAIRN_Chest","head":"CAIRN_Head","neck":"CAIRN_Neck",
              "arm_up_L":"CAIRN_Shoulder_L","arm_lo_L":"CAIRN_Elbow_L","hand_L":"CAIRN_Hand_L",
              "arm_up_R":"CAIRN_Shoulder_R","arm_lo_R":"CAIRN_Elbow_R","hand_R":"CAIRN_Hand_R",
              "symbol_gate_L":"CAIRN_Hand_L","symbol_clock_R":"CAIRN_Hand_R","symbol_gear":"CAIRN_Spine"}
def part_joint(p):
    if p in PART_JOINT: return PART_JOINT[p]
    if p.startswith("j_"):
        for sd in ("_L", "_R"):
            if p.endswith(sd):
                core = p[2:-2]
                m = {"hip":"CAIRN_Hip","knee":"CAIRN_Knee","ankle":"CAIRN_Foot","sh":"CAIRN_Shoulder","el":"CAIRN_Elbow"}
                return m.get(core, "CAIRN_Pelvis") + sd
    return "CAIRN_Chest"
def world_pos(name):
    x = y = z = 0.0; cur = name
    while cur is not None:
        i = JIDX[cur]; p = JOINTS[i][2]; x += p[0]; y += p[1]; z += p[2]; cur = JOINTS[i][1]
    return (x, y, z)

def qx(d):
    h = math.radians(d)/2; return (math.sin(h), 0.0, 0.0, math.cos(h))
def qz(d):
    h = math.radians(d)/2; return (0.0, 0.0, math.sin(h), math.cos(h))
def qy(d):
    h = math.radians(d)/2; return (0.0, math.sin(h), 0.0, math.cos(h))

# 五态（其 §2.6）：每态＝(name, 采样时刻, {关节: [角度序列], 轴})
STATES = [
    ("IDLE_VERIFY", [0.0, 1.0, 2.0], {"CAIRN_Chest": ("x", [0.0, 1.5, 0.0]), "CAIRN_Head": ("x", [0.0, -1.2, 0.0])}),
    ("WEIGH",       [0.0, 0.8, 1.6], {"CAIRN_Elbow_L": ("z", [0.0, -22.0, 0.0]), "CAIRN_Elbow_R": ("z", [0.0, 22.0, 0.0]),
                                      "CAIRN_Chest": ("y", [0.0, 6.0, 0.0])}),
    ("INSPECT",     [0.0, 0.7, 1.4], {"CAIRN_Shoulder_R": ("x", [0.0, -65.0, -55.0]), "CAIRN_Head": ("x", [0.0, 14.0, 10.0])}),
    ("RELAY",       [0.0, 0.6, 1.2, 1.8], {"CAIRN_Shoulder_R": ("x", [0.0, -55.0, -40.0, 0.0]),
                                           "CAIRN_Foot_L": ("z", [0.0, 90.0, 60.0, 120.0])}),
    ("REFUSE",      [0.0, 0.5, 1.0, 1.5], {"CAIRN_Shoulder_L": ("y", [0.0, 40.0, 35.0, 0.0]),
                                           "CAIRN_Shoulder_R": ("y", [0.0, -40.0, -35.0, 0.0]),
                                           "CAIRN_Spine": ("x", [0.0, -8.0, -6.0, 0.0])}),
]

def build(ns, lod_name, lite=False):
    plist = parts_for(ns, lite)
    pos, idx, jts, wts, part_of = [], [], [], [], []
    for pname, p, ix in plist:
        b = len(pos)
        for v in p: pos.append(v); part_of.append(pname)
        idx += [b + t for t in ix]
    jw = [world_pos(n) for n, _, _ in JOINTS]
    for vi, v in enumerate(pos):
        d = sorted(((math.dist(v, jw[j]), j) for j in range(len(JOINTS))))[:2]
        (d0, j0), (d1, j1) = d[0], d[1]
        pji = JIDX[part_joint(part_of[vi])]
        w0 = 0.92 if j0 == pji else 0.82
        w = {pji: w0, (j1 if j1 != pji else j0): round(1.0-w0, 4)}
        if len(w) == 1: w = {pji: 1.0}
        ids = list(w.keys())[:4]; ws = [w[k] for k in ids]
        while len(ids) < 4: ids.append(0); ws.append(0.0)
        s = sum(ws) or 1.0
        jts.append(ids); wts.append([round(x/s, 5) for x in ws])
    pos_b = b"".join(struct.pack("<3f", *p) for p in pos)
    j_b = b"".join(struct.pack("<4H", *j) for j in jts)
    w_b = b"".join(struct.pack("<4f", *w) for w in wts)
    idx_b = b"".join(struct.pack("<I", i) for i in idx)
    # 五态之采样器数据
    anim_data = []
    for name, ts, chans in STATES:
        t_b = struct.pack("<%df" % len(ts), *ts)
        outs = []
        for joint, (axis, degs) in chans.items():
            qs = []
            for d in degs:
                q = qx(d) if axis == "x" else (qz(d) if axis == "z" else qy(d))
                qs += list(q)
            outs.append((joint, struct.pack("<%df" % len(qs), *qs)))
        anim_data.append((name, ts, chans, t_b, outs))
    ibm = []
    for j in range(len(JOINTS)):
        wx, wy, wz = jw[j]
        ibm += [1,0,0,0, 0,1,0,0, 0,0,1,0, -wx,-wy,-wz,1]
    ibm_b = struct.pack("<%df" % len(ibm), *ibm)
    blobs = {"pos": pos_b, "idx": idx_b, "jts": j_b, "wts": w_b}
    for i, (name, ts, chans, t_b, outs) in enumerate(anim_data):
        blobs["t%d" % i] = t_b
        for k, (joint, ob) in enumerate(outs): blobs["o%d_%d" % (i, k)] = ob
    blobs["ibm"] = ibm_b
    off = 0; o = {}
    for k, b in blobs.items(): o[k] = off; off += len(b)
    blob = b"".join(blobs[k] for k in blobs)
    acc = [{"bufferView": 0, "componentType": 5126, "count": len(pos), "type": "VEC3",
            "min": [min(p[i] for p in pos) for i in range(3)], "max": [max(p[i] for p in pos) for i in range(3)]},
           {"bufferView": 1, "componentType": 5125, "count": len(idx), "type": "SCALAR"},
           {"bufferView": 2, "componentType": 5123, "count": len(jts), "type": "VEC4"},
           {"bufferView": 3, "componentType": 5126, "count": len(wts), "type": "VEC4"}]
    bviews = []; order = list(blobs.keys())
    for k in order:
        bv = {"buffer": 0, "byteOffset": o[k], "byteLength": len(blobs[k])}
        if k == "pos": bv["target"] = 34962
        if k == "jts" or k == "wts": bv["target"] = 34962
        if k == "idx": bv["target"] = 34963
        bviews.append(bv)
    BV = {k: i for i, k in enumerate(order)}
    anims = []
    for i, (name, ts, chans, t_b, outs) in enumerate(anim_data):
        acc_t = len(acc); acc.append({"bufferView": BV["t%d" % i], "componentType": 5126, "count": len(ts),
                                      "type": "SCALAR", "min": [min(ts)], "max": [max(ts)]})
        samplers, channels = [], []
        for k, (joint, ob) in enumerate(outs):
            acc_o = len(acc); acc.append({"bufferView": BV["o%d_%d" % (i, k)], "componentType": 5126,
                                          "count": len(ts), "type": "VEC4"})
            samplers.append({"input": acc_t, "output": acc_o, "interpolation": "LINEAR"})
            channels.append({"sampler": k, "target": {"node": JIDX[joint], "path": "rotation"}})
        anims.append({"name": name, "samplers": samplers, "channels": channels})
    acc_ibm = len(acc); acc.append({"bufferView": BV["ibm"], "componentType": 5126, "count": len(JOINTS), "type": "MAT4"})
    nodes = []
    for i, (name, parent, _) in enumerate(JOINTS):
        nd = {"name": name}
        if parent is None: nd["translation"] = list(JOINTS[i][2])
        else:
            pi = JIDX[parent]
            nd["translation"] = [round(JOINTS[i][2][k] - JOINTS[pi][2][k], 4) for k in range(3)]
        ch = []
        for j, (n2, p2, _) in enumerate(JOINTS):
            if p2 == name: ch.append(j)
        if name == "CAIRN_Pelvis":
            mesh_node = len(JOINTS)
            ch = ch + [mesh_node]
        if ch: nd["children"] = ch
        nodes.append(nd)
    nodes.append({"name": "CAIRN_Body_%s" % lod_name, "mesh": 0, "skin": 0, "rotation": [0, 0, 0, 1]})
    gltf = {"asset": {"version": "2.0", "generator": "cairn-dsh/avatar_lod_make_v2.py (self-made; zero-3rd-party)"},
            "scene": 0, "scenes": [{"name": "CAIRN_avatar_%s" % lod_name, "nodes": [JIDX["CAIRN_Pelvis"]]}],
            "nodes": nodes,
            "meshes": [{"name": "CAIRN_Body", "primitives": [{"attributes": {"POSITION": 0, "JOINTS_0": 2, "WEIGHTS_0": 3},
                                                              "indices": 1, "mode": 4}]}],
            "skins": [{"name": "CAIRN_Rig", "joints": list(range(len(JOINTS))), "inverseBindMatrices": acc_ibm,
                       "skeleton": JIDX["CAIRN_Pelvis"]}],
            "accessors": acc, "bufferViews": bviews, "buffers": [{"byteLength": len(blob)}], "animations": anims,
            "extras": {"by": "a2a-node-local", "seat": "CAIRN", "lod": lod_name, "version": "v2", "segments": ns,
                       "units": "meter", "up": "Y", "forward": "+Z", "height_m": H, "joints": len(JOINTS),
                       "animations": [s[0] for s in STATES], "spec": "DF-SPEC-20261009-HY4-07 五态对齐",
                       "fixes": "v1 三缺陷：体量连接（关节球）／符号件放大 1.6×／LOD0 段数 16"}}
    js = json.dumps(gltf, ensure_ascii=False, separators=(",", ":")).encode("utf-8"); js += b" " * ((-len(js)) % 4)
    glb = b"glTF" + struct.pack("<II", 2, 12+8+len(js)+8+len(blob)) + struct.pack("<II", len(js), 0x4E4F534A) + js + struct.pack("<II", len(blob), 0x004E4942) + blob
    out = OUTD/("CAIRN_avatar_v2_%s.glb" % lod_name)
    out.write_bytes(glb)
    return out, glb, len(pos), len(idx)//3

res = {}
for ns, lod, lite in ((16, "LOD0", False), (10, "LOD1", False), (6, "LOD2", True)):
    out, glb, nv, nt = build(ns, lod, lite)
    sha = hashlib.sha3_512(glb).hexdigest()
    res[lod] = {"file": out.name, "bytes": len(glb), "verts": nv, "tris": nt, "sha3_24": sha[:24]}
    print("  ★ %s：%s（%d B）｜ 顶点 %d ｜ 三角 %d ｜ 关节 17 ｜ 动画 5 ｜ sha3-24=%s" % (lod, out.name, len(glb), nv, nt, sha[:24]))
