# -*- coding: utf-8 -*-
"""bss_budget_probe.py —— 只读查询"预算管理"（Budget Management）配置
★绝不修改：改预算＝授权花钱，须主权人明示。
★密钥仅内存读取、不打印、不落盘；仅输出动作名、状态码与服务端原话。
（中文串一律用「」）
"""
import base64, csv, hashlib, hmac, json, pathlib, sys, time, urllib.parse, urllib.request, urllib.error
sys.stdout.reconfigure(encoding="utf-8")
D = pathlib.Path.home()/"OneDrive"/"桌面"

def read_key(fn):
    t = (D/fn).read_bytes().decode("utf-8-sig", "replace")
    for r in csv.reader(t.splitlines()):
        a = (r[0] or "").strip() if r else ""
        b = (r[1] or "").strip() if len(r) > 1 else ""
        if a and b and "AccessKey" not in a and len(a) >= 12 and len(b) >= 12:
            return a, b
    raise SystemExit("★未取到数据行")

AK, SK = read_key("AccessKey 阿里云百炼主账户.csv")

def rpc(endpoint, version, action, extra=None):
    p = {"AccessKeyId": AK, "Action": action, "Format": "JSON", "SignatureMethod": "HMAC-SHA1",
         "SignatureNonce": str(int(time.time()*1000)), "SignatureVersion": "1.0",
         "Timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "Version": version}
    if extra: p.update(extra)
    q = "&".join("%s=%s" % (urllib.parse.quote(k, safe=""), urllib.parse.quote(str(v), safe="")) for k, v in sorted(p.items()))
    sig = base64.b64encode(hmac.new((SK + "&").encode(), ("GET&%2F&" + urllib.parse.quote(q, safe="")).encode(), hashlib.sha1).digest()).decode()
    try:
        with urllib.request.urlopen("https://%s/?Signature=%s&%s" % (endpoint, urllib.parse.quote(sig, safe=""), q), timeout=45) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read().decode("utf-8", "replace"))
        except Exception: return e.code, {}
    except Exception as e:
        return -1, {"__exc": str(e)[:120]}

print("  ═══ 只读探「预算管理」相关动作（不修改）═══")
for ep, ver, act in (("business.aliyuncs.com", "2017-12-14", "DescribeBudgetList"),
                     ("business.aliyuncs.com", "2017-12-14", "QueryBudget"),
                     ("business.aliyuncs.com", "2017-12-14", "DescribeBudgets"),
                     ("bssopenapi.aliyuncs.com", "2017-12-14", "QueryAccountBalance")):
    st, j = rpc(ep, ver, act)
    msg = j.get("Message") or j.get("message") or ""
    code = j.get("Code") or j.get("code") or ""
    print("   %-18s %-22s ⇒ HTTP %-4s ｜ Code=%-24s ｜ %s" % (ep.split(".")[0], act, st, str(code)[:24], str(msg)[:80]))
    if act.startswith("Describe") and isinstance(j.get("Data"), (dict, list)):
        print("      ★Data：%s" % json.dumps(j["Data"], ensure_ascii=False)[:260])
