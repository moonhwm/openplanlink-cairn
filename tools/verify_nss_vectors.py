#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""verify_nss_vectors.py —— 用 NSS/Wycheproof 全套 HMAC-SHA3-512 向量验本实现。

语义（关键）：
  - struct 末字段是 `bool invalid`（非 valid）：true=tag 被翻转（应拒），false=tag 正确（应受）。
  - 向量分两类：完整 64 字节 tag（128 hex）与 截断 tag（<128 hex）。
    · 完整 tag：应匹配 ⟺ invalid=false。
    · 截断 tag：HMAC-SHA3-512 恒输出 128 hex ⇒ 对截断 tag 必须【不匹配】（拒收）。
"""
import hmac
import hashlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
path = sys.argv[1]

text = open(path, encoding="utf-8", errors="replace").read()
body = text.split("kHmacSha3512WycheproofVectors[] = {", 1)[1]
body = body.split("};", 1)[0]

blocks = re.findall(r"\{([^{}]*)\}", body)

full = truncated = full_ok = trunc_ok = full_bad = trunc_bad = 0
for b in blocks:
    parts = b.split(",")
    if len(parts) < 6:
        continue
    key = "".join(re.findall(r'"([0-9a-fA-F]*)"', parts[2]))
    msg = "".join(re.findall(r'"([0-9a-fA-F]*)"', parts[3]))
    tag = "".join(re.findall(r'"([0-9a-fA-F]*)"', parts[4]))
    invalid = ("true" in parts[5])

    got = hmac.new(bytes.fromhex(key), bytes.fromhex(msg), hashlib.sha3_512).hexdigest()
    match = hmac.compare_digest(got, tag)

    if len(tag) == 128:  # 完整 64 字节 tag
        full += 1
        good = (match == (not invalid))
        if good:
            full_ok += 1
        else:
            full_bad += 1
    else:  # 截断 tag
        truncated += 1
        good = (not match)
        if good:
            trunc_ok += 1
        else:
            trunc_bad += 1

print("  完整 64 字节 tag 向量 = %d ｜ 行为正确 = %d ｜ 错误 = %d" % (full, full_ok, full_bad))
print("  截断 tag 向量         = %d ｜ 正确拒收 = %d ｜ 错误 = %d" % (truncated, trunc_ok, trunc_bad))
print("  ★ 总行为正确 = %d / %d" % (full_ok + trunc_ok, full + truncated))
print("★ VERDICT=" + ("PASS" if (full_bad == 0 and trunc_bad == 0) else "BAD"))
sys.exit(0 if (full_bad == 0 and trunc_bad == 0) else 1)
