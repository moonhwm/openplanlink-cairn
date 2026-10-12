# -*- coding: utf-8 -*-
"""本席人形分身（CAIRN_avatar）三 LOD 生成器 —— 照 HY4《席位分身 3D 资产 Unity 规范》之可对齐项
① 单位米、Y-up、-Z forward（面朝 +Z）、身高 1.72 m ② LOD0/1/2（段数 12/8/6）
③ 最小 Humanoid 骨架 15 关节（pelvis→spine→chest→neck→head；chest→肩→肘→手×2；pelvis→髋→膝→足×2）
④ 蒙皮：每顶点取最近两关节，按距离比线性混合权重（JOINTS_0/WEIGHTS_0）＋ inverseBindMatrices
⑤ 两条动画：`IDLE_VERIFY`（待核，微起伏）／`RELAY`（转述，右臂抬起＋腰间齿轮转）
⑥ 命名 `<SEAT>_<Bone>_<Side>`：CAIRN_Head／CAIRN_Hand_L…（英文、无空格）
⑦ 自渲染四时相（正视图，正交投影）以证蒙皮与动画  —— 零第三方 3D 库、零付费
（引号一律用「」）
"""
import hashlib, json, math, pathlib, struct, sys, time

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
SEAT = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928")
OUTD = SEAT/"exp"; SEAT_ID = "CAIRN"; H = 1.72

# ─────────────────────── 几何：以「盒」拼人形（低模），段数 ns 控制圆度 ───────────────────────
def box(cx, cy, cz, sx, sy, sz):
    p = []; i = []
    for dz in (-sz, sz):
        for dx, dy in ((-sx,-sy), (sx,-sy), (sx,sy), (-sx,sy)):
            p.append((cx+dx, cy+dy, cz+dz))
    for t in [(0,1,2),(0,2,3),(4,6,5),(4,7,6),(0,4,5),(0,5,1),(1,5,6),(1,6,2),(2,6,7),(2,7,3),(3,7,4),(3,4,0)]:
        i += list(t)
    return p, i

def prism(cx, cy, cz, r, h, ns, axis="y"):
    """正 ns 边形棱柱（ns=4 即盒）"""
    p = []; i = []
    for k in range(ns):
        a = 2*math.pi*k/ns
        for dz in (-h/2, h/2):
            if axis == "y":
                p.append((cx+r*math.cos(a), cy+dz, cz+r*math.sin(a)))
            else:
                p.append((cx+dz, cy+r*math.cos(a), cz+r*math.sin(a)))
    for k in range(ns):
        k2 = (k+1) % ns
        i += [2*k, 2*k2, 2*k+1, 2*k+1, 2*k2, 2*k2+1]
    for k in range(1, ns-1):   # 端盖
        i += [0, 2*k+2, 2*k]; i += [1, 2*k+1, 2*k+3]
    return p, i

def parts_for(ns):
    """各部件（局部坐标，原点在两脚中点、Y 向上、面朝 +Z）"""
    P = []
    # 腿：髋 0.90 → 膝 0.48 → 足 0.06
    P.append(("leg_up_L", *prism(-0.11, 0.69, 0.0, 0.075, 0.42, ns)))
    P.append(("leg_up_R", *prism( 0.11, 0.69, 0.0, 0.075, 0.42, ns)))
    P.append(("leg_lo_L", *prism(-0.11, 0.27, 0.0, 0.062, 0.42, ns)))
    P.append(("leg_lo_R", *prism( 0.11, 0.27, 0.0, 0.062, 0.42, ns)))
    P.append(("foot_L", *box(-0.11, 0.045, 0.06, 0.065, 0.045, 0.13)))
    P.append(("foot_R", *box( 0.11, 0.045, 0.06, 0.065, 0.045, 0.13)))
    # 躯干：pelvis 0.95 → chest 1.25 → neck 1.46
    P.append(("pelvis", *prism(0.0, 1.00, 0.0, 0.14, 0.20, ns)))
    P.append(("spine",  *prism(0.0, 1.18, 0.0, 0.145, 0.20, ns)))
    P.append(("chest",  *prism(0.0, 1.36, 0.0, 0.15, 0.22, ns)))
    # 头
    P.append(("head", *box(0.0, 1.60, 0.005, 0.085, 0.10, 0.085)))
    P.append(("neck", *prism(0.0, 1.475, 0.0, 0.04, 0.07, ns)))
    # 臂：肩 1.40 → 肘 1.16 → 手 0.94
    for side, sx in (("L", -1), ("R", 1)):
        P.append(("arm_up_%s" % side, *prism(sx*0.215, 1.30, 0.0, 0.055, 0.28, ns)))
        P.append(("arm_lo_%s" % side, *prism(sx*0.215, 1.05, 0.0, 0.048, 0.26, ns)))
        P.append(("hand_%s" % side, *box(sx*0.215, 0.90, 0.0, 0.045, 0.055, 0.03)))
    # 人设符号：左手闸门／右手座钟／腰间齿轮／未闭合虚线
    P.append(("symbol_gate_L", *box(-0.30, 0.90, 0.02, 0.02, 0.075, 0.075)))
    P.append(("symbol_clock_R", *prism(0.30, 0.90, 0.02, 0.05, 0.03, ns, axis="z")))
    P.append(("symbol_gear", *prism(0.0, 1.02, 0.16, 0.045, 0.02, ns, axis="z")))
    # 未闭合虚线（背后一环，留缺口 ⇒ 未闭合）
    for k in range(9):
        a = -math.pi*0.85 + k*(2*math.pi*0.85/8)
        P.append(("symbol_dash_%d" % k, *box(0.28*math.sin(a), 1.15, -0.16 - 0.06*math.cos(a), 0.02, 0.02, 0.02)))
    return P

# ─────────────────────── 骨架：15 关节 ───────────────────────
JOINTS = [
    ("CAIRN_Pelvis",   None,        (0.00, 0.95, 0.0)),
    ("CAIRN_Spine",    "CAIRN_Pelvis", (0.00, 1.10, 0.0)),
    ("CAIRN_Chest",    "CAIRN_Spine",  (0.00, 1.26, 0.0)),
    ("CAIRN_Neck",     "CAIRN_Chest",  (0.00, 1.44, 0.0)),
    ("CAIRN_Head",     "CAIRN_Neck",   (0.00, 1.50, 0.0)),
    ("CAIRN_Shoulder_L", "CAIRN_Chest", (-0.18, 1.42, 0.0)),
    ("CAIRN_Elbow_L",    "CAIRN_Shoulder_L", (-0.215, 1.16, 0.0)),
    ("CAIRN_Hand_L",     "CAIRN_Elbow_L",    (-0.215, 0.92, 0.0)),
    ("CAIRN_Shoulder_R", "CAIRN_Chest", ( 0.18, 1.42, 0.0)),
    ("CAIRN_Elbow_R",    "CAIRN_Shoulder_R", ( 0.215, 1.16, 0.0)),
    ("CAIRN_Hand_R",     "CAIRN_Elbow_R",    ( 0.215, 0.92, 0.0)),
    ("CAIRN_Hip_L",      "CAIRN_Pelvis", (-0.11, 0.90, 0.0)),
    ("CAIRN_Knee_L",     "CAIRN_Hip_L",  (-0.11, 0.48, 0.0)),
    ("CAIRN_Foot_L",     "CAIRN_Knee_L", (-0.11, 0.06, 0.0)),
    ("CAIRN_Hip_R",      "CAIRN_Pelvis", ( 0.11, 0.90, 0.0)),
    ("CAIRN_Knee_R",     "CAIRN_Hip_R",  ( 0.11, 0.48, 0.0)),
    ("CAIRN_Foot_R",     "CAIRN_Knee_R", ( 0.11, 0.06, 0.0)),
]
JIDX = {n: i for i, (n, _, _) in enumerate(JOINTS)}
# 部件 → 主要关节（决定蒙皮归属）
PART_JOINT = {"leg_up_L":"CAIRN_Hip_L","leg_lo_L":"CAIRN_Knee_L","foot_L":"CAIRN_Foot_L",
              "leg_up_R":"CAIRN_Hip_R","leg_lo_R":"CAIRN_Knee_R","foot_R":"CAIRN_Foot_R",
              "pelvis":"CAIRN_Pelvis","spine":"CAIRN_Spine","chest":"CAIRN_Chest",
              "head":"CAIRN_Head","neck":"CAIRN_Neck",
              "arm_up_L":"CAIRN_Shoulder_L","arm_lo_L":"CAIRN_Elbow_L","hand_L":"CAIRN_Hand_L",
              "arm_up_R":"CAIRN_Shoulder_R","arm_lo_R":"CAIRN_Elbow_R","hand_R":"CAIRN_Hand_R",
              "symbol_gate_L":"CAIRN_Hand_L","symbol_clock_R":"CAIRN_Hand_R","symbol_gear":"CAIRN_Spine"}
def part_joint(pname):
    if pname in PART_JOINT: return PART_JOINT[pname]
    return "CAIRN_Chest"        # 未闭合虚线随胸

def world_pos(name):
    """绑定姿态下关节之世界位置（沿链求和）"""
    x = y = z = 0.0
    cur = name
    while cur is not None:
        i = JIDX[cur]; p = JOINTS[i][2]
        x += p[0]; y += p[1]; z += p[2]
        cur = JOINTS[i][1]
    return (x, y, z)

# ─────────────────────── 单 LOD 之 GLB 组装 ───────────────────────
def build(ns, lod_name):
    plist = parts_for(ns)
    pos, nrm_dummy, idx, jts, wts, part_of = [], [], [], [], [], []
    for pname, p, ix in plist:
        b = len(pos)
        for v in p: pos.append(v); part_of.append(pname)
        idx += [b + t for t in ix]
    # 蒙皮：每顶点取最近两关节（按到关节世界位置之距离）
    jw = [world_pos(n) for n, _, _ in JOINTS]
    for vi, v in enumerate(pos):
        d = sorted(((math.dist(v, jw[j]), j) for j in range(len(JOINTS))))[:2]
        (d0, j0), (d1, j1) = d[0], d[1]
        # 同部件之关节优先（避免"左腿顶点被右腿关节吸走"）
        pj = part_joint(part_of[vi]); pji = JIDX[pj]
        w0 = 0.82 if j0 != pji else 0.92
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
    # 动画：IDLE_VERIFY（头/胸微起伏）与 RELAY（右臂抬起＋齿轮转）
    t_idle = [0.0, 1.0, 2.0]; t_relay = [0.0, 0.6, 1.2, 1.8]
    def quat_y(deg):
        h = math.radians(deg)/2; return (0.0, math.sin(h), 0.0, math.cos(h))
    def quat_x(deg):
        h = math.radians(deg)/2; return (math.sin(h), 0.0, 0.0, math.cos(h))
    def quat_z(deg):
        h = math.radians(deg)/2; return (0.0, 0.0, math.sin(h), math.cos(h))
    anims = []
    # ① IDLE_VERIFY：Chest 绕 X 微倾 ±1.5°，Head 反向补偿
    t_b1 = struct.pack("<3f", *t_idle)
    q1 = []
    for d in (0.0, 1.5, 0.0): q1 += list(quat_x(d))
    q_b1 = struct.pack("<12f", *q1)
    q2 = []
    for d in (0.0, -1.2, 0.0): q2 += list(quat_x(d))
    q_b2 = struct.pack("<12f", *q2)
    # ② RELAY：右肩绕 X 抬 55°→0；齿轮绕 Z 转 0→120°
    t_b2 = struct.pack("<4f", *t_relay)
    q3 = []
    for d in (0.0, 55.0, 40.0, 0.0): q3 += list(quat_x(-d))
    q_b3 = struct.pack("<16f", *q3)
    q4 = []
    for d in (0.0, 90.0, 60.0, 120.0): q4 += list(quat_z(d))
    q_b4 = struct.pack("<16f", *q4)
    # IBM：绑定姿态无旋转 ⇒ 逆＝平移 -world_pos（列主序 4x4）
    ibm = []
    for j in range(len(JOINTS)):
        wx, wy, wz = jw[j]
        ibm += [1,0,0,0, 0,1,0,0, 0,0,1,0, -wx,-wy,-wz,1]
    ibm_b = struct.pack("<%df" % len(ibm), *ibm)
    blob = pos_b + idx_b + j_b + w_b + t_b1 + q_b1 + q_b2 + t_b2 + q_b3 + q_b4 + ibm_b
    o = {}
    off = 0
    for k, b in (("pos", pos_b), ("idx", idx_b), ("jts", j_b), ("wts", w_b),
                 ("t1", t_b1), ("q1", q_b1), ("q2", q_b2), ("t2", t_b2), ("q3", q_b3), ("q4", q_b4), ("ibm", ibm_b)):
        o[k] = off; off += len(b)
    accessors = [
        {"bufferView": 0, "componentType": 5126, "count": len(pos), "type": "VEC3",
         "min": [min(p[i] for p in pos) for i in range(3)], "max": [max(p[i] for p in pos) for i in range(3)]},
        {"bufferView": 1, "componentType": 5125, "count": len(idx), "type": "SCALAR"},
        {"bufferView": 2, "componentType": 5123, "count": len(jts), "type": "VEC4"},
        {"bufferView": 3, "componentType": 5126, "count": len(wts), "type": "VEC4"},
        {"bufferView": 4, "componentType": 5126, "count": 3, "type": "SCALAR", "min": [0.0], "max": [2.0]},
        {"bufferView": 5, "componentType": 5126, "count": 3, "type": "VEC4"},
        {"bufferView": 6, "componentType": 5126, "count": 3, "type": "VEC4"},
        {"bufferView": 7, "componentType": 5126, "count": 4, "type": "SCALAR", "min": [0.0], "max": [1.8]},
        {"bufferView": 8, "componentType": 5126, "count": 4, "type": "VEC4"},
        {"bufferView": 9, "componentType": 5126, "count": 4, "type": "VEC4"},
        {"bufferView": 10, "componentType": 5126, "count": len(JOINTS), "type": "MAT4"},
    ]
    bviews = []
    for k, b in (("pos", pos_b), ("idx", idx_b), ("jts", j_b), ("wts", w_b), ("t1", t_b1), ("q1", q_b1),
                 ("q2", q_b2), ("t2", t_b2), ("q3", q_b3), ("q4", q_b4), ("ibm", ibm_b)):
        bv = {"buffer": 0, "byteOffset": o[k], "byteLength": len(b)}
        if k in ("pos", "jts", "wts"): bv["target"] = 34962
        if k == "idx": bv["target"] = 34963
        bviews.append(bv)
    nodes = []
    for i, (name, parent, _) in enumerate(JOINTS):
        nd = {"name": name}
        if i == JIDX["CAIRN_Pelvis"]:
            nd["translation"] = list(JOINTS[i][2])
        else:
            pi = JIDX[parent]; px, py, pz = JOINTS[pi][2]; cx, cy, cz = JOINTS[i][2]
            nd["translation"] = [round(cx-px, 4), round(cy-py, 4), round(cz-pz, 4)]
        if name == "CAIRN_Chest":
            nd["children"] = [JIDX["CAIRN_Neck"], JIDX["CAIRN_Shoulder_L"], JIDX["CAIRN_Shoulder_R"]]
        elif name == "CAIRN_Neck": nd["children"] = [JIDX["CAIRN_Head"]]
        elif name == "CAIRN_Shoulder_L": nd["children"] = [JIDX["CAIRN_Elbow_L"]]
        elif name == "CAIRN_Elbow_L": nd["children"] = [JIDX["CAIRN_Hand_L"]]
        elif name == "CAIRN_Shoulder_R": nd["children"] = [JIDX["CAIRN_Elbow_R"]]
        elif name == "CAIRN_Elbow_R": nd["children"] = [JIDX["CAIRN_Hand_R"]]
        elif name == "CAIRN_Spine": nd["children"] = [JIDX["CAIRN_Chest"]]
        elif name == "CAIRN_Pelvis": nd["children"] = [JIDX["CAIRN_Spine"], JIDX["CAIRN_Hip_L"], JIDX["CAIRN_Hip_R"]]
        elif name == "CAIRN_Hip_L": nd["children"] = [JIDX["CAIRN_Knee_L"]]
        elif name == "CAIRN_Knee_L": nd["children"] = [JIDX["CAIRN_Foot_L"]]
        elif name == "CAIRN_Hip_R": nd["children"] = [JIDX["CAIRN_Knee_R"]]
        elif name == "CAIRN_Knee_R": nd["children"] = [JIDX["CAIRN_Foot_R"]]
        nodes.append(nd)
    mesh_node = len(nodes)
    nodes.append({"name": "CAIRN_Body_%s" % lod_name, "mesh": 0, "skin": 0,
                  "translation": [0, 0, 0], "rotation": [0, 0, 0, 1]})
    nodes[JIDX["CAIRN_Pelvis"]]["children"] = nodes[JIDX["CAIRN_Pelvis"]]["children"] + [mesh_node]
    gltf = {
      "asset": {"version": "2.0", "generator": "cairn-dsh/avatar_lod_make.py (self-made; zero-3rd-party)"},
      "scene": 0, "scenes": [{"name": "CAIRN_avatar_%s" % lod_name, "nodes": [JIDX["CAIRN_Pelvis"]]}],
      "nodes": nodes,
      "meshes": [{"name": "CAIRN_Body", "primitives": [{"attributes": {
                    "POSITION": 0, "JOINTS_0": 2, "WEIGHTS_0": 3}, "indices": 1, "mode": 4}]}],
      "skins": [{"name": "CAIRN_Rig", "joints": list(range(len(JOINTS))), "inverseBindMatrices": 10,
                 "skeleton": JIDX["CAIRN_Pelvis"]}],
      "accessors": accessors, "bufferViews": bviews, "buffers": [{"byteLength": len(blob)}],
      "animations": [
        {"name": "IDLE_VERIFY", "samplers": [{"input": 4, "output": 5, "interpolation": "LINEAR"},
                                             {"input": 4, "output": 6, "interpolation": "LINEAR"}],
         "channels": [{"sampler": 0, "target": {"node": JIDX["CAIRN_Chest"], "path": "rotation"}},
                      {"sampler": 1, "target": {"node": JIDX["CAIRN_Head"], "path": "rotation"}}]},
        {"name": "RELAY", "samplers": [{"input": 7, "output": 8, "interpolation": "LINEAR"},
                                       {"input": 7, "output": 9, "interpolation": "LINEAR"}],
         "channels": [{"sampler": 0, "target": {"node": JIDX["CAIRN_Shoulder_R"], "path": "rotation"}},
                      {"sampler": 1, "target": {"node": JIDX["CAIRN_Foot_L"], "path": "rotation"}}]}],
      "extras": {"by": "a2a-node-local", "seat": "CAIRN", "lod": lod_name, "segments": ns,
                 "units": "meter", "up": "Y", "forward": "+Z", "height_m": H,
                 "joints": len(JOINTS), "vertex_joints": 4, "triangles": len(idx)//3,
                 "animations": ["IDLE_VERIFY", "RELAY"], "naming": "<SEAT>_<Bone>_<Side>",
                 "spec_align": "照 DF-SPEC-20261009-HY4-07 之可对齐项（米/Y-up/混合蒙皮/命名/两动画）"},
    }
    js = json.dumps(gltf, ensure_ascii=False, separators=(",", ":")).encode("utf-8"); js += b" " * ((-len(js)) % 4)
    glb = b"glTF" + struct.pack("<II", 2, 12+8+len(js)+8+len(blob)) + struct.pack("<II", len(js), 0x4E4F534A) + js + struct.pack("<II", len(blob), 0x004E4942) + blob
    out = OUTD/("CAIRN_avatar_%s.glb" % lod_name)
    out.write_bytes(glb)
    return out, glb, len(pos), len(idx)//3, jts, wts, pos, idx, jw, ibm

res = {}
for ns, lod in ((12, "LOD0"), (8, "LOD1"), (6, "LOD2")):
    out, glb, nv, nt, jts, wts, pos, idx, jw, ibm = build(ns, lod)
    sha = hashlib.sha3_512(glb).hexdigest()
    res[lod] = {"file": out.name, "bytes": len(glb), "verts": nv, "tris": nt, "sha3_24": sha[:24], "ns": ns}
    print("  ★ %s：%s（%d B）｜ 顶点 %d ｜ 三角 %d ｜ 关节 17 ｜ sha3-24=%s" % (lod, out.name, len(glb), nv, nt, sha[:24]))

# ─────────────────────── 四时相自渲染（含蒙皮，正交正视）───────────────────────
from PIL import Image, ImageDraw, ImageFont
def cjk(sz):
    for p in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"):
        try: return ImageFont.truetype(p, sz)
        except Exception: pass
    return ImageFont.load_default()
out, glb, nv, nt, jts, wts, pos, idx, jw, ibm = build(12, "LOD0")
def mat_mul(a, b):
    """4x4 列主序相乘 a*b"""
    r = [0.0]*16
    for c in range(4):
        for row in range(4):
            r[c*4+row] = sum(a[k*4+row]*b[c*4+k] for k in range(4))
    return r
def trs(t, q):
    x, y, z, w = q
    xx, yy, zz = x*x, y*y, z*z
    m = [1-2*(yy+zz), 2*(x*y+z*w), 2*(x*z-y*w), 0,
         2*(x*y-z*w), 1-2*(xx+zz), 2*(y*z+x*w), 0,
         2*(x*z+y*w), 2*(y*z-x*w), 1-2*(xx+yy), 0,
         t[0], t[1], t[2], 1]
    return m
def anim_pose(which, t):
    """返回 {关节名: (translation, quat)} —— 由动画通道求值（线性插值）"""
    def lerp_q(qs, ts, tv):
        for i in range(len(ts)-1):
            if ts[i] <= tv <= ts[i+1]:
                u = (tv-ts[i])/max(1e-9, ts[i+1]-ts[i])
                a, b = qs[i], qs[i+1]
                q = [a[k]*(1-u)+b[k]*u for k in range(4)]
                n = math.sqrt(sum(v*v for v in q)) or 1
                return [v/n for v in q]
        return qs[-1]
    if which == "IDLE_VERIFY":
        ts = [0.0, 1.0, 2.0]
        qc = qs_from_deg_x([0.0, 1.5, 0.0]); qh = qs_from_deg_x([0.0, -1.2, 0.0])
        return {"CAIRN_Chest": lerp_q(qc, ts, t), "CAIRN_Head": lerp_q(qh, ts, t)}
    ts = [0.0, 0.6, 1.2, 1.8]
    qa = qs_from_deg_x([0.0, -55.0, -40.0, 0.0]); qf = qs_from_deg_z([0.0, 90.0, 60.0, 120.0])
    return {"CAIRN_Shoulder_R": lerp_q(qa, ts, t), "CAIRN_Foot_L": lerp_q(qf, ts, t)}
def qs_from_deg_x(ds):
    out = []
    for d in ds:
        h = math.radians(d)/2; out.append((math.sin(h), 0.0, 0.0, math.cos(h)))
    return out
def qs_from_deg_z(ds):
    out = []
    for d in ds:
        h = math.radians(d)/2; out.append((0.0, 0.0, math.sin(h), math.cos(h)))
    return out
def joint_world(pose):
    """含动画之关节世界矩阵"""
    W = {}
    order = ["CAIRN_Pelvis","CAIRN_Spine","CAIRN_Chest","CAIRN_Neck","CAIRN_Head",
             "CAIRN_Shoulder_L","CAIRN_Elbow_L","CAIRN_Hand_L",
             "CAIRN_Shoulder_R","CAIRN_Elbow_R","CAIRN_Hand_R",
             "CAIRN_Hip_L","CAIRN_Knee_L","CAIRN_Foot_L","CAIRN_Hip_R","CAIRN_Knee_R","CAIRN_Foot_R"]
    for name in order:
        i = JIDX[name]; parent = JOINTS[i][1]
        t = list(JOINTS[i][2]) if parent is None else [
            JOINTS[i][2][k] - JOINTS[JIDX[parent]][2][k] for k in range(3)]
        q = pose.get(name, (0.0, 0.0, 0.0, 1.0))
        local = trs(t, q)
        W[name] = local if parent is None else mat_mul(W[parent], local)
    return W
def skin_apply(which, t):
    W = joint_world(anim_pose(which, t))
    M = [mat_mul(W[JOINTS[j][0]], [ibm[j*16+k] for k in range(16)]) for j in range(len(JOINTS))]
    out = []
    for vi, v in enumerate(pos):
        js, ws = jts[vi], wts[vi]
        acc = [0.0, 0.0, 0.0]
        for k in range(4):
            if ws[k] <= 0: continue
            m = M[js[k]]
            acc[0] += ws[k]*(m[0]*v[0]+m[4]*v[1]+m[8]*v[2]+m[12])
            acc[1] += ws[k]*(m[1]*v[0]+m[5]*v[1]+m[9]*v[2]+m[13])
            acc[2] += ws[k]*(m[2]*v[0]+m[6]*v[1]+m[10]*v[2]+m[14])
        out.append(tuple(acc))
    return out

img = Image.new("RGB", (1920, 1080), (10, 11, 14)); d = ImageDraw.Draw(img)
F42, F24, F20 = cjk(46), cjk(27), cjk(22)
SCENES = [("IDLE_VERIFY", 0.0), ("IDLE_VERIFY", 1.0), ("RELAY", 0.6), ("RELAY", 1.2)]
P = 420
for pi, (which, tv) in enumerate(SCENES):
    verts = skin_apply(which, tv)
    px = 70 + pi*455; py = 300
    d.rectangle([px, py, px+P, py+P], outline=(92, 96, 104), width=2)
    d.text((px+10, py+8), "%s ｜ t=%.1fs" % (which, tv), fill=(238, 236, 230), font=F20)
    xs = [v[0] for v in verts]; ys = [v[1] for v in verts]; zs = [v[2] for v in verts]
    span = max(max(xs)-min(xs), max(ys)-min(ys)) or 1
    k = P*0.86/span
    cx = (max(xs)+min(xs))/2; cy = (max(ys)+min(ys))/2
    for n in range(0, len(idx), 3):
        tri = [verts[idx[n+i]] for i in range(3)]
        pts = [(px+P/2 + (tri[i][0]-cx)*k, py+P/2 - (tri[i][1]-cy)*k) for i in range(3)]
        zavg = sum(tri[i][2] for i in range(3))/3
        lum = 110 + int(70*max(0.0, min(1.0, (zavg+0.4)/0.8)))
        d.polygon(pts, fill=(lum, lum, min(255, lum+10)))
    d.text((px+10, py+P-30), "身高 1.72 m ｜ Y-up ｜ 面朝 +Z", fill=(150, 152, 148), font=F20)
d.text((70, 60), "本席人形分身 CAIRN_avatar（三 LOD＋最小 Humanoid 骨架＋混合蒙皮＋两动画）", fill=(242, 240, 234), font=F42)
d.text((70, 130), "LOD0 %d B／%d 三角 ｜ LOD1 %d B／%d 三角 ｜ LOD2 %d B／%d 三角 ｜ 关节 17 ｜ 每顶点 4 关节权重" % (
    res["LOD0"]["bytes"], res["LOD0"]["tris"], res["LOD1"]["bytes"], res["LOD1"]["tris"],
    res["LOD2"]["bytes"], res["LOD2"]["tris"]), fill=(178, 176, 170), font=F24)
d.text((70, 205), "对齐 DF-SPEC-20261009-HY4-07：米／Y-up／-Z forward／命名 <SEAT>_<Bone>_<Side>／LOD 预算（本席远低于）｜零第三方 3D 库、零付费", fill=(172, 202, 206), font=F20)
d.text((70, 790), "★ 骨节：Pelvis→Spine→Chest→Neck→Head；Chest→Shoulder/Elbow/Hand ×2；Pelvis→Hip/Knee/Foot ×2", fill=(190, 186, 180), font=F20)
d.text((70, 830), "★ 动画：IDLE_VERIFY（胸/头微起伏）｜RELAY（右臂抬起＋左足（齿轮随动）旋转）", fill=(190, 186, 180), font=F20)
d.text((70, 870), "★ 人设符号：左手闸门／右手座钟／腰间齿轮／背后未闭合虚线（缺口留白）", fill=(190, 186, 180), font=F20)
png = OUTD/"CAIRN_avatar_3lod_4phases_20261009.png"
img.save(png, "PNG", optimize=True)
print("  ★ 四时相渲染：%s（%.2f MB）" % (png.name, png.stat().st_size/1048576))
(OUTD/"CAIRN_avatar_manifest_20261009.json").write_text(json.dumps(
 {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "seat": "a2a-node-local", "asset": "CAIRN_avatar",
  "units": "meter", "up": "Y", "forward": "+Z", "height_m": H, "joints": len(JOINTS),
  "animations": ["IDLE_VERIFY", "RELAY"], "lods": res,
  "spec_align": "DF-SPEC-20261009-HY4-07（可对齐项）", "third_party_3d_libs": 0, "cost": 0},
 ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
