# -*- coding: utf-8 -*-
"""v9_anim_world.py —— "动态完善"之第二轮：依 v7 观图之问题调构图，再建一世界（2026-10-13 立）
由来：令条原文"个人基于人设的★动态完善3D建模，放到世界模型中" ⇒ ★"动态完善"＝迭代。
      v7（世界「霓虹虚空」）观图见三处可改：①点云落在金边框之后（被框遮）②人物偏大、头顶近框顶
      ③标签在画面中部，略挡人物 ⇒ 本器为 v8：★人物居右、缩放收小、标签移至下缘。
本器（★零外呼 API；一次建世界；★不回显凭据）：
  ①读 Tripo 高模点云（tripo_convert_119a7289-…glb，★1,105,744 顶点）
  ②渲点云（采样 ≤45,000；z 灰度＋3×3 膨胀＋蓝调；★scale 0.62／cx 0.645／cy 0.50）
  ③叠底图；★标签置下缘（y 0.905）："回望 v9 · 侧视 · 固定世界原点 · 第 1/1 · 动作池之试"
  ④POST /worlds { async, perspective, ★prompt, firstFrameImage } ⇒ 轮询 build-status（★带退避重试）
判据（可失败）：①点云源顶点 > 100000；②★图已生成；③★建世界 code=0 且 ready
用法：python v9_anim_world.py [--dry] [--timeout 220]
（中文串一律用「」）
"""
import argparse, base64, json, pathlib, struct, sys, time, urllib.request, urllib.error

HOME = pathlib.Path.home()
SEAT = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"
TRIPO_DIR = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"_Download_待清理"/"com.huawei.hmos.browser"
_PT = sorted(TRIPO_DIR.glob("tripo_convert_119a7289*.glb")) if TRIPO_DIR.is_dir() else []
PTGLB = _PT[0] if _PT else None
BASEIMG = SEAT/"exp"/"opening_firstframe_16x9_20261011.jpg"
OUTIMG = SEAT/"assets"/"v9_actionpool_firstframe_20261013.jpg"
ENVF = HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env"
API = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1"
PROXY = "http://127.0.0.1:10081"
LABEL = "回望 v9 · 侧视 · 固定世界原点 · 第 1/1 · 动作池之试"


def key():
    for l in ENVF.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if l.strip().startswith("DASHSCOPE_API_KEY"):
            return l.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def call(path, body=None, to=180, tries=4):
    """★带退避重试（承 -1419：瞬态 WinError 10054 两度致崩）"""
    last = None
    for i in range(tries):
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
        except Exception as e:                      # ★瞬态网络错 ⇒ 退避重试
            last = str(e)[:90]
            print("      ★第 %d 试瞬态异常：%s ⇒ 退避 %d s" % (i+1, last, 3*(i+1)))
            time.sleep(3*(i+1))
    return -1, {"err": last}


def parse_glb(p):
    raw = p.read_bytes()
    jl = struct.unpack("<I", raw[12:16])[0]
    return raw, json.loads(raw[20:20+jl].decode("utf-8", "replace")), 20+jl


def main():
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    ap = argparse.ArgumentParser(); ap.add_argument("--dry", action="store_true")
    ap.add_argument("--timeout", type=int, default=220); a = ap.parse_args()
    print("  ═══ v8：动态完善之第二轮（调构图再建世界）═══")
    if PTGLB is None or not PTGLB.exists():
        print("   ★未找到 Tripo 高模 ⇒ 止"); return 2
    raw, G, off = parse_glb(PTGLB)
    prim = G["meshes"][0]["primitives"][0]
    acc = G["accessors"][prim["attributes"]["POSITION"]]
    bv = G["bufferViews"][acc["bufferView"]]
    o = off + 8 + bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    V = np.frombuffer(raw, dtype="<f4", count=acc["count"]*3, offset=o).reshape(-1, 3).astype(np.float32)
    nv = len(V)
    print("   ① 点云源：%s ｜ ★顶点 %d" % (PTGLB.name[:40], nv))
    V = V[:: max(1, nv//45000)]
    th = np.deg2rad(16.0)                            # ★"回望"侧转角（近似）
    R = np.array([[np.cos(th), 0, np.sin(th)], [0, 1, 0], [-np.sin(th), 0, np.cos(th)]], np.float32)
    V = V @ R.T
    V = V - (V.max(0)+V.min(0))/2.0
    W, H = 1280, 720
    size = float(np.abs(V).max())*2.05
    s = min(W/size, H/size)*0.62                      # ★收小（v7 用 0.82）
    px = (V[:, 0]*s + W*0.645).astype(np.int32)       # ★人物居右（v7 居中）
    py = (-V[:, 1]*s + H*0.50).astype(np.int32)
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
    base = Image.open(BASEIMG).convert("RGB").resize((W, H))
    base = Image.fromarray(np.maximum(np.asarray(base).astype(np.float32), np.asarray(layer).astype(np.float32)).astype(np.uint8))
    d = ImageDraw.Draw(base)
    fnt = None
    for cand in ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf"):
        try: fnt = ImageFont.truetype(cand, 19); break
        except Exception: continue
    lab = LABEL if fnt else "v9 lookaround / side / fixed origin / actionpool"
    x0, y0 = int(W*0.06), int(H*0.905)               # ★标签置下缘（v7 在中部）
    try:
        bb = d.textbbox((x0, y0), lab, font=fnt); tw = max(160, bb[2]-x0+12)
    except Exception:
        tw = 460
    d.rectangle([x0-6, y0-7, int(x0+tw), y0+25], fill=(0, 0, 0))
    d.text((x0, y0), lab, fill=(235, 240, 250), font=fnt)
    base.save(OUTIMG, "JPEG", quality=88)
    print("   ② 已渲：%s ｜ %d B ｜ 标签「%s」" % (OUTIMG.name, OUTIMG.stat().st_size, lab))
    crit1 = nv > 100000; crit2 = OUTIMG.exists() and OUTIMG.stat().st_size > 5000
    if a.dry:
        for k, v in (("①点云源顶点>100000", crit1), ("②图已生成", crit2)):
            print("   %s ⇒ %s" % (k, "✓" if v else "✗"))
        print("   ⇒ DRY：止（不建世界）"); return 0
    b64 = base64.b64encode(OUTIMG.read_bytes()).decode()
    prompt = ("夜色游乐场之回望：一位白色点云少女立于画面右侧、侧身回望；深蓝黑夜景、一排暖黄地灯、金边方框；固定世界原点。★场内之门可开可闭（open_close_door）；★人物可行走、奔跑、跳跃、下蹲、攻击（walk / dash / jump / crouch / attack）。")
    st, j = call("/worlds", {"async": True, "perspective": "third_person", "prompt": prompt,
                             "firstFrameImage": {"base64": b64}})
    o2 = j.get("output") or {}; wid = ((o2.get("data") or {}).get("encryptedWorldId"))
    print("   ③ 建世界：HTTP %s ｜ code=%s ｜ 世界=%s" % (st, o2.get("code"), "有" if wid else "无"))
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
    for k, v in (("①点云源顶点>100000", crit1), ("②图已生成", crit2), ("③★建世界 ready", crit3)):
        print("   %s ⇒ %s" % (k, "✓" if v else "✗"))
    out = SEAT/"outbox"/"mem"/"v9_anim_world_20261013.json"
    out.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "iter": 2,
        "point_source": PTGLB.name, "vertices": nv, "label": lab, "image": OUTIMG.name,
        "world_id_tail": str(wid)[-8:], "build_status": ready,
        "criteria": {"pts": crit1, "image": crit2, "ready": crit3}}, ensure_ascii=False, indent=1),
        encoding="utf-8", newline="\n")
    print("   ⇒ 已写：%s" % out.name)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True); sys.exit(main())

