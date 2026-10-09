# -*- coding: utf-8 -*-
"""对照探测：判「200 + timestamp」是否为兜底响应（引号一律用「」）"""
import json, pathlib, sys, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
env = {}
for line in (pathlib.Path.home()/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
K = env.get("DASHSCOPE_API_KEY", "")
B = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1"

def call(path, body=None, method="POST", to=40):
    r = urllib.request.Request(B + path, data=json.dumps(body, ensure_ascii=False).encode() if body else None, method=method)
    r.add_header("Authorization", "Bearer " + K)
    if body: r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=to) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")[:170]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:170]
    except Exception as e:
        return -1, str(e)[:110]

CTRL = [
    ("已知存在", "/worlds?page=1&pageSize=1&status=ready", None, "GET"),
    ("随机乱写", "/travels/xyzqwerty123", {"x": 1}, "POST"),
    ("随机乱写2", "/totally/made/up/path", {"x": 1}, "POST"),
    ("已知不存在参数", "/travels/status", None, "GET"),
    ("正解端点", "/travels/status?encryptedTravelId=nonexistent", None, "GET"),
]
print("  === 对照探测（判「200 + timestamp」是否为兜底）===")
for label, p, body, m in CTRL:
    st, tx = call(p, body, m)
    print("     %-14s %-38s ⇒ HTTP %-4s ｜ %s" % (label, p[:38], st, tx.replace("\n", " ")[:95]))
print("\n  ★ 判读规则：若「随机乱写」亦得 200+timestamp ⇒ **该 200 为兜底响应，不证明端点存在**；")
print("     若随机乱写得 404 ⇒ **则先前 200 者为真端点（须再验其语义）**")
