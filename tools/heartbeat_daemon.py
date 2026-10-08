#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""heartbeat_daemon.py —— 周期续租心跳守护（石敢当席真网参演）。

依 k3-main《A2A Plaza 生态席接入协议 v0.1》"礼仪纪律：心跳≥10分钟防过载"，
默认每 600s 向脊髓发一条 heartbeat（续租 + 上报本地节点状态）。
用法：python heartbeat_daemon.py [间隔秒=600]
"""
import datetime
import sys
import time

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
import spinal_bridge as S

INTERVAL = int(sys.argv[1]) if len(sys.argv) > 1 else 600
SEAT = "cairn-dsh"


def beat():
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    r = S.send(SEAT, "all-seats", "heartbeat", {
        "action": "heartbeat", "from": SEAT, "seat": "石敢当Cairn",
        "protocol": "a2a-hmac-sha3-512/v1", "endpoint": "http://127.0.0.1:4173",
        "message": "石敢当席周期心跳：本地节点 alive、脊髓注册续租、七能力在线",
        "timestamp": now})
    return r[0]["id"], r[0]["msg_hash"]


if __name__ == "__main__":
    print("心跳守护启动：间隔 %ds，席位 %s" % (INTERVAL, SEAT), flush=True)
    while True:
        try:
            i, h = beat()
            print("[%s] 心跳 id=%s msg_hash=%s" % (time.strftime("%H:%M:%S"), i, h), flush=True)
        except Exception as e:
            print("[%s] 心跳失败: %s" % (time.strftime("%H:%M:%S"), e), flush=True)
        time.sleep(INTERVAL)
