# -*- coding: utf-8 -*-
"""履约令条「两个 AccessKey CSV 均须强制调用」：本席**独立实现**阿里云 STS GetCallerIdentity（RPC 签名 HMAC-SHA1）
- 凭据纪律：**AK/SK 仅在进程内存**；**不打印任何键值**；**只报长度与 sha3_512 前 16 位**
- 目的：①履约（强制调用）②取得 AccountId/Arn 作为"开通 Directing"之申请依据 ③与守藏席之留痕**交叉验证指纹**
"""
import base64, datetime, hashlib, hmac, json, pathlib, sys, time, urllib.parse, urllib.request, urllib.error, uuid

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
CSVS = [("RAM角色", pathlib.Path(r"C:\Users\欧阳宏俊\OneDrive\桌面\AccessKey RAM角色.csv")),
        ("阿里云百炼主账户", pathlib.Path(r"C:\Users\欧阳宏俊\OneDrive\桌面\AccessKey 阿里云百炼主账户.csv"))]
PEER = {"RAM角色": ("bffc0ea0a908f156", "789edcfedddbc614"),
        "阿里云百炼主账户": ("76d85139e06047db", None)}   # 守藏席留痕（其自述）

def pe(s):
    return urllib.parse.quote(str(s), safe="~")

def read_csv(p):
    raw = p.read_bytes()
    txt = raw.decode("utf-8-sig", errors="replace")
    lines = [l for l in txt.splitlines() if l.strip()]
    hdr = [h.strip() for h in lines[0].split(",")]
    vals = [v.strip() for v in lines[1].split(",")]
    return raw, hdr, vals

def get_caller(ak, sk):
    params = {
        "Action": "GetCallerIdentity", "Format": "JSON", "Version": "2015-04-01",
        "AccessKeyId": ak, "SignatureMethod": "HMAC-SHA1", "SignatureVersion": "1.0",
        "SignatureNonce": str(uuid.uuid4()),
        "Timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    q = "&".join("%s=%s" % (pe(k), pe(params[k])) for k in sorted(params))
    sts = "GET&%2F&" + pe(q)
    sig = base64.b64encode(hmac.new((sk + "&").encode(), sts.encode(), hashlib.sha1).digest()).decode()
    url = "https://sts.aliyuncs.com/?%s&Signature=%s" % (q, pe(sig))
    t0 = time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=45) as resp:
            return resp.status, round(time.time()-t0, 2), json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try: body = json.loads(body)
        except Exception: body = {"raw": body[:200]}
        return e.code, round(time.time()-t0, 2), body
    except Exception as e:
        return -1, round(time.time()-t0, 2), {"err": str(e)[:150]}

out = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "by": "a2a-node-local", "method": "STS GetCallerIdentity (HMAC-SHA1, 独立实现)",
       "credential_discipline": "AK/SK 仅在进程内存；不打印键值；只报长度与 sha3_512 前 16 位", "results": []}
for label, p in CSVS:
    rec = {"label": label, "file_present": p.exists()}
    if not p.exists():
        print("  × %s：文件不存在" % label); out["results"].append(rec); continue
    raw, hdr, vals = read_csv(p)
    ak, sk = (vals + ["", ""])[0], (vals + ["", ""])[1]
    rec.update({"file_bytes": len(raw), "csv_header": hdr,
                "ak_len": len(ak), "ak_sha3_16": hashlib.sha3_512(ak.encode()).hexdigest()[:16],
                "sk_len": len(sk), "sk_sha3_16": hashlib.sha3_512(sk.encode()).hexdigest()[:16]})
    st, dt, j = get_caller(ak, sk)
    rec.update({"http": st, "sec": dt,
                "IdentityType": j.get("IdentityType"), "AccountId": j.get("AccountId"),
                "Arn": j.get("Arn"), "PrincipalId": j.get("PrincipalId"),
                "RequestId": j.get("RequestId"), "Code": j.get("Code"), "Message": j.get("Message")})
    pk = PEER.get(label) or (None, None)
    rec["peer_ak_sha3_16"] = pk[0]
    rec["ak_fingerprint_match"] = (pk[0] == rec["ak_sha3_16"]) if pk[0] else None
    print("  ★ %s ⇒ HTTP %s ｜ %.2fs ｜ IdentityType=%s" % (label, st, dt, rec["IdentityType"]))
    print("     AccountId=%s ｜ Arn=%s" % (rec["AccountId"], rec["Arn"]))
    print("     AK len=%d sha3_16=%s ｜ 与守藏席留痕%s" % (
        rec["ak_len"], rec["ak_sha3_16"],
        "★相符" if rec["ak_fingerprint_match"] else ("不符" if rec["ak_fingerprint_match"] is False else "无可比")))
    out["results"].append(rec)
    time.sleep(0.5)

dest = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A共同体_共享交换区\sts_caller_identity_20261009_CAIRN.json")
dest.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("  落盘：%s（%d B）" % (dest.name, dest.stat().st_size))
