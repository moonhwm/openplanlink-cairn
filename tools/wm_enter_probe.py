# -*- coding: utf-8 -*-
"""wm_enter_probe.py —— 判世界模型之 403 是"仅列表腿"还是"全 app"（2026-10-14 立，承 -1467）
背景：/worlds 自 10-13 03:33 起持续 403（23.5 h）⇒ 须判：仅列表端点受限，还是 app 级全拒？
本器（★零成本；只读；★不新建世界、不进入 travel、不消耗门票）：
  ① 自本地世界志取一个 encryptedWorldId
  ② GET /worlds/build-status?encryptedWorldId=<id>   ← 只读
  ③ GET /worlds?page=1&pageSize=1                    ← 对照
  ④ 另试 /worlds/get-travel-credential（仅 GET，不带参）以观察其错误形态
判据：给三者 HTTP ⇒ 判「全 app 拒」或「仅列表腿拒」或「皆通」
（中文串一律用「」）
"""
import json, pathlib, sys, time, urllib.request, urllib.error

H = pathlib.Path.home()
EX = H/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"
SEAT = H/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"
ENVF = H/".zcode"/"workspace"/"default"/"a2a-bridge"/".env"
API = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1"
PROXY = "http://127.0.0.1:10081"


def key():
    for l in ENVF.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if l.strip().startswith("DASHSCOPE_API_KEY"):
            return l.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def get(path, tries=2, to=45):
    op = urllib.request.build_opener(urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
    last = (-1, {})
    for i in range(tries):
        try:
            r = urllib.request.Request(API + path, headers={"Authorization": "Bearer " + key()})
            with op.open(r, timeout=to) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            try: last = (e.code, json.loads(e.read().decode("utf-8", "replace")))
            except Exception: last = (e.code, {})
        except Exception as e:
            last = (-1, {"err": str(e)[:80]})
        time.sleep(3)
    return last


def find_id():
    for d in (EX, SEAT/"outbox"/"mem"):
        if not d.exists():
            continue
        for f in sorted(d.glob("*worlds*manifest*.json")) + sorted(d.glob("worlds_manifest*.json")):
            try:
                j = json.loads(f.read_text(encoding="utf-8-sig"))
            except Exception:
                continue
            for w in (j.get("worlds") or j.get("items") or []):
                if isinstance(w, dict) and w.get("encryptedWorldId"):
                    return str(w["encryptedWorldId"]), str(w.get("name")), f.name
    return None, None, None


def main():
    print("  ═══ 世界模型：判 403 之范围（★零成本；只读；不消耗门票）═══")
    wid, wname, src = find_id()
    print("   ① 本地册取 id：%s（%s）｜源 %s" % ((wid or "★无")[-8:] if wid else "★无", wname or "-", src or "-"))
    st0, j0 = get("/worlds?page=1&pageSize=1")
    print("   ② /worlds（列表腿）        ⇒ HTTP %s" % st0)
    if wid:
        st1, j1 = get("/worlds/build-status?encryptedWorldId=" + wid)
        code1 = (j1.get("output") or {}).get("code")
        print("   ③ /worlds/build-status（单项腿）⇒ HTTP %s ｜ code=%s" % (st1, code1))
        st2, j2 = get("/worlds/get-travel-credential")
        print("   ④ /worlds/get-travel-credential（★无参，仅观错误形态）⇒ HTTP %s ｜ %s"
              % (st2, str(j2)[:90].replace("\n", " ")))
    else:
        st1 = st2 = None
    print("   ── 判 ──")
    if st0 == 200 and st1 == 200:
        print("   ★列表与单项皆通 ⇒ 403 已解")
    elif st0 != 200 and st1 == 200:
        print("   ★仅「列表腿」受限（单项腿通）⇒ 可用 build-status 与进入腿")
    elif st0 != 200 and st1 is not None and st1 != 200:
        print("   ★★两腿皆拒 ⇒ 疑 app 级（免费通道到期／权限变更）")
    else:
        print("   ★数据不足（见上）")
    out = SEAT/"outbox"/"mem"/("wm_enter_probe_%s.json" % time.strftime("%Y%m%d_%H%M"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "id_tail": (wid or "")[-8:],
        "worlds_http": st0, "build_status_http": st1, "credential_http": st2},
        ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print("   ⇒ 已写：%s" % out.name)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True); sys.exit(main())
