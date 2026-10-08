#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""event_driven.py —— 事件驱动骨架：信息等幂消费共振场。

本体系由事件驱动（非预编排固定流程）：系统依据运行时发生的各类事件
（用户操作 / 消息到达 / 状态变化 / 定时到期）触发相应响应与处理逻辑。

事件模型：事件 = (type, 来源, 载荷, 幂等键, 时间戳)
  共振场  = 事件总线：事件入 → 幂等去重（CAS）→ 路由到 handler → 留痕审计
  等幂消费 = 同一事件（同幂等键）只处理一次（复用 cas_store 的 CAS 语义）
纯标准库。留痕进 _audit JSONL。
"""
import json
import pathlib
import time

LOG_FILE = pathlib.Path(__file__).parent / "event_field_audit.jsonl"
DLQ_FILE = pathlib.Path(__file__).parent / "event_dlq.jsonl"

EVENT_TYPES = {"user_op", "message_arrival", "state_change", "timer_due", "model_result",
               "mfa_fail", "git_hook_fail"}

_HANDLERS = {}
_SEEN = {}  # 幂等键 → 处理时间（内存共振场；持久化可换 cas_store）


def _append_jsonl(path, obj):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def dlq_len():
    """死信队列长度。"""
    if not DLQ_FILE.exists():
        return 0
    return sum(1 for _ in open(DLQ_FILE, encoding="utf-8"))


def dlq_drain():
    """读出并清空死信队列（供重试）。"""
    items = []
    if DLQ_FILE.exists():
        items = [json.loads(l) for l in open(DLQ_FILE, encoding="utf-8") if l.strip()]
        DLQ_FILE.unlink()
    return items


def rollback(ev, reason=""):
    """补偿回滚：登记回滚审计（由 compensate.saga 执行具体逆操作）。"""
    _append_jsonl(LOG_FILE, {"event": ev, "action": "rollback", "reason": reason, "ts": time.time()})
    return {"ok": True, "rolled_back": True, "reason": reason}


def retry(ev, max_retries=3):
    """死信重试：重试未超限→重新 emit；超限→回滚。确保不丢失且最终可达。"""
    tries = int(ev.get("tries", 0)) + 1
    ev["tries"] = tries
    if tries > max_retries:
        _append_jsonl(DLQ_FILE, ev)
        return rollback(ev, "重试超限(%d/%d)" % (tries, max_retries))
    return emit(ev["type"], ev["source"], ev["payload"], ev.get("key"), on_failure="dlq")


def on(event_type):
    """装饰器：注册某事件类型的 handler。"""
    def deco(fn):
        _HANDLERS[event_type] = fn
        return fn
    return deco


def _audit(ev, result):
    _append_jsonl(LOG_FILE, {"event": ev, "result": result, "ts": time.time()})


def emit(event_type, source, payload, idempotency_key=None, now=None, on_failure="dlq"):
    """事件入共振场：幂等去重 + 路由 handler + 留痕；失败按 on_failure 入死信/回滚。"""
    if event_type not in EVENT_TYPES:
        return {"ok": False, "reason": "未知事件类型"}
    key = idempotency_key or json.dumps([event_type, source, payload], ensure_ascii=False, sort_keys=True)
    if key in _SEEN:
        return {"ok": True, "dup": True, "reason": "等幂跳过（已消费）"}
    _SEEN[key] = time.time()
    ev = {"type": event_type, "source": source, "payload": payload, "key": key}
    handler = _HANDLERS.get(event_type)
    if handler is None:
        _append_jsonl(DLQ_FILE, ev)
        return {"ok": False, "reason": "无 handler", "dlq": True}
    try:
        result = handler(source, payload)
    except Exception as e:
        result = {"ok": False, "reason": "%s: %s" % (type(e).__name__, e)}
    _audit(ev, result)
    if not result.get("ok", True):
        if on_failure == "dlq":
            _append_jsonl(DLQ_FILE, ev)
            return {"ok": False, "dlq": True, "result": result}
        if on_failure == "rollback":
            return rollback(ev, result.get("reason", ""))
    return {"ok": True, "dup": False, "result": result}


if __name__ == "__main__":
    @on("message_arrival")
    def _route(sender, payload):
        return {"ok": True, "routed_to": payload.get("recipient_id", "?")}

    @on("mfa_fail")
    def _mfa(sender, payload):
        return {"ok": False, "reason": "MFA 验证失败"}

    r1 = emit("message_arrival", "cairn-dsh", {"recipient_id": "workbuddy-hy4"}, "msg-1")
    r2 = emit("message_arrival", "cairn-dsh", {"recipient_id": "workbuddy-hy4"}, "msg-1")  # 等幂重复
    r3 = emit("mfa_fail", "cairn-dsh", {"ip": "127.0.0.1"}, "mfa-1", on_failure="rollback")
    r4 = emit("mfa_fail", "cairn-dsh", {"ip": "127.0.0.1"}, "mfa-2", on_failure="dlq")
    print("  事件1 =", r1)
    print("  事件2（重复幂等） =", r2)
    print("  事件3（MFA失败回滚） =", r3)
    print("  事件4（MFA失败入死信） =", r4)
    print("  死信队列长度 =", dlq_len())
    print("  共振场留痕 =", LOG_FILE.exists())
