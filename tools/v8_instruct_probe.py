# -*- coding: utf-8 -*-
"""v8_instruct_probe.py —— 在"我亲手建之世界"下一道明确指令，复验"演绎"是否跨世界一致（2026-10-13 立）
法源：令条「…涵盖世界探索、实时导演、角色演绎三类运行模式」；-1378 已证"夜间游乐场"之五假设皆否证
      （末态 userInstructions[].status 恒 UNEXECUTED）。本器复验：★在我自建之世界是否亦然。
本器（★一次会话 60 s；★不回显凭据；★带退避重试）：
  ① 列世界，★定位"夜游回望"（v8 自建世界）；② 取票；③ 进房（mode=acting，60 s）；
  ④ ★读基线 status（characterActions／environmentActions／userInstructions 数）；
  ⑤ ★POST /travels/instruct 一条点名动作之明确指令（"dash"）；
  ⑥ ★再读 status ⇒ ★对照 userInstructions 之 status／startTime／endTime；
  ⑦ 报判：★若仍 UNEXECUTED ⇒ 跨世界一致（强化 -1378）
判据（可失败）：①进房 code=0；②★指令已被服务端记录（userInstructions 数增）；③★给出跨世界之判
用法：python v8_instruct_probe.py [--sec 60] [--world 夜游回望] [--instr dash]
（中文串一律用「」）
"""
import argparse, json, pathlib, sys, time, urllib.parse, urllib.request, urllib.error

SEAT = pathlib.Path(__file__).resolve().parent.parent
ENVF = pathlib.Path.home()/".zcode"/"workspace"/"default"/"a2a-bridge"/".env"
API = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1"
PROXY = "http://127.0.0.1:10081"


def key():
    for l in ENVF.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if l.strip().startswith("DASHSCOPE_API_KEY"):
            return l.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def call(path, body=None, to=90, tries=4):
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
        except Exception as e:
            last = str(e)[:80]
            print("      ★第 %d 试瞬态：%s ⇒ 退避 %d s" % (i+1, last, 3*(i+1)))
            time.sleep(3*(i+1))
    return -1, {"err": last}


def ui_of(s):
    return s.get("userInstructions") or []


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--sec", type=int, default=60, choices=(60, 90, 120))
    ap.add_argument("--world", default="夜游回望"); ap.add_argument("--instr", default="dash")
    a = ap.parse_args()
    print("  ═══ 在自建世界下指令（复验演绎之跨世界一致性）═══")
    st, j = call("/worlds?page=1&pageSize=50&status=ready")
    items = ((j.get("output") or {}).get("data") or {}).get("items") or []
    pick = next((x for x in items if a.world in str(x.get("name") or "")), None)
    if not pick:
        print("   ★未见世界「%s」⇒ 止。候选：%s" % (a.world, "、".join(str(x.get("name"))[:10] for x in items[:6]))); return 2
    wid = pick.get("encryptedWorldId")
    print("   ① 世界：%s ｜ 建于 %s" % (str(pick.get("name")), str(pick.get("createdAt"))[:19]))
    st, j = call("/worlds/get-travel-credential", {"encryptedWorldId": wid})
    tk = ((j.get("output") or {}).get("data") or {}).get("ticket")
    print("   ② 取票：%s" % ("★有" if tk else "无"))
    if not tk: return 2
    st, j = call("/travels/enter-travel", {"ticket": tk, "maxExperienceTimeSec": a.sec, "mode": "acting"})
    o = j.get("output") or {}; d = o.get("data") or {}
    tid = d.get("encryptedTravelId")
    print("   ③ 进房：code=%s ｜ TravelId=%s ｜ rtcStatus 初值=%s" % (o.get("code"), "有" if tid else "无", d.get("rtcStatus")))
    if o.get("code") != 0 or not tid: return 2
    st, j = call("/travels/status?encryptedTravelId=" + urllib.parse.quote(str(tid)))
    s0 = ((j.get("output") or {}).get("data") or {})
    n0 = len(ui_of(s0))
    print("   ④ 基线：characterActions=%s ｜ environmentActions=%s ｜ userInstructions=%d"
          % (s0.get("characterActions"), s0.get("environmentActions"), n0))
    time.sleep(3)
    st, j = call("/travels/instruct", {"encryptedTravelId": tid, "content": a.instr})
    o2 = j.get("output") or {}
    print("   ⑤ 指令「%s」：HTTP %s ｜ code=%s" % (a.instr, st, o2.get("code")))
    time.sleep(6)
    st, j = call("/travels/status?encryptedTravelId=" + urllib.parse.quote(str(tid)))
    s1 = ((j.get("output") or {}).get("data") or {})
    u = ui_of(s1); n1 = len(u)
    sts = [str(r.get("status")) for r in u]
    print("   ⑥ 对照：userInstructions=%d ｜ ★状态：%s" % (n1, "、".join(sts) if sts else "（无）"))
    for r in u[-3:]:
        print("      ★content=「%s」｜ status=%s ｜ start=%s ｜ end=%s"
              % (str(r.get("content"))[:40], r.get("status"), r.get("startTime"), r.get("endTime")))
    print("   ── 判 ──")
    print("   ★★本世界（我自建之「%s」）亦 %s ⇒ %s"
          % (pick.get("name"), "记录指令但未执行" if (n1 > n0 and all(s == "UNEXECUTED" for s in sts)) else "见上",
             "★跨世界一致（强化 -1378）" if (n1 > n0 and sts and all(s == "UNEXECUTED" for s in sts)) else "★与 -1378 不一致 ⇒ 须核"))
    crit = {"①进房 code=0": o.get("code") == 0, "②★★指令已被服务端记录": n1 > n0, "③★已给跨世界之判": True}
    for k, v in crit.items(): print("   %s ⇒ %s" % (k, "✓" if v else "✗"))
    out = SEAT/"outbox"/"mem"/"v8_instruct_probe_20261013.json"
    out.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "world": str(pick.get("name")),
        "createdAt": pick.get("createdAt"), "instr": a.instr, "enter_code": o.get("code"),
        "ui_before": n0, "ui_after": n1, "ui_status": sts, "criteria": crit}, ensure_ascii=False, indent=1),
        encoding="utf-8", newline="\n")
    print("   ⇒ 已写：%s" % out.name)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True); sys.exit(main())
