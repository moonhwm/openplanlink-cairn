# -*- coding: utf-8 -*-
"""行走 v4：脚掌贴地之 IK 修正
法：逐相位以 FK 求两脚之世界 y 最小值 ⇒ 令骨盆纵向偏移 = −min ⇒ 最低脚恒触 y=0
     （替代原正弦起伏；正弦起伏为"示意"，贴地为准）
输出：CAIRN_avatar_v4_LODk_walk.glb（三 LOD）＋ 修正前后对照表
★ 独立读取器复核（骨盆 translation 之 y 序列、脚底最低 y）
（引号一律用「」）
"""
import json, math, pathlib, struct, sys

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
EXP = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"/"exp"
NKEY = 14

def qx(d):
    a = math.radians(d)/2
    return (math.sin(a), 0.0, 0.0, math.cos(a))
def rot_pose(ph):
    A = 2*math.pi*ph
    return {
        "CAIRN_Hip_L": qx(26.0*math.sin(A)), "CAIRN_Hip_R": qx(26.0*math.sin(A+math.pi)),
        "CAIRN_Knee_L": qx(-max(0.0, 34.0*math.sin(A-0.9))), "CAIRN_Knee_R": qx(-max(0.0, 34.0*math.sin(A+math.pi-0.9))),
        "CAIRN_Foot_L": qx(8.0*math.sin(A+1.6)), "CAIRN_Foot_R": qx(8.0*math.sin(A+math.pi+1.6)),
        "CAIRN_Shoulder_L": qx(-18.0*math.sin(A)), "CAIRN_Shoulder_R": qx(-18.0*math.sin(A+math.pi)),
        "CAIRN_Elbow_L": qx(-14.0-8.0*math.sin(A+0.6)), "CAIRN_Elbow_R": qx(-14.0-8.0*math.sin(A+math.pi+0.6)),
        "CAIRN_Spine": qx(3.0*math.sin(2*A)), "CAIRN_Chest": qx(2.0*math.sin(2*A+1.0)),
        "CAIRN_Head": qx(2.0*math.sin(A)),
    }

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
    bo = 20+jl; bl, _ = struct.unpack_from("<II", raw, bo); b = raw[bo+8:bo+8+bl]
    return raw, j, b

def fk_foot_y(js, overrides, pelvis_dy):
    """以 FK 求两脚关节之世界 y（取 Foot 与 Knee 之下端近似 ⇒ 用 Foot 关节原点）"""
    PARENT = {}
    for i, nd in enumerate(js["nodes"]):
        for c in nd.get("children", []): PARENT[c] = i
    NAME = {i: js["nodes"][i].get("name","?") for i in range(len(js["nodes"]))}
    order = sorted(range(len(js["nodes"])), key=lambda i: (lambda f: f(f, i))(lambda f, x: 0 if x not in PARENT else 1+f(f, PARENT[x])))
    W = {}
    for i in order:
        nd = js["nodes"][i]; t0 = list(nd.get("translation", [0,0,0])); q = list(nd.get("rotation", [0,0,0,1]))
        nm = NAME[i]
        if nm in overrides: q = list(overrides[nm])
        if nm == "CAIRN_Pelvis": t0 = [t0[0], t0[1]+pelvis_dy, t0[2]]
        loc = trs(t0, q); W[i] = loc if i not in PARENT else mul(W[PARENT[i]], loc)
    out = {}
    for nm in ("CAIRN_Foot_L", "CAIRN_Foot_R", "CAIRN_Knee_L", "CAIRN_Knee_R"):
        idx = {v: k for k, v in NAME.items()}[nm]
        m = W[idx]
        out[nm] = m[13]  # 世界 y
    return out

# ── 以 LOD1 为参照：逐相位求"最低脚 y"并定修正量 ──
src1 = EXP/"CAIRN_avatar_v2_LOD1.glb"
_, js1, _ = load(src1)
print("  === 修正前后（LOD1 参照；以 FK 求最低脚之世界 y）===")
print("   相位  帧 ｜ 未修正之最低脚 y ｜ 修正量(dy) ｜ 修正后之最低脚 y")
fix = []
for i in range(NKEY):
    ph = i/NKEY
    ov = rot_pose(ph)
    f0 = fk_foot_y(js1, ov, 0.0)
    lo0 = min(f0.values())
    dy = -lo0
    f1 = fk_foot_y(js1, ov, dy)
    lo1 = min(f1.values())
    fix.append(dy)
    print("   %.3f %3d ｜ %+8.4f ｜ %+8.4f ｜ %+8.5f" % (ph, i+1, lo0, dy, lo1))
print("   ⇒ 修正量范围 %+.4f–%+.4f m（起伏 %.1f mm）｜ 修正后最低脚 y 之最大值 %.5f（应≈0）" % (
    min(fix), max(fix), (max(fix)-min(fix))*1000, max(abs(fk_foot_y(js1, rot_pose(i/NKEY), fix[i])[k]) for i in range(NKEY) for k in ("CAIRN_Foot_L","CAIRN_Foot_R"))))

def bake(src, dst):
    raw, js, bin0 = load(src)
    NAME = {i: js["nodes"][i].get("name","?") for i in range(len(js["nodes"]))}
    IDX = {v: k for k, v in NAME.items()}
    pel = IDX["CAIRN_Pelvis"]; t0 = list(js["nodes"][pel].get("translation", [0.0, 0.95, 0.0]))
    times = [round(i*(1.3/(NKEY-1)), 4) for i in range(NKEY)]
    poses = [rot_pose(i/NKEY) for i in range(NKEY)]
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
    for k in range(NKEY): add += struct.pack("<3f", t0[0], t0[1]+fix[k], t0[2])
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
    ys = [t0[1]+fix[k] for k in range(NKEY)]
    a2 = acc(bv(base+toff, 12*NKEY), NKEY, "VEC3", [t0[0], min(ys), t0[2]], [t0[0], max(ys), t0[2]])
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

print("\n  === 烘焙 v4（三 LOD；含贴地修正）===")
for lod in ("LOD0", "LOD1", "LOD2"):
    s = EXP/("CAIRN_avatar_v2_%s.glb" % lod)
    d = EXP/("CAIRN_avatar_v4_%s_walk.glb" % lod)
    if not s.exists(): continue
    n = bake(s, d)
    print("   %s ⇒ %s（%d B）" % (s.name, d.name, n))

print("\n  === 独立读取器复核（三件；骨盆 y 序列应与 fix 逐位相符）===")
for lod in ("LOD0", "LOD1", "LOD2"):
    d = EXP/("CAIRN_avatar_v4_%s_walk.glb" % lod)
    if not d.exists(): continue
    _, j, b = load(d)
    walk = next(a for a in j["animations"] if a["name"] == "WALK")
    pel = next(c for c in walk["channels"] if j["nodes"][c["target"]["node"]]["name"] == "CAIRN_Pelvis" and c["target"]["path"] == "translation")
    a = j["accessors"][walk["samplers"][pel["sampler"]]["output"]]
    bv2 = j["bufferViews"][a["bufferView"]]; off = bv2.get("byteOffset",0)+a.get("byteOffset",0)
    ys = [round(struct.unpack_from("<3f", b, off+k*12)[1], 5) for k in range(a["count"])]
    exp_ys = [round(0.95+fix[k], 5) for k in range(NKEY)]
    same = ys == exp_ys
    print("   %s ⇒ 动画 %d ｜ 通道 %d ｜ 骨盆 y 序列%s ｜ 前 4 值 %s" % (
        d.name, len(j["animations"]), len(walk["channels"]), "★与修正量逐位相符 ✓" if same else "✗ 不符", ys[:4]))
