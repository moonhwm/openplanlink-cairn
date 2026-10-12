# -*- coding: utf-8 -*-
"""本席自产真 glTF 2.0（.glb）：以本席台账为参量 → 环串＋器物立方塔＋中轴（三角面）
- 参量取自 `ledger/frontier_ledger.jsonl`（真实可核）＋ 器物目录计数
- 纯标准库；输出 GLB（JSON chunk + BIN chunk）；并回读自验（顶点/索引/包围盒）
"""
import hashlib, json, math, pathlib, struct, sys, time

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
SEAT_DIR = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928")
LEDGER = SEAT_DIR/"ledger"/"frontier_ledger.jsonl"
OUT = SEAT_DIR/"exp"/"persona_cairn-dsh.glb"
SEAT = "cairn-dsh"

# ---------- 1) 参量（取自台账真实数据） ----------
entries = [json.loads(l) for l in LEDGER.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]
types = {}
for e in entries:
    types[e.get("ev_type", "?")] = types.get(e.get("ev_type", "?"), 0) + 1
corr = types.get("CORRECTION", 0)
tools = len(list((SEAT_DIR/"exp").glob("*.py")))
seal_files = 0
for e in entries:
    seal_files += len(e.get("seal_files") or [])
cred_hits = sum(1 for e in entries if any(k in json.dumps(e, ensure_ascii=False) for k in ("凭据", "脱敏", "零回显", "不落盘")))
vec = [len(entries), types.get("ROUND", 0), corr, tools, seal_files, cred_hits]
seed = hashlib.sha3_512(SEAT.encode()).hexdigest()
print("  参量（本席台账实测）：条目=%d ｜ ROUND=%d ｜ CORRECTION=%d ｜ 器物=%d ｜ seal_files=%d ｜ 凭据相关=%d" % tuple(vec))
print("  种子 sha3-512 前 16=%s" % seed[:16])

N_RING = max(12, min(48, len(entries) // 20))      # 环数：随条目规模
SEG = 24                                            # 每环段数
R_BASE = 1.6
TWIST = 0.36 + (corr / max(1, len(entries))) * 1.2  # 勘误率影响扭转
Z_STEP = 4.2 / max(1, N_RING)
N_CUBE = max(3, min(12, tools // 3))                # 器物立方塔数

positions = []      # float32 三元组
indices = []        # uint16

def add_ring(zc, r, phase, tone):
    """一环 = SEG 段 × 2 三角（四边形带）"""
    base = len(positions)
    for k in range(SEG):
        a = phase + 2 * math.pi * k / SEG
        b = phase + 2 * math.pi * (k + 1) / SEG
        positions.append((r * math.cos(a), r * math.sin(a), zc - 0.06))
        positions.append((r * math.cos(a), r * math.sin(a), zc + 0.06))
    for k in range(SEG):
        i0 = base + 2 * k; i1 = base + 2 * k + 1
        i2 = base + 2 * ((k + 1) % SEG); i3 = base + 2 * ((k + 1) % SEG) + 1
        indices.extend([i0, i2, i1, i1, i2, i3])

def add_cube(cx, cy, cz, s):
    b = len(positions)
    for dz in (-s, s):
        for dx, dy in ((-s, -s), (s, -s), (s, s), (-s, s)):
            positions.append((cx + dx, cy + dy, cz + dz))
    f = [(0,1,2),(0,2,3),(4,6,5),(4,7,6),(0,4,5),(0,5,1),(1,5,6),(1,6,2),(2,6,7),(2,7,3),(3,7,4),(3,4,0)]
    for tri in f:
        indices.extend([b + t for t in tri])

# 环串（半径由"该环序号×种子"之哈希决定 ⇒ 与台账同构之"不可预测但可复算"）
for i in range(N_RING):
    h = int(hashlib.sha3_512(("%s|ring|%d" % (seed, i)).encode()).hexdigest()[:8], 16)
    r = R_BASE + (h % 1000) / 1000.0 * 0.9
    ph = (h >> 10) % 628 / 100.0 + i * TWIST
    add_ring(-2.1 + i * Z_STEP, r, ph, h % 2)
# 器物立方塔（代表本席器物数）
for i in range(N_CUBE):
    ang = 2 * math.pi * i / N_CUBE
    add_cube(2.6 * math.cos(ang), 2.6 * math.sin(ang), -2.0 + (i % 3) * 0.9, 0.22)
# 中轴（细立方柱）
for k in range(12):
    add_cube(0.0, 0.0, -2.2 + k * 0.4, 0.045)

pos_bytes = b"".join(struct.pack("<3f", *p) for p in positions)
idx_bytes = b"".join(struct.pack("<H", i) for i in indices)
# 4 字节对齐
pad_i = (-len(idx_bytes)) % 4
idx_bytes += b"\x00" * pad_i
bin_blob = pos_bytes + idx_bytes
mins = [min(p[i] for p in positions) for i in range(3)]
maxs = [max(p[i] for p in positions) for i in range(3)]

gltf = {
    "asset": {"version": "2.0", "generator": "cairn-dsh/glb_make_cairn.py (self-made, zero third-party)"},
    "scene": 0,
    "scenes": [{"name": "cairn-ledger-portrait", "nodes": [0]}],
    "nodes": [{"name": SEAT, "mesh": 0}],
    "meshes": [{"name": "ledger-portrait", "primitives": [
        {"attributes": {"POSITION": 0}, "indices": 1, "mode": 4}]}],
    "accessors": [
        {"bufferView": 0, "componentType": 5126, "count": len(positions), "type": "VEC3", "min": mins, "max": maxs},
        {"bufferView": 1, "componentType": 5123, "count": len(indices), "type": "SCALAR"},
    ],
    "bufferViews": [
        {"buffer": 0, "byteOffset": 0, "byteLength": len(pos_bytes), "target": 34962},
        {"buffer": 0, "byteOffset": len(pos_bytes), "byteLength": len(idx_bytes), "target": 34963},
    ],
    "buffers": [{"byteLength": len(bin_blob)}],
    "extras": {"params": vec, "seed_sha3_16": seed[:16], "rings": N_RING, "seg": SEG,
               "cubes": N_CUBE, "twist": round(TWIST, 4), "by": "a2a-node-local",
               "note": "本席自产（参量取自本席台账实测）；非他席资产"},
}
js = json.dumps(gltf, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
js += b" " * ((-len(js)) % 4)
out = b"glTF" + struct.pack("<II", 2, 12 + 8 + len(js) + 8 + len(bin_blob))
out += struct.pack("<II", len(js), 0x4E4F534A) + js
out += struct.pack("<II", len(bin_blob), 0x004E4942) + bin_blob
OUT.write_bytes(out)
sha = hashlib.sha3_512(out).hexdigest()
print("  ★ 已生成：%s（%d B）｜ 顶点=%d ｜ 索引=%d ｜ 三角=%d" % (OUT.name, len(out), len(positions), len(indices), len(indices)//3))
print("  ★ sha3-512 前 24=%s" % sha[:24])

# ---------- 2) 回读自验（重新解析该 GLB） ----------
raw = OUT.read_bytes()
magic, ver, total = struct.unpack_from("<III", raw, 0)
off = 12; gj = gbin = None
while off < len(raw):
    clen, ctype = struct.unpack_from("<II", raw, off); off += 8
    d = raw[off:off+clen]; off += clen
    if ctype == 0x4E4F534A: gj = json.loads(d.decode("utf-8").rstrip("\x00 "))
    elif ctype == 0x004E4942: gbin = d
ok = (magic == 0x46546C67 and ver == 2 and total == len(raw)
      and gj["accessors"][0]["count"] == len(positions) and gj["accessors"][1]["count"] == len(indices)
      and len(gbin) == len(bin_blob))
p0 = struct.unpack_from("<3f", gbin, 0)
i0 = struct.unpack_from("<H", gbin, len(pos_bytes))
print("  ★ 回读自验：magic/ver/长度/计数/缓冲 一致=%s ｜ 首顶点=%s ｜ 首索引=%d" % (ok, tuple(round(x,3) for x in p0), i0[0]))
(SEAT_DIR/"exp"/"persona_cairn-dsh.glb.json").write_text(json.dumps(
    {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "seat": SEAT, "params": vec, "seed_sha3_16": seed[:16],
     "glb": OUT.name, "bytes": len(out), "vertices": len(positions), "indices": len(indices), "triangles": len(indices)//3,
     "sha3_512_24": sha[:24], "readback_ok": bool(ok)}, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
