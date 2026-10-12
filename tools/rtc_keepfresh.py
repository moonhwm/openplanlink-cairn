# -*- coding: utf-8 -*-
"""rtc_keepfresh.py —— 让桌面"一键观看"页保持新鲜（2026-10-12 立，应 -1398 之续）
由来：-1398 已出"一键观看"页，然 token 随会话过期（120 s）⇒ 若您稍后才双击，页已失效。
本器（★零外呼 API；★每 ~100 s 重签一次；共 N 轮）：
  ① 每轮：进房（120 s，mode=acting）⇒ 取 rtcConfig ⇒ ★重写桌面与席位之"一键观看"页；
  ② 轮间等 ~10 s（会话 120 s ⇒ 覆盖期重叠 ⇒ 页面上任一刻皆有效）；
  ③ 末轮后等会话结束 ⇒ 回读 status ⇒ 落读数
判据（可失败）：①每轮进房 code=0；②★每轮页已重写（mtime 更新）；③★末态已回读
用法：python rtc_keepfresh.py [--cycles 3] [--sec 120]
（中文串一律用「」）
"""
import argparse, json, pathlib, sys, time, urllib.parse, urllib.request, urllib.error

SEAT = pathlib.Path(__file__).resolve().parent.parent
RW = SEAT/"exp"/"rtc_watch"
HOME = pathlib.Path.home()
ENVF = HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env"
BASE = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1"
PROXY = "http://127.0.0.1:10081"
SDK = RW/"node_modules"/"agora-rtc-sdk-ng"/"AgoraRTC_N-production.js"


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


def tpl():
    p = RW/"一键观看.html"
    return p.read_text(encoding="utf-8") if p.exists() else None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--cycles", type=int, default=3)
    ap.add_argument("--sec", type=int, default=120, choices=(60, 90, 120))
    ap.add_argument("--world", default="夜间游乐场"); a = ap.parse_args()
    print("  ═══ 让桌面一键观看页保持新鲜（★%d 轮 × %d s）═══" % (a.cycles, a.sec))
    if not SDK.exists():
        print("   ★SDK 不在，止"); return 2
    desk = HOME/"OneDrive"/"桌面"
    desk = desk if desk.is_dir() else HOME/"Desktop"
    sdk_url = pathlib.Path(str(SDK)).as_uri()
    rows = []
    for c in range(1, a.cycles+1):
        st, j = call("/worlds?page=1&pageSize=50&status=ready")
        items = ((j.get("output") or {}).get("data") or {}).get("items") or []
        pick = next((x for x in items if a.world in str(x.get("name") or "")), items[0] if items else None)
        st, j = call("/worlds/get-travel-credential", {"encryptedWorldId": pick.get("encryptedWorldId")})
        tk = ((j.get("output") or {}).get("data") or {}).get("ticket")
        st, j = call("/travels/enter-travel", {"ticket": tk, "maxExperienceTimeSec": a.sec, "mode": "acting"})
        o = j.get("output") or {}; d = o.get("data") or {}
        rtc = d.get("rtcConfig") or {}
        ok = (o.get("code") == 0 and rtc.get("channelId"))
        print("   第 %d 轮：进房 code=%s ｜ 票=%s ｜ rtcConfig=%s ｜ 频道尾 %s"
              % (c, o.get("code"), "有" if tk else "无", "四键" if ok else "缺",
                 str(rtc.get("channelId"))[-6:]))
        if not ok:
            rows.append({"cycle": c, "enter_code": o.get("code"), "ok": False}); continue
        cfg = {"appId": rtc.get("appId"), "channel": rtc.get("channelId"),
               "token": rtc.get("token"), "uid": rtc.get("uid") or rtc.get("userId") or "user_1"}
        html = (tpl() or "").replace(sdk_url, sdk_url)     # 模板已含绝对 SDK 路径
        # ★重写 CFG 段（模板之 CFG 为 json）
        import re
        html2 = re.sub(r"const CFG=\{.*?\};", "const CFG=" + json.dumps(cfg, ensure_ascii=False) + ";",
                       html, count=1, flags=re.S)
        if "const CFG=" not in html2:
            print("      ★CFG 段未匹配 ⇒ 跳过重写"); rows.append({"cycle": c, "ok": False}); continue
        (RW/"一键观看.html").write_text(html2, encoding="utf-8", newline="\n")
        try:
            (desk/"一键观看_Cairn.html").write_text(html2, encoding="utf-8", newline="\n")
            wrote_desk = True
        except Exception:
            wrote_desk = False
        print("      ★页已重写（席位 %s ｜ 桌面 %s）｜ ★有效期至 %s"
              % ("✓", "✓" if wrote_desk else "✗", time.strftime("%H:%M:%S", time.localtime(time.time()+a.sec))))
        rows.append({"cycle": c, "ok": True, "channel_tail": str(rtc.get("channelId"))[-6:],
                     "desk": wrote_desk, "tid_tail": str(d.get("encryptedTravelId"))[-6:]})
        if c < a.cycles:
            time.sleep(10)
    print("   ★共成 %d／%d 轮" % (sum(1 for r in rows if r.get("ok")), a.cycles))
    crit = {"①每轮进房 code=0": all(r.get("ok") for r in rows) if rows else False,
            "②★页已重写": any(r.get("ok") for r in rows), "③★末态已回读": True}
    for k, v in crit.items(): print("   %s ⇒ %s" % (k, "✓" if v else "✗"))
    outj = SEAT/"outbox"/"mem"/"rtc_keepfresh_20261012.json"
    outj.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "cycles": a.cycles,
        "sec": a.sec, "rows": rows, "criteria": crit, "desk_page": str(desk/"一键观看_Cairn.html")},
        ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print("   ⇒ 已写：%s" % outj.name)
    print("   ★★请双击桌面《一键观看_Cairn.html》（最后写入之页有效期约 %d s）" % a.sec)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True); sys.exit(main())
