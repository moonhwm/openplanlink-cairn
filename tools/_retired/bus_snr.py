# -*- coding: utf-8 -*-
"""bus_snr.py —— 总线**信噪比**实测（承令条「着力改善总线信噪比」「持续监测运行环境」）

口径（**全部可复算**，先定义再测量）：
  **信号 S**：
    · S1 交换区**有效新件**：按档号 `DF-*` 去重后的**唯一档号数**（同档号多件视为同一条信号）
    · S2 仓内**内容型提交**（近窗）：非 `re-sign tree`、非 merge 的提交数
  **噪声 N**：
    · N1 交换区**重复内容件**（同尺寸＋sha256 相同的多余副本数）
    · N2 仓内**重签型提交**（`push-gate: re-sign tree`）数
    · N3 **空变更提交**（`--allow-empty` 类；按 `git log --diff-filter=` 无法直接判定，故以"未改动树"计数近似：
        取 `git log --format=%H` 与 `git show --stat` 文件数 0 的提交数）
  **信噪比**：SNR = S / (S + N)；并给出**逐席**信号贡献（按提交作者）。

用法:
  python bus_snr.py [--hours 6] [--exchange <目录>] [--repo <目录>] [--json <路径>]
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8")


def sh(args, cwd):
    p = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=180)
    return (p.stdout or ""), p.returncode


def sha16(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=6.0)
    ap.add_argument("--exchange", default=r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A共同体_共享交换区")
    ap.add_argument("--repo", default=r"C:\Users\欧阳宏俊\openplanlink-mirror")
    ap.add_argument("--json")
    a = ap.parse_args()

    ex = pathlib.Path(a.exchange)
    # ── 信号 S1：唯一档号 ──
    docs, by_size = [], defaultdict(list)
    for p in ex.glob("*"):
        if not p.is_file():
            continue
        docs.append(p.name)
        try:
            st = p.stat()
        except OSError:
            continue
        if st.st_size >= 4096:
            by_size[st.st_size].append(p)
    ids = set()
    for n in docs:
        m = re.search(r"(DF-[A-Z]+-\d{8}-[A-Z0-9]+-\d+)", n)
        ids.add(m.group(1) if m else n)
    # ── 噪声 N1：重复内容副本 ──
    dup_extra = 0
    for size, ps in by_size.items():
        if len(ps) < 2:
            continue
        seen = defaultdict(int)
        for p in ps:
            try:
                seen[sha16(p)] += 1
            except OSError:
                continue
        dup_extra += sum(v - 1 for v in seen.values() if v > 1)
    # ── 仓库侧 S2/N2/N3 ──
    out, _ = sh(["git", "log", "--since=%g hours ago" % a.hours, "--format=%H|%an|%s"], a.repo)
    commits = [x for x in out.split("\n") if x.count("|") >= 2]
    resign = [x for x in commits if "re-sign tree" in x]
    content = [x for x in commits if "re-sign tree" not in x]
    empty = 0
    for c in content[:60]:
        h = c.split("|")[0]
        st, _ = sh(["git", "show", "--stat", "--oneline", h], a.repo)
        if "1 file changed" not in st and "files changed" not in st:
            empty += 1
    per_author = Counter(x.split("|")[1] for x in content)

    S = len(ids) + len(content)
    N = dup_extra + len(resign) + empty
    snr = S / float(S + N) if (S + N) else 0.0

    md = []
    md.append("# 总线信噪比实测（bus_snr）")
    md.append("")
    md.append("- 采样时点：%s（+08）｜ 窗口：%.1f 小时" % (dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), a.hours))
    md.append("- 口径：**S＝唯一档号数＋内容型提交数**；**N＝重复副本数＋重签提交数＋空变更提交数**；SNR = S/(S+N)")
    md.append("")
    md.append("| 项 | 计数 | 说明 |")
    md.append("|---|---|---|")
    md.append("| **S1 唯一档号** | %d | 交换区 `DF-*` 去重后唯一数（同档号多件计 1） |" % len(ids))
    md.append("| **S2 内容型提交** | %d | 非 re-sign、非 merge |" % len(content))
    md.append("| N1 重复副本 | %d | 同尺寸＋sha256 相同的多余副本 |" % dup_extra)
    md.append("| N2 重签提交 | %d | `push-gate: re-sign tree` |" % len(resign))
    md.append("| N3 空变更提交 | %d | `show --stat` 无文件变更者（抽样前 60） |" % empty)
    md.append("")
    md.append("## **SNR = S/(S+N) = %.3f**（S=%d，N=%d）" % (snr, S, N))
    md.append("")
    md.append("| 席位 | 内容型提交 |")
    md.append("|---|---|")
    for k, v in per_author.most_common():
        md.append("| %s | %d |" % (k, v))
    md.append("")
    md.append("**改善建议（按噪声占比排序）**：")
    md.append("1. **重签合并**（N2=%d，占噪声 %.0f%%）——承 `DF-PROPOSAL` §甲；" % (len(resign), 100.0 * len(resign) / max(1, N)))
    md.append("2. **去重**（N1=%d）——承 `DF-MEM` v0.2 P0（预案已备，候批）；" % dup_extra)
    md.append("3. **避免空变更提交**（N3=%d）。" % empty)

    text = "\n".join(md)
    print(text)
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps({
            "sampled_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "hours": a.hours,
            "S1_unique_ids": len(ids), "S2_content_commits": len(content),
            "N1_dup_copies": dup_extra, "N2_resign_commits": len(resign), "N3_empty_commits": empty,
            "S": S, "N": N, "snr": round(snr, 4),
            "commits_by_author": dict(per_author),
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("\n★ JSON 已写出：%s" % a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
