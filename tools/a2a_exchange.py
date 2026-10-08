#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""a2a_exchange.py —— 最小可用的 A2A 消息交换（A2A 0.3.0 JSON-RPC + HMAC-SHA3-512 包络）。

把 a2a_hmac.py 的包络接到 JSON-RPC 上，形成可"强制使用"的 A2A 消息原语：
  消息 = HMAC 包络(body = JSON-RPC 2.0 请求)
  发送方 build → 接收方 verify(版本/接收方/key_id/时间窗/nonce/正文摘要/HMAC) → 解包处理
"""
import json
import secrets
import sys
import uuid

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
import a2a_hmac as M

sys.stdout.reconfigure(encoding="utf-8")


def rpc_body(method, params):
    """构造 JSON-RPC 2.0 请求正文（规范字节）。"""
    rpc = {"jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": method, "params": params}
    return json.dumps(rpc, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


class Seat:
    """一个 A2A 席位：信任域共享密钥 + 独立 nonce 缓存。"""

    def __init__(self, seat_id, key_id, key):
        self.seat_id = seat_id
        self.key_id = key_id
        self.key = key
        self.seen = set()

    def send(self, recipient, method, params):
        """构建一条 A2A 消息（JSON-RPC 请求 + HMAC 包络）。正文随包络一并由传输层送。"""
        body = rpc_body(method, params)
        envelope = M.build_envelope(self.seat_id, recipient, body, self.key, self.key_id)
        return envelope, body

    def receive(self, envelope, body):
        """接收并验证；(ok, reason, rpc)。验证不过即拒绝，不返回 rpc。"""
        ok, reason = M.verify_envelope(envelope, self.key, self.key_id, self.seat_id, body=body, seen_nonces=self.seen)
        if not ok:
            return ok, reason, None
        rpc = json.loads(body.decode("utf-8"))
        return ok, reason, rpc


def demo():
    key = secrets.token_bytes(64)
    key_id = "opl-a2a-2026q4"
    A = Seat("cairn-dsh", key_id, key)
    B = Seat("workbuddy-hy4", key_id, key)

    env, body = A.send("workbuddy-hy4", "seat/hello", {"msg": "强制 A2A 使用"})
    ok, r, rpc = B.receive(env, body)
    print("  A→B 验证 = %s（%s）method=%s" % (ok, r, rpc.get("method") if rpc else None))

    ok2, r2, _ = B.receive(env, body)  # 重放同一条
    print("  重放拒绝 = %s（%s）" % (ok2, r2))

    env3, body3 = A.send("workbuddy-hy4", "seat/hello", {"msg": "x"})  # 新消息(fresh nonce)
    ok3, r3, _ = B.receive(env3, b"tampered-body")  # 篡改正文
    print("  篡改拒绝 = %s（%s）" % (ok3, r3))

    env2, body2 = B.send("cairn-dsh", "seat/ack", {"ok": True})
    ok4, r4, rpc4 = A.receive(env2, body2)
    print("  B→A 应答 = %s（%s）method=%s" % (ok4, r4, rpc4.get("method") if rpc4 else None))

    good = (ok and not ok2 and not ok3 and ok4)
    print("★ VERDICT=" + ("PASS" if good else "BAD"))
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(demo())
