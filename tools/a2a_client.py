#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""a2a_client.py —— A2A 客户端：向节点发 JSON-RPC（HMAC 包络），验证响应。"""
import base64
import http.client
import json
import sys
import uuid

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
import a2a_hmac as M

sys.stdout.reconfigure(encoding="utf-8")

NODE = "127.0.0.1"
PORT = 4173
KEY_FILE = r"C:\Users\欧阳宏俊\.a2a-hmac-key.bin"
KEY = open(KEY_FILE, "rb").read()
KEY_ID = "opl-a2a-2026q4"
SENDER = "cairn-dsh"
import tempfile, os
replay = M.ReplayCache(os.path.join(tempfile.gettempdir(), "client_replay.sqlite"))


def main():
    rpc = {"jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": "seat/hello", "params": {"msg": "强制 A2A 使用"}}
    body = json.dumps(rpc, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    env = M.build_envelope(SENDER, "a2a-node-local", body, KEY, KEY_ID)
    payload = {"envelope": env, "body_b64": base64.b64encode(body).decode("ascii")}

    conn = http.client.HTTPConnection(NODE, PORT, timeout=10)
    conn.request("POST", "/", body=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    data = json.loads(resp.read().decode("utf-8"))
    conn.close()

    if "envelope" not in data:
        print("  节点返回错误 = %s" % data.get("error"))
        return 1

    resp_env = data["envelope"]
    resp_body = base64.b64decode(data["body_b64"])
    ok, reason = M.verify_envelope(resp_env, KEY, KEY_ID, "a2a-node-local", SENDER, resp_body, replay)
    rpc_resp = json.loads(resp_body.decode("utf-8"))
    print("  节点响应验证 = %s（%s）" % (ok, reason))
    print("  result = %s" % rpc_resp.get("result"))
    print("★ VERDICT=" + ("PASS" if ok else "BAD"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
