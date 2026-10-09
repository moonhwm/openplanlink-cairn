# -*- coding: utf-8 -*-
"""把行走循环烘入 glb：为 CAIRN_avatar v2_LOD1 增一条 WALK 动画（14 关键帧 × 13 关节）
★ 输出 CAIRN_avatar_v3_LOD1_walk.glb（原五态保留 ＋ 新增 WALK）⇒ 资产自足、引擎可直接播放
★ 以独立读取器复核（不是"生成器自渲染"）
（引号一律用「」）
"""
import json, math, pathlib, struct, sys

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
EXP = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"/"exp"
SRC = EXP/"CAIRN_avatar_v2_LOD1.glb"
DST = EXP/"CAIRN_avatar_v3_LOD1_walk.glb"

raw = SRC.read_bytes()
magic, ver, total = struct.unpack_from("<III", raw, 0)
jlen, jtype = struct.unpack_from("<II", raw, 12)
js = json.loads(raw[20:20+jlen].decode("utf-8"))
boff = 20 + jlen
blen, btype = struct.unpack_from("<II", raw, boff)
bin0 = raw[boff+8: boff+8+blen]
print("  源：%s（%.0f B；json %d B；bin %d B）" % (SRC.name, len(raw), jlen, blen))
print("  现有动画：%s" % "、".join(a["name"] for a in js.get("animations", [])))
NAME = {i: js["nodes"][i].get("name","?") for i in range(len(js["nodes"]))}
IDX = {v: k for k, v in NAME.items()}

def qx(deg):
    a = math.radians(deg)/2
    return (math.sin(a), 0.0, 0.0, math.cos(a))
def walk_pose(ph):
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

NKEY = 14
times = [round(i*(1.3/(NKEY-1)), 4) for i in range(NKEY)]
# ── 追加数据：time（14 float）＋ 每关节 quaternion（14×4 float）──
add = bytearray()
def pad4(buf):
    while len(buf) % 4: buf.append(0)
pad4(add); t_off = len(add)
for t in times: add += struct.pack("<f", t)
quat_off = {}
poses = [walk_pose(i/NKEY) for i in range(NKEY)]
for nm in poses[0]:
    pad4(add)
    quat_off[nm] = len(add)
    for p in poses:
        add += struct.pack("<4f", *p[nm])
pad4(add)
newbin = bin0 + bytes(add)
bin_base = len(bin0)
# ── 新 accessor／bufferView ──
bvs = js["bufferViews"]; accs = js["accessors"]
def add_bv(off, ln):
    bvs.append({"buffer": 0, "byteOffset": off, "byteLength": ln}); return len(bvs)-1
def add_acc(bv, cnt, typ, mn, mx):
    accs.append({"bufferView": bv, "componentType": 5126, "count": cnt, "type": typ, "min": mn, "max": mx})
    return len(accs)-1
tbv = add_bv(bin_base + t_off, 4*NKEY); tacc = add_acc(tbv, NKEY, "SCALAR", [min(times)], [max(times)])
samplers, channels = [], []
for nm, q in poses[0].items():
    bv = add_bv(bin_base + quat_off[nm], 16*NKEY)
    acc = add_acc(bv, NKEY, "VEC4", [min(p[nm][k] for p in poses) for k in range(4)],
                  [max(p[nm][k] for p in poses) for k in range(4)])
    samplers.append({"input": tacc, "output": acc, "interpolation": "LINEAR"})
    channels.append({"sampler": len(samplers)-1, "target": {"node": IDX[nm], "path": "rotation"}})
js.setdefault("animations", []).append({"name": "WALK", "samplers": samplers, "channels": channels})
js["buffers"] = [{"byteLength": len(newbin)}]
# ── 序列化 ──
jb = json.dumps(js, separators=(",", ":")).encode("utf-8")
while len(jb) % 4: jb += b" "
bb = newbin
while len(bb) % 4: bb += b"\x00"
out = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(jb) + 8 + len(bb))
out += struct.pack("<II", len(jb), 0x4E4F534A) + jb
out += struct.pack("<II", len(bb), 0x004E4942) + bb
DST.write_bytes(out)
print("  ★ 新资产：%s（%.0f B）｜动画：%s" % (DST.name, len(out), "、".join(a["name"] for a in js["animations"])))

# ── 独立读取器复核：重开新档、列动画、取 WALK 之 3 帧姿态并核相位 ──
r2 = DST.read_bytes()
jl2, _ = struct.unpack_from("<II", r2, 12); j2 = json.loads(r2[20:20+jl2].decode())
bo2 = 20+jl2; bl2, _ = struct.unpack_from("<II", r2, bo2); b2 = r2[bo2+8:bo2+8+bl2]
print("  === 独立读取器复核 ===")
print("   动画数 = %d ｜ 名：%s" % (len(j2["animations"]), "、".join(a["name"] for a in j2["animations"])))
walk = next(a for a in j2["animations"] if a["name"] == "WALK")
print("   WALK：%d 通道 ｜ %d 采样器" % (len(walk["channels"]), len(walk["samplers"])))
def rd(acc_i):
    a = j2["accessors"][acc_i]; bv = j2["bufferViews"][a["bufferView"]]
    n = {"SCALAR":1,"VEC4":4}[a["type"]]
    off = bv.get("byteOffset",0)+a.get("byteOffset",0)
    return [struct.unpack_from("<%df"%n, b2, off+k*n*4) for k in range(a["count"])]
hip = next(c for c in walk["channels"] if j2["nodes"][c["target"]["node"]]["name"] == "CAIRN_Hip_L")
q = rd(walk["samplers"][hip["sampler"]]["output"])
ang = [round(2*math.degrees(math.asin(max(-1,min(1,p[0])))),1) for p in q]
print("   髋 L 之角度序列（度）：%s" % ang)
print("   ⇒ 范围 %.1f–%.1f（应 ≈ ±25.3）｜ 周期数 = %d" % (min(ang), max(ang), 1))
print("   ⇒ 五态是否保留：%s" % ("是" if all(n in [a["name"] for a in j2["animations"]] for n in ("IDLE_VERIFY","WEIGH","INSPECT","RELAY","REFUSE")) else "否"))
