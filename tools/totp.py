#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""totp.py —— RFC 6238 TOTP（时间同步一次性口令），纯标准库实现。

用途：为 A2A 节点认证流程引入 MFA 第二因子（HMAC 信封为第一因子，
TOTP 为第二因子）。算法：RFC 4226 HOTP + RFC 6238 时间步。
"""
import base64
import hmac
import hashlib
import struct
import time


def _hotp(key: bytes, counter: int, digits: int = 6) -> str:
    """RFC 4226 HOTP。key 为共享密钥字节串。"""
    msg = struct.pack(">Q", counter)
    h = hmac.new(key, msg, hashlib.sha1).digest()
    offset = h[-1] & 0x0F
    code = (struct.unpack(">I", h[offset:offset + 4])[0] & 0x7FFFFFFF) % (10 ** digits)
    return str(code).zfill(digits)


def totp(key: bytes, step: int = 30, digits: int = 6, t: int | None = None) -> str:
    """RFC 6238 TOTP。t 为 Unix 秒，缺省取当前时间。"""
    if t is None:
        t = int(time.time())
    return _hotp(key, t // step, digits)


def verify(key: bytes, code: str, step: int = 30, digits: int = 6,
           window: int = 1, t: int | None = None) -> bool:
    """校验 TOTP，允许 ±window 个时间步（防时钟漂移），常数时间比较。"""
    if t is None:
        t = int(time.time())
    code = str(code).strip()
    counter = t // step
    for w in range(-window, window + 1):
        if hmac.compare_digest(_hotp(key, counter + w, digits), code):
            return True
    return False


def gen_secret(nbytes: int = 20) -> str:
    """生成 base32 随机密钥（供 TOTP 应用导入）。"""
    import secrets
    return base64.b32encode(secrets.token_bytes(nbytes)).decode("ascii")


if __name__ == "__main__":
    # RFC 6238 Appendix B：secret=ASCII "12345678901234567890"，8 位，T=59 → 94287082
    sec = b"12345678901234567890"
    got = totp(sec, digits=8, t=59)
    print("  RFC6238 测试向量 T=59 (8位) = %s ｜ 期望 94287082 ｜ %s" %
          (got, "PASS" if got == "94287082" else "BAD"))
    demo = gen_secret()
    print("  示例密钥(base32) =", demo)
    print("  当前 6 位口令 =", totp(base64.b32decode(demo)))
