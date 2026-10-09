# -*- coding: utf-8 -*-
"""行走烘焙 v3b：①补骨盆起伏（translation 通道）②为三 LOD 各烘 WALK
输出：CAIRN_avatar_v3_LOD0_walk.glb／_LOD1_walk.glb／_LOD2_walk.glb
★ 以独立读取器复核（动画名、通道数、髋角序列、骨盆 translation 范围）
（引号一律用「」）
"""
import json, math, pathlib, struct, sys

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
EXP = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"/"exp"
NKEY = 14

def qx(deg):
    a = math.radians(deg)/2
    return (math.sin(a), 0.0, 0.0, math.cos(a))
def pose(ph):
    A = 2*math.pi*ph
    rot = {
        "CAIRN_Hip_L": qx(26.0*math.sin(A)), "CAIRN_Hip_R": qx(26.0*math.sin(A+math.pi)),
        "CAIRN_Knee_L": qx(-max(0.0, 34.0*math.sin(A-0.9))), "CAIRN_Knee_R": qx(-max(0.0, 34.0*math.sin(A+math.pi-0.9))),
        "CAIRN_Foot_L": qx(8.0*math.sin(A+1.6)), "CAIRN_Foot_R": qx(8.0*math.sin(A+math.pi+1.6)),
        "CAIRN_Shoulder_L": qx(-18.0*math.sin(A)), "CAIRN_Shoulder_R": qx(-18.0*math.sin(A+math.pi)),
        "CAIRN_Elbow_L": qx(-14.0-8.0*math.sin(A+0.6)), "CAIRN_Elbow_R": qx(-14.0-8.0*math.sin(A+math.pi+0.6)),
        "CAIRN_Spine": qx(3.0*math.sin(2*A)), "CAIRN_Chest": qx(2.0*math.sin(2*A+1.0)),
        "CAIRN_Head": qx(2.0*math.sin(A)),
    }
    bob = 0.022*abs(math.cos(A)) - 0.011
    return rot, bob

def bake(src, dst):
    raw = src.read_bytes()
    jlen, _ = struct.unpack_from("<II", raw, 12); js = json.loads(raw[20:20+jlen].decode())
    boff = 20+jlen; blen, _ = struct.unpack_from("<II", raw, boff); bin0 = raw[boff+8:boff+8+blen]
    NAME = {i: js["nodes"][i].get("name","?") for i in range(len(js["nodes"]))}
    IDX = {v: k for k, v in NAME.items()}
    pelvis = IDX["CAIRN_Pelvis"]
    t0 = list(js["nodes"][pelvis].get("translation", [0.0, 0.95, 0.0]))
    times = [round(i*(1.3/(NKEY-1)), 4) for i in range(NKEY)]
    poses = [pose(i/NKEY) for i in range(NKEY)]
    add = bytearray()
    def pad4(b):
        while len(b) % 4: b.append(0)
    pad4(add); t_off = len(add)
    for t in times: add += struct.pack("<f", t)
    roff, toff = {}, None
    for nm in poses[0][0]:
        pad4(add); roff[nm] = len(add)
        for r, _ in poses: add += struct.pack("<4f", *r[nm])
    pad4(add); toff = len(add)
    for _, b in poses: add += struct.pack("<3f", t0[0], t0[1]+b, t0[2])
    pad4(add)
    newbin = bin0 + bytes(add); base = len(bin0)
    bvs, accs = js["bufferViews"], js["accessors"]
    def bv(off, ln):
        bvs.append({"buffer":0, "byteOffset":off, "byteLength":ln}); return len(bvs)-1
    def acc(b, cnt, typ, mn, mx):
        accs.append({"bufferView":b, "componentType":5126, "count":cnt, "type":typ, "min":mn, "max":mx}); return len(accs)-1
    tacc = acc(bv(base+t_off, 4*NKEY), NKEY, "SCALAR", [min(times)], [max(times)])
    # 先剔除同名旧 WALK（幂等）
    js["animations"] = [a for a in js.get("animations", []) if a["name"] != "WALK"]
    samplers, channels = [], []
    for nm in poses[0][0]:
        vox = [p[0][nm][k] for p in poses for k in range(4)]
        a = acc(bv(base+roff[nm], 16*NKEY), NKEY, "VEC4",
                [min(p[0][nm][k] for p in poses) for k in range(4)],
                [max(p[0][nm][k] for p in poses) for k in range(4)])
        samplers.append({"input": tacc, "output": a, "interpolation": "LINEAR"})
        channels.append({"sampler": len(samplers)-1, "target": {"node": IDX[nm], "path": "rotation"}})
    # ★ 骨盆 translation 通道（含起伏）
    ys = [t0[1]+b for _, b in poses]
    a2 = acc(bv(base+toff, 12*NKEY), NKEY, "VEC3", [t0[0], min(ys), t0[2]], [t0[0], max(ys), t0[2]])
    samplers.append({"input": tacc, "output": a2, "interpolation": "LINEAR"})
    channels.append({"sampler": len(samplers)-1, "target": {"node": pelvis, "path": "translation"}})
    js["animations"].append({"name": "WALK", "samplers": samplers, "channels": channels})
    js["buffers"] = [{"byteLength": len(newbin)}]
    jb = json.dumps(js, separators=(",", ":")).encode()
    while len(jb) % 4: jb += b" "
    bb = newbin
    while len(bb) % 4: bb += b"\x00"
    out = struct.pack("<III", 0x46546C67, 2, 12+8+len(jb)+8+len(bb)) + struct.pack("<II", len(jb), 0x4E4F534A) + jb + struct.pack("<II", len(bb), 0x004E4942) + bb
    dst.write_bytes(out)
    return dst, len(out), len(js["animations"])

print("  === 烘焙（三 LOD；含骨盆起伏）===")
outs = []
for lod in ("LOD0", "LOD1", "LOD2"):
    src = EXP/("CAIRN_avatar_v2_%s.glb" % lod)
    dst = EXP/("CAIRN_avatar_v3_%s_walk.glb" % lod)
    if not src.exists():
        print("   缺 %s" % src.name); continue
    d, size, n = bake(src, dst)
    print("   %s ⇒ %s（%d B；动画 %d）" % (src.name, d.name, size, n))
    outs.append(d)

print("\n  === 独立读取器复核（三件）===")
for d in outs:
    r = d.read_bytes()
    jl, _ = struct.unpack_from("<II", r, 12); j = json.loads(r[20:20+jl].decode())
    bo = 20+jl; bl, _ = struct.unpack_from("<II", r, bo); b = r[bo+8:bo+8+bl]
    names = [a["name"] for a in j["animations"]]
    walk = next(a for a in j["animations"] if a["name"] == "WALK")
    paths = {}
    for c in walk["channels"]:
        paths[j["nodes"][c["target"]["node"]]["name"]] = c["target"]["path"]
    def rd(i):
        a = j["accessors"][i]; bv2 = j["bufferViews"][a["bufferView"]]
        n = {"SCALAR":1,"VEC3":3,"VEC4":4}[a["type"]]
        off = bv2.get("byteOffset",0)+a.get("byteOffset",0)
        return [struct.unpack_from("<%df"%n, b, off+k*n*4) for k in range(a["count"])]
    hip = next(c for c in walk["channels"] if j["nodes"][c["target"]["node"]]["name"] == "CAIRN_Hip_L")
    ang = [round(2*math.degrees(math.asin(max(-1,min(1,p[0])))),1) for p in rd(walk["samplers"][hip["sampler"]]["output"])]
    pel = next((c for c in walk["channels"] if j["nodes"][c["target"]["node"]]["name"] == "CAIRN_Pelvis" and c["target"]["path"] == "translation"), None)
    ys = [round(p[1], 4) for p in rd(walk["samplers"][pel["sampler"]]["output"])] if pel else []
    print("   %s ⇒ 动画 %d：%s" % (d.name, len(names), "、".join(names)))
    print("      通道 %d ｜ 髋 L 范围 %.1f–%.1f ｜ ★骨盆 translation 通道=%s ｜ y 范围 %s" % (
        len(walk["channels"]), min(ang), max(ang), "有" if pel else "无",
        ("%.4f–%.4f（起伏 %.1f mm）" % (min(ys), max(ys), (max(ys)-min(ys))*1000)) if ys else "—"))
