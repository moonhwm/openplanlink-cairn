# -*- coding: utf-8 -*-
"""ops_event.py —— 节点操作事件日志（哈希链）与事件工单生成

对应本轮新增令条：
  · 「将各节点操作日志**同步至主控台**，便于追溯异常行为并生成审计报告」
  · 「针对迁移过程中出现的异常事件与策略偏离，系统将**自动生成事件工单**并关联至对应责任人，
     确保每一项偏差均有明确的处置路径与时限要求」
  · 「复核通过后，相关配置基线将同步更新至**版本库**」

设计（只写本席自己的 ops 目录，不动任何系统配置、不启停任何进程）：
  - 事件日志：`ops_event.jsonl`，每行一条，字段
      seq / ts_utc / seat / actor / action / target / result / evidence / hash_prev / hash_self
    其中 hash_self = sha256(规范序列化正文 + hash_prev)，形成**可验证哈希链**。
  - 工单：`workorder_<UTC>.json`（机器可读）＋ `.md`（呈报件），由偏离清单生成，
    含 id / 发现时刻 / 对象 / 类别 / 偏离类型 / 证据 / 责任人（候指派）/ 时限（候指派）/ 状态。

用法:
  python ops_event.py log --action "push" --target "origin/main" --result OK --evidence "abc123" [--actor cairn-dsh]
  python ops_event.py tickets --deviations <desk_deviations_*.md>
  python ops_event.py verify
  python ops_event.py list [-n 10]
"""
import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = pathlib.Path(__file__).resolve().parent
OPS = HERE.parent / "ops"
OPS.mkdir(parents=True, exist_ok=True)
EVENT_LOG = OPS / "ops_event.jsonl"
SEAT = "a2a-node-local"


def now_utc():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def canon(d):
    return json.dumps({k: d[k] for k in sorted(d)}, ensure_ascii=False, separators=(",", ":"))


def last_hash():
    if not EVENT_LOG.exists():
        return "GENESIS"
    last = None
    for line in EVENT_LOG.read_text(encoding="utf-8").splitlines():
        if line.strip():
            last = line
    if not last:
        return "GENESIS"
    try:
        return json.loads(last)["hash_self"]
    except Exception:  # noqa: BLE001
        return "GENESIS"


def append_event(seat, actor, action, target, result, evidence):
    seq = 0
    if EVENT_LOG.exists():
        seq = sum(1 for l in EVENT_LOG.read_text(encoding="utf-8").splitlines() if l.strip())
    body = {
        "seq": seq,
        "ts_utc": now_utc(),
        "seat": seat,
        "actor": actor,
        "action": action,
        "target": target,
        "result": result,
        "evidence": evidence,
        "hash_prev": last_hash(),
    }
    body["hash_self"] = hashlib.sha256((canon(body) + body["hash_prev"]).encode("utf-8")).hexdigest()
    with EVENT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(body, ensure_ascii=False) + "\n")
    return body


def verify_chain():
    if not EVENT_LOG.exists():
        return True, 0, "无日志"
    prev = "GENESIS"
    n = 0
    for line in EVENT_LOG.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        body = {k: v for k, v in d.items() if k != "hash_self"}
        calc = hashlib.sha256((canon(body) + body["hash_prev"]).encode("utf-8")).hexdigest()
        if body["hash_prev"] != prev:
            return False, n, "第 %d 条 prev 指针断裂" % (n + 1)
        if calc != d["hash_self"]:
            return False, n, "第 %d 条 hash 不符" % (n + 1)
        prev = d["hash_self"]
        n += 1
    return True, n, "链内自洽"


def parse_deviations(path):
    """从 desk_deviations_*.md 的待处置表提取 (对象, 类别, 偏离类型)。"""
    rows = []
    text = pathlib.Path(path).read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        m = re.match(r"^\|\s*\d+\s*\|\s*`([^`]+)`\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", line)
        if m:
            rows.append({"target": m.group(1).strip(), "category": m.group(2).strip(),
                         "deviation": m.group(3).strip()})
    return rows


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("log")
    p1.add_argument("--seat", default=SEAT)
    p1.add_argument("--actor", default="cairn-dsh")
    p1.add_argument("--action", required=True)
    p1.add_argument("--target", default="")
    p1.add_argument("--result", default="OK")
    p1.add_argument("--evidence", default="")

    p2 = sub.add_parser("tickets")
    p2.add_argument("--deviations", required=True)
    p2.add_argument("--assignee", default="候指派")
    p2.add_argument("--deadline", default="候指派")

    sub.add_parser("verify")

    p4 = sub.add_parser("list")
    p4.add_argument("-n", type=int, default=10)

    a = ap.parse_args()

    if a.cmd == "log":
        ev = append_event(a.seat, a.actor, a.action, a.target, a.result, a.evidence)
        print("★ 已记事件 seq=%d hash=%s…" % (ev["seq"], ev["hash_self"][:16]))
        return 0

    if a.cmd == "verify":
        ok, n, why = verify_chain()
        print("★ 事件链校验：%s（%d 条）——%s" % ("PASS" if ok else "FAIL", n, why))
        return 0 if ok else 1

    if a.cmd == "list":
        if not EVENT_LOG.exists():
            print("（无事件）")
            return 0
        for line in EVENT_LOG.read_text(encoding="utf-8").splitlines()[-a.n:]:
            d = json.loads(line)
            print("  #%d %s %-10s %-22s %-8s %s" % (d["seq"], d["ts_utc"], d["action"],
                                                    d["target"][:22], d["result"], d["evidence"][:24]))
        return 0

    # tickets
    rows = parse_deviations(a.deviations)
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    tickets = []
    for i, r in enumerate(rows, 1):
        tickets.append({
            "id": "WO-%s-%03d" % (ts, i),
            "found_at_utc": ts,
            "object": r["target"],
            "category": r["category"],
            "deviation": r["deviation"],
            "evidence": pathlib.Path(a.deviations).name,
            "assignee": a.assignee,
            "deadline": a.deadline,
            "status": "待复核",
        })
    out_json = OPS / ("workorder_%s.json" % ts)
    out_json.write_text(json.dumps({"generated_at_utc": ts, "source": pathlib.Path(a.deviations).name,
                                    "count": len(tickets), "tickets": tickets},
                                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    L = ["# 事件工单（自动生成）", "",
         "- 生成时刻（UTC）：%s ｜ 来源偏离清单：`%s` ｜ 工单数：%d" % (ts, pathlib.Path(a.deviations).name, len(tickets)),
         "", "| 工单号 | 对象 | 类别 | 偏离 | 责任人 | 时限 | 状态 |", "|---|---|---|---|---|---|---|"]
    for t in tickets:
        L.append("| `%s` | `%s` | %s | %s | %s | %s | %s |" % (
            t["id"], t["object"], t["category"], t["deviation"], t["assignee"], t["deadline"], t["status"]))
    if not tickets:
        L.append("| — | — | — | 无偏离 | — | — | — |")
    L += ["", "> 责任人与时限**候安全运营中心指派**；本席只生成工单，不代指派、不代处置。", ""]
    out_md = OPS / ("workorder_%s.md" % ts)
    out_md.write_text("\n".join(L) + "\n", encoding="utf-8")

    append_event(SEAT, "cairn-dsh", "workorder.generate", pathlib.Path(a.deviations).name,
                 "OK(%d)" % len(tickets), out_json.name)
    print("★ 工单：%s（%d 张）" % (out_json, len(tickets)))
    print("★ 呈报件：%s" % out_md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
