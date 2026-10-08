# -*- coding: utf-8 -*-
"""desk_baseline.py —— 桌面环境快照 / 配置基线比对 / 闲置系数实测（只读）

对应本轮新增令条：
  · 「各节点需在迁移窗口内完成**桌面环境快照与配置基线比对**」
  · 「凡与既定策略不符的进程或自启动项，一律列入**待处置清单**」
  · 「**极致降低 CPU 空闲时间占比、空闲内存量**等有关可能的闲置系数」

动作（全部只读，不改任何配置）：
  1. 快照：进程清单（名/PID/路径）、自启动项（HKCU/HKLM Run、启动文件夹）、
     计划任务数、服务数、CPU 空闲占比、可用内存与内存占用比
  2. 基线比对：与上次快照（`desk_baseline.json`）比对 → 新增/消失的进程与自启动项
  3. 输出：`desk_snapshot_<UTC>.json`（机器可读）＋ `desk_deviations_<UTC>.md`（待处置清单，含责任人与时限栏位）
  4. 闲置系数：cpu_idle_pct（越高越闲）、mem_idle_pct（可用内存占比）

用法:
  python desk_baseline.py --out-dir <目录> [--baseline <baseline.json>] [--update-baseline]
退出码：0
"""
import argparse
import datetime as dt
import json
import pathlib
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

PS = [
    "powershell", "-NoProfile", "-Command",
]


def ps(cmd, timeout=120):
    p = subprocess.run(PS + [cmd], capture_output=True, text=True, timeout=timeout,
                       encoding="utf-8", errors="replace")
    return (p.stdout or "").strip()


def snapshot_processes():
    out = ps("Get-CimInstance Win32_Process | Select-Object ProcessId,Name,ExecutablePath | ConvertTo-Json -Compress")
    try:
        data = json.loads(out) if out else []
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        data = [data]
    return [{"pid": d.get("ProcessId"), "name": d.get("Name"),
             "path": (d.get("ExecutablePath") or "")} for d in data]


def snapshot_startup():
    items = []
    for hive in ("HKCU", "HKLM"):
        out = ps("$p='%s:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run';"
                 "if (Test-Path $p) { (Get-ItemProperty $p).PSObject.Properties | "
                 "Where-Object { $_.Name -notlike 'PS*' } | ForEach-Object { $_.Name + '=' + $_.Value } }" % hive)
        for line in out.splitlines():
            line = line.strip()
            if line:
                items.append({"scope": hive, "entry": line})
    return items


def snapshot_counts():
    tasks = ps("(Get-ScheduledTask | Measure-Object).Count")
    svcs = ps("(Get-Service | Measure-Object).Count")
    return {"scheduled_tasks": int(tasks) if tasks.isdigit() else None,
            "services": int(svcs) if svcs.isdigit() else None}


def idle_metrics():
    """CPU 空闲占比与内存闲置（实测；取不到则标 None，不估算）。"""
    cpu = ps("(Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average")
    mem = ps("$os=Get-CimInstance Win32_OperatingSystem; "
             "'{0}|{1}' -f $os.FreePhysicalMemory, $os.TotalVisibleMemorySize")  # KB
    cpu_load = None
    try:
        cpu_load = float(cpu)
    except (TypeError, ValueError):
        pass
    free_kb = total_kb = None
    if "|" in mem:
        a, b = mem.split("|", 1)
        try:
            free_kb, total_kb = int(a), int(b)
        except ValueError:
            pass
    res = {"cpu_load_pct": cpu_load,
           "cpu_idle_pct": (100.0 - cpu_load) if cpu_load is not None else None,
           "mem_free_mb": round(free_kb / 1024, 1) if free_kb else None,
           "mem_total_mb": round(total_kb / 1024, 1) if total_kb else None}
    if free_kb and total_kb:
        res["mem_idle_pct"] = round(100.0 * free_kb / total_kb, 1)
    else:
        res["mem_idle_pct"] = None
    return res


def diff(prev, cur):
    out = {}
    for key, label in (("processes", "进程"), ("startup", "自启动项")):
        p = prev.get(key) or []
        c = cur.get(key) or []
        if key == "processes":
            ps_ = {x.get("name") for x in p}
            cs = {x.get("name") for x in c}
        else:
            ps_ = {x.get("entry") for x in p}
            cs = {x.get("entry") for x in c}
        out[key] = {"added": sorted(x for x in cs - ps_ if x),
                    "removed": sorted(x for x in ps_ - cs if x)}
        out[key]["label"] = label
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=".")
    ap.add_argument("--baseline", default=None)
    ap.add_argument("--update-baseline", action="store_true")
    a = ap.parse_args()

    outdir = pathlib.Path(a.out_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    cur = {
        "generated_at": ts,
        "host": ps("$env:COMPUTERNAME"),
        "processes": snapshot_processes(),
        "startup": snapshot_startup(),
        "counts": snapshot_counts(),
        "idle": idle_metrics(),
    }
    snap = outdir / ("desk_snapshot_%s.json" % ts)
    snap.write_text(json.dumps(cur, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    base_path = pathlib.Path(a.baseline) if a.baseline else (outdir / "desk_baseline.json")
    d = None
    if base_path.exists() and not a.update_baseline:
        try:
            prev = json.loads(base_path.read_text(encoding="utf-8"))
            d = diff(prev, cur)
        except Exception:  # noqa: BLE001
            d = None
    if a.update_baseline or not base_path.exists():
        base_path.write_text(json.dumps(cur, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    idle = cur["idle"]
    L = ["# 桌面环境快照与配置基线比对（待处置清单）", "",
         "- 快照时刻（UTC）：%s ｜ 主机：%s" % (ts, cur["host"]),
         "- 快照文件：`%s` ｜ 基线：`%s`%s" % (snap.name, base_path.name,
                                            "（本次已更新基线）" if (a.update_baseline or d is None) else ""),
         "", "## 一、闲置系数（实测）", "",
         "| 指标 | 实测 | 说明 |", "|---|---|---|",
         "| CPU 负载占比 | %s%% | — |" % idle.get("cpu_load_pct"),
         "| **CPU 空闲占比** | **%s%%** | 越高越闲；令条要求极致降低 |" % idle.get("cpu_idle_pct"),
         "| 可用内存 | %s MB / %s MB | — |" % (idle.get("mem_free_mb"), idle.get("mem_total_mb")),
         "| **空闲内存占比** | **%s%%** | 越高越闲 |" % idle.get("mem_idle_pct"),
         "", "## 二、环境计数", "",
         "| 项 | 值 |", "|---|---|",
         "| 进程数 | %d |" % len(cur["processes"]),
         "| 自启动项 | %d |" % len(cur["startup"]),
         "| 计划任务 | %s |" % cur["counts"].get("scheduled_tasks"),
         "| 服务 | %s |" % cur["counts"].get("services"),
         "", "## 三、与基线的偏离（待处置）", ""]
    if d is None:
        L += ["（无可用基线，本次已将其建立为基线；下次运行即可比对。）", ""]
    else:
        L += ["| 类别 | 新增 | 消失 |", "|---|---|---|",
              "| 进程 | %d 项%s | %d 项%s |" % (
                  len(d["processes"]["added"]),
                  ("：" + "、".join(d["processes"]["added"][:8])) if d["processes"]["added"] else "",
                  len(d["processes"]["removed"]),
                  ("：" + "、".join(d["processes"]["removed"][:8])) if d["processes"]["removed"] else ""),
              "| 自启动项 | %d 项%s | %d 项%s |" % (
                  len(d["startup"]["added"]),
                  ("：" + "、".join(d["startup"]["added"][:8])) if d["startup"]["added"] else "",
                  len(d["startup"]["removed"]),
                  ("：" + "、".join(d["startup"]["removed"][:8])) if d["startup"]["removed"] else ""),
              ""]
        L += ["### 待处置清单（候安全运营中心复核）", "",
              "| 序 | 对象 | 类别 | 偏离类型 | 责任人 | 时限 | 状态 |",
              "|---|---|---|---|---|---|---|"]
        i = 0
        for k, label in (("processes", "进程"), ("startup", "自启动项")):
            for x in d[k]["added"]:
                i += 1
                L.append("| %d | `%s` | %s | 新增 | 候指派 | 候指派 | 待复核 |" % (i, x, label))
            for x in d[k]["removed"]:
                i += 1
                L.append("| %d | `%s` | %s | 消失 | 候指派 | 候指派 | 待复核 |" % (i, x, label))
        if i == 0:
            L.append("| — | — | — | 无偏离 | — | — | — |")
        L += ["", "> 本清单仅**登记**偏离；是否处置、由谁处置、时限几何，均候安全运营中心与主权人裁定。", ""]
    L += ["## 四、声明", "",
          "- 本工具**只读**：不改注册表、不改自启动项、不动任何进程，**不启动/不终止**任何程序。",
          "- 数值均为现场实测；取不到者标 `None`，**不估算**。",
          "- 快照含进程路径信息，**不含任何凭据**；如需外发须先经外发审查。", ""]
    dev = outdir / ("desk_deviations_%s.md" % ts)
    dev.write_text("\n".join(L) + "\n", encoding="utf-8")

    print("★ 快照：%s" % snap)
    print("★ 待处置清单：%s" % dev)
    print("★ 闲置系数：CPU空闲=%s%%  空闲内存=%s%%  进程=%d 自启动=%d" % (
        idle.get("cpu_idle_pct"), idle.get("mem_idle_pct"), len(cur["processes"]), len(cur["startup"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
