# -*- coding: utf-8 -*-
"""复测昨日已打通之三动作（承 DF-AI-12）：① POST /worlds ② build-status ③ get-travel-credential
★ 与昨夜之"列举探针"（GET /worlds?...）作对照 ⇒ 判"403 未购买"之判是否成立
★ ticket 不落盘、不打印
（引号一律用「」）
"""
import json, pathlib, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
env = {}
for line in (pathlib.Path.home()/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8-sig", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
K = env.get("DASHSCOPE_API_KEY", "")
BASE = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1"


def call(method, path, body=None, key=None, to=90):
    url = path if path.startswith("http") else BASE + path
    r = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode() if body else None, method=method)
    r.add_header("Authorization", "Bearer " + (key or K))
    if body: r.add_header("Content-Type", "application/json")
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=to) as resp:
            return resp.status, resp.read().decode("utf-8", "replace"), round(time.time()-t0, 2)
    except urllib.error.HTTPError as e:

        """★墙闸"""
        try:
            _b = e.read().decode("utf-8", "replace")
            import sys as _s, pathlib as _p
            _s.path.insert(0, str(_p.Path(__file__).resolve().parent))
            import wall_guard as _wg
            if _wg.classify(_b)[0] == "wall":
                _wg.record(_b, source=_p.Path(__file__).name, channel="wall")
                print("   ★撞墙即停（零重试）")
                return e.code, _b[:200]
        except Exception:
            pass
        return e.code, e.read().decode("utf-8", "replace"), round(time.time()-t0, 2)
    except Exception as e:
        return -1, str(e)[:160], round(time.time()-t0, 2)


print("  === 对照 A：昨夜之「列举」探针（GET /worlds?…）===")
st, tx, dt = call("GET", "/worlds?page=1&pageSize=1&status=ready")
print("   GET /worlds ⇒ HTTP %-4s ｜ %.2f s ｜ %s" % (st, dt, tx[:130].replace("\n", " ")))

print("\n  === 对照 B：昨日已打通之「创建」（POST /worlds）===")
body = {"async": True, "perspective": "third_person",
        "prompt": "第三人称：一间没有门窗的居所内，地面有七枚发光节点连成一环；一个人形分身立于环心，左手持闸门、右手持座钟。"}
st, tx, dt = call("POST", "/worlds", body)
wid = None
try:
    j = json.loads(tx); wid = (((j.get("output") or {}).get("data")) or {}).get("encryptedWorldId")
except Exception:
    pass
print("   POST /worlds ⇒ HTTP %-4s ｜ %.2f s ｜ id=%s ｜ %s" % (st, dt, ("…" + str(wid)[-8:]) if wid else "无", tx[:150].replace("\n", " ")))

if wid:
    print("\n  === ③ 构建状态（轮询 3 次）===")
    for i in range(3):
        st2, tx2, dt2 = call("GET", "/worlds/build-status?encryptedWorldId=" + str(wid))
        stat = ""
        try: stat = ((json.loads(tx2).get("output") or {}).get("data") or {}).get("status", "")
        except Exception: pass
        print("   第%d次 ⇒ HTTP %-4s ｜ %.2f s ｜ status=%s" % (i+1, st2, dt2, stat or tx2[:80].replace("\n"," ")))
        if stat in ("ready", "failed"): break
        time.sleep(6)
    print("\n  === ④ 换取体验凭证（ticket 不落盘）===")
    st3, tx3, dt3 = call("POST", "/worlds/get-travel-credential", {"encryptedWorldId": str(wid)})
    code = ""
    try:
        j3 = json.loads(tx3); code = ((j3.get("output") or {}).get("data") or {}).get("code", j3.get("code", ""))
    except Exception: pass
    print("   POST /worlds/get-travel-credential ⇒ HTTP %-4s ｜ %.2f s ｜ code=%s ｜ ticket=%s" % (
        st3, dt3, code, "★已取得（值不落盘）" if '"ticket"' in tx3 or "ticket" in tx3.lower() else "未含"))
    print("   （响应前 100 字，脱敏示）：" + tx3[:100].replace("\n", " "))
print("\n  ⇒ 判：若 B 段为 200 ⇒ 「三 app 皆 403／资格未购」之判不成立（列举与创建之权限不同）")
