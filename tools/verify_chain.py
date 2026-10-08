#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""verify_chain.py —— 闭环验证记录 HMAC-SHA3-512 签名链。

依《认证流程专章》第七章（四）：闭环验证记录与门禁判定采用 HMAC-SHA3-512 签名链路，
对记录内容计算 HMAC-SHA3-512 摘要，链式关联前一记录摘要，形成防篡改链。
本模块用与 A2A 节点同源密钥（.a2a-hmac-key.bin），追加式只增不改。
纯标准库（hashlib/hmac），Windows 直跑。
"""
import hashlib
import hmac as hmac_mod
import json
import os
import time

KEY_PATH = r"C:\Users\欧阳宏俊\.a2a-hmac-key.bin"


def _key():
    return open(KEY_PATH, "rb").read()


def seal(record, key):
    """对记录内容计算 HMAC-SHA3-512 摘要。"""
    body = json.dumps(record, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hmac_mod.new(key, body, hashlib.sha3_512).hexdigest()


def append(chain_file, event_type, subject, detail="", prev_hash=None):
    """追加一条闭环验证记录，链式关联前一记录摘要。"""
    if prev_hash is None:
        prev_hash = "GENESIS"
        if os.path.exists(chain_file):
            try:
                lines = [l for l in open(chain_file, encoding="utf-8").read().splitlines() if l.strip()]
                if lines:
                    prev_hash = json.loads(lines[-1]).get("sig")
            except Exception:
                pass
    rec = {"ts": time.time(), "type": event_type, "subject": subject,
           "detail": detail, "prev": prev_hash}
    rec["sig"] = seal(rec, _key())
    with open(chain_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec["sig"]


def verify(chain_file):
    """校验整链：每条 HMAC-SHA3-512 与内容相符、prev 指针相连。"""
    lines = [l for l in open(chain_file, encoding="utf-8").read().splitlines() if l.strip()]
    prev = "GENESIS"
    for i, line in enumerate(lines):
        r = json.loads(line)
        sig = r.pop("sig")
        calc = seal(r, _key())
        if calc != sig:
            return False, "第%d条签名不符" % (i + 1)
        if r.get("prev") != prev:
            return False, "第%d条prev断链(%s≠%s)" % (i + 1, r.get("prev"), prev)
        r["sig"] = sig
        prev = sig
    return True, "%d条链内自洽" % len(lines)


if __name__ == "__main__":
    import tempfile
    cf = os.path.join(tempfile.gettempdir(), "verify_chain_demo.jsonl")
    if os.path.exists(cf):
        os.remove(cf)
    a = append(cf, "MFA", "MFA验证通过", "TOTP 双因子")
    b = append(cf, "GATE", "门禁判定", "AGP矩阵匹配通过")
    ok, msg = verify(cf)
    print("  记录1 sig=%s… 记录2 sig=%s…（prev=%s）" % (a[:16], b[:16], a[:16]))
    print("  链校验 =", ok, "｜", msg)
