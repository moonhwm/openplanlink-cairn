#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""spinal_bridge.py —— Supabase 脊髓桥（读/写 cross_mode_channel，真网契约）。

真网契约（对齐 a2a_bridge.mjs / 席位盘点实测）：
  行 = {id 自增, ts 自生, from_mode, to_mode, kind, payload_md, status, msg_hash}
  msg_hash = md5(payload_md utf-8)[:16] 小写 hex（去重核验，非本席本地 HMAC 信封）
凭据：优先环境变量 SUPABASE_CHANNEL_KEY，其次 router-hub/credentials/supabase_channel.json。
纯标准库，Windows 直跑。
"""
import hashlib
import json
import os
import urllib.parse
import urllib.request

URL = "https://ltdodcumoxiqsnakpqog.supabase.co"
TABLE = "cross_mode_channel"
CRED_PATH = r"C:\Users\欧阳宏俊\Documents\kimi\router-hub\credentials\supabase_channel.json"


def _key():
    k = os.environ.get("SUPABASE_CHANNEL_KEY", "")
    if k:
        return k
    if os.path.exists(CRED_PATH):
        d = json.load(open(CRED_PATH, encoding="utf-8"))
        return d.get("publishable_key") or d.get("anon_legacy") or ""
    return ""


def read(limit=50, from_mode=None):
    """读脊髓最近 N 条（可按席位过滤）。"""
    q = "?order=id.desc&limit=%d&select=id,ts,from_mode,to_mode,kind,payload_md,status,msg_hash" % limit
    if from_mode:
        q += "&from_mode=eq." + urllib.parse.quote(from_mode)
    req = urllib.request.Request(URL + "/rest/v1/" + TABLE + q,
                                 headers={"apikey": _key(), "Authorization": "Bearer " + _key()})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def send(from_mode, to_mode, kind, payload, status="new"):
    """写脊髓一条（自动 msg_hash=md5[:16]）。payload 为 dict 或 str。"""
    pmd = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False, sort_keys=True)
    body = {"from_mode": from_mode, "to_mode": to_mode, "kind": kind,
            "payload_md": pmd, "status": status,
            "msg_hash": hashlib.md5(pmd.encode("utf-8")).hexdigest()[:16]}
    req = urllib.request.Request(URL + "/rest/v1/" + TABLE, data=json.dumps(body).encode("utf-8"),
                                 headers={"apikey": _key(), "Authorization": "Bearer " + _key(),
                                          "Content-Type": "application/json", "Prefer": "return=representation"},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def read_since(last_id, limit=100):
    """增量读：id > last_id 的新消息（值守工具，按 id 升序）。"""
    q = "?id=gt.%d&order=id.asc&limit=%d&select=id,ts,from_mode,to_mode,kind,payload_md,status,msg_hash" % (last_id, limit)
    req = urllib.request.Request(URL + "/rest/v1/" + TABLE + q,
                                 headers={"apikey": _key(), "Authorization": "Bearer " + _key()})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def to_cairn(last_id=0, limit=50):
    """增量读：id > last_id 且 to_mode=cairn-dsh 的致本席消息（值守工具）。"""
    q = "?id=gt.%d&to_mode=eq.cairn-dsh&order=id.asc&limit=%d&select=id,from_mode,kind,payload_md,msg_hash" % (last_id, limit)
    req = urllib.request.Request(URL + "/rest/v1/" + TABLE + q,
                                 headers={"apikey": _key(), "Authorization": "Bearer " + _key()})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


if __name__ == "__main__":
    import datetime
    print("  键已载入 =", bool(_key()))
    rows = read(3)
    print("  脊髓最近 3 条：")
    for x in rows:
        print("    #%s [%s] %s→%s %s" % (x["id"], x["kind"], x["from_mode"], x["to_mode"], x["msg_hash"]))
    import datetime
    r = send("cairn-dsh", "all-seats", "heartbeat",
             {"action": "heartbeat", "from": "cairn-dsh", "via": "spinal_bridge.py",
              "message": "石敢当席脊髓桥自检", "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()})
    print("  桥自检发送 → id=%s msg_hash=%s" % (r[0]["id"], r[0]["msg_hash"]))
