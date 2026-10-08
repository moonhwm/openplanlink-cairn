# -*- coding: utf-8 -*-
"""mem_audit.py —— 内存体检与「空闲但常驻」候选清单（只读）

对应令条：
  · 「**极致降低** CPU 空闲时间占比、**空闲内存量**等有关可能的闲置系数」
  · 「凡与既定策略不符的进程或自启动项，一律列入**待处置清单**并推送至安全运营中心复核」

背景（本席实测）：本机 **空闲内存占比仅 5.3–5.9%**（854–950 MB / 16 GB），而 CPU 空闲 43–61%
  ⇒ **内存是真正的瓶颈**（与 DF-START 所摄外部经验的「带宽/显存才是瓶颈」同向）。

本工具**只读**（不结束进程、不改工作集、不动任何配置），产出：
  1. 内存组成：总/可用/已用、可用占比、提交量（如可得）、页面文件使用
  2. 工作集 Top-N（按 WorkingSet 降序）
  3. **「空闲但常驻」候选**（启发式，明确标注）：工作集 ≥ 阈值 **且** 累计 CPU 时间低于阈值
     —— 仅供参考，**是否处置候安全运营中心裁定**；本席不代处置
  4. 待处置清单（含责任人/时限/状态栏位）

用法:
  python mem_audit.py --out-dir <目录> [--top 15] [--min-ws-mb 200] [--max-cpu-s 10]
"""
import argparse
import datetime as dt
import json
import pathlib
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")


def ps(cmd, timeout=180):
    p = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True,
                       text=True, timeout=timeout, encoding="utf-8", errors="replace")
    return (p.stdout or "").strip()


def os_mem():
    out = ps("$os=Get-CimInstance Win32_OperatingSystem; "
             "'{0}|{1}|{2}|{3}' -f $os.TotalVisibleMemorySize, $os.FreePhysicalMemory, "
             "$os.TotalVirtualMemorySize, $os.FreeVirtualMemory")
    try:
        t, f, tv, fv = [int(x) for x in out.split("|")]
    except Exception:  # noqa: BLE001
        return {}
    used = t - f
    return {
        "total_mb": round(t / 1024, 1), "free_mb": round(f / 1024, 1),
        "used_mb": round(used / 1024, 1),
        "free_pct": round(100.0 * f / t, 1) if t else None,
        "used_pct": round(100.0 * used / t, 1) if t else None,
        "commit_total_mb": round(tv / 1024, 1), "commit_free_mb": round(fv / 1024, 1),
    }


def pagefile():
    out = ps("$p=Get-CimInstance Win32_PageFileUsage; if ($p) { '{0}|{1}|{2}' -f "
             "$p.AllocatedBaseSize, $p.CurrentUsage, $p.PeakUsage }")
    if "|" not in out:
        return {}
    try:
        a, c, pk = [int(x) for x in out.split("|")]
        return {"allocated_mb": a, "current_usage_mb": c, "peak_usage_mb": pk}
    except Exception:  # noqa: BLE001
        return {}


def procs():
    out = ps("Get-CimInstance Win32_Process | Select-Object Name,ProcessId,WorkingSetSize,"
             "PageFileUsage,UserModeTime,KernelModeTime | ConvertTo-Json -Compress")
    try:
        d = json.loads(out) if out else []
    except json.JSONDecodeError:
        return []
    if isinstance(d, dict):
        d = [d]
    rows = []
    for x in d:
        ws = int(x.get("WorkingSetSize") or 0)
        ut = int(x.get("UserModeTime") or 0)      # 100ns
        kt = int(x.get("KernelModeTime") or 0)
        rows.append({"name": x.get("Name"), "pid": x.get("ProcessId"),
                     "ws_mb": round(ws / 1048576, 1),
                     "pagefile_mb": round(int(x.get("PageFileUsage") or 0) / 1024, 1),
                     "cpu_s": round((ut + kt) / 1e7, 2)})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=".")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--min-ws-mb", type=float, default=200.0)
    ap.add_argument("--max-cpu-s", type=float, default=10.0)
    a = ap.parse_args()

    outdir = pathlib.Path(a.out_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    m = os_mem()
    pf = pagefile()
    ps_ = sorted(procs(), key=lambda r: r["ws_mb"], reverse=True)
    top = ps_[: a.top]
    # 启发式：工作集大、累计 CPU 时间低 ⇒ 常驻但（迄今）少用；仅供复核参考
    cand = [r for r in ps_ if r["ws_mb"] >= a.min_ws_mb and r["cpu_s"] <= a.max_cpu_s]
    cand_ws = round(sum(r["ws_mb"] for r in cand), 1)

    # ── R_mem（内存风险量）·HY4 裁决第 4 条/C-24 定为**必填第四项** ──
    # 口径声明：规范层权威属 cpu-squeeze-c1 席（本席**非**规范层权威）；此处按其公开阈值推算，
    # 如与规范层不符**以规范层为准**。承 §六.18：数值带采样时点。
    total = m.get("total_mb") or 0.0
    free = m.get("free_mb") or 0.0
    m_floor = round(total * 0.08, 1)                  # 8% 安全下限（c1 席口径）
    r_mem_mb = round(max(0.0, m_floor - free), 1)     # 低于下限的风险量
    thr = {"降并行度_0.5GB": 512.0, "协办受理准入恢复线_0.8GB": 819.0,
           "M_floor_8pct": m_floor, "填谷申请上限_可用减2GB": round(free - 2048.0, 1)}
    breached = []
    if free < thr["降并行度_0.5GB"]:
        breached.append("降并行度线(0.5GB)")
    if free < thr["协办受理准入恢复线_0.8GB"]:
        breached.append("协办受理准入/恢复线(0.8GB)")
    if free < m_floor:
        breached.append("M_floor 安全下限(8%)")
    r_mem = {"R_mem_mb": r_mem_mb, "mem_available_mb": free, "total_mb": total,
             "M_floor_mb": m_floor, "thresholds_mb": thr, "breached": breached,
             "state": "低于安全下限" if free < m_floor else "高于安全下限",
             "sampled_at_utc": ts,
             "口径": "本席按公开阈值推算（M_floor − MemAvailable）；规范层权威属 cpu-squeeze-c1 席，待其校准"}

    data = {"generated_at_utc": ts, "memory": m, "pagefile": pf,
            "R_mem": r_mem,
            "top": top, "candidates": cand, "candidate_ws_mb": cand_ws,
            "params": {"min_ws_mb": a.min_ws_mb, "max_cpu_s": a.max_cpu_s, "top": a.top},
            "note": "候选为启发式（工作集大且累计 CPU 少），不代表可安全处置；处置候安全运营中心裁定"}
    (outdir / ("mem_audit_%s.json" % ts)).write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    L = ["# 内存体检与「空闲但常驻」候选清单（只读）", "",
         "- 时刻（UTC）：%s" % ts,
         "- 口径：Win32_Process 工作集 + User/KernelModeTime 累计 CPU；**只读**", "",
         "## 一、内存组成", "", "| 项 | 读数 |", "|---|---|",
         "| 物理内存总量 | %s MB |" % m.get("total_mb"),
         "| 已用 | %s MB（%s%%） |" % (m.get("used_mb"), m.get("used_pct")),
         "| **可用（空闲）** | **%s MB（%s%%）** |" % (m.get("free_mb"), m.get("free_pct")),
         "| 提交上限/可用 | %s MB / %s MB |" % (m.get("commit_total_mb"), m.get("commit_free_mb")),
         "| 页面文件 已分配/当前/峰值 | %s / %s / %s MB |" % (
             pf.get("allocated_mb"), pf.get("current_usage_mb"), pf.get("peak_usage_mb")),
         "", "## 一之二、**R_mem（内存风险量）** —— 必填第四项", "",
         "| 项 | 读数 |", "|---|---|",
         "| **R_mem** | **%s MB**（%s） |" % (r_mem["R_mem_mb"], r_mem["state"]),
         "| MemAvailable / 总量 | %s MB / %s MB |" % (r_mem["mem_available_mb"], r_mem["total_mb"]),
         "| M_floor 安全下限（8%%） | %s MB |" % r_mem["M_floor_mb"],
         "| 已击穿阈值 | %s |" % ("、".join(r_mem["breached"]) if r_mem["breached"] else "无"),
         "| 口径 | %s |" % r_mem["口径"],
         "| 采样时点 | %s |" % r_mem["sampled_at_utc"],
         "", "## 二、工作集 Top-%d" % a.top, "",
         "| # | 进程 | PID | 工作集 MB | 页面文件 MB | 累计 CPU 秒 |", "|---|---|---|---|---|---|"]
    for i, r in enumerate(top, 1):
        L.append("| %d | %s | %s | %s | %s | %s |" % (i, r["name"], r["pid"], r["ws_mb"],
                                                      r["pagefile_mb"], r["cpu_s"]))
    L += ["", "## 三、待处置清单（启发式候选，候安全运营中心复核）", "",
          "判据：工作集 ≥ %s MB **且** 累计 CPU ≤ %s 秒（合计工作集 %s MB）" % (
              a.min_ws_mb, a.max_cpu_s, cand_ws), "",
          "| 序 | 对象 | PID | 工作集 MB | 累计 CPU 秒 | 责任人 | 时限 | 状态 |",
          "|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(cand, 1):
        L.append("| %d | `%s` | %s | %s | %s | 候指派 | 候指派 | 待复核 |" % (
            i, r["name"], r["pid"], r["ws_mb"], r["cpu_s"]))
    if not cand:
        L.append("| — | — | — | — | — | — | — | 无候选 |")
    L += ["", "> **本清单只登记**：候选≠应处置（工作集大且 CPU 少也可能是正常缓存行为）。",
          "> 是否处置、由谁处置、时限几何，均候安全运营中心与主权人裁定；本席**不结束任何进程**。", ""]
    (outdir / ("mem_audit_%s.md" % ts)).write_text("\n".join(L) + "\n", encoding="utf-8")

    print("★ 内存：总量 %s MB ／ 已用 %s%% ／ **可用 %s%%**（%s MB）" % (
        m.get("total_mb"), m.get("used_pct"), m.get("free_pct"), m.get("free_mb")))
    print("★ R_mem（第四必填项）= **%s MB**（%s）；已击穿：%s；M_floor=%s MB" % (
        r_mem["R_mem_mb"], r_mem["state"],
        "、".join(r_mem["breached"]) if r_mem["breached"] else "无", r_mem["M_floor_mb"]))
    print("★ Top-%d 已列出；启发式候选 %d 个（合计工作集 %s MB）" % (a.top, len(cand), cand_ws))
    print("★ 已写出：%s（md+json）" % outdir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
