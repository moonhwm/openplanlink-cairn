# -*- coding: utf-8 -*-
"""足部滑移之量测与线性化（v5）
① 量：逐相位以 FK 求两脚世界 z（前进向）⇒ 判支撑脚（较低者）⇒ 算滑移率 Δz 与其离散
② 改：为骨盆加 z 平移通道，使"支撑脚之 z"随相位线性变化（原地走＝地面匀速后移之约定）
③ 复核：修正后支撑脚 z 之线性度（残差）
输出：CAIRN_avatar_v5_LODk_walk.glb
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
    bo = 20+jl; bl, _ = struct.unpack_from("<II", raw, bo); return raw, j, raw[bo+8:bo+8+bl]
def fk(js, ov, dy, dz):
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
        if nm == "CAIRN_Pelvis": t0 = [t0[0], t0[1]+dy, t0[2]+dz]
        loc = trs(t0, q); W[i] = loc if i not in PARENT else mul(W[PARENT[i]], loc)
    return {nm: (W[IDX[nm]][12], W[IDX[nm]][13], W[IDX[nm]][14]) for nm in ("CAIRN_Foot_L","CAIRN_Foot_R","CAIRN_Knee_L","CAIRN_Knee_R")}

_, js1, _ = load(EXP/"CAIRN_avatar_v2_LOD1.glb")
print("  === ① 量：两脚之 (y, z) 与支撑脚（较低者）之滑移 ===")
print("   相位  帧 ｜ 脚L(y,z) ｜ 脚R(y,z) ｜ 支撑 ｜ 支撑脚 z")
prev_support_z = None
slip = []
rows = []
for i in range(NKEY):
    ph = i/NKEY
    f = fk(js1, rot_pose(ph), 0.0, 0.0)
    L, R = f["CAIRN_Foot_L"], f["CAIRN_Foot_R"]
    sup = "L" if L[1] <= R[1] else "R"
    sz = L[2] if sup == "L" else R[2]
    d = None if prev_support_z is None else sz - prev_support_z
    if d is not None and sup == "L":  # 仅同脚连续支撑时段计滑移
        slip.append(d)
    rows.append({"ph": ph, "sup": sup, "sz": round(sz, 4), "dz": None if d is None else round(d, 4)})
    print("   %.3f %3d ｜ (%+.3f,%+.3f) ｜ (%+.3f,%+.3f) ｜ %s ｜ %+.4f%s" % (
        ph, i+1, L[1], L[2], R[1], R[2], sup, sz, ("" if d is None else "  Δ=%+.4f" % d)))
    prev_support_z = sz
if slip:
    import statistics
    print("   ⇒ 支撑脚 z 之逐帧变化：均 %+.4f ｜ 标准差 %.4f ｜ 范围 %+.4f…%+.4f" % (
        statistics.mean(slip), statistics.pstdev(slip), min(slip), max(slip)))
    print("   ⇒ ★离散度（σ/|均|）＝ %.2f ⇒ %s" % (
        abs(statistics.pstdev(slip)/statistics.mean(slip)) if statistics.mean(slip) else float("nan"),
        "滑移不匀" if abs(statistics.pstdev(slip)/statistics.mean(slip)) > 0.5 else "滑移较匀"))

# ── ② 生成 z 通道：令支撑脚 z 随相位线性后移（原地走约定：地面匀速）──
zs = [r["sz"] for r in rows]
z0, z1 = zs[0], zs[-1] + (zs[0]-zs[7])  # 推一个周期
target = [z0 + (z1-z0)*(i/(NKEY-1)) for i in range(NKEY)]
dz_off = [zs[i]-target[i] for i in range(NKEY)]
print("\n  === ② 线性化之偏移（骨盆 z）===")
print("   支撑脚 z 实测：%s" % " ".join("%+.3f" % v for v in zs))
print("   线性目标   ：%s" % " ".join("%+.3f" % v for v in target))
print("   偏移 dz    ：%s" % " ".join("%+.4f" % v for v in dz_off))

def bake(src, dst, dz_list, dy_list):
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
    for k in range(NKEY): add += struct.pack("<3f", t0[0], t0[1]+dy_list[k], t0[2]+dz_list[k])
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
    xs = [t0[0]]*NKEY
    ys = [t0[1]+dy_list[k] for k in range(NKEY)]
    zz = [t0[2]+dz_list[k] for k in range(NKEY)]
    a2 = acc(bv(base+toff, 12*NKEY), NKEY, "VEC3", [min(xs), min(ys), min(zz)], [max(xs), max(ys), max(zz)])
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

# dy：贴地修正（承 v4）
dy_list = []
for i in range(NKEY):
    f = fk(js1, rot_pose(i/NKEY), 0.0, 0.0)
    dy_list.append(-min(f["CAIRN_Foot_L"][1], f["CAIRN_Foot_R"][1]))
print("\n  === ③ 烘焙 v5（贴地＋滑移线性化；三 LOD）===")
for lod in ("LOD0", "LOD1", "LOD2"):
    s = EXP/("CAIRN_avatar_v2_%s.glb" % lod)
    d = EXP/("CAIRN_avatar_v5_%s_walk.glb" % lod)
    if not s.exists(): continue
    n = bake(s, d, dz_off, dy_list)
    print("   %s ⇒ %s（%d B）" % (s.name, d.name, n))

print("\n  === ④ 复核（以 v5_LOD1 重算两脚 y 与支撑脚 z）===")
_, js5, _ = load(EXP/"CAIRN_avatar_v5_LOD1.glb")
sup_z2, minY = [], []
for i in range(NKEY):
    f = fk(js5, rot_pose(i/NKEY), 0.0, dz_off[i])   # dy 已含于资产；此处 dz 用同一偏移复算
    L, R = f["CAIRN_Foot_L"], f["CAIRN_Foot_R"]
    sup_z2.append((L[2] if L[1] <= R[1] else R[2]))
    minY.append(min(L[1], R[1]))
print("   支撑脚 z（含 dz 偏移）：%s" % " ".join("%+.3f" % v for v in sup_z2))
d2 = [sup_z2[i+1]-sup_z2[i] for i in range(NKEY-1)]
import statistics
print("   逐帧 Δz：均 %+.4f ｜ σ %.4f ｜ σ/|均| %.2f" % (statistics.mean(d2), statistics.pstdev(d2),
      abs(statistics.pstdev(d2)/statistics.mean(d2)) if statistics.mean(d2) else float("nan")))
print("   最低脚 y：%s（应≈0，因 dy 已在资产中 ⇒ 此为不含 dy 之复算，仅供参考）" % " ".join("%+.3f" % v for v in minY))
