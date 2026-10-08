#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""proto.py —— A2A 协议基座（四元标签 + kind 三平面 + 限频）。

依《蓝图OTL主文档》第三章（三）：A2A 协议规范 https://a2a-protocol.cn/specification；
总线实测形态 = 四元标签（priority/ttl/delivery/reply_to）+ kind 三平面（hb./biz./esc.*）
+ esc.trace 双段式留痕；8000 字符上限、90 req/min 限频。
纯标准库，Windows 直跑。
"""
import time
from collections import deque

# 四元标签
QUAD_LABELS = ("priority", "ttl", "delivery", "reply_to")

# kind 三平面
KIND_PLANES = ("hb.", "biz.", "esc.")

# 硬约束
MAX_CHARS = 8000          # 消息字符上限
RATE_LIMIT = 90           # req/min 限频


def plane_of(method):
    """按方法名归属三平面。"""
    if method.startswith("hb."):
        return "hb"
    if method.startswith("esc."):
        return "esc"
    return "biz"


def quad_of(m):
    """提取四元标签（缺省给出默认值）。"""
    return {k: m.get(k) for k in QUAD_LABELS}


def over_limit(text):
    """是否超 8000 字符上限。"""
    return len(text) > MAX_CHARS


class RateLimiter:
    """滑动窗口限频（默认 90 req/min）。"""

    def __init__(self, limit=RATE_LIMIT, window=60.0):
        self.limit = limit
        self.window = window
        self.hits = deque()

    def allow(self):
        now = time.time()
        while self.hits and now - self.hits[0] >= self.window:
            self.hits.popleft()
        if len(self.hits) < self.limit:
            self.hits.append(now)
            return True
        return False


if __name__ == "__main__":
    print("  四元标签 =", QUAD_LABELS)
    print("  kind三平面 =", KIND_PLANES)
    print("  plane_of(hb.ping) =", plane_of("hb.ping"), "｜ plane_of(esc.trace) =", plane_of("esc.trace"))
    print("  over_limit(8001字) =", over_limit("x" * 8001), "｜ over_limit(8000字) =", over_limit("x" * 8000))
    rl = RateLimiter(limit=3, window=60)
    ok = [rl.allow() for _ in range(5)]
    print("  限频(3/min)前5次 =", ok, "（第4次起拒绝）")
