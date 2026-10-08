#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""a2a_send_remote.py —— 向真实 A2A 网络（120.46.86.165）发 message/send。"""
import http.client
import json
import sys
import uuid

sys.stdout.reconfigure(encoding="utf-8")

FACE = "120.46.86.165"
PATH = "/functions/v1/app"

rpc = {
    "jsonrpc": "2.0",
    "id": str(uuid.uuid4()),
    "method": "message/send",
    "params": {
        "message": {
            "messageId": str(uuid.uuid4()),
            "role": "user",
            "parts": [{"kind": "text", "text": "来自 cairn-dsh（石敢当）的握手：A2A 网络可达确认"}],
        }
    },
}

body = json.dumps(rpc, ensure_ascii=False).encode("utf-8")
print("  请求 = %s" % json.dumps(rpc, ensure_ascii=False)[:160])

conn = http.client.HTTPConnection(FACE, 80, timeout=20)
conn.request("POST", PATH, body=body, headers={"Content-Type": "application/json"})
resp = conn.getresponse()
data = resp.read().decode("utf-8", errors="replace")
print("  HTTP = %s" % resp.status)
print("  响应 = %s" % data)
conn.close()
