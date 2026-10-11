# -*- coding: utf-8 -*-
"""实时交互入口之探查：enter-travel 返回之 playUrl／rtcConfig 结构（令牌零回显）
① 建世界→ready→换票→进房，打印 data 之全部键与各键类型/长度（敏感值只报长度与前 4 字符）
② 取 playUrl 之 HTTP 响应（状态、content-type、长度、前 200 字，遮令牌）
（引号一律用「」）
"""
import base64, json, pathlib, re, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
SEAT = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"
EX = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"
env = {}
for line in (HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8-sig", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
K = env.get("DASHSCOPE_API_KEY", "")
B = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1"
R = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "probe": "rtc-entry", "steps": []}


def call(method, path, body=None, to=180):
    r = urllib.request.Request((path if path.startswith("http") else B + path),
                               data=json.dumps(body, ensure_ascii=False).encode() if body else None, method=method)
    r.add_header("Authorization", "Bearer " + K)
    if body: r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=to) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return -1, str(e)[:150]


SENS = re.compile(r"(?i)(token|secret|key|ticket|signature|password|authorization)")


def shape(v, key="", depth=0):
    """只报结构；敏感键只报长度与前 4 字符"""
    if isinstance(v, dict):
        return {k: shape(vv, k, depth+1) for k, vv in list(v.items())[:20]}
    if isinstance(v, list):
        return ["(%d 项) %s" % (len(v), shape(v[0], key, depth+1) if v else "空")]
    if isinstance(v, str):
        if SENS.search(key) or len(v) > 60:
            return "«%s…»（长 %d）" % (v[:4], len(v)) if SENS.search(key) else (v[:80] + ("…" if len(v) > 80 else ""))
        return v
    return v


img = "data:image/jpeg;base64," + base64.b64encode((SEAT/"exp"/"opening_firstframe_16x9_20261011.jpg").read_bytes()).decode()
st, tx = call("POST", "/worlds", {"async": True, "perspective": "third_person",
                                  "prompt": "第三人称：夜间游乐场门前，七点成环，分身立于环心。", "firstFrameImage": {"base64": img}})
j = json.loads(tx); wid = ((j.get("output") or {}).get("data") or {}).get("encryptedWorldId")
print("  ① 建世界 code=%s id尾=%s" % ((j.get("output") or {}).get("code"), str(wid)[-8:]))
for i in range(10):
    st, tx = call("GET", "/worlds/build-status?encryptedWorldId=" + str(wid))
    s = (((json.loads(tx).get("output") or {}).get("data")) or {}).get("status")
    if s in ("ready", "failed"): break
    time.sleep(7)
print("     status=%s" % s)
st, tx = call("POST", "/worlds/get-travel-credential", {"encryptedWorldId": str(wid)})
tk = (((json.loads(tx).get("output") or {}).get("data")) or {}).get("ticket")
print("  ② 换票 code=%s ticket=%s" % (((json.loads(tx).get("output") or {}).get("code")), "有" if tk else "无"))
st, tx = call("POST", "/travels/enter-travel", {"ticket": tk, "maxExperienceTimeSec": 60})
o = json.loads(tx).get("output") or {}
d = o.get("data") or {}
print("  ③ 进房 code=%s ｜ data 键：%s" % (o.get("code"), list(d.keys())))
R["steps"].append({"step": "enter", "code": o.get("code"), "keys": list(d.keys())})
print("  ④ data 之形状（敏感键只报长度与前 4 字）：")
sh = shape(d)
print("     " + json.dumps(sh, ensure_ascii=False)[:1400])
R["data_shape"] = sh
# ⑤ 取 playUrl
pu = d.get("playUrl")
if pu:
    print("  ⑤ playUrl：%s…（长 %d）" % (str(pu)[:60], len(str(pu))))
    try:
        req = urllib.request.Request(pu); req.add_header("User-Agent", "cairn/1.0")
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read(2000).decode("utf-8", "replace")
            ct = resp.headers.get("content-type", "")
            print("     HTTP %s ｜ content-type=%s ｜ 前 200 字：%s" % (
                resp.status, ct, re.sub(r"(?i)(token|key)=[^&\"']+", r"\1=«遮»", body[:200]).replace("\n", " ")))
            R["steps"].append({"step": "playUrl", "http": resp.status, "ct": ct, "head": body[:200]})
    except urllib.error.HTTPError as e:
        print("     HTTP %s ｜ %s" % (e.code, e.read().decode("utf-8", "replace")[:160]))
        R["steps"].append({"step": "playUrl", "http": e.code})
    except Exception as e:
        print("     异常：%s" % str(e)[:120])
else:
    print("  ⑤ 无 playUrl")
(EX/"rtc_entry_probe_20261011.json").write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("\n  落盘：rtc_entry_probe_20261011.json")
