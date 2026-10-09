# -*- coding: utf-8 -*-
"""行走 v6：支撑相冻结（世界坐标行走）
法：①分相（每腿半周期支撑／半周期摆动）②支撑相内令"该脚之世界 z 恒定" ⇒ 以两连杆 IK 反解髋/膝
     ③骨盆（root）随之前进 ⇒ 净前进 = 每周期 2×步长
参数：股 0.42 m｜胫 0.42 m｜髋高 0.90 m｜步长 0.35 m｜周期 1.3 s｜14 帧
复核：支撑脚世界 z 之恒定度（滑移）｜最低脚 y｜净前进量
输出：CAIRN_avatar_v6_LODk_walk.glb
（引号一律用「」）
"""
import json, math, pathlib, struct, sys

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
EXP = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"/"exp"
NKEY = 14
L1 = L2 = 0.42      # 股／胫
HIP_Y = 0.90        # 髋关节离地高（Pelvis 0.95 − Hip 0.05）
STEP = 0.35         # 步长（半周期前进量）
T = 1.3

def ik(dy, dz):
    """目标脚位（相对髋；dy 向下为负）⇒ 返回 (髋角, 膝角)（度；绕 X；负角＝向后/屈）"""
    d = math.hypot(dy, dz)
    d = min(d, (L1+L2)*0.995)
    # 余弦定理
    cos_k = (L1*L1 + L2*L2 - d*d)/(2*L1*L2)
    knee = math.degrees(math.acos(max(-1.0, min(1.0, cos_k))))          # 0（直）…180（全屈）
    cos_h = (L1*L1 + d*d - L2*L2)/(2*L1*d) if d > 1e-6 else 1.0
    alpha = math.degrees(math.acos(max(-1.0, min(1.0, cos_h))))
    beta = math.degrees(math.atan2(-dz, -dy)) if (dy or dz) else 0.0     # 目标方向（自"竖直向下"起算，向前为正）
    hip = beta + alpha
    return -hip, -(180.0 - knee)   # 髋向前为正→取负以配 X 轴；膝只单向屈（负）

def qx(deg):
    a = math.radians(deg)/2
    return (math.sin(a), 0.0, 0.0, math.cos(a))

def gait(ph):
    """返回每腿之(髋角, 膝角, 踝角)(度) 与骨盆 (dy, dz)"""
    # 骨盆前进（世界坐标；一个周期前进 2×STEP）
    pel_dz = 2*STEP*ph
    out = {}
    for side, off in (("L", 0.0), ("R", 0.5)):
        p = (ph + off) % 1.0
        if p < 0.5:      # 支撑相：脚固定于世界（相对骨盆则向后匀速移）
            u = p/0.5
            z_plant = STEP/2                      # 支撑脚在世界坐标之位置（相对周期起点）
            z_rel = (z_plant - (2*STEP*ph) + (0.0 if off == 0 else STEP))   # 相对骨盆
            y_rel = -HIP_Y
            hip, knee = ik(y_rel, z_rel)
            ank = 6.0*(u - 0.5)                   # 踝微调
            tag = "支撑"
        else:            # 摆动相：由后向前划弧并抬起
            u = (p-0.5)/0.5
            z_from = -STEP/2
            z_to = STEP/2
            z_rel = z_from + (z_to-z_from)*u
            lift = 0.075*math.sin(math.pi*u)
            y_rel = -HIP_Y + lift
            hip, knee = ik(y_rel, z_rel)
            ank = 10.0*math.sin(math.pi*u)
            tag = "摆动"
        out[side] = (hip, knee, ank, tag)
    return out, pel_dz

def pose_of(ph):
    g, pdz = gait(ph)
    ov = {}
    for side in ("L", "R"):
        hip, knee, ank, _ = g[side]
        ov["CAIRN_Hip_%s" % side] = qx(hip)
        ov["CAIRN_Knee_%s" % side] = qx(knee)
        ov["CAIRN_Foot_%s" % side] = qx(ank)
    # 上身：与对侧腿反相之臂摆
    A = 2*math.pi*ph
    ov["CAIRN_Shoulder_L"] = qx(-16.0*math.sin(A))
    ov["CAIRN_Shoulder_R"] = qx(-16.0*math.sin(A+math.pi))
    ov["CAIRN_Elbow_L"] = qx(-16.0)
    ov["CAIRN_Elbow_R"] = qx(-16.0)
    ov["CAIRN_Spine"] = qx(3.0*math.sin(2*A))
    ov["CAIRN_Chest"] = qx(2.0*math.sin(2*A+1.0))
    ov["CAIRN_Head"] = qx(2.0*math.sin(A))
    return ov, pdz, g

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
def load(src):
    raw = src.read_bytes()
    jl, _ = struct.unpack_from("<II", raw, 12); j = json.loads(raw[20:20+jl].decode())
    bo = 20+jl; bl, _ = struct.unpack_from("<II", raw, bo); return raw, j, raw[bo+8:bo+8+bl]
def fk(js, ov, pdy, pdz):
    PARENT = {}
    for i, nd in enumerate(js["nodes"]):
        for c in nd.get("children", []): PARENT[c] = i
    NAME = {i: js["nodes"][i].get("name","?") for i in range(len(js["nodes"]))}
    IDX = {v: k for k, v in NAME.items()}
    order = sorted(range(len(js["nodes"])), key=lambda i: (lambda f: f(f, i))(lambda f, x: 0 if x not in PARENT else 1+f(f, PARENT[x])))
    W = {}
    for i in order:
        nd = js["nodes"][i]; t0 = list(nd.get("translation", [0,0,0])); q = list(nd.get("rotation", [0,0,0,1]))
        nm = NAME[i]
        if nm in ov: q = list(ov[nm])
        if nm == "CAIRN_Pelvis": t0 = [t0[0], t0[1]+pdy, t0[2]+pdz]
        loc = trs(t0, q); W[i] = loc if i not in PARENT else mul(W[PARENT[i]], loc)
    return {nm: (W[IDX[nm]][12], W[IDX[nm]][13], W[IDX[nm]][14]) for nm in ("CAIRN_Foot_L","CAIRN_Foot_R")}

_, js1, _ = load(EXP/"CAIRN_avatar_v2_LOD1.glb")
print("  === v6 之相位表（支撑相冻结；脚之世界 z 应恒定于支撑期内）===")
print("   相位  帧 ｜ L(髋,膝,相) ｜ R(髋,膝,相) ｜ 骨盆 dz ｜ 支撑脚世界 z（L/R）")
plant = {"L": None, "R": None}
slip = []
for i in range(NKEY):
    ph = i/NKEY
    ov, pdz, g = pose_of(ph)
    f = fk(js1, ov, 0.0, pdz)
    Lz = f["CAIRN_Foot_L"][2]; Rz = f["CAIRN_Foot_R"][2]
    Ly = f["CAIRN_Foot_L"][1]; Ry = f["CAIRN_Foot_R"][1]
    st = []
    for side, z, y in (("L", Lz, Ly), ("R", Rz, Ry)):
        if g[side][3] == "支撑":
            if plant[side] is None: plant[side] = z
            st.append("%s %.4f(偏差%+.4f)" % (side, z, z-plant[side]))
            slip.append(abs(z-plant[side]))
    print("   %.3f %3d ｜ (%+6.1f,%+6.1f,%s) ｜ (%+6.1f,%+6.1f,%s) ｜ %+.3f ｜ %s" % (
        ph, i+1, g["L"][0], g["L"][1], g["L"][3], g["R"][0], g["R"][1], g["R"][3], pdz,
        "；".join(st) if st else "（皆摆动）"))
import statistics
print("   ⇒ 支撑相内脚之世界 z 偏差：最大 %.4f m ｜ 均 %.5f m（★应≈0）" % (max(slip) if slip else 0, statistics.mean(slip) if slip else 0))
_, _, ovl = pose_of(0.0), None, None
fl = fk(js1, pose_of(0.0)[0], 0.0, 0.0)
print("   ⇒ 起步脚高 L %.4f／R %.4f（应≈0）｜ 周期净前进 %.2f m ⇒ 速度 %.2f m/s" % (
    fl["CAIRN_Foot_L"][1], fl["CAIRN_Foot_R"][1], 2*STEP, 2*STEP/T))

def bake(src, dst):
    raw, js, bin0 = load(src)
    NAME = {i: js["nodes"][i].get("name","?") for i in range(len(js["nodes"]))}
    IDX = {v: k for k, v in NAME.items()}
    pel = IDX["CAIRN_Pelvis"]; t0 = list(js["nodes"][pel].get("translation", [0.0, 0.95, 0.0]))
    times = [round(i*(T/(NKEY-1)), 4) for i in range(NKEY)]
    poses, pdzs = [], []
    for i in range(NKEY):
        ov, pdz, g = pose_of(i/NKEY); poses.append(ov); pdzs.append(pdz)
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
    for k in range(NKEY): add += struct.pack("<3f", t0[0], t0[1], t0[2]+pdzs[k])
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
        ch.append({"sampler": len(sm)-1, "target": {"node": IDX[nm], "path": "rotation"}})
    ys = [t0[1]]*NKEY
    zs = [t0[2]+p for p in pdzs]
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

print("\n  === 烘焙 v6（支撑相冻结；三 LOD）===")
for lod in ("LOD0", "LOD1", "LOD2"):
    s = EXP/("CAIRN_avatar_v2_%s.glb" % lod)
    d = EXP/("CAIRN_avatar_v6_%s_walk.glb" % lod)
    if not s.exists(): continue
    n = bake(s, d)
    print("   %s ⇒ %s（%d B）" % (s.name, d.name, n))
print("\n  === 独立读取器复核（v6_LOD1 之骨盆 z 序列应线性、髋角应与 IK 输出一致）===")
_, j6, b6 = load(EXP/"CAIRN_avatar_v6_LOD1_walk.glb")
walk = next(a for a in j6["animations"] if a["name"] == "WALK")
pelch = next(c for c in walk["channels"] if j6["nodes"][c["target"]["node"]]["name"] == "CAIRN_Pelvis" and c["target"]["path"] == "translation")
a = j6["accessors"][walk["samplers"][pelch["sampler"]]["output"]]
bv2 = j6["bufferViews"][a["bufferView"]]; off = bv2.get("byteOffset",0)+a.get("byteOffset",0)
zs = [round(struct.unpack_from("<3f", b6, off+k*12)[2], 4) for k in range(a["count"])]
print("   动画 %d ｜ 通道 %d ｜ 骨盆 z 序列：%s" % (len(j6["animations"]), len(walk["channels"]), zs))
print("   ⇒ 末值 %.3f m（应 %.3f ＝ 2×步长）｜ 线性度：相邻差 %s" % (
    zs[-1], 2*STEP, "、".join("%.3f" % (zs[i+1]-zs[i]) for i in range(min(4, len(zs)-1)))))
