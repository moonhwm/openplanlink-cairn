#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""test_totp.py —— TOTP 模块测试：RFC 6238 附录 B 全部测试向量 + 漂移窗口。"""
import sys
import base64

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
import totp as T

SEC = b"12345678901234567890"  # RFC 6238 附录 B，ASCII 20 字节

# (时间 T, 8 位期望) — 取自 RFC 6238 附录 B（SHA1 行）
VECTORS = [
    (59, "94287082"),
    (1111111109, "07081804"),
    (1111111111, "14050471"),
    (1234567890, "89005924"),
    (2000000000, "69279037"),
    (20000000000, "65353130"),
]

results = []
print("  RFC 6238 附录 B 测试向量（SHA1，8 位）：")
for t, expect in VECTORS:
    got = T.totp(SEC, digits=8, t=t)
    ok = got == expect
    results.append(ok)
    print("    T=%-12s got=%s expect=%s %s" % (t, got, expect, "PASS" if ok else "BAD"))

# 漂移窗口：verify 应接受当前窗口及 ±1 步
import time as _t
now = int(_t.time())
cur = T.totp(SEC, t=now)
ok_cur = T.verify(SEC, cur, t=now)
ok_prev = T.verify(SEC, T.totp(SEC, t=now - 30), t=now)   # 前一步
ok_next = T.verify(SEC, T.totp(SEC, t=now + 30), t=now)   # 后一步
ok_far = T.verify(SEC, T.totp(SEC, t=now + 120), t=now)   # 超窗口应拒
results += [ok_cur, ok_prev, ok_next, (not ok_far)]
print("  漂移窗口：cur=%s prev=%s next=%s far拒=%s" % (ok_cur, ok_prev, ok_next, not ok_far))

bad = sum(1 for r in results if not r)
print("  ★ 失败 %d 项 ｜ VERDICT=%s" % (bad, "PASS" if bad == 0 else "BAD"))
sys.exit(0 if bad == 0 else 1)
