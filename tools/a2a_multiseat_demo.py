#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""a2a_multiseat_demo.py —— 两席位经节点信箱互发（A→B、B→A），端到端验证。"""
import base64
import http.client
import json
import sys
import uuid

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
import a2a_hmac as M
import totp as T

sys.stdout.reconfigure(encoding="utf-8")

KEY = open(r"C:\Users\欧阳宏俊\.a2a-hmac-key.bin", "rb").read()
KEY_ID = "opl-a2a-2026q4"
NODE, PORT = "127.0.0.1", 4173
A, B = "cairn-dsh", "workbuddy-hy4"
TOTP_SECRET = base64.b32decode("GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ")
import tempfile, os
replay = M.ReplayCache(os.path.join(tempfile.gettempdir(), "multiseat_replay.sqlite"))


def post(sender, recipient, method, params):
    rpc = {"jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": method, "params": params}
    body = json.dumps(rpc, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    env = M.build_envelope(sender, recipient, body, KEY, KEY_ID)
    payload = {"envelope": env, "body_b64": base64.b64encode(body).decode("ascii")}
    conn = http.client.HTTPConnection(NODE, PORT, timeout=10)
    conn.request("POST", "/", body=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    data = json.loads(resp.read().decode("utf-8"))
    code = resp.status
    conn.close()
    return code, data


def mailbox(seat):
    code = T.totp(TOTP_SECRET)  # MFA 第二因子
    conn = http.client.HTTPConnection(NODE, PORT, timeout=10)
    conn.request("GET", "/mailbox/%s?totp=%s" % (seat, code))
    resp = conn.getresponse()
    data = json.loads(resp.read().decode("utf-8"))
    conn.close()
    return data.get("messages", [])


code, data = post(A, B, "seat/hello", {"msg": "A 向 B 问好"})
print("  A→B 投递 code=%s queued=%s" % (code, data.get("queued")))

msgs = mailbox(B)
ok = rpc = None
if msgs:
    m = msgs[-1]
    body = base64.b64decode(m["body_b64"])
    ok, r = M.verify_envelope(m["envelope"], KEY, KEY_ID, A, B, body, replay)
    rpc = json.loads(body.decode("utf-8"))
print("  B 收信验证 = %s（%s）method=%s" % (ok, r, rpc.get("method") if rpc else None))

code, data = post(B, A, "seat/ack", {"ok": True})
print("  B→A 投递 code=%s queued=%s" % (code, data.get("queued")))

msgs2 = mailbox(A)
ok2 = r2 = None
if msgs2:
    m = msgs2[-1]
    body = base64.b64decode(m["body_b64"])
    ok2, r2 = M.verify_envelope(m["envelope"], KEY, KEY_ID, B, A, body, replay)
print("  A 收信验证 = %s（%s）" % (ok2, r2))

good = (ok and ok2)
print("★ VERDICT=" + ("PASS" if good else "BAD"))
sys.exit(0 if good else 1)
