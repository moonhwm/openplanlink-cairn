#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""umc.py —— UMC v0.1 统一消息契约（kind 三面 + 五段式消息）。

依《A2A 云端实时模拟演练·复现种子稿》：UMC v0.1 = msg_hash/幂等键/身份标签；
kind 三面 hb.*（心跳）/ biz.*（业务）/ esc.*（升级面）；五段式消息（事项/状态/已完成/阻塞/下一步）。
本模块提供五段式消息构建/校验 + kind 分类，供节点消息契约对齐。纯标准库。
"""
import hashlib
import json


KINDS = ("hb", "biz", "esc")


def build_msg(kind, item, status, done="", blocked="", next_step="", sender=""):
    """构建五段式 UMC 消息，并附 msg_hash（幂等/溯源）。"""
    if kind not in KINDS:
        raise ValueError("kind 须为 %s" % "/".join(KINDS))
    m = {"umc": "v0.1", "kind": kind, "item": item, "status": status,
         "done": done, "blocked": blocked, "next": next_step, "sender": sender}
    m["msg_hash"] = hashlib.sha3_512(
        json.dumps(m, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    return m


def kind_of(method):
    """按方法名分类 kind（hb/biz/esc）。"""
    if method.startswith("hb."):
        return "hb"
    if method.startswith("esc."):
        return "esc"
    return "biz"


def is_valid(msg):
    """校验 UMC 消息五段式完整 + kind 合法。"""
    return (isinstance(msg, dict) and msg.get("umc") == "v0.1"
            and msg.get("kind") in KINDS and "item" in msg and "status" in msg
            and "done" in msg and "blocked" in msg and "next" in msg)


if __name__ == "__main__":
    m = build_msg("biz", "接入 Supabase 脊髓", "进行中", done="", blocked="缺 URL 凭据",
                  next_step="待机主给凭据", sender="cairn-dsh")
    print("  五段式消息 =", json.dumps(m, ensure_ascii=False))
    print("  is_valid =", is_valid(m), "｜ kind_of(biz.*) =", kind_of("biz.seat/send"), "｜ kind_of(hb.*) =", kind_of("hb.ping"))
