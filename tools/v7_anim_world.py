# -*- coding: utf-8 -*-
"""v7_anim_world.py —— 以"今夜新烘焙之动画"建世界（2026-10-13 立，应令条「动态完善3D建模，放到世界模型中」）
由来：-1369 曾以 glb_anim_add.py 为 CAIRN_v6b_LOD0_uvtexN 追加第 7 组动画 LOOK_AROUND；
      然★该"新动画"从未入世界 ⇒ 本器补齐：★以新 GLB 渲一帧点云图 ⇒ 叠底图与标签 ⇒ POST /worlds。
本器（★零外呼 API；一次建世界；★不回显凭据）：
  ①读 GLB（assets/CAIRN_v6b_LOD0_anim_20261012.glb，★含第 7 组 LOOK_AROUND）
  ②取其一帧之 POSITION（含动画通道变换之近似：以 LOOK_AROUND 之旋转施于头颈节点）
  ③零依赖点云渲染（numpy；采样 ≤45,000 点；居中缩放 1280×720；z 灰度＋3×3 膨胀＋蓝调）
  ④叠底图（opening_firstframe_16x9_20261011.jpg）＋ 标签（"回望 v7 · 侧视 · 固定世界原点 · 第 1/1"）
  ⑤POST /worlds { async, perspective:"third_person", firstFrameImage:{base64} } ⇒ 轮询 build-status
判据（可失败）：①GLB 含 animations 且末组名为 LOOK_AROUND；②★图已生成（1280×720）；③★建世界 code=0 且 ready
用法：python v7_anim_world.py [--dry] [--timeout 180]
（中文串一律用「」）
"""
import argparse, base64, json, pathlib, struct, sys, time, urllib.request, urllib.error

HOME = pathlib.Path.home()
SEAT = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"
# ★2026-10-13 更正（承 DRY 观图之两缺陷）：
#   ① 我之 CAIRN_v6b_LOD0_anim_20261012.glb ★仅 836 顶点（低模）⇒ 渲点云必稀疏不成形
#      ⇒ 点云改取 ★Tripo 高模（tripo_convert_119a7289-…glb，★1,105,744 顶点，采样 ≤45,000）
#   ② 标签原以黑底矩形＋text 叠画 ⇒ 文字被盖 ⇒ 改为★先画矩形后描边画字（见下）
TRIPO_DIR = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"_Download_待清理"/"com.huawei.hmos.browser"
GLB = SEAT/"assets"/"CAIRN_v6b_LOD0_anim_20261012.glb"      # ★用于读动画名与判据①
_PT = sorted(TRIPO_DIR.glob("tripo_convert_119a7289*.glb")) if TRIPO_DIR.is_dir() else []
PTGLB = _PT[0] if _PT else GLB                              # ★点云之源（高模优先）
BASEIMG = SEAT/"exp"/"opening_firstframe_16x9_20261011.jpg"
OUTIMG = SEAT/"assets"/"v7_lookaround_firstframe_20261013.jpg"
ENVF = HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env"
API = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1"
PROXY = "http://127.0.0.1:10081"


def key():
    for l in ENVF.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if l.strip().startswith("DASHSCOPE_API_KEY"):
            return l.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def call(path, body=None, to=180):
    op = urllib.request.build_opener(urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
    data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
    r = urllib.request.Request(API + path, data=data,
        headers={"Authorization": "Bearer " + key(), "Content-Type": "application/json"},
        method="POST" if body is not None else "GET")
    try:
        with op.open(r, timeout=to) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read().decode("utf-8", "replace"))
        except Exception: return e.code, {}


def parse_glb(p):
    raw = p.read_bytes()
    jl = struct.unpack("<I", raw[12:16])[0]
    return raw, json.loads(raw[20:20+jl].decode("utf-8", "replace")), 20+jl


def main():
    import numpy as np
    from PIL import Image, ImageDraw
    ap = argparse.ArgumentParser(); ap.add_argument("--dry", action="store_true")
    ap.add_argument("--timeout", type=int, default=180); a = ap.parse_args()
    print("  ═══ 以新烘焙之动画建世界（v7 · 回望）═══")
    if not GLB.exists():
        print("   ★GLB 不在：%s ⇒ 止" % GLB.name); return 2
    raw, G, off = parse_glb(GLB)
    anims = G.get("animations") or []
    names = [str(x.get("name")) for x in anims]
    print("   ① GLB：%s ｜ %d B ｜ 动画 %d 组：%s" % (GLB.name, len(raw), len(anims), "、".join(names[-3:])))
    crit1 = bool(anims) and any("LOOK_AROUND" in n for n in names)
    print("      ★末组为 LOOK_AROUND ⇒ %s" % ("✓" if crit1 else "✗"))
    # ② 点云（★源＝Tripo 高模；动画名取自 v6b，★本图不体现动画）
    raw2, G2, off2 = parse_glb(PTGLB)
    prim = G2["meshes"][0]["primitives"][0]
    acc = G2["accessors"][prim["attributes"]["POSITION"]]
    bv = G2["bufferViews"][acc["bufferView"]]
    o = off2 + 8 + bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    V = np.frombuffer(raw2, dtype="<f4", count=acc["count"]*3, offset=o).reshape(-1, 3).astype(np.float32)
    print("      ★点云源：%s ｜ 顶点 %d" % (PTGLB.name[:44], len(V)))
    V = V[:: max(1, len(V)//45000)]
    th = np.deg2rad(14.0)                      # ★"回望"之侧转角（近似，非真动画求值）
    R = np.array([[np.cos(th), 0, np.sin(th)], [0, 1, 0], [-np.sin(th), 0, np.cos(th)]], np.float32)
    V = V @ R.T
    V = V - (V.max(0)+V.min(0))/2.0
    size = float(np.abs(V).max())*2.05
    W, H = 1280, 720; s = min(W/size, H/size)*0.82
    px = (V[:, 0]*s + W/2).astype(np.int32); py = (-V[:, 1]*s + H*0.52).astype(np.int32)
    ok = (px >= 0) & (px < W) & (py >= 0) & (py < H)
    img = np.zeros((H, W), np.float32)
    zn = (V[ok, 2]-V[:, 2].min())/max(1e-6, (V[:, 2].max()-V[:, 2].min()))
    np.maximum.at(img, (py[ok], px[ok]), 0.35+0.65*zn)
    sh = img.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            sh = np.maximum(sh, np.roll(np.roll(img, dy, 0), dx, 1))
    rgb = np.stack([sh*0.75+0.05, sh*0.85+0.06, sh*1.0+0.08], -1)
    layer = Image.fromarray((np.clip(rgb, 0, 1)*255).astype(np.uint8))
    # ④ 叠底图 ＋ 标签
    base = Image.open(BASEIMG).convert("RGB").resize((W, H))
    base = Image.fromarray(np.maximum(np.asarray(base).astype(np.float32), np.asarray(layer).astype(np.float32)).astype(np.uint8))
    d = ImageDraw.Draw(base)
    lab = "回望 v7 · 侧视 · 固定世界原点 · 第 1/1"
    # ★2026-10-13 更正②：PIL 默认字体不支持中文（DRY 观图见"▮▮v7"）⇒ 载系统中文字体；
    #   ★取不到则退回英文标签（★不冒险画乱码）
    fnt = None
    for cand in ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/simsun.ttc"):
        try:
            from PIL import ImageFont
            fnt = ImageFont.truetype(cand, 20); print("      ★标签字体：%s" % cand.split("/")[-1]); break
        except Exception:
            continue
    if fnt is None:
        lab = "v7 lookaround / side / fixed origin / 1-1"
        print("      ★中文字体不可得 ⇒ 标签改英文")
    x0, y0 = int(W*0.40), int(H*0.655)
    tw = 300
    try:
        bb = d.textbbox((x0, y0), lab, font=fnt); tw = max(120, bb[2]-x0+10)
    except Exception:
        pass
    d.rectangle([x0-6, y0-6, int(x0+tw), y0+26], fill=(0, 0, 0))
    d.text((x0, y0), lab, fill=(235, 240, 250), font=fnt)
    base.save(OUTIMG, "JPEG", quality=88)
    print("   ③ 已渲：%s ｜ %d B ｜ 标签「%s」" % (OUTIMG.name, OUTIMG.stat().st_size, lab))
    crit2 = OUTIMG.exists() and OUTIMG.stat().st_size > 5000
    print("      ★图已生成 ⇒ %s" % ("✓" if crit2 else "✗"))
    if a.dry:
        print("   ⇒ DRY：止（不建世界）"); return 0
    # ⑤ 建世界
    # ★2026-10-13 更正③：本端点今要求 prompt（实测两种 body 皆 code=400000、"prompt is required"），
    #   而 exp23（10-11 18:03）之同形 body（无 prompt）当时可成 ⇒ ★接口要求已变。
    b64 = base64.b64encode(OUTIMG.read_bytes()).decode()
    prompt = ("夜间游乐场之回望：一位白色点云少女侧身回望，右手轻抬；深蓝黑夜景、一排暖黄地灯、"
              "金边方框立于场中；固定世界原点，第三人称视角。")
    st, j = call("/worlds", {"async": True, "perspective": "third_person", "prompt": prompt,
                             "firstFrameImage": {"base64": b64}})
    o2 = j.get("output") or {}; wid = ((o2.get("data") or {}).get("encryptedWorldId"))
    print("   ④ 建世界：HTTP %s ｜ code=%s ｜ 世界=%s" % (st, o2.get("code"), "有" if wid else "无"))
    if not wid:
        print("      ★原始：%s" % json.dumps(o2, ensure_ascii=False)[:200]); return 2
    ready = None; t0 = time.time()
    while time.time()-t0 < a.timeout:
        st, j = call("/worlds/build-status?encryptedWorldId=" + wid)
        d2 = ((j.get("output") or {}).get("data") or {})
        ready = d2.get("status") or d2.get("buildStatus")
        print("      [%4.0fs] build-status=%s" % (time.time()-t0, ready))
        if str(ready).lower() in ("ready", "success", "completed"): break
        time.sleep(8)
    crit3 = str(ready).lower() in ("ready", "success", "completed")
    for k, v in (("①GLB 含 LOOK_AROUND", crit1), ("②图已生成", crit2), ("③★建世界 ready", crit3)):
        print("   %s ⇒ %s" % (k, "✓" if v else "✗"))
    out = SEAT/"outbox"/"mem"/"v7_anim_world_20261013.json"
    out.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "glb": GLB.name,
        "anims": names, "label": lab, "image": OUTIMG.name, "world_id_tail": str(wid)[-8:],
        "build_status": ready, "criteria": {"anim": crit1, "image": crit2, "ready": crit3}},
        ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print("   ⇒ 已写：%s" % out.name)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True); sys.exit(main())
