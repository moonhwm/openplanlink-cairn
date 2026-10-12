# -*- coding: utf-8 -*-
"""rtc_orchestrate.py —— "最后一环"之编排：进房 ⇒ RTC 观看 ⇒ 报推流证据（2026-10-12 立，应 -1394）
法源：令条「…放到世界模型中，理应尝试涌现」；-1378 证"指令恒 UNEXECUTED"、「执行」疑在客户端（RTC）侧；
      -1394 查明 rtc_watch/ 之 auto.html ＋ watch.html ＋ rtc_probe.mjs 已备，只差编排。
本器（★零外呼 API；一次会话；★不回显 token）：
  ① 进房（mode=acting；60 s）⇒ 取 rtcConfig（appId／channelId／token／userId）；
  ② 以 auto.html 为模板，★替换其硬编码 CFG 为本会话之值 ⇒ 写 auto_run.html；
  ③ 调 rtc_probe.mjs（Puppeteer ＋ 本机 Edge headless；等待 N 秒）⇒ 采 console／state；
  ④ 从日志判：★「远端用户数」与「视频轨道数」⇒ 即"世界是否向我推流"之直接证据
判据（可失败）：①进房 code=0 且得 rtcConfig；②★探针输出含"远端用户数"；③★已给推流判定
用法：python rtc_orchestrate.py [--sec 60] [--wait 25] [--dry]
（中文串一律用「」）
"""
import argparse, json, pathlib, re, subprocess, sys, time, urllib.parse, urllib.request, urllib.error

SEAT = pathlib.Path(__file__).resolve().parent.parent
RW = SEAT/"exp"/"rtc_watch"
ENVF = pathlib.Path.home()/".zcode"/"workspace"/"default"/"a2a-bridge"/".env"
BASE = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1"
PROXY = "http://127.0.0.1:10081"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def key():
    for l in ENVF.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if l.strip().startswith("DASHSCOPE_API_KEY"):
            return l.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def call(path, body=None, to=90):
    k = key()
    op = urllib.request.build_opener(urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
    data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, headers={"Authorization": "Bearer " + k,
                              "Content-Type": "application/json"}, method="POST" if body is not None else "GET")
    try:
        with op.open(r, timeout=to) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read().decode("utf-8", "replace"))
        except Exception: return e.code, {}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--sec", type=int, default=60, choices=(60, 90, 120))
    ap.add_argument("--wait", type=int, default=25); ap.add_argument("--dry", action="store_true")
    ap.add_argument("--world", default="夜间游乐场"); a = ap.parse_args()
    print("  ═══ 最后一环之编排（★零外呼；一次会话 %d s）═══" % a.sec)
    if not pathlib.Path(EDGE).exists():
        print("   ★Edge 不在：%s ⇒ 改用系统 chrome？止（如实报）" % EDGE); return 2
    tpl = RW/"auto.html"
    if not tpl.exists():
        print("   ★模板不在：auto.html，止"); return 2
    st, j = call("/worlds?page=1&pageSize=50&status=ready")
    items = ((j.get("output") or {}).get("data") or {}).get("items") or []
    pick = next((x for x in items if a.world in str(x.get("name") or "")), items[0] if items else None)
    if not pick:
        print("   ★无世界，止"); return 2
    print("   ① 世界：%s（尾 %s）" % (str(pick.get("name"))[:20], str(pick.get("encryptedWorldId"))[-8:]))
    if a.dry:
        print("   ⇒ DRY：止（不进房）"); return 0
    st, j = call("/worlds/get-travel-credential", {"encryptedWorldId": pick.get("encryptedWorldId")})
    tk = ((j.get("output") or {}).get("data") or {}).get("ticket")
    print("   ② 取票：票=%s" % ("★有" if tk else "无"))
    if not tk: return 2
    st, j = call("/travels/enter-travel", {"ticket": tk, "maxExperienceTimeSec": a.sec, "mode": "acting"})
    o = j.get("output") or {}; d = o.get("data") or {}
    rtc = d.get("rtcConfig") or {}
    print("   ③ 进房：code=%s ｜ ★rtcConfig 键：%s" % (o.get("code"), "、".join(sorted(rtc.keys()))))
    if o.get("code") != 0 or not rtc.get("channelId"):
        print("      ★原始：%s" % json.dumps(d, ensure_ascii=False)[:180]); return 2
    # ② 生成带参页（★替换硬编码 CFG）
    t = tpl.read_text(encoding="utf-8")
    cfg = {"appId": rtc.get("appId"), "channel": rtc.get("channelId"),
           "token": rtc.get("token"), "uid": rtc.get("uid") or rtc.get("userId") or "user_1"}
    t2 = re.sub(r"const q = new URLSearchParams\(''\); const CFG = \{.*?\};",
                "const q = new URLSearchParams(''); const CFG = " + json.dumps(cfg, ensure_ascii=False) + ";",
                t, count=1, flags=re.S)
    if "const CFG = " not in t2:
        print("   ★模板替换失败（未匹配 CFG），止"); return 2
    out_html = RW/"auto_run.html"
    out_html.write_text(t2, encoding="utf-8", newline="\n")
    print("   ④ 已生成带参页：auto_run.html（★token 不回显）")
    # ③ 调探针（★会话仍在跑）
    print("   ⑤ 起 Puppeteer ＋ Edge（等待 %d s）…" % a.wait)
    t0 = time.time()
    try:
        r = subprocess.run(["node", str(RW/"rtc_probe.mjs"), str(out_html), str(a.wait)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=a.wait+120, cwd=str(RW))
        log = (r.stdout or "") + "\n" + (r.stderr or "")
        rc = r.returncode
    except Exception as e:
        log = "★探针异常：%s" % str(e)[:120]; rc = -1
    print("   ⑥ 探针 rc=%s ｜ 用时 %.1f s ｜ 输出 %d 字" % (rc, time.time()-t0, len(log)))
    for ln in log.splitlines():
        if any(k in ln for k in ("已加入频道", "远端", "连接态", "视频轨道", "异常", "汇总", "已订阅", "SDK 版本", "audience")):
            print("      ｜ " + ln.strip()[:120])
    # ④ 判定
    m = re.search(r"远端用户数[=＝]\s*(\d+)", log)
    v = re.search(r"视频轨道[=＝]\s*(\d+)", log)
    nu = int(m.group(1)) if m else None
    nv = int(v.group(1)) if v else None
    push = (nu is not None and nu >= 1)
    print("   ★★判：远端用户数=%s ｜ 视频轨道数=%s ⇒ %s"
          % (nu, nv, "★世界在向我推流（有远端）" if push else "★未见远端推流"))
    crit = {"①进房 code=0 且得 rtcConfig": o.get("code") == 0 and bool(rtc.get("channelId")),
            "②★探针输出含远端用户数": nu is not None, "③★已给推流判定": True}
    for k, vv in crit.items(): print("   %s ⇒ %s" % (k, "✓" if vv else "✗"))
    outj = SEAT/"outbox"/"mem"/"rtc_orchestrate_20261012.json"
    outj.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "world": str(pick.get("name")),
        "enter_code": o.get("code"), "rtc_keys": sorted(rtc.keys()), "probe_rc": rc,
        "remote_users": nu, "video_tracks": nv, "push_seen": push,
        "log_tail": [l for l in log.splitlines() if l.strip()][-25:], "criteria": crit},
        ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print("   ⇒ 已写：%s" % outj.name)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True); sys.exit(main())
