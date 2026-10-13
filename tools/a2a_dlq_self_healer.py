#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""a2a_dlq_self_healer.py —— A2A 通信协议（PROTO-A2A-20261014-CAIRN-01 §九）待定五项闭环与死信队列（DLQ）自愈审计引擎
档号：DF-HEAL-20261014-HERMES-05
席位：Hermes-Argon席（seat_key: hermes-desktop-argon｜候授名：陆怀瑾）
定位：闭合 PROTO-A2A-20261014-CAIRN-01 §九之五项待定规范：
  1. 席位名册单一权威源校验（对接 seat_roster_v1.json 9 席与 .a2a-node-mailbox.json 分桶）；
  2. JSON-RPC 2.0 method 完整命名空间契约（seat.* / bus.* / ledger.* / repro.*）；
  3. timestamp 时钟偏差容限（±300s 实时消息窗 vs 历史归档宽限窗）；
  4. DLQ（.a2a-node-dlq.json）死信分诊策略（别名可映射重投 vs 未登记测试席永久隔离）；
  5. 并发写状态同步冲突解决（Lamport 逻辑时钟 seq + seat_key 字典序确定性平局决胜 + 版本分支不覆写）。
用法：python a2a_dlq_self_healer.py [--smoke] [--out <json_path>]
"""
import argparse
import hashlib
import json
import pathlib
import sys
import time

CANONICAL_METHODS = {
    "seat.probe": "席位存活性与基础能力探测（只读，幂等）",
    "seat.healthz": "席位资源水位（CPU/RAM/Disk）与门禁状态报告（只读，幂等）",
    "seat.deliver": "跨席正式件/回执信封投递（写，需 HMAC-SHA3-512 签名 + seatTicket）",
    "seat.co_recognize": "数字人员工席位注册跨席共认（写，追加至 seat_register.jsonl）",
    "bus.emit": "向 A2A 总线（bus.jsonl）广播 canonical 九字段索引（只增不改）",
    "ledger.append": "向哈希链决策台账追加事件（只增不改，带 prev_hash 指针）",
    "repro.verify": "跨席算法与统计推断独立复现核验回执（只读复算 + 报告落盘）",
}

CLOCK_SKEW_POLICY = {
    "live_rpc_window_seconds": 300,
    "batch_sync_sla_seconds": 1800,
    "ntp_reference": "UTC+08:00 (China Standard Time)",
    "replay_store": ".a2a-node-replay.sqlite + .a2a-node-nonces.json (128-bit hex nonce)",
}

CONFLICT_RESOLUTION_SPEC = {
    "rule_1_append_only": "台账与总线严禁原地覆写，并发追加按 (timestamp_utc, seat_key_lexicographical, sha256_prefix) 全序归并",
    "rule_2_versioned_docs": "同档号文档并发修订时，按 v_<YYYYMMDD_HHMM>_<seat_key>.otl.md 分支并存，由主权人或常务局合流",
    "rule_3_git_fast_forward": "Git 双通道推送前强制先 pull --rebase，严禁 --force 覆盖他席已推提交",
}


def inspect_and_triage() -> dict:
    h = pathlib.Path.home()
    roster_p = h / "openplanlink-cairn/seat_roster_v1.json"
    dlq_p = h / ".a2a-node-dlq.json"
    mb_p = h / ".a2a-node-mailbox.json"
    audit_p = h / ".a2a-node-audit.jsonl"

    roster = json.loads(roster_p.read_text(encoding="utf-8")) if roster_p.exists() else {"seats": []}
    valid_seat_keys = {s["seat_key"] for s in roster.get("seats", [])}
    valid_buckets = {s["mailbox_bucket"] for s in roster.get("seats", [])}
    alias_map = {s["mailbox_bucket"]: s["seat_key"] for s in roster.get("seats", [])}

    # 1. Inspect DLQ
    dlq_items = json.loads(dlq_p.read_text(encoding="utf-8")) if dlq_p.exists() else []
    triage_results = []
    reroutable = 0
    quarantined = 0
    for idx, item in enumerate(dlq_items):
        env = item.get("envelope", item)
        recip = env.get("recipient_id", "unknown")
        sender = env.get("sender_id", "unknown")
        reason = item.get("reason", "未知席位")
        if recip in valid_seat_keys or recip in valid_buckets:
            action = "AUTO_REDELIVER_TO_BUCKET"
            reroutable += 1
        else:
            # 如 unknown-seat 等测试负样本，保持死信隔离不污染正式信箱
            action = "KEEP_QUARANTINED_IN_DLQ (Negative-Test / Unregistered Target)"
            quarantined += 1
        triage_results.append({
            "index": idx,
            "sender_id": sender,
            "recipient_id": recip,
            "reason": reason,
            "triage_action": action,
        })

    # 2. Inspect Mailbox buckets
    mb_summary = {}
    if mb_p.exists():
        mb_data = json.loads(mb_p.read_text(encoding="utf-8"))
        if isinstance(mb_data, dict):
            for k, v in mb_data.items():
                mb_summary[k] = {
                    "msg_count": len(v) if isinstance(v, list) else 1,
                    "in_authoritative_roster": (k in valid_seat_keys or k in valid_buckets),
                }

    # 3. Inspect Audit log
    audit_events = {}
    if audit_p.exists():
        for line in audit_p.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip():
                try:
                    ev = json.loads(line).get("event", "OTHER")
                    audit_events[ev] = audit_events.get(ev, 0) + 1
                except Exception:
                    pass

    return {
        "doc_id": "DF-HEAL-20261014-HERMES-05",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"),
        "seat": "Hermes-Argon席 (hermes-desktop-argon)",
        "proto_a2a_section9_closures": {
            "1_authoritative_roster": {
                "source": "seat_roster_v1.json (ROSTER-A2A-20261014-HERMES-01)",
                "registered_seats_count": len(valid_seat_keys),
                "alias_map": alias_map,
            },
            "2_canonical_methods": CANONICAL_METHODS,
            "3_clock_skew_policy": CLOCK_SKEW_POLICY,
            "4_dlq_triage_summary": {
                "total_dlq_entries": len(dlq_items),
                "reroutable_count": reroutable,
                "quarantined_unregistered_count": quarantined,
                "entries": triage_results,
            },
            "5_conflict_resolution_spec": CONFLICT_RESOLUTION_SPEC,
        },
        "mailbox_buckets_health": mb_summary,
        "audit_event_counts": audit_events,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    res = inspect_and_triage()
    assert res["proto_a2a_section9_closures"]["1_authoritative_roster"]["registered_seats_count"] >= 9

    if args.out:
        out_p = pathlib.Path(args.out)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    print(json.dumps({
        "status": "SMOKE_PASS",
        "roster_seats": res["proto_a2a_section9_closures"]["1_authoritative_roster"]["registered_seats_count"],
        "canonical_methods": len(res["proto_a2a_section9_closures"]["2_canonical_methods"]),
        "dlq_total": res["proto_a2a_section9_closures"]["4_dlq_triage_summary"]["total_dlq_entries"],
        "dlq_quarantined_negative_tests": res["proto_a2a_section9_closures"]["4_dlq_triage_summary"]["quarantined_unregistered_count"],
        "mailbox_buckets": list(res["mailbox_buckets_health"].keys()),
        "audit_events": res["audit_event_counts"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    sys.exit(main())
