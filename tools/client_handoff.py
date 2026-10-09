# -*- coding: utf-8 -*-
"""客户端交接一键器：换票 → 进房 → 打印客户端所需字段
★默认零回显：token 不打印、不落盘；仅当显式 --show-token 时**打印一次**（供操作者当次使用）
用法：python client_handoff.py --world 极简检验室 [--max-sec 90] [--show-token]
（引号一律用「」）
"""
import argparse, json, pathlib, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
ENV = HOME / ".zcode" / "workspace" / "default" / "a2a-bridge" / ".env"
B = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1"

ap = argparse.ArgumentParser()
ap.add_argument("--world", default="极简检验室", help="世界之平台命名")
ap.add_argument("--max-sec", type=int, default=90, choices=(60, 90, 120))
ap.add_argument("--show-token", action="store_true", help="★显式要求打印 token（默认不打印）")
args = ap.parse_args()

env = {}
for line in ENV.read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
K = env.get("DASHSCOPE_API_KEY", "")

def api(path, body=None, to=90):
    r = urllib.request.Request(B + path, data=json.dumps(body, ensure_ascii=False).encode() if body else None,
                               method="POST" if body else "GET")
    r.add_header("Authorization", "Bearer " + K)
    if body: r.add_header("Content-Type", "application/json")
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=to) as resp:
            return resp.status, round(time.time()-t0, 2), json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, round(time.time()-t0, 2), {"err": e.read().decode("utf-8", "replace")[:200]}
    except Exception as e:
        return -1, round(time.time()-t0, 2), {"err": str(e)[:140]}

print("  ① 查世界「%s」…" % args.world)
st, dt, j = api("/worlds?page=1&pageSize=50&status=ready")
items = ((j.get("output") or {}).get("data") or {}).get("items") or []
tgt = next((i for i in items if i.get("name") == args.world), None)
if not tgt:
    print("  × 未找到该世界；可选：%s" % "、".join(i.get("name") for i in items[:12])); sys.exit(1)
WID = tgt["encryptedWorldId"]
print("     ⇒ 已找到（ID 尾 %s）" % str(WID)[-10:])

st, dt, j = api("/worlds/get-travel-credential", {"encryptedWorldId": WID})
tk = ((j.get("output") or {}).get("data") or {}).get("ticket")
print("  ② 换票 ⇒ HTTP %s ｜ %.2fs ｜ 得票=%s（★不落盘）" % (st, dt, bool(tk)))
if not tk: sys.exit(1)

st, dt, j = api("/travels/enter-travel", {"ticket": tk, "maxExperienceTimeSec": args.max_sec})
dd = (j.get("output") or {}).get("data") or {}
TID = dd.get("encryptedTravelId"); rtc = dd.get("rtcConfig") or {}
print("  ③ 进房 ⇒ HTTP %s ｜ %.2fs ｜ TravelId=%s" % (st, dt, TID))
print("\n  === 交客户端之字段（可用者）===")
for k in ("appId", "channelId", "userId", "expireTime", "expireAt"):
    if k in rtc: print("     %-12s = %s" % (k, rtc.get(k)))
print("     version      = %s" % dd.get("version"))
print("     token        = %s" % ("（见下——仅当次使用，勿存）" if args.show_token else "**默认不打印（零回显）**"))
if args.show_token:
    print("\n  ★★ 一次性 token（**请勿保存、勿转发、用毕即弃**）：")
    print("     %s" % rtc.get("token"))
print("\n  === 客户端应做（探针 v4 之 B 组）===")
print("     ① 以 rtcConfig 连入 RTC；② 按《真实进房作业包 v1》十拍序列下发指令；")
print("     ③ 记录每拍发出时刻／应答／延迟（DataChannel 留痕）；④ 会话结束后取产物录像并回传。")
print("\n  ★ 边界：本器不落盘任何 ticket／token；ticket 为一次性（复用将报 401011）。")
