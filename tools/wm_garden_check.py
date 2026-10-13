# -*- coding: utf-8 -*-
"""wm_garden_check.py —— 核「夜间游乐场」之开园状态（2026-10-13 立，承 -1457）
缘由：令条「夜间游乐场开园」⇒ 其世界（今晚 19:14 出 248 帧）应仍在 50 世界之列；
      ★本器零成本核：其名／状态／建于何时／与"夜色游乐场"（我 v9）之别。
用法：python wm_garden_check.py
（中文串一律用「」）
"""
import json, pathlib, sys, time, urllib.request, urllib.error

ENVF = pathlib.Path.home()/".zcode"/"workspace"/"default"/"a2a-bridge"/".env"
API = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1"
PROXY = "http://127.0.0.1:10081"


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
    print("  ═══ 「夜间游乐场」开园状态核（★零成本；只读）═══")
    st, j = get()
    items = ((j.get("output") or {}).get("data") or {}).get("items") or []
    # ★自纠三十九：判「不在」之前须先判「已取到」（10054／403 时 items 为空 ≠ 不在）
    if st != 200 or not items:
        print("   ★★★未取到列表（HTTP %s）⇒ ★「不在」之判无效 ⇒ 如实报「须核」" % st)
        out = pathlib.Path(__file__).resolve().parent.parent/"outbox"/"mem"/("wm_garden_check_%s.json" % time.strftime("%Y%m%d_%H%M"))
        out.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "fetched": False,
            "http": st, "note": "未取到列表，判无效"}, ensure_ascii=False, indent=1),
            encoding="utf-8", newline="\n")
        print("   ⇒ 已写：%s" % out.name)
        return 2
    g = [x for x in items if (x.get("name") or "") == "夜间游乐场"]
    if g:
        w = g[0]
        print("   ★「夜间游乐场」★在：status=%s ｜ 建于 %s ｜ id 尾八 %s ｜ 视角 %s"
              % (w.get("status"), str(w.get("createdAt"))[:19], str(w.get("encryptedWorldId"))[-8:],
                 w.get("perspective")))
    else:
        print("   ★「夜间游乐场」★不在 50 世界之列（如实）")
    v9 = [x for x in items if (x.get("name") or "") == "夜色游乐场"]
    print("   ·「夜色游乐场」（我 v9）%s" % ("★在（" + str(v9[0].get("createdAt"))[:19] + "）" if v9 else "★不在"))
    ok = bool(g and g[0].get("status") == "ready")
    print("   ── 判 ──")
    print("   ★开园状态：%s" % ("★ready（已开）" if ok else "★须核"))
    out = pathlib.Path(__file__).resolve().parent.parent/"outbox"/"mem"/("wm_garden_check_%s.json" % time.strftime("%Y%m%d_%H%M"))
    out.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "garden": bool(g),
        "garden_status": (g[0].get("status") if g else None), "v9_in_list": bool(v9)},
        ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print("   ⇒ 已写：%s" % out.name)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True); sys.exit(main())
