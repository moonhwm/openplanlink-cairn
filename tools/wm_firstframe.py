# -*- coding: utf-8 -*-
"""wm_firstframe.py —— 取世界之首帧图（2026-10-12 立，应 -1382 之请）
由来：-1382 见 enter-travel 返回 firstFrame（首帧图 URL），而 10-11 探针所记之 URL ★被截断（尾部 …）
     ⇒ ★本器以一次会话取完整 URL 并下载其图（★零外呼；仅读 CDN）。
本器（★最小化：一次会话 60 s；★不发指令；★不回显凭据）：
  ① 列世界 ⇒ 取"夜间游乐场"；② 取票；③ 进房（★读 firstFrame 之完整 URL 与 rtcConfig 之键）；
  ④ ★下载 firstFrame 至 assets/；⑤ 报其大小／类型／尺寸；⑥ 会话结束
判据（可失败）：①进房 code=0；②★firstFrame 非空且已下载；③图为 JPEG／PNG
用法：python wm_firstframe.py [--sec 60] [--world 夜间游乐场]
（中文串一律用「」）
"""
import argparse, json, pathlib, struct, sys, time, urllib.request, urllib.error

ENVF = pathlib.Path.home()/".zcode"/"workspace"/"default"/"a2a-bridge"/".env"
BASE = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1"
PROXY = "http://127.0.0.1:10081"
ASSETS = pathlib.Path(__file__).resolve().parent.parent/"assets"


def key():
    for l in ENVF.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if l.strip().startswith("DASHSCOPE_API_KEY"):
            return l.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def op():
    return urllib.request.build_opener(urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))


def call(path, body=None, to=90):
    k = key()
    data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, headers={"Authorization": "Bearer " + k,
                              "Content-Type": "application/json"}, method="POST" if body is not None else "GET")
    try:
        with op().open(r, timeout=to) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read().decode("utf-8", "replace"))
        except Exception: return e.code, {}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--sec", type=int, default=60, choices=(60, 90, 120))
    ap.add_argument("--world", default="夜间游乐场"); a = ap.parse_args()
    print("  ═══ 取世界之首帧图（★一次会话 %d s；不发指令）═══" % a.sec)
    st, j = call("/worlds?page=1&pageSize=50&status=ready")
    items = ((j.get("output") or {}).get("data") or {}).get("items") or []
    pick = next((x for x in items if a.world in str(x.get("name") or "")), items[0] if items else None)
    if not pick:
        print("   ⇒ 判：★无世界，止"); return 2
    print("   ① 世界：%s（尾 %s）｜ ready %d" % (str(pick.get("name"))[:20], str(pick.get("encryptedWorldId"))[-8:], len(items)))
    st, j = call("/worlds/get-travel-credential", {"encryptedWorldId": pick.get("encryptedWorldId")})
    tk = ((j.get("output") or {}).get("data") or {}).get("ticket")
    print("   ② 取票：HTTP %s ｜ 票=%s" % (st, "★有" if tk else "无"))
    if not tk: return 2
    st, j = call("/travels/enter-travel", {"ticket": tk, "maxExperienceTimeSec": a.sec})
    o = j.get("output") or {}; d = o.get("data") or {}
    print("   ③ 进房：HTTP %s ｜ code=%s ｜ TravelId=%s" % (st, o.get("code"), "有" if d.get("encryptedTravelId") else "无"))
    ff = d.get("firstFrame"); rtc = d.get("rtcConfig") or {}
    print("   ★firstFrame（完整）：%s" % (ff or "（null）"))
    print("   ★rtcConfig 之键：%s" % "、".join(rtc.keys()) or "（无）")
    print("   ★version=%s ｜ mode=%s ｜ playUrl=%s" % (d.get("version"), d.get("mode"), d.get("playUrl")))
    ok_img = False; path = None
    if ff:
        try:
            with op().open(urllib.request.Request(ff), timeout=90) as r:
                b = r.read()
            ct = r.headers.get("content-type") or ""
            sig = b[:4]
            ext = ".jpg" if sig[:2] == b"\xff\xd8" else (".png" if sig == b"\x89PNG" else ".bin")
            path = ASSETS/("firstframe_%s%s" % (time.strftime("%Y%m%d_%H%M"), ext))
            path.write_bytes(b)
            print("   ④ 已下载：%s ｜ %d B ｜ content-type=%s ｜ magic=%s" % (path.name, len(b), ct, sig.hex()))
            ok_img = ext in (".jpg", ".png")
            if ext == ".jpg":
                w = h = None
                i = 2
                while i < len(b)-8:
                    if b[i] != 0xFF: i += 1; continue
                    m = b[i+1]
                    if m in (0xC0, 0xC1, 0xC2):
                        h, w = struct.unpack(">HH", b[i+5:i+9]); break
                    if m in (0xD8, 0xD9) or 0xD0 <= m <= 0xD7: i += 2; continue
                    ln = struct.unpack(">H", b[i+2:i+4])[0]; i += 2 + ln
                print("   ★JPEG 尺寸：%sx%s" % (w, h))
        except Exception as e:
            print("   ④ 下载失败：%s" % str(e)[:90])
    crit = {"①进房 code=0": o.get("code") == 0, "②★firstFrame 非空且已下载": bool(ff) and path is not None and path.exists(),
            "③图为 JPEG／PNG": ok_img}
    for k, v in crit.items(): print("   %s ⇒ %s" % (k, "✓" if v else "✗"))
    print("   ★等待会话结束（%d s）…" % a.sec); time.sleep(a.sec)
    outj = pathlib.Path(__file__).resolve().parent.parent/"outbox"/"mem"/"wm_firstframe_20261012.json"
    outj.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "world": str(pick.get("name")),
        "firstFrame": ff, "rtc_keys": sorted(rtc.keys()), "version": d.get("version"), "mode": d.get("mode"),
        "playUrl": d.get("playUrl"), "image": path.name if path else None, "criteria": crit},
        ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print("   ⇒ 已写：%s" % outj.name)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True); sys.exit(main())
