# -*- coding: utf-8 -*-
"""capacity_alert.py —— **容量预警阈值**检查（承令条「设置容量预警阈值」「容量预警阈值」之要求）

输入：`outbox/mem/mem_tier_scan.json`（分层盘点）＋（可选）`outbox/mem/dedup_plan_v6.json`（可回收）
输出：**阈值判定表** ＋ `outbox/mem/capacity_alert.json` ＋ （可选）`esc.capacity` 事件

## 阈值（**显式声明，不隐藏**）
| 代号 | 判据 | 级别 | 依 |
|---|---|---|---|
| **A1** | **层-冷 占比 ＞ 70%** | **ALERT** | 令条"设置容量预警阈值"＋本席"冷层 81.9%"之既有发现 |
| **A2** | **层-未分 件数 ＞ 0** | **WARN** | 未分层数据**无从调度**（承"未分即未测"） |
| **A3** | **可回收（逐字重复） ＞ 0** | **INFO** | **仅为候选**；处置**须候批**（承"候选≠判据"） |
| **A4** | **单层件数 ＞ 3000** | **WARN** | 单层件数过多**降低遍历效率**（与本席 `exp/` 1,688 件之观察同族） |

**纪律**：告警**不等于**处置；本器**只报告**；清单缺失 ⇒**未测**（不臆造）。
退出码：0＝无告警｜1＝有 ALERT｜2＝清单缺失（未测）｜3＝用法错误
"""
import argparse
import datetime as dt
import json
import pathlib
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
SEAT = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928")
MEM = SEAT / "outbox" / "mem"
TIER = MEM / "mem_tier_scan.json"
DEDUP = MEM / "dedup_plan_v6.json"
OUT = MEM / "capacity_alert.json"

THRESHOLDS = {
    "A1_cold_share_pct_gt": 70.0,
    "A2_unfiled_count_gt": 0,
    "A3_reclaim_bytes_gt": 0,
    "A4_single_tier_count_gt": 3000,
}


def load(p):
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def log_event(action, target, result, evidence):
    src = SEAT / "exp" / "ops_event.py"
    if not src.exists():
        return "（未记事件：ops_event.py 缺失）"
    p = subprocess.run([sys.executable, str(src), "log", "--action", action, "--target", target,
                        "--result", result, "--evidence", evidence],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (p.stdout or p.stderr or "").strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log-event", action="store_true")
    a = ap.parse_args()

    tier = load(TIER)
    if not tier:
        print("★ 分层清单缺失 ⇒ **未测**（%s）" % TIER)
        return 2
    dedup = load(DEDUP) or {}

    tiers = tier.get("tiers", {})
    total_bytes = sum(int(v.get("bytes", 0)) for v in tiers.values())
    cold = tiers.get("层-冷", {})
    cold_pct = (100.0 * int(cold.get("bytes", 0)) / total_bytes) if total_bytes else 0.0
    unfiled = tiers.get("层-未分", {})
    reclaim = int(dedup.get("reclaim_bytes", 0)) if dedup else 0
    max_tier = max(tiers.items(), key=lambda kv: int(kv[1].get("n", 0))) if tiers else ("—", {})

    rows = []
    rows.append(("A1 层-冷占比", "%.2f%%（阈值 ＞%.1f%%）" % (cold_pct, THRESHOLDS["A1_cold_share_pct_gt"]),
                 "ALERT" if cold_pct > THRESHOLDS["A1_cold_share_pct_gt"] else "OK"))
    rows.append(("A2 层-未分件数", "%d（阈值 ＞%d）" % (int(unfiled.get("n", 0)), THRESHOLDS["A2_unfiled_count_gt"]),
                 "WARN" if int(unfiled.get("n", 0)) > THRESHOLDS["A2_unfiled_count_gt"] else "OK"))
    rows.append(("A3 可回收(逐字重复)", "%d B（阈值 ＞%d）" % (reclaim, THRESHOLDS["A3_reclaim_bytes_gt"]),
                 "INFO" if reclaim > THRESHOLDS["A3_reclaim_bytes_gt"] else "OK"))
    rows.append(("A4 单层最大件数", "%s=%d（阈值 ＞%d）" % (max_tier[0], int(max_tier[1].get("n", 0)),
                 THRESHOLDS["A4_single_tier_count_gt"]),
                 "WARN" if int(max_tier[1].get("n", 0)) > THRESHOLDS["A4_single_tier_count_gt"] else "OK"))

    print("★ 容量预警检查（%s ｜ 清单采样 %s）" % (dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S +08"),
                                                  tier.get("sampled_at", "未标")))
    print("  总量：%.2f MB（%d 件）｜ 分层：%s" % (total_bytes / 1048576.0,
          sum(int(v.get("n", 0)) for v in tiers.values()),
          "，".join("%s=%d" % (k, v.get("n")) for k, v in tiers.items())))
    for name, val, level in rows:
        print("  [%-5s] %-18s %s" % (level, name, val))
    alerts = [r for r in rows if r[2] == "ALERT"]
    warns = [r for r in rows if r[2] == "WARN"]
    print("  ⇒ ALERT %d ｜ WARN %d ｜ INFO/OK %d" % (len(alerts), len(warns), len(rows) - len(alerts) - len(warns)))
    print("  **纪律**：告警≠处置；本器只报告，处置**候批**（承「候选≠判据」）")

    rec = {"checked_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S +08"),
           "source": str(TIER), "source_sampled_at": tier.get("sampled_at"),
           "thresholds": THRESHOLDS, "total_bytes": total_bytes,
           "tiers": tiers, "rows": [{"name": n, "value": v, "level": l} for n, v, l in rows],
           "alerts": len(alerts), "warns": len(warns), "executed": False}
    OUT.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    print("  JSON：%s" % OUT)
    if a.log_event:
        print("  事件：%s" % log_event("esc.capacity", "tier-inventory",
                                      "alerts=%d;warns=%d;cold=%.2f%%" % (len(alerts), len(warns), cold_pct),
                                      "thresholds=%s" % json.dumps(THRESHOLDS)))
    return 1 if alerts else 0


if __name__ == "__main__":
    sys.exit(main())
