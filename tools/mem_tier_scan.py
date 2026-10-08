# -*- coding: utf-8 -*-
"""mem_tier_scan.py —— 记忆分层 **只读盘点**（承 DF-MEM-20261007-CAIRN-01；丙项试点第一步）

纪律：**只读**——不移动、不删除、不改名任何文件；仅统计与建议。
输出：分层的 文件数／字节／龄期中位数；**重复内容检测**（同尺寸候选→哈希确认）与其**可回收字节**；
      容量预警阈值判定；冷层占比建议。采样带时点（承 §六.18）。

分层口径（按路径与龄期，先粗分后可按访问频次细化）：
  · **层-热**：exp/（工具与在役脚本）、ledger/（台账，链式在役）
  · **层-温**：outbox/（产出待投）、exchange 副本、console/eff 快照
  · **层-冷**：archive/（归档 .otl）、handshake/（历史握手，体积最大）、*.upack（压缩包）

用法:
  python mem_tier_scan.py [--seat <路径>] [--min-dup-size 4096] [--json <路径>]
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")

TIERS = {
    "层-热": ["exp", "ledger"],
    "层-温": ["outbox", "console", "eff", "ops"],
    "层-冷": ["archive", "handshake"],
}


def classify(rel: str, name: str):
    top = rel.split(os.sep, 1)[0]
    for tier, tops in TIERS.items():
        if top in tops:
            return tier
    if name.endswith(".upack"):
        return "层-冷"
    return "层-未分"


def sha256(p, cap=8 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seat", default=r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928")
    ap.add_argument("--min-dup-size", type=int, default=4096)
    ap.add_argument("--json")
    a = ap.parse_args()

    seat = pathlib.Path(a.seat)
    now = dt.datetime.now()
    stats = defaultdict(lambda: {"n": 0, "bytes": 0, "ages": []})
    by_size = defaultdict(list)
    all_rows = []

    for root, dirs, files in os.walk(seat):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        for fn in files:
            p = pathlib.Path(root) / fn
            try:
                st = p.stat()
            except OSError:
                continue
            rel = str(p.relative_to(seat))
            tier = classify(rel, fn)
            age = (now - dt.datetime.fromtimestamp(st.st_mtime)).total_seconds() / 86400.0
            s = stats[tier]
            s["n"] += 1
            s["bytes"] += st.st_size
            s["ages"].append(age)
            all_rows.append((tier, rel, st.st_size, round(age, 1)))
            if st.st_size >= a.min_dup_size:
                by_size[st.st_size].append(p)

    # 重复检测：仅对同尺寸候选做哈希（省 IO）
    dups = []
    wasted = 0
    for size, paths in by_size.items():
        if len(paths) < 2:
            continue
        seen = defaultdict(list)
        for p in paths:
            try:
                seen[sha256(p)].append(p)
            except OSError:
                continue
        for h, ps in seen.items():
            if len(ps) > 1:
                wasted += size * (len(ps) - 1)
                dups.append({"size": size, "count": len(ps),
                             "wasted": size * (len(ps) - 1),
                             "paths": [str(x.relative_to(seat)) for x in ps[:4]]})

    total_bytes = sum(v["bytes"] for v in stats.values()) or 1
    def pct(b):
        return 100.0 * b / total_bytes

    md = []
    md.append("# 记忆分层只读盘点（mem_tier_scan）")
    md.append("")
    md.append("- 采样时点：%s（+08）｜ 目标：`%s`" % (now.strftime("%Y-%m-%d %H:%M:%S"), seat.name))
    md.append("- 纪律：**只读**（不移动/删除/改名）；分层为粗分，可据访问频次再细化")
    md.append("")
    md.append("| 层 | 文件数 | 字节 | 占比 | 龄期中位数(天) | 龄期 P90(天) |")
    md.append("|---|---|---|---|---|---|")
    for tier in ("层-热", "层-温", "层-冷", "层-未分"):
        v = stats.get(tier)
        if not v or not v["n"]:
            continue
        ages = sorted(v["ages"])
        med = ages[len(ages) // 2]
        p90 = ages[int(len(ages) * 0.9)] if len(ages) > 1 else ages[0]
        md.append("| %s | %d | %.2f MB | %.1f%% | %.1f | %.1f |"
                  % (tier, v["n"], v["bytes"] / 1048576.0, pct(v["bytes"]), med, p90))
    md.append("| **合计** | %d | %.2f MB | 100%% | — | — |"
              % (sum(v["n"] for v in stats.values()), total_bytes / 1048576.0))
    md.append("")
    cold = stats.get("层-冷", {"bytes": 0})["bytes"]
    md.append("## 容量预警与建议")
    md.append("")
    md.append("- 冷层占比：**%.1f%%**（阈值建议：>70%% ⇒ 优先冷化/归档；本盘为**只读评估**）" % pct(cold))
    n_dup = sum(d["count"] - 1 for d in dups)
    md.append("- 重复内容：**%d 组**、可回收 **%d 个副本 / %.2f MB**（同尺寸候选→哈希确认）"
              % (len(dups), n_dup, wasted / 1048576.0))
    if dups:
        md.append("")
        md.append("| 尺寸(B) | 副本数 | 可回收(B) | 示例路径（截断） |")
        md.append("|---|---|---|---|")
        for d in sorted(dups, key=lambda x: -x["wasted"])[:8]:
            md.append("| %d | %d | %d | `%s` |" % (d["size"], d["count"], d["wasted"], d["paths"][0][:70]))
    md.append("")
    md.append("> 判读：本件**不含任何处置动作**；若网络批准冷化，建议先行「**重复副本去重**」与「**冷层压缩**」，")
    md.append("> 并以 `DF-MEM` 的层-热/层-温/层-冷定义执行（术语承 `DF-ALIGN` 甲案：层级用 `层-*`）。")

    text = "\n".join(md)
    print(text)
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps({
            "sampled_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "tiers": {k: {"n": v["n"], "bytes": v["bytes"]} for k, v in stats.items()},
            "cold_share_pct": round(pct(cold), 2),
            "dup_groups": len(dups), "dup_wasted_bytes": wasted,
            "samples": [{"tier": t, "rel": r, "size": s, "age_days": g}
                        for t, r, s, g in sorted(all_rows, key=lambda x: -x[2])[:40]],
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("\n★ JSON 已写出：%s" % a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
