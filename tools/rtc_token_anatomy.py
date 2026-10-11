# -*- coding: utf-8 -*-
"""RTC 令牌之结构解剖（JWT）—— 只报 header/payload 之键与非敏感值；★签名段零回显
目的：判"世界模型之 RTC 是公网声网还是私有实现"，并寻接入之网关线索
（引号一律用「」）
"""
import base64, json, pathlib, sys

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
W = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"/"exp"/"rtc_watch"
p = W/"rtc_session.json"
if not p.exists():
    print("  无会话文件（须先建会话）"); sys.exit(0)
S = json.loads(p.read_text(encoding="utf-8"))
tk = S.get("token") or ""
print("  ═══ rtcConfig（非令牌部分）═══")
for k in ("appId", "channelId", "uid", "travel", "noStreamAutoEndTimeoutSec"):
    print("   %-26s = %s" % (k, S.get(k)))
print("   token 长度 = %d ｜ 段数 = %d" % (len(tk), tk.count(".") + 1))


def b64d(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


parts = tk.split(".")
SENS = ("sign", "signature", "key", "secret", "password")
if len(parts) >= 2:
    try:
        h = json.loads(b64d(parts[0])); pl = json.loads(b64d(parts[1]))
        print("\n  ═══ JWT header ═══")
        for k, v in h.items():
            print("   %-22s = %s" % (k, str(v)[:80]))
        print("\n  ═══ JWT payload（键与非敏感值）═══")
        for k, v in pl.items():
            if any(s in k.lower() for s in SENS):
                print("   %-22s «敏感，仅报长 %d»" % (k, len(str(v))))
            else:
                print("   %-22s = %s" % (k, str(v)[:120]))
        # Agora 风格 token 之特权位
        if "privilege" in pl or "privileges" in pl:
            print("\n   ★ 特权（privilege）＝" + json.dumps(pl.get("privilege") or pl.get("privileges"), ensure_ascii=False))
        if "exp" in pl:
            import datetime
            print("   ★ 到期 = " + datetime.datetime.fromtimestamp(pl["exp"]).strftime("%Y-%m-%d %H:%M:%S") + "（本地时区）")
    except Exception as e:
        print("  解析失败：" + str(e)[:90])
print("\n  ★ 签名段（第三段）：长 %d ｜ 本文不回显" % (len(parts[2]) if len(parts) > 2 else 0))
print("  ★ 判：若 header.alg＝HS256／payload 含 privilege＋appID ⇒ 声网（Agora）风格；")
print("       若 payload 含自定义 iss／私有字段 ⇒ 自建私有 RTC。")
