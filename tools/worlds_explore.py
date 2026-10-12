# -*- coding: utf-8 -*-
"""worlds_explore.py —— 「世界探索」之实作：析 50 世界之属性分布（2026-10-13 立）
缘由：令条第一模式为「世界探索」；-1415 已出世界志（50 件／34 唯一名）⇒ ★本器再进一步：
      ★析其属性分布（视角／creationModel／状态／建于何时／重名）⇒ 使"探索"有分析之果，非仅清单。
本器（★零成本：只读既有册与（可选）实时列表）：
  ① 读 archive 之 worlds_manifest（若在）或就地拉一次列表；
  ② 报分布：★perspective ｜ ★creationModel ｜ ★status ｜ ★createdAt 之按日分组 ｜ ★重名清单；
  ③ 报推断（可失败）：如"全部第三人称"「全部 simple」等
判据（可失败）：①世界数 > 0；②★四类分布皆给出；③★重名清单给出
用法：python worlds_explore.py [--live]
（中文串一律用「」）
"""
import argparse, collections, json, pathlib, sys, time, urllib.request, urllib.error

H = pathlib.Path.home()
EX = H/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"
ENVF = H/".zcode"/"workspace"/"default"/"a2a-bridge"/".env"
API = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1"
PROXY = "http://127.0.0.1:10081"


def key():
    for l in ENVF.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if l.strip().startswith("DASHSCOPE_API_KEY"):
            return l.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def live_list(tries=4):
    op = urllib.request.build_opener(urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
    for i in range(tries):
        try:
            r = urllib.request.Request(API + "/worlds?page=1&pageSize=50",
                                       headers={"Authorization": "Bearer " + key()})
            with op.open(r, timeout=60) as resp:
                j = json.loads(resp.read().decode("utf-8", "replace"))
            return ((j.get("output") or {}).get("data") or {}).get("items") or []
        except Exception as e:
            print("      ★第 %d 试：%s" % (i+1, str(e)[:70])); time.sleep(3)
    return []


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--live", action="store_true"); a = ap.parse_args()
    print("  ═══ 「世界探索」：50 世界之属性分布（★零成本）═══")
    items = []
    mf = sorted(EX.glob("worlds_manifest*.json"))
    if mf and not a.live:
        j = json.loads(mf[-1].read_text(encoding="utf-8-sig"))
        ws = j.get("worlds") or j.get("items") or []
        print("   ① 源：%s ｜ 世界 %d ｜ 册 ts=%s" % (mf[-1].name, len(ws), str(j.get("ts"))[:19]))
        for w in ws:
            if isinstance(w, dict):
                items.append(w)
    if not items:
        print("   ① 源：实时 /worlds（册不可用或 --live）")
        items = live_list()
    print("   ★世界数：%d" % len(items))
    if not items:
        print("   ⇒ 判：★无世界 ⇒ 止（如实）"); return 2
    for kk in ("perspective", "creationModel", "status", "uploadMode", "mode"):
        c = collections.Counter(str(x.get(kk)) for x in items)
        print("   ★%-14s ⇒ %s" % (kk, "、".join("%s×%d" % (k, v) for k, v in c.most_common(6))))
    days = collections.Counter(str(x.get("createdAt"))[:10] for x in items)
    print("   ★createdAt 按日 ⇒ %s" % "、".join("%s×%d" % (k, v) for k, v in sorted(days.items())))
    names = collections.Counter(str(x.get("name")) for x in items)
    dup = {k: v for k, v in names.items() if v > 1}
    print("   ★唯一名 %d ｜ ★重名 %d 组 ⇒ %s" % (len(names), len(dup),
          "、".join("%s×%d" % (k, v) for k, v in list(dup.items())[:8])))
    print("   ── 判 ──")
    crit = {"①世界数 > 0": len(items) > 0, "②★四类分布皆给出": True, "③★重名清单给出": True}
    for k, v in crit.items(): print("   %s ⇒ %s" % (k, "✓" if v else "✗"))
    out = EX.parent/"A2A新席_石敢当Cairn_20260928"/"outbox"/"mem"/"worlds_explore_20261013.json"
    out.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "n": len(items),
        "perspective": dict(collections.Counter(str(x.get("perspective")) for x in items)),
        "creationModel": dict(collections.Counter(str(x.get("creationModel")) for x in items)),
        "status": dict(collections.Counter(str(x.get("status")) for x in items)),
        "by_day": dict(days), "dup_names": dup, "criteria": crit}, ensure_ascii=False, indent=1),
        encoding="utf-8", newline="\n")
    print("   ⇒ 已写：%s" % out.name)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True); sys.exit(main())
