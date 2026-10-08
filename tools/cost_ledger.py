# -*- coding: utf-8 -*-
"""cost_ledger.py —— 固定成本记账（承 DF-START5 §四 甲/丙/戊：重签≤1 次／隐性成本显式／给出上界）

背景（实测）：本日近 6 小时出现 **40 次** `push-gate: re-sign tree` 提交；单次重签 **0.75 秒**
（另加 pre-commit 校验、prepush_samebatch 守卫、push 往返）。此即"**输出不变、成本累积**"
（见 DF-START5：与 06 线 acceptance-collapse 同构）⇒ 需**显式记账并给上界**。

口径：
  · 重签成本 = 窗口内 re-sign 提交数 × 单次重签耗时（`--sign-sec`，缺省取实测 0.75s）
  · 守卫成本 = 窗口内 commit 数 × 单次守卫耗时（`--guard-sec`，缺省保守 1.5s）
  · 扫描成本 = 显式传入的全仓扫描次数 × 119.6s（`--scans N`，缺省 0）
  · **上界**：以上三项之和即"**固定开销上界**"（不含真实内容工作）
输出：仅计数与秒数，**不回显任何值**；带采样时点（承 §六.18）。

用法：
  python cost_ledger.py [--hours 6] [--scans 0] [--sign-sec 0.75] [--guard-sec 1.5]
"""
import argparse
import datetime as dt
import pathlib
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
REPO = pathlib.Path(r"C:\Users\欧阳宏俊\openplanlink-mirror")
SCAN_SEC = 119.6  # 全仓披露扫描实测（119.6s，1989 文件）


def git(args):
    p = subprocess.run(["git", *args], cwd=str(REPO), capture_output=True, text=True,
                       timeout=120, encoding="utf-8", errors="replace")
    return (p.stdout or ""), p.returncode



def scan_count_from_events(hours):
    """从事件链 ops/ops_event.jsonl 统计窗口内 disclosure.scan 次数（自动计次，替占位值）。"""
    import json as _j
    import datetime as _dt
    p = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928\ops\ops_event.jsonl")
    if not p.exists():
        return None
    cut = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(hours=hours)
    n = 0
    try:
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            o = _j.loads(line)
            if o.get("action") != "disclosure.scan":
                continue
            try:
                ts = _dt.datetime.strptime(o["ts_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=_dt.timezone.utc)
            except Exception:  # noqa: BLE001
                continue
            if ts >= cut:
                n += 1
    except Exception:  # noqa: BLE001
        return None
    return n

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=6.0)
    ap.add_argument("--scans", type=int, default=-1, help="窗口内全仓扫描次数；-1=自动读事件链")
    ap.add_argument("--sign-sec", type=float, default=0.75)
    ap.add_argument("--guard-sec", type=float, default=1.5)
    a = ap.parse_args()

    scans = scan_count_from_events(a.hours) if a.scans < 0 else a.scans
    scans_src = "自动(事件链)" if a.scans < 0 else "显式传入"
    if scans is None:
        scans = 0
        scans_src = "未测(事件链不可读)"
    out, _ = git(["log", "--since=%g hours ago" % a.hours, "--format=%H|%s"])
    lines = [x for x in out.split("\n") if "|" in x]
    resign = [x for x in lines if "re-sign tree" in x]
    # 守卫通常每次提交都跑：以"非 merge 的提交数"近似
    commits = [x for x in lines if "push-gate: re-sign tree" not in x]

    sign_cost = len(resign) * a.sign_sec
    guard_cost = len(lines) * a.guard_sec
    scan_cost = scans * SCAN_SEC
    total = sign_cost + guard_cost + scan_cost

    print("★ 固定成本记账（采样时点 %s ｜ 窗口 %.1f 小时 ｜ 仓 %s）"
          % (dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), a.hours, REPO.name))
    print("")
    print("| 项 | 计数 | 单次耗时 | 小计 |")
    print("|---|---|---|---|")
    print("| 重签（re-sign tree） | %d | %.2fs（实测） | %.1fs |" % (len(resign), a.sign_sec, sign_cost))
    print("| 提交（含守卫近似） | %d | %.2fs（保守估） | %.1fs |" % (len(lines), a.guard_sec, guard_cost))
    print("| 全仓披露扫描 | %d（%s） | %.1fs（实测） | %.1fs |" % (scans, scans_src, SCAN_SEC, scan_cost))
    print("| **固定开销上界** | — | — | **%.1fs（≈%.1f 分钟）** |" % (total, total / 60.0))
    print("")
    print("判读：")
    print("  · 「内容型提交」%d 次 vs 「重签型提交」%d 次 ⇒ 重签占比 **%.0f%%**"
          % (len(commits), len(resign), 100.0 * len(resign) / max(1, len(lines))))
    print("  · 建议（承 DF-START5 甲）：**连续提交合并为一次重签**；核验一次可省 %.1fs/轮" % a.sign_sec)
    print("  · 建议（乙）：全仓扫描限夜维/显式请求；常规只用 --staged（单次可省 %.1fs）" % SCAN_SEC)
    if len(resign) > max(3, len(commits)):
        print("  · ⚠ **本窗口重签次数已超过内容型提交数** ⇒ 命中『输出不变、成本累积』形态（DF-START5 §三）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
