# -*- coding: utf-8 -*-
"""世界探索之服务端末步：换取体验凭证（ticket）
- 官档：POST …/apps/happyoyster-1.0-adventure/openapi/v1/worlds/get-travel-credential
- 请求体：{"encryptedWorldId": "<ready 之 World>"}；仅主 API Key
- **纪律：ticket 短时效（1800s）一次性 ⇒ 本席仅验证 `code=0`，不落盘、不打印 ticket 值**
"""
import json, pathlib, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
WID = "8rcpnKlw6xp3FtpLvZIGB9mlTipFohD7syfWSOD-bt5fNs2BU7TeGEDpaTrloI7x"
URL = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1/worlds/get-travel-credential"
env = {}
for line in (pathlib.Path.home()/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
K = env.get("DASHSCOPE_API_KEY", "")
body = {"encryptedWorldId": WID}
r = urllib.request.Request(URL, data=json.dumps(body).encode(), method="POST")
r.add_header("Authorization", "Bearer " + K); r.add_header("Content-Type", "application/json")
t0 = time.time()
try:
    with urllib.request.urlopen(r, timeout=60) as resp:
        st, txt = resp.status, resp.read().decode("utf-8", "replace")
        dt = round(time.time()-t0, 2)
except urllib.error.HTTPError as e:
    st, txt, dt = e.code, e.read().decode("utf-8", "replace")[:400], round(time.time()-t0, 2)
except Exception as e:
    st, txt, dt = -1, str(e)[:160], round(time.time()-t0, 2)
print("=== 换取体验凭证 ⇒ HTTP %s ｜ %.2fs ===" % (st, dt))
ok = False
try:
    j = json.loads(txt)
    out = j.get("output") or j
    data = (out.get("data") if isinstance(out, dict) else None) or {}
    code = out.get("code") if isinstance(out, dict) else None
    # 只报"是否取到"与有效期，不打印 ticket 值
    tk = data.get("ticket") or ""
    print("   code=%s ｜ message=%s" % (code, out.get("message") if isinstance(out, dict) else ""))
    print("   取到 ticket=%s ｜ 前缀=%s ｜ 长度=%d ｜ expiresIn=%s ｜ 对应 World=%s…" % (
        "★是" if tk else "否", (tk[:3] if tk else "—"), len(tk), data.get("expiresIn"), str(data.get("encryptedWorldId"))[:12]))
    ok = bool(code == 0 and tk)
except Exception:
    print("   原始（截断）：%s" % txt[:300])
print("   ⇒ %s" % ("★服务端链路已通至「换取体验凭证」（ticket 未落盘、未打印，将自然过期）" if ok
                  else "× 未取到（可能为 403007 未购规格 / 403008 容量 / 其它，见上）"))
