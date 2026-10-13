# -*- coding: utf-8 -*-
"""wm_quick_check.py —— 世界模型免费通道之快速核（2026-10-13 立，承 -1444）
缘由：百炼账户欠费（−8.44 CNY）后，世界模型（Adventure trial app）★走免费通道尚可用（00:44 实证）；
      ★本器为零成本之复验：列世界、核我之三世界（霓虹虚空／夜游回望／夜色游乐场）仍在且 ready。
本器（★零成本；只读；★带退避重试；零凭据回显）：
  ① GET /worlds?page=1&pageSize=50
  ② 报总数与 ready 数
  ③ ★核三世界之名与状态
判据（可失败）：①HTTP 200 且 code=0；②★三世界皆 ready
用法：python wm_quick_check.py
（中文串一律用「」）
"""
import json, pathlib, sys, time, urllib.request, urllib.error

ENVF = pathlib.Path.home()/".zcode"/"workspace"/"default"/"a2a-bridge"/".env"
API = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1"
PROXY = "http://127.0.0.1:10081"
WATCH = ("霓虹虚空", "夜游回望", "夜色游乐场")


def key():
    for l in ENVF.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if l.strip().startswith("DASHSCOPE_API_KEY"):
            return l.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def get(tries=4):
    op = urllib.request.build_opener(urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
    for i in range(tries):
        try:
            r = urllib.request.Request(API + "/worlds?page=1&pageSize=50",
                                       headers={"Authorization": "Bearer " + key()})
            with op.open(r, timeout=60) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8", "replace"))
        except Exception as e:
            print("      ★第 %d 试：%s" % (i+1, str(e)[:70])); time.sleep(3)
    return -1, {}


def main():
    print("  ═══ 世界模型免费通道之快速核（★零成本；只读）═══")
    st, j = get()
    o = j.get("output") or {}
    items = (o.get("data") or {}).get("items") or []
    print("   ① HTTP %s ｜ code=%s ｜ ★世界数 %d ｜ ready %d"
          % (st, o.get("code"), len(items), sum(1 for x in items if x.get("status") == "ready")))
    for name in WATCH:
        w = next((x for x in items if x.get("name") == name), None)
        print("   ★%s ⇒ %s" % (name, ("★ready（建于 %s）" % str(w.get("createdAt"))[:19]) if w else "★不在列表"))
    ok = (st == 200 and o.get("code") == 0 and
          all(next((x for x in items if x.get("name") == n), None) is not None for n in WATCH))
    crit = {"①HTTP 200 且 code=0": st == 200 and o.get("code") == 0, "②★三世界皆在": ok}
    for k, v in crit.items(): print("   %s ⇒ %s" % (k, "✓" if v else "✗"))
    out = pathlib.Path(__file__).resolve().parent.parent/"outbox"/"mem"/("wm_quick_check_%s.json" % time.strftime("%Y%m%d_%H%M"))
    out.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "http": st, "code": o.get("code"),
        "worlds": len(items), "ready": sum(1 for x in items if x.get("status") == "ready"),
        "watched": {n: bool(next((x for x in items if x.get("name") == n), None)) for n in WATCH},
        "criteria": crit}, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print("   ⇒ 已写：%s" % out.name)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True); sys.exit(main())
