# -*- coding: utf-8 -*-
"""火山引擎（Volcengine）签名 v4 探针 ＋ 纲要中 ark 之上下文
① 以 AK/SK 走 Volcengine Signature v4（HMAC-SHA256）调 ARK 对话端点
② 打印纲要正文中 ark 之两处上下文（读本地正文副本）
（引号一律用「」）
"""
import datetime, hashlib, hmac, json, pathlib, sys, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
E = {}
for line in (HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8-sig", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); E[k.strip()] = v.strip().strip('"').strip("'")
AK, SK = E.get("ARK_ACCESS_KEY", ""), E.get("ARK_SECRET_KEY", "")
MODEL = E.get("ARK_ENDPOINT") or E.get("ARK_MODEL") or "doubao-pro-32k"
HOST = "ark.cn-beijing.volces.com"
REGION, SERVICE = "cn-beijing", "ark"


def sign_v4(method, path, query, body_bytes, ak, sk):
    t = datetime.datetime.now(datetime.timezone.utc)
    xdate = t.strftime("%Y%m%dT%H%M%SZ")
    short = t.strftime("%Y%m%d")
    payload_hash = hashlib.sha256(body_bytes).hexdigest()
    signed_headers = "content-type;host;x-content-sha256;x-date"
    canonical = "\n".join([method, path, query, "content-type:application/json", "host:" + HOST,
                           "x-content-sha256:" + payload_hash, "x-date:" + xdate, "", signed_headers, payload_hash])
    scope = "%s/%s/%s/request" % (short, REGION, SERVICE)
    sts = "\n".join(["HMAC-SHA256", xdate, scope, hashlib.sha256(canonical.encode()).hexdigest()])
    def h(k, m): return hmac.new(k, m.encode(), hashlib.sha256).digest()
    kSign = h(h(h(h(sk.encode(), short), REGION), SERVICE), "request")
    sig = hmac.new(kSign, sts.encode(), hashlib.sha256).hexdigest()
    auth = "HMAC-SHA256 Credential=%s/%s, SignedHeaders=%s, Signature=%s" % (ak, scope, signed_headers, sig)
    return {"Content-Type": "application/json", "Host": HOST, "X-Date": xdate,
            "X-Content-Sha256": payload_hash, "Authorization": auth}


body = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": "回一字：可"}], "max_tokens": 16}).encode()
print("  === ① 火山签名 v4 探针（模型/端点：%s）===" % MODEL[:30])
for path in ("/api/v3/chat/completions", "/api/v3/bots/chat/completions"):
    hdrs = sign_v4("POST", path, "", body, AK, SK)
    r = urllib.request.Request("https://" + HOST + path, data=body, method="POST")
    for k, v in hdrs.items(): r.add_header(k, v)
    try:
        with urllib.request.urlopen(r, timeout=45) as resp:
            print("   %-34s ⇒ HTTP %s ｜ ★通 ｜ %s" % (path, resp.status, resp.read().decode("utf-8","replace")[:110]))
    except urllib.error.HTTPError as e:
        print("   %-34s ⇒ HTTP %-4s ｜ %s" % (path, e.code, e.read().decode("utf-8","replace")[:130].replace("\n"," ")))
    except Exception as e:
        print("   %-34s ⇒ 异常 %s" % (path, str(e)[:90]))

print("\n  === ② 纲要正文中 ark 之上下文（本地正文副本）===")
docx = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"Plan提示词工程"/"openplanlink-docx"
cand = sorted(docx.glob("*纲要*正文副本*.md"))
if cand:
    t = cand[0].read_text(encoding="utf-8", errors="replace")
    print("   文件：" + cand[0].name + "（%d 字）" % len(t))
    low = t.lower()
    idx = 0; n = 0
    while True:
        i = low.find("ark", idx)
        if i < 0 or n >= 4: break
        seg = t[max(0, i-160):i+200].replace("\n", " ")
        print("   ── 第%d处（偏移 %d）：…%s…" % (n+1, i, seg))
        idx = i + 3; n += 1
else:
    print("   未找到正文副本")
