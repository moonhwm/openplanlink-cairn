#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""test_a2a_hmac.py —— a2a_hmac 正/负向验收向量（对齐 Qoder DF-NOTICE 第六节"验收"）。

覆盖：正确向量、正文单字节变更、tag 单字节变更、错误 key_id、过期时间、
重复 nonce、接收方错配、平台不支持。未通过全部负向测试的席位不得标 READY。
"""
import hashlib
import secrets
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
import a2a_hmac as M

sys.stdout.reconfigure(encoding="utf-8")

KEY = secrets.token_bytes(64)
KEY_ID = "k-20261003-test"
SENDER = "cairn-dsh"
RECIP = "workbuddy-hy4"
BODY = b"OpenPlanLink A2A handshake payload"

results = []


# ⓪ JCS 规范化（RFC 8785）——先验规范本身
print("⓪ JCS 规范化（RFC 8785）")
def jcs_eq(name, obj, expect):
    got = M.jcs(obj)
    good = (got == expect)
    results.append(good)
    print("  %s %-20s got=%s 期望=%s" % ("✅" if good else "★", name, got, expect))

jcs_eq("键排序", {"b": 1, "a": 2}, '{"a":2,"b":1}')
jcs_eq("无空白", {"a": 1}, '{"a":1}')
jcs_eq("引号转义", {"a": 'x"y'}, '{"a":"x\\"y"}')
jcs_eq("反斜杠转义", {"a": "x\\y"}, '{"a":"x\\\\y"}')
jcs_eq("控制字符", {"a": "\u0001"}, '{"a":"\\u0001"}')
jcs_eq("换行制表", {"a": "\n\t"}, '{"a":"\\n\\t"}')
jcs_eq("中文原样", {"a": "石敢当"}, '{"a":"石敢当"}')
jcs_eq("整数浮点", {"a": 1.0}, '{"a":1}')
jcs_eq("负零", {"a": -0.0}, '{"a":0}')
jcs_eq("小数", {"a": 1.5}, '{"a":1.5}')
jcs_eq("尾零去除", {"a": 1.50}, '{"a":1.5}')
jcs_eq("大数展开", {"a": 1e30}, '{"a":1000000000000000000000000000000}')
jcs_eq("嵌套数组", [1, "a", True, None], '[1,"a",true,null]')


def check(name, expect_ok, ok, reason):
    good = (ok == expect_ok)
    results.append(good)
    print("  %s %-22s 期望=%s 实测=%s%s" % (
        "✅" if good else "★", name, expect_ok, ok,
        ("  reason=" + reason) if reason else ""))


def fresh(seen):
    return dict(seen)


# 0. 平台支持
print("① 平台能力")
supp = M.platform_supported()
results.append(supp)
print("  %s 平台支持 HMAC-SHA3-512 = %s" % ("✅" if supp else "★", supp))

# 1. 正确向量
print("② 正向")
env = M.build_envelope(SENDER, RECIP, BODY, KEY, KEY_ID)
ok, r = M.verify_envelope(env, KEY, KEY_ID, RECIP, body=BODY)
check("正确向量", True, ok, r)

# 2. 正文单字节变更
env2 = M.build_envelope(SENDER, RECIP, BODY, KEY, KEY_ID)
tampered_body = b"OpenPlanLink A2A handshake payload!"  # 末字节变化
ok, r = M.verify_envelope(env2, KEY, KEY_ID, RECIP, body=tampered_body)
check("正文单字节变更", False, ok, r)

# 3. tag 单字节变更
env3 = M.build_envelope(SENDER, RECIP, BODY, KEY, KEY_ID)
tag = env3["tag"]
flip = "0" if tag[0] != "0" else "1"
env3["tag"] = flip + tag[1:]
ok, r = M.verify_envelope(env3, KEY, KEY_ID, RECIP, body=BODY)
check("tag 单字节变更", False, ok, r)

# 4. 错误 key_id
env4 = M.build_envelope(SENDER, RECIP, BODY, KEY, KEY_ID)
ok, r = M.verify_envelope(env4, KEY, "k-WRONG", RECIP, body=BODY)
check("错误 key_id", False, ok, r)

# 5. 过期时间（正确 tag，但时间戳已超窗）
env5 = M.build_envelope(SENDER, RECIP, BODY, KEY, KEY_ID)
old = datetime.now(timezone.utc).astimezone() - timedelta(seconds=400)
env5["timestamp"] = old.isoformat(timespec="seconds")
env5["tag"] = M.compute_tag({k: v for k, v in env5.items() if k != "tag"}, KEY)
ok, r = M.verify_envelope(env5, KEY, KEY_ID, RECIP, body=BODY)
check("过期时间", False, ok, r)

# 6. 重复 nonce
env6 = M.build_envelope(SENDER, RECIP, BODY, KEY, KEY_ID)
seen = set()
ok1, _ = M.verify_envelope(env6, KEY, KEY_ID, RECIP, body=BODY, seen_nonces=seen)
ok2, r2 = M.verify_envelope(env6, KEY, KEY_ID, RECIP, body=BODY, seen_nonces=seen)
good = (ok1 is True and ok2 is False)
results.append(good)
print("  %s 重复 nonce              期望=先True后False 实测=%s,%s%s" % (
    "✅" if good else "★", ok1, ok2, ("  reason=" + r2) if not ok2 else ""))

# 7. 接收方错配
env7 = M.build_envelope(SENDER, RECIP, BODY, KEY, KEY_ID)
ok, r = M.verify_envelope(env7, KEY, KEY_ID, "someone-else", body=BODY)
check("接收方错配", False, ok, r)

# 8. nonce 太短
env8 = M.build_envelope(SENDER, RECIP, BODY, KEY, KEY_ID)
env8["nonce"] = "abcd"
env8["tag"] = M.compute_tag({k: v for k, v in env8.items() if k != "tag"}, KEY)
ok, r = M.verify_envelope(env8, KEY, KEY_ID, RECIP, body=BODY)
check("nonce 太短", False, ok, r)

# 9. 版本不匹配
env9 = M.build_envelope(SENDER, RECIP, BODY, KEY, KEY_ID)
env9["version"] = "a2a-hmac-sha3-256/v1"
env9["tag"] = M.compute_tag({k: v for k, v in env9.items() if k != "tag"}, KEY)
ok, r = M.verify_envelope(env9, KEY, KEY_ID, RECIP, body=BODY)
check("版本不匹配", False, ok, r)

# 10. Z 时区时间戳（RFC 3339 合法，应通过）
env10 = M.build_envelope(SENDER, RECIP, BODY, KEY, KEY_ID)
from datetime import timezone as _tz
env10["timestamp"] = datetime.now(_tz.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
env10["tag"] = M.compute_tag({k: v for k, v in env10.items() if k != "tag"}, KEY)
ok, r = M.verify_envelope(env10, KEY, KEY_ID, RECIP, body=BODY)
check("Z 时区时间戳", True, ok, r)

# 11. 畸形时间戳（应干净拒绝，不抛异常）
env11 = M.build_envelope(SENDER, RECIP, BODY, KEY, KEY_ID)
env11["timestamp"] = "not-a-timestamp"
env11["tag"] = M.compute_tag({k: v for k, v in env11.items() if k != "tag"}, KEY)
ok, r = M.verify_envelope(env11, KEY, KEY_ID, RECIP, body=BODY)
check("畸形时间戳", False, ok, r)

print()
print("════ 结果 ════")
bad = results.count(False)
print("  共 %d 项 ｜ ★ 失败 %d 项" % (len(results), bad))
print("★ VERDICT=" + ("PASS" if bad == 0 else "BAD"))
sys.exit(0 if bad == 0 else 1)
