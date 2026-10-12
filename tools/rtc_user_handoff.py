# -*- coding: utf-8 -*-
"""rtc_user_handoff.py —— 把"接 RTC 观看"之最后一环交到用户侧（2026-10-12 立，应 -1397 之请求②）
由来：-1396／-1397 证本环境之 Edge ★完全不可用（连 --version 都挂起）⇒ 观看须在"用户侧浏览器"。
本器（★零外呼 API；一次会话；★不回显 token 于命令行；★token 仅落在用户侧页面一次）：
  ① 进房（mode=acting；120 s）⇒ 取 rtcConfig；
  ② 生成"一键打开"页（自包含：内嵌 rtcConfig ＋ agora-rtc-sdk-ng 之★绝对 file:// 路径）
     ⇒ 写两处：rtc_watch/一键观看.html 与★桌面/一键观看_Cairn.html；
  ③ 打印★三步说明（双击 → 看待连入日志 → 回来告我）；
  ④ 会话结束后读 status 之 userInstructions ⇒ ★看是否有 EXECUTED（可否因客户端在线而改变）
判据（可失败）：①进房 code=0 且得 rtcConfig；②★两处页已生成；③★会话末已回读 status
用法：python rtc_user_handoff.py [--sec 120] [--world 夜间游乐场]
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


PAGE = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>Cairn 席 · 一键观看世界</title>
<script src="__SDK__"></script></head>
<body style="font-family:system-ui;margin:16px">
<h3>★Cairn 席 · 一键观世（本页由本席生成；会话 %SEC% s）</h3>
<div id="log" style="white-space:pre-wrap;font:13px/1.5 ui-monospace;background:#111;color:#ddd;padding:12px;border-radius:6px">[起点] 页面已载入</div>
<video id="v" autoplay playsinline width="720" style="margin-top:12px;background:#000"></video>
<script>
const L=(m)=>{const d=document.getElementById('log');d.textContent+="\\n["+new Date().toISOString().slice(11,19)+"] "+m;};
const CFG=__CFG__;
L("参数：appId="+(CFG.appId?CFG.appId.slice(0,8)+"…":"缺")+" channel="+(CFG.channel||"缺")+" token="+(CFG.token?"有(长"+CFG.token.length+")":"缺")+" uid="+CFG.uid);
if(!window.AgoraRTC){L("★SDK 未载入（AgoraRTC 不存在）—— 请确认本页与 node_modules 同一目录，或改用 rtc_watch 内之页");}
else{(async()=>{try{
  L("SDK 版本："+(AgoraRTC.VERSION||"?"));
  const c=AgoraRTC.createClient({mode:"live",codec:"vp8"});
  c.on("user-published",async(u,mt)=>{L("★远端发布："+mt+" uid="+u.uid);await c.subscribe(u,mt);
    if(mt==="video"){u.videoTrack.play(document.getElementById('v'));L("★已订阅视频并播放（若画面出现，即为世界在推流）");}
    if(mt==="audio"){u.audioTrack.play();L("★已订阅音频");}});
  c.on("user-joined",(u)=>L("远端加入 uid="+u.uid));
  c.on("user-left",(u)=>L("远端离开 uid="+u.uid));
  c.on("connection-state-change",(s,p)=>L("连接态："+p+" → "+s));
  await c.join(CFG.appId,CFG.channel,CFG.token||null,CFG.uid);
  L("★★已加入频道");
  try{await c.setClientRole("audience");L("★已设为 audience");}catch(e){L("设角色失败："+e.message);}
  L("频道内远端用户数："+c.remoteUsers.length+" ｜ 视频轨道："+c.remoteUsers.filter(u=>u.hasVideo).length);
  setTimeout(()=>{L("30 秒后：远端用户数="+c.remoteUsers.length+" ｜ 视频轨道="+c.remoteUsers.filter(u=>u.hasVideo).length+" ｜ ★探针完成");},30000);
}catch(e){L("★异常："+e.name+" / "+e.message);}})();}
</script></body></html>
"""


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--sec", type=int, default=120, choices=(60, 90, 120))
    ap.add_argument("--world", default="夜间游乐场"); a = ap.parse_args()
    print("  ═══ 把「接 RTC 观看」交到用户侧（★零外呼；一次会话 %d s）═══" % a.sec)
    if not SDK.exists():
        print("   ★SDK 不在：%s ⇒ 止（如实报）" % SDK); return 2
    st, j = call("/worlds?page=1&pageSize=50&status=ready")
    items = ((j.get("output") or {}).get("data") or {}).get("items") or []
    pick = next((x for x in items if a.world in str(x.get("name") or "")), items[0] if items else None)
    print("   ① 世界：%s（尾 %s）" % (str(pick.get("name"))[:20], str(pick.get("encryptedWorldId"))[-8:]))
    st, j = call("/worlds/get-travel-credential", {"encryptedWorldId": pick.get("encryptedWorldId")})
    tk = ((j.get("output") or {}).get("data") or {}).get("ticket")
    print("   ② 取票：票=%s" % ("★有" if tk else "无"))
    if not tk: return 2
    st, j = call("/travels/enter-travel", {"ticket": tk, "maxExperienceTimeSec": a.sec, "mode": "acting"})
    o = j.get("output") or {}; d = o.get("data") or {}
    tid = d.get("encryptedTravelId"); rtc = d.get("rtcConfig") or {}
    print("   ③ 进房：code=%s ｜ ★rtcConfig 四键：%s" % (o.get("code"), "、".join(sorted(rtc.keys()))))
    if o.get("code") != 0 or not tid:
        print("      ★原始：%s" % json.dumps(d, ensure_ascii=False)[:180]); return 2
    cfg = {"appId": rtc.get("appId"), "channel": rtc.get("channelId"),
           "token": rtc.get("token"), "uid": rtc.get("uid") or rtc.get("userId") or "user_1"}
    # ★自包含页（SDK 用绝对 file:// 路径 ⇒ 桌面副本亦可载入）
    sdk_url = pathlib.Path(str(SDK)).as_uri()
    html = PAGE.replace("__SDK__", sdk_url).replace("__CFG__", json.dumps(cfg, ensure_ascii=False)).replace("%SEC%", str(a.sec))
    p1 = RW/"一键观看.html"; p1.write_text(html, encoding="utf-8", newline="\n")
    desk = HOME/"OneDrive"/"桌面"
    desk = desk if desk.is_dir() else HOME/"Desktop"
    p2 = desk/"一键观看_Cairn.html"
    try:
        p2.write_text(html, encoding="utf-8", newline="\n")
    except Exception as e:
        print("   ⚠ 桌面副本未成：%s" % str(e)[:60])
    print("   ④ ★已生成：")
    print("      ★%s" % p1)
    print("      ★%s" % p2 if p2.exists() else "      （桌面副本未成）")
    print("\n  ═══ ★请您做（三步）═══")
    print("     ① 双击桌面之《一键观看_Cairn.html》（用您的浏览器打开）")
    print("     ② 看页面上之日志：若现「★远端发布：video」且视频区出画面 ⇒ ★世界在推到您侧")
    print("     ③ 回来告我结果（或把日志末 5 行贴我）")
    print("     ★本会话 %d s 内有效；过期后我可再出一份（一次会话）" % a.sec)
    print("   ★等待会话结束（%d s）…" % a.sec)
    time.sleep(a.sec)
    st, j = call("/travels/status?encryptedTravelId=" + urllib.parse.quote(str(tid)))
    s2 = ((j.get("output") or {}).get("data") or {})
    ui = s2.get("userInstructions") or []
    sts = [str(r.get("status")) for r in ui]
    print("   ⑤ 末态：status=%s ｜ ★userInstructions 状态：%s" % (s2.get("status"), "、".join(sts) if sts else "（无）"))
    crit = {"①进房 code=0 且得 rtcConfig": o.get("code") == 0 and bool(rtc.get("channelId")),
            "②★两处页已生成": p1.exists(), "③★会话末已回读 status": bool(s2)}
    for k, v in crit.items(): print("   %s ⇒ %s" % (k, "✓" if v else "✗"))
    outj = SEAT/"outbox"/"mem"/"rtc_user_handoff_20261012.json"
    outj.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "world": str(pick.get("name")),
        "sec": a.sec, "enter_code": o.get("code"), "rtc_keys": sorted(rtc.keys()),
        "page_rtc": str(p1), "page_desktop": str(p2) if p2.exists() else None,
        "end_status": s2.get("status"), "ui_status": sts, "criteria": crit}, ensure_ascii=False, indent=1),
        encoding="utf-8", newline="\n")
    print("   ⇒ 已写：%s" % outj.name)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True); sys.exit(main())
