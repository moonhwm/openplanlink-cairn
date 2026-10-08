# -*- coding: utf-8 -*-
"""mem_guard.py —— **R_mem 破线期失败/重试计数**（承 DF-ACK-20261007-CAIRN-06 §四）

背景（实测，2026-10-07 13:40）：系统可用内存 **0.11 GB（0.71%）**、**R_mem 1280.3 MB ＜ M_floor 1286.1 MB**
⇒ 本席本地工具在**正常规模遍历**中 `MemoryError`，**重跑方成**。⇒ 该现象须**计数留痕**，
而非仅作一次性观察（承 `DF-START5` §四 丙/戊：隐性成本显式化 + 上界）。

功能：
  1. `check`      —— 读当前 R_mem 与三阈值，输出是否破线（承既有口径：0.5 GB／0.8 GB／M_floor）
  2. `wrap -- <cmd...>` —— 在受护状态下运行命令：**记录 成功/失败/重试 次数与耗时**，
                     失败时**自动重试一次**（`--retries N`），结果追加至 `mem_guard_log.jsonl`
  3. `stats`      —— 汇总计数（总运行／成功／失败／重试成功／破线期运行占比）

口径：M_floor = 8% × 总内存；阈值沿用 `exp/mem_audit.py`（0.5 GB 降并行度线／0.8 GB 准入线）。
纪律：**只读系统指标**；**不修改任何被运行命令的语义**；所有数字**实测**，取不到即标"未测"。
"""
import argparse
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
SEAT = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928")
LOG = SEAT / "outbox" / "mem" / "mem_guard_log.jsonl"


def _ps(script, timeout=150):
    """调用 PowerShell 取值（承 mem_audit 之同法：单次组合脚本）。"""
    p = subprocess.run(["powershell", "-NoProfile", "-Command", script],
                       capture_output=True, text=True, timeout=timeout)
    return (p.stdout or "").strip()


def r_mem_mb():
    """R_mem ≈ MemAvailable（MB）。**双法回退**并记录来源；取不到返回 (None, "未测")。"""
    try:
        out = _ps("$os=Get-CimInstance Win32_OperatingSystem; '{0}|{1}' -f $os.TotalVisibleMemorySize, $os.FreePhysicalMemory")
        if "|" in out:
            tot_kb, free_kb = (int(x) for x in out.split("|")[:2])
            return round(free_kb / 1024.0, 1), "CimInstance.FreePhysicalMemory"
    except Exception:  # noqa: BLE001
        pass
    try:
        out = _ps("(Get-Counter '\\Memory\\Available MBytes').CounterSamples[0].CookedValue")
        return round(float(out), 1), "PerfCounter.AvailableMBytes"
    except Exception:  # noqa: BLE001
        return None, "未测"


def total_mb():
    try:
        out = _ps("(Get-CimInstance Win32_OperatingSystem).TotalVisibleMemorySize")
        return round(int(out) / 1024.0, 1)
    except Exception:  # noqa: BLE001
        return None


def total_mb():
    try:
        p = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "(Get-CimInstance Win32_OperatingSystem).TotalVisibleMemorySize"],
                           capture_output=True, text=True, timeout=60)
        kb = int((p.stdout or "").strip() or 0)
        return round(kb / 1024.0, 1) if kb else None
    except Exception:  # noqa: BLE001
        return None


def thresholds():
    tot = total_mb()
    m_floor = round(0.08 * tot, 1) if tot else None
    return {"total_mb": tot, "m_floor_mb": m_floor, "line_0_8gb": 819.2, "line_0_5gb": 512.0}


def breached(rm, th):
    if rm is None or th.get("m_floor_mb") is None:
        return None
    return {"below_m_floor": rm < th["m_floor_mb"], "below_0_8gb": rm < th["line_0_8gb"],
            "below_0_5gb": rm < th["line_0_5gb"]}


def append(rec):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def cmd_check(a):
    rm, src = r_mem_mb()
    th = thresholds()
    br = breached(rm, th)
    print("★ R_mem 检查（%s）：R_mem=%s MB ｜ M_floor=%s MB ｜ 0.8GB线=%s ｜ 0.5GB线=%s"
          % (dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ("%s（来源=%s）" % (rm, src)), th["m_floor_mb"], th["line_0_8gb"], th["line_0_5gb"]))
    if br is None:
        print("  ⇒ **未测**（取不到系统内存指标）")
        return 1
    print("  ⇒ 破线：M_floor=%s ｜ 0.8GB=%s ｜ 0.5GB=%s" % (br["below_m_floor"], br["below_0_8gb"], br["below_0_5gb"]))
    return 0


def cmd_wrap(a):
    cmd = a.cmd
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        print("★ 用法：mem_guard.py wrap -- <命令...>")
        return 2
    rm0, rsrc = r_mem_mb()
    th = thresholds()
    br0 = breached(rm0, th)
    attempts, ok, err = 0, False, ""
    t0 = time.time()
    while attempts <= a.retries:
        attempts += 1
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=a.timeout)
        if p.returncode == 0:
            ok = True
            break
        err = ((p.stderr or "") + (p.stdout or ""))[-300:]
        time.sleep(a.backoff)
    dur = round(time.time() - t0, 2)
    rec = {"ts": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "cmd": " ".join(cmd)[:120],
           "r_mem_mb_at_start": rm0, "r_mem_source": rsrc, "breached_at_start": br0, "attempts": attempts,
           "success": ok, "elapsed_s": dur, "last_err_tail": err if not ok else ""}
    append(rec)
    print("★ 受护运行：%s ｜ 尝试 %d 次 ｜ %s ｜ 耗时 %.2fs ｜ 起始 R_mem=%s MB%s"
          % (" ".join(cmd)[:60], attempts, "成功" if ok else "**失败**", dur, rm0,
             "（**破线期**）" if (br0 and br0["below_m_floor"]) else ""))
    if not ok:
        print("  末次错误尾部：%s" % err.replace("\n", " ")[:200])
    return 0 if ok else 1


def cmd_stats(a):
    if not LOG.exists():
        print("★ 无记录（%s）" % LOG)
        return 0
    rows = []
    for line in LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except Exception:  # noqa: BLE001
                continue
    n = len(rows)
    succ = sum(1 for r in rows if r.get("success"))
    retried = sum(1 for r in rows if (r.get("attempts") or 1) > 1)
    retry_succ = sum(1 for r in rows if r.get("success") and (r.get("attempts") or 1) > 1)
    brk = sum(1 for r in rows if (r.get("breached_at_start") or {}).get("below_m_floor"))
    print("★ R_mem 破线期运行统计（%s）" % dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("  总运行 %d ｜ 成功 %d ｜ 失败 %d ｜ 曾重试 %d ｜ **重试后成功 %d** ｜ **破线期运行 %d（占 %.0f%%）**"
          % (n, succ, n - succ, retried, retry_succ, brk, 100.0 * brk / max(1, n)))
    print("  ⇒ 判读：**重试后成功数**即「因资源而受阻但可恢复」的操作量（承 DF-ACK-06 §四）")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check").set_defaults(fn=cmd_check)
    w = sub.add_parser("wrap")
    w.add_argument("cmd", nargs=argparse.REMAINDER)
    w.add_argument("--retries", type=int, default=1)
    w.add_argument("--backoff", type=float, default=2.0)
    w.add_argument("--timeout", type=int, default=900)
    w.set_defaults(fn=cmd_wrap)
    sub.add_parser("stats").set_defaults(fn=cmd_stats)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
