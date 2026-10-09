# -*- coding: utf-8 -*-
"""行迹驱动之替身世界：七拍之数值取自本席真实台账（世界数／审计／条目／器物／自正／复现／暂止）
★ 映射规则由本席所定并明示 ⇒ 非涌现（如实标注）
输出：①七拍数值柱＋分身立于「留痕」拍之画面 ②JSON 记录映射
（引号一律用「」）
"""
import json, math, pathlib, struct, sys, time

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
SEAT = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"
EX = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"

# ── ① 采集真实数值 ──
ledger = SEAT/"ledger"/"frontier_ledger.jsonl"
events = SEAT/"ops"/"ops_event.jsonl"
n_led = sum(1 for _ in ledger.open(encoding="utf-8", errors="replace")) if ledger.exists() else 0
n_ev = sum(1 for _ in events.open(encoding="utf-8", errors="replace")) if events.exists() else 0
n_tools = len(list((SEAT/"exp").glob("*.py"))) + len(list((SEAT/"exp").glob("*.cs")))
n_art = len(list(EX.glob("*CAIRN*.otl")))
worlds = 23          # 已知：worlds_manifest 22 件 + v7 之世界（`-57`）
audit = 9            # A 级九项（08:35 日更）
import re as _re
n_self = 0
for p in EX.glob("*CAIRN*.otl"):
    t = p.read_text(encoding="utf-8", errors="replace")
    if any(k in t for k in ("自查", "更正", "收紧", "撤回", "否证", "自我归因")):
        n_self += 1
n_repro = sum(1 for p in EX.glob("*CAIRN*.otl") if "复现" in p.read_text(encoding="utf-8", errors="replace"))
n_pause = sum(1 for p in EX.glob("*CAIRN*.otl") if "暂止" in p.read_text(encoding="utf-8", errors="replace"))
BEATS = [("游戏", worlds, "已建世界数（清单 22＋v7）"),
         ("验收", audit, "A 级九项审计通过项"),
         ("留痕", n_led, "台账条目数"),
         ("器物", n_tools, "exp/ 之脚本数（.py/.cs）"),
         ("自正", n_self, "含自查/更正/收紧/撤回/否证之件数"),
         ("复现", n_repro, "含「复现」之件数"),
         ("暂止", n_pause, "含「暂止」之件数")]
print("  === 七拍真实数值 ===")
for nm, v, src in BEATS:
    print("    %-4s = %-6s （%s）" % (nm, v, src))
vals = [v for _, v, _ in BEATS]
mx = max(vals) or 1

# ── ② 分身渲染（取 LOD1；立于「留痕」拍，态＝RELAY）──
raw = (SEAT/"exp"/"CAIRN_avatar_v2_LOD1.glb").read_bytes()
jlen, _ = struct.unpack_from("<II", raw, 12); js = json.loads(raw[20:20+jlen].decode())
boff = 20+jlen; blen, _ = struct.unpack_from("<II", raw, boff); bn = raw[boff+8:boff+8+blen]
CT = {5123:("H",2),5125:("I",4),5126:("f",4)}; NC = {"SCALAR":1,"VEC3":3,"VEC4":4,"MAT4":16}
def racc(i):
    a = js["accessors"][i]; bv = js["bufferViews"][a["bufferView"]]
    f, s = CT[a["componentType"]]; n = NC[a["type"]]
    off = bv.get("byteOffset",0)+a.get("byteOffset",0)
    return [struct.unpack_from("<%d%s"%(n,f), bn, off+k*n*s) for k in range(a["count"])]
prim = js["meshes"][0]["primitives"][0]
POS = racc(prim["attributes"]["POSITION"]); JTS = racc(prim["attributes"]["JOINTS_0"]); WTS = racc(prim["attributes"]["WEIGHTS_0"])
IDX = [i[0] for i in racc(prim["indices"])]
JN = js["skins"][0]["joints"]; IBM = racc(js["skins"][0]["inverseBindMatrices"])
PARENT = {}
for i, nd in enumerate(js["nodes"]):
    for c in nd.get("children", []): PARENT[c] = i
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
def eval_anim(name, t):
    out = {}
    an = next((a for a in js["animations"] if a["name"] == name), None)
    if not an: return out
    for ch in an["channels"]:
        if ch["target"]["path"] != "rotation": continue
        s = an["samplers"][ch["sampler"]]
        ti = [v[0] for v in racc(s["input"])]; qq = racc(s["output"])
        if t <= ti[0]: q = list(qq[0])
        elif t >= ti[-1]: q = list(qq[-1])
        else:
            for k in range(len(ti)-1):
                if ti[k] <= t <= ti[k+1]:
                    u = (t-ti[k])/max(1e-9, ti[k+1]-ti[k]); q = [qq[k][m]*(1-u)+qq[k+1][m]*u for m in range(4)]; break
        n = math.sqrt(sum(v*v for v in q)) or 1.0
        out[ch["target"]["node"]] = [v/n for v in q]
    return out
def skin(anim):
    W = {}
    order = sorted(range(len(js["nodes"])), key=lambda i: (lambda f: f(f, i))(lambda f, x: 0 if x not in PARENT else 1+f(f, PARENT[x])))
    for i in order:
        nd = js["nodes"][i]; t0 = list(nd.get("translation", [0,0,0])); q = list(nd.get("rotation", [0,0,0,1]))
        if i in anim: q = anim[i]
        loc = trs(t0, q); W[i] = loc if i not in PARENT else mul(W[PARENT[i]], loc)
    M = [mul(W[JN[k]], list(IBM[k])) for k in range(len(JN))]
    out = []
    for vi, v in enumerate(POS):
        acc = [0.0, 0.0, 0.0]
        for k in range(4):
            w = WTS[vi][k]
            if w <= 0: continue
            m = M[JTS[vi][k]]
            acc[0] += w*(m[0]*v[0]+m[4]*v[1]+m[8]*v[2]+m[12]); acc[1] += w*(m[1]*v[0]+m[5]*v[1]+m[9]*v[2]+m[13]); acc[2] += w*(m[2]*v[0]+m[6]*v[1]+m[10]*v[2]+m[14])
        out.append(tuple(acc))
    return out

from PIL import Image, ImageDraw, ImageFont
def cjk(sz):
    for p in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"):
        try: return ImageFont.truetype(p, sz)
        except Exception: pass
    return ImageFont.load_default()
F46, F26, F20 = cjk(50), cjk(28), cjk(22)
W, H = 1680, 1000
img = Image.new("RGB", (W, H), (9, 10, 13)); d = ImageDraw.Draw(img)
d.text((40, 26), "行迹驱动之替身世界 —— 七拍之数值取自本席真实台账", fill=(244, 242, 236), font=F46)
d.text((40, 92), "★ 映射规则由本席所定并明示 ⇒ 非涌现；数值源：正本仓台账／事件链／exp 目录／交换区件数", fill=(196, 170, 150), font=F20)
# 七拍柱
bx0, by0, bw, bh = 90, 640, 150, 150
for i, (nm, v, src) in enumerate(BEATS):
    x = bx0 + i*(bw+60)
    hh = int(bh * (v/mx))
    d.rectangle([x, by0+bh-hh, x+bw, by0+bh], fill=(120, 150, 170))
    d.text((x, by0+bh+8), "%s %s" % (nm, v), fill=(230, 228, 222), font=F26)
    d.text((x, by0+bh+44), src[:16], fill=(150, 152, 158), font=F20)
# 分身（立于「留痕」拍；态＝RELAY）
verts = skin(eval_anim("RELAY", 0.6))
cx_px, cy_px, k = 1180, 430, 195
xs = [v[0] for v in verts]; ys = [v[1] for v in verts]
cx = (max(xs)+min(xs))/2
tris = sorted(range(len(IDX)//3), key=lambda n: -(verts[IDX[n*3]][2]+verts[IDX[n*3+1]][2]+verts[IDX[n*3+2]][2]))
for n in tris:
    pts = [(cx_px + (verts[IDX[n*3+j]][0]-cx)*k, cy_px + 240 - (verts[IDX[n*3+j]][1]-0.9)*k) for j in range(3)]
    zavg = sum(verts[IDX[n*3+j]][2] for j in range(3))/3
    lum = int(150 + 70*max(0.0, min(1.0, (zavg+0.3)/0.6)))
    d.polygon(pts, fill=(lum, lum, min(255, lum+8)))
d.text((cx_px-140, cy_px+300), "分身（CAIRN_avatar v2_LOD1）", fill=(230, 228, 222), font=F26)
d.text((cx_px-175, cy_px+336), "立于「留痕」拍 ｜ 态＝RELAY（数据流带点亮）", fill=(178, 176, 170), font=F20)
# 右栏：数值明细
d.text((980, 130), "七拍之真实数值与来源", fill=(238, 236, 230), font=F26)
for i, (nm, v, src) in enumerate(BEATS):
    d.text((980, 175 + i*38), "%-4s = %-6s  %s" % (nm, v, src), fill=(198, 196, 190), font=F20)
d.text((980, 460), "★ 本席自称：本图所示「世界」仍非平台世界模型；", fill=(196, 170, 150), font=F20)
d.text((980, 492), "   其数值为真、其映射为人工 ⇒ 不含涌现（未闭合）", fill=(196, 170, 150), font=F20)
png = SEAT/"exp"/"trace_driven_surrogate_20261009.png"
img.save(png, "PNG", optimize=True)
print("  ★ 图：%s（%.2f MB）" % (png.name, png.stat().st_size/1048576))
(EX/"trace_driven_surrogate_20261009_CAIRN.json").write_text(json.dumps(
    {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "seat": "a2a-node-local",
     "concept": "行迹驱动之替身世界：七拍数值取自真实台账",
     "beats": [{"beat": nm, "value": v, "source": src} for nm, v, src in BEATS],
     "mapping_rule": "七拍＝{游戏:世界数, 验收:A级九项, 留痕:台账条目, 器物:exp 脚本数, 自正:含自查类件数, 复现:含复现类件数, 暂止:含暂止类件数}",
     "note": "★非平台世界模型；数值真实、映射人工 ⇒ 不含涌现"},
    ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("  ★ JSON：trace_driven_surrogate_20261009_CAIRN.json")
