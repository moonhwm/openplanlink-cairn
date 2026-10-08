#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""test_a2a_node.py —— 对运行中的 A2A 节点做正/负向 HTTP 测试。"""
import base64
import http.client
import json
import sys
import uuid

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
import a2a_hmac as M

sys.stdout.reconfigure(encoding="utf-8")

KEY = open(r"C:\Users\欧阳宏俊\.a2a-hmac-key.bin", "rb").read()
KEY_ID = "opl-a2a-2026q4"
SENDER = "cairn-dsh"
NODE = "a2a-node-local"


def post(envelope, body):
    payload = {"envelope": envelope, "body_b64": base64.b64encode(body).decode("ascii")}
    conn = http.client.HTTPConnection("127.0.0.1", 4173, timeout=10)
    conn.request("POST", "/", body=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    data = json.loads(resp.read().decode("utf-8"))
    code = resp.status
    conn.close()
    return code, data


def rpc_body(method, params):
    rpc = {"jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": method, "params": params}
    return json.dumps(rpc, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


results = []

body = rpc_body("seat/hello", {"msg": "hi"})
env = M.build_envelope(SENDER, NODE, body, KEY, KEY_ID)
code, data = post(env, body)
ok = (code == 200 and "envelope" in data)
results.append(ok)
print("  正向       code=%s 通过=%s" % (code, ok))

code, data = post(env, body)  # 重放同一条
ok = (code == 401)
results.append(ok)
print("  重放       code=%s 拒绝=%s（%s）" % (code, ok, data.get("error", {}).get("message")))

body2 = rpc_body("seat/hello", {"msg": "hi2"})
env2 = M.build_envelope(SENDER, NODE, body2, KEY, KEY_ID)
code, data = post(env2, b"tampered")  # 篡改正文
ok = (code == 401)
results.append(ok)
print("  篡改正文   code=%s 拒绝=%s（%s）" % (code, ok, data.get("error", {}).get("message")))

body3 = rpc_body("seat/hello", {"msg": "hi3"})
env3 = M.build_envelope(SENDER, "workbuddy-hy4", body3, KEY, KEY_ID)  # 发往已知席位
code, data = post(env3, body3)
ok = (code == 200 and data.get("queued") is True)
results.append(ok)
print("  中转已知席位 code=%s queued=%s" % (code, data.get("queued")))

body4 = rpc_body("seat/hello", {"msg": "hi4"})
env4 = M.build_envelope(SENDER, "unknown-seat", body4, KEY, KEY_ID)  # 发往未知席位
code, data = post(env4, body4)
ok = (code == 404)
results.append(ok)
print("  未知席位   code=%s 拒绝=%s（%s）" % (code, ok, data.get("error", {}).get("message")))

bad = results.count(False)
print("★ VERDICT=" + ("PASS" if bad == 0 else "BAD"))
sys.exit(0 if bad == 0 else 1)
