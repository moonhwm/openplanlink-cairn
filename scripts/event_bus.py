#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only AND SSPL-1.0
"""事件总线——信息等幂消费共振场核心组件
部署位置：幻16 /root/incoming/openplanlink-mirror/GOVERNANCE/event_store/
"""

import os
import json
import time
import uuid
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))

# 事件存储根目录（部署在幻16上）
EVENT_STORE_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "GOVERNANCE", "event_store"
)


def _now_iso():
    """当前CST时间ISO格式"""
    return datetime.now(CST).isoformat()


def _date_str():
    """当前日期字符串 YYYY-MM-DD"""
    return datetime.now(CST).strftime("%Y-%m-%d")


def publish(event_type, source_seat, payload, target_seats=None, priority="NORMAL", ttl=3600):
    """
    发布事件到事件总线

    参数：
        event_type: 事件类型（negotiation_request/state_change/alert_critical/heartbeat/consensus_request等）
        source_seat: 发起席位名称
        payload: 事件负载（dict）
        target_seats: 目标席位列表（空=广播）
        priority: 优先级（CRITICAL/HIGH/NORMAL/LOW）
        ttl: 事件有效期（秒）

    返回：event_id
    """
    now = datetime.now(CST)
    date_str = now.strftime("%Y-%m-%d")
    seq = int(time.time() * 1000) % 1000000
    event_id = f"evt_{now.strftime('%Y%m%d')}_{seq:06d}"

    event = {
        "event_id": event_id,
        "event_type": event_type,
        "source_seat": source_seat,
        "target_seats": target_seats or [],
        "timestamp": now.isoformat(),
        "payload": payload,
        "ttl": ttl,
        "priority": priority
    }

    # 持久化到日期目录
    store_dir = os.path.join(EVENT_STORE_ROOT, date_str)
    os.makedirs(store_dir, exist_ok=True)
    event_file = os.path.join(store_dir, f"{event_id}.json")
    with open(event_file, "w", encoding="utf-8") as f:
        json.dump(event, f, ensure_ascii=False, indent=2)

    return event_id


def consume(event_id, seat):
    """
    消费事件（等幂保证）

    参数：
        event_id: 事件ID
        seat: 消费席位名称

    返回：(should_process: bool, event: dict or None)
        should_process=True 表示首次消费，应处理事件
        should_process=False 表示已消费过，等幂跳过
    """
    # 检查消费日志
    log_file = os.path.join(EVENT_STORE_ROOT, "consumption_logs", f"{seat}.json")
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            log = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        log = {"seat": seat, "consumed_events": []}

    consumed_ids = {e["event_id"] for e in log["consumed_events"]}
    if event_id in consumed_ids:
        return False, None  # 已消费，等幂跳过

    # 读取事件文件
    parts = event_id.split("_")
    if len(parts) >= 2:
        date_raw = parts[1]
        if len(date_raw) == 8:
            date_formatted = f"{date_raw[:4]}-{date_raw[4:6]}-{date_raw[6:8]}"
        else:
            date_formatted = _date_str()
    else:
        date_formatted = _date_str()

    event_file = os.path.join(EVENT_STORE_ROOT, date_formatted, f"{event_id}.json")

    try:
        with open(event_file, "r", encoding="utf-8") as f:
            event = json.load(f)
    except FileNotFoundError:
        return False, None  # 事件不存在

    # 检查TTL是否过期
    event_time = datetime.fromisoformat(event["timestamp"])
    elapsed = (datetime.now(CST) - event_time).total_seconds()
    if elapsed > event.get("ttl", 3600):
        return False, None  # TTL过期

    # 检查目标席位
    targets = event.get("target_seats", [])
    if targets and seat not in targets:
        return False, None  # 非目标席位

    # 标记为已消费
    log["consumed_events"].append({
        "event_id": event_id,
        "consumed_at": _now_iso(),
        "result": "processing",
        "event_type": event.get("event_type", "unknown")
    })

    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

    return True, event


def get_pending_events(seat):
    """
    获取席位待消费的事件列表

    参数：
        seat: 席位名称

    返回：[event_id, ...]
    """
    # 读取消费日志
    log_file = os.path.join(EVENT_STORE_ROOT, "consumption_logs", f"{seat}.json")
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            log = json.load(f)
        consumed_ids = {e["event_id"] for e in log["consumed_events"]}
    except (FileNotFoundError, json.JSONDecodeError):
        consumed_ids = set()

    # 扫描今天的事件存储
    pending = []
    today = _date_str()
    today_dir = os.path.join(EVENT_STORE_ROOT, today)

    if os.path.exists(today_dir):
        for fname in sorted(os.listdir(today_dir)):
            if not fname.endswith(".json"):
                continue
            event_id = fname.replace(".json", "")
            if event_id in consumed_ids:
                continue

            event_file = os.path.join(today_dir, fname)
            try:
                with open(event_file, "r", encoding="utf-8") as f:
                    event = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                continue

            # 检查TTL
            event_time = datetime.fromisoformat(event["timestamp"])
            elapsed = (datetime.now(CST) - event_time).total_seconds()
            if elapsed > event.get("ttl", 3600):
                continue

            # 检查目标席位
            targets = event.get("target_seats", [])
            if not targets or seat in targets:
                pending.append(event_id)

    return pending


def publish_and_notify(event_type, source_seat, payload, target_seats=None, priority="NORMAL", ttl=3600):
    """
    发布事件并尝试通过Server酱通知机主（如果事件优先级为CRITICAL或HIGH）

    返回：event_id
    """
    event_id = publish(event_type, source_seat, payload, target_seats, priority, ttl)

    if priority in ("CRITICAL", "HIGH"):
        try:
            import serverchan_push
            serverchan_push.push_alert(
                event_type=f"事件总线: {event_type}",
                details=f"事件ID: {event_id}\n来源: {source_seat}\n负载: {json.dumps(payload, ensure_ascii=False)[:200]}",
                impact=f"目标席位: {target_seats or '广播'}",
                action="已发布到事件总线"
            )
        except ImportError:
            pass  # serverchan_push模块不可用时静默跳过

    return event_id


# ============ 共识聚合器 ============

def aggregate_consensus(consensus_id, mode, responses, threshold=None):
    """
    聚合多席位响应，收敛为单一决策

    参数：
        consensus_id: 共识ID
        mode: roundtable（全体一致）/ moa（多数同意）/ jury（评委投票）
        responses: {seat: {"decision": "accept"/"reject", "reason": "..."}}
        threshold: jury模式下的通过阈值（默认60%）

    返回：共识结果dict
    """
    if mode == "roundtable":
        all_accept = all(r.get("decision") == "accept" for r in responses.values())
        result = {
            "consensus_id": consensus_id,
            "mode": "roundtable",
            "decision": "accepted" if all_accept else "rejected",
            "responses": responses,
            "timestamp": _now_iso()
        }
    elif mode == "moa":
        accept_count = sum(1 for r in responses.values() if r.get("decision") == "accept")
        total = len(responses)
        result = {
            "consensus_id": consensus_id,
            "mode": "moa",
            "decision": "accepted" if accept_count > total / 2 else "rejected",
            "vote_count": {"accept": accept_count, "reject": total - accept_count},
            "responses": responses,
            "timestamp": _now_iso()
        }
    elif mode == "jury":
        accept_count = sum(1 for r in responses.values() if r.get("decision") == "accept")
        passed = accept_count >= (threshold or len(responses) * 0.6)
        result = {
            "consensus_id": consensus_id,
            "mode": "jury",
            "decision": "accepted" if passed else "rejected",
            "threshold": threshold,
            "vote_count": {"accept": accept_count, "reject": len(responses) - accept_count},
            "responses": responses,
            "timestamp": _now_iso()
        }
    else:
        result = {
            "consensus_id": consensus_id,
            "mode": mode,
            "decision": "unknown_mode",
            "responses": responses,
            "timestamp": _now_iso()
        }

    # 持久化共识结果
    result_dir = os.path.join(EVENT_STORE_ROOT, "consensus_results")
    os.makedirs(result_dir, exist_ok=True)
    result_file = os.path.join(result_dir, f"{consensus_id}.json")
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 发布共识结果事件
    publish(
        event_type="consensus_result",
        source_seat="consensus_aggregator",
        payload={"consensus_id": consensus_id, "decision": result["decision"]},
        target_seats=[],
        priority="HIGH"
    )

    return result


# ============ 5种事件分发模式（借鉴Cordis） ============

def dispatch_emit(event_name, *args, **kwargs):
    """emit模式：触发所有监听器，不等待返回（广播通知）"""
    # 在当前架构中，emit等价于publish + 所有目标席位各自consume
    pass  # 由publish + consume组合实现


def dispatch_parallel(event_name, seats, *args, **kwargs):
    """parallel模式：并行触发所有席位，等待全部完成（共振发散）"""
    event_id = publish(event_name, "dispatcher", kwargs.get("payload", {}), seats, "HIGH")
    results = {}
    for seat in seats:
        should_process, event = consume(event_id, seat)
        if should_process:
            # 模拟席位处理（实际由各席位自行consume）
            results[seat] = "dispatched"
        else:
            results[seat] = "skipped"
    return results


def dispatch_serial(event_name, seats, *args, **kwargs):
    """serial模式：串行触发席位，等待每个完成（顺序协商）"""
    event_id = publish(event_name, "dispatcher", kwargs.get("payload", {}), seats, "HIGH")
    results = {}
    for seat in seats:
        should_process, event = consume(event_id, seat)
        if should_process:
            results[seat] = "dispatched"
        else:
            results[seat] = "skipped"
    return results


def dispatch_bail(event_name, seats, *args, **kwargs):
    """bail模式：触发席位，第一个非空返回值终止（门禁拦截）"""
    event_id = publish(event_name, "dispatcher", kwargs.get("payload", {}), seats, "CRITICAL")
    for seat in seats:
        should_process, event = consume(event_id, seat)
        if should_process:
            # 第一个消费成功即终止
            return {"bail_seat": seat, "event_id": event_id}
    return {"bail_seat": None, "event_id": event_id}


def dispatch_waterfall(event_name, seats, initial_value, *args, **kwargs):
    """waterfall模式：串行触发，每个席位的返回值传给下一个（共识收敛）"""
    event_id = publish(
        event_name, "dispatcher",
        {"initial_value": initial_value, "waterfall": True},
        seats, "HIGH"
    )
    current_value = initial_value
    for seat in seats:
        should_process, event = consume(event_id, seat)
        if should_process:
            # 在实际实现中，席位的处理结果会更新current_value
            # 此处为原型，简化处理
            current_value = {"processed_by": seat, "value": current_value}
    return current_value


# ============ 自检与演示 ============

def self_test():
    """事件总线自检"""
    print("=" * 60)
    print("事件总线ICRF原型自检")
    print("=" * 60)

    # 测试1：发布事件
    print("\n[测试1] 发布事件...")
    eid = publish(
        event_type="heartbeat",
        source_seat="yanjian",
        payload={"message": "砚坚席心跳"},
        target_seats=["qoder", "kimi"],
        priority="NORMAL"
    )
    print(f"  发布成功: event_id={eid}")

    # 测试2：消费事件
    print("\n[测试2] 首次消费事件...")
    should_process, event = consume(eid, "qoder")
    print(f"  should_process={should_process}, event_type={event['event_type'] if event else 'None'}")

    # 测试3：等幂消费（重复消费应跳过）
    print("\n[测试3] 等幂消费（重复消费）...")
    should_process2, event2 = consume(eid, "qoder")
    print(f"  should_process={should_process2} (应为False)")

    # 测试4：获取待消费事件
    print("\n[测试4] 获取kimi席位的待消费事件...")
    pending = get_pending_events("kimi")
    print(f"  pending={pending}")

    # 测试5：共识聚合——MoA模式
    print("\n[测试5] 共识聚合（MoA模式）...")
    responses = {
        "qoder": {"decision": "accept", "reason": "同意"},
        "kimi": {"decision": "accept", "reason": "同意"},
        "yanjian": {"decision": "reject", "reason": "需要修改"}
    }
    result = aggregate_consensus("test_consensus_001", "moa", responses)
    print(f"  decision={result['decision']}, votes={result['vote_count']}")

    # 测试6：共识聚合——圆桌模式（须全体一致）
    print("\n[测试6] 共识聚合（圆桌模式，非全体一致）...")
    result2 = aggregate_consensus("test_consensus_002", "roundtable", responses)
    print(f"  decision={result2['decision']} (应为rejected)")

    print("\n" + "=" * 60)
    print("自检完成")
    print("=" * 60)


if __name__ == "__main__":
    self_test()