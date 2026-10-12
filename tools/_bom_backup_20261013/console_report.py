# -*- coding: utf-8 -*-
"""console_report.py —— 主控台一页纸读数（审计就绪）

对应令条：
  · 「将各节点操作日志**同步至主控台**，便于追溯异常行为并**生成审计报告**」
  · 「迁移结束后，主控台将依据日志留存周期与合规要求，统一归档会话记录与文件指纹」
  · 「在工作汇报时**强制考虑相关使用效能报告**」

本工具**只读聚合**本席既有事实源，输出**一页纸**（md）与机器可读（json），便于主控台汇聚：
  1. 台账：条目数 + 链自洽结论
  2. 事件链：条数 + 链自洽结论（ops_event.jsonl）
  3. 仓库三面：local / origin / gitcode 是否一致（git ls-remote 实查，带代理回退）
  4. MCP 通道：在线通道（launch.mjs 子进程）
  5. 闲置系数：取最近 desk_snapshot（CPU 空闲% / 空闲内存%）
  6. 夜间窗口：当前是否在窗口内、距最近边界、是否临近需落盘
  7. 工单：最新 workorder 张数
  8. CI/CD：可选（`--no-net` 可跳过），取最近工作流结论

用法:
  python console_report.py                       # 一页纸到标准输出
  python console_report.py --out-dir <目录>       # 同时落盘 md+json
  python console_report.py --no-net              # 跳过网络查询（离线可用）
"""
import argparse
import datetime as dt
import glob
import json
import os
import pathlib
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

SEAT = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928")
REPO = pathlib.Path(r"C:\Users\欧阳宏俊\openplanlink-mirror")
PY = sys.executable
PROXY_OFF = ["-c", "http.proxy=", "-c", "https.proxy="]



def host_ref():
    """主机名伪名（承脱敏口径：主机名不录值，但需可关联）——H-<sha256(hostname)[:8]>。"""
    import hashlib as _h
    import os as _o
    hn = (_o.environ.get("COMPUTERNAME") or "unknown").strip().lower()
    return "H-" + _h.sha256(hn.encode("utf-8")).hexdigest()[:8]

def run(args, cwd=None, timeout=180):
    try:
        p = subprocess.run(args, cwd=str(cwd or REPO), capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        return (p.stdout or "") + (p.stderr or ""), p.returncode
    except Exception as exc:  # noqa: BLE001
        return "ERR:%s" % exc, 1


def ledger_stats():
    out, _ = run([PY, str(SEAT / "ledger" / "cairn_ledger.py"), "verify"])
    n = None
    for line in out.splitlines():
        if "条目数" in line:
            try:
                n = int("".join(ch for ch in line if ch.isdigit()))
            except ValueError:
                pass
    return {"entries": n, "chain_ok": "PASS" in out}


def ops_stats():
    out, code = run([PY, str(SEAT / "exp" / "ops_event.py"), "verify"])
    n = None
    if "（" in out:
        try:
            n = int(out.split("（")[1].split("条")[0])
        except Exception:  # noqa: BLE001
            pass
    return {"events": n, "chain_ok": code == 0}


def repo_three_way():
    local, _ = run(["git", "rev-parse", "--short", "HEAD"])
    res = {"local": local.strip()}
    for r in ("origin", "gitcode"):
        out, code = run(["git", *PROXY_OFF, "ls-remote", r, "refs/heads/main"])
        if code != 0 or not out:
            out2, code2 = run(["git", "ls-remote", r, "refs/heads/main"])
            out = out2 if code2 == 0 else ""
        res[r] = out.split()[0][:7] if out.strip() else None
    res["aligned"] = bool(res["local"]) and res["local"] == res.get("origin") == res.get("gitcode")
    return res


def disk_block():
    """磁盘水位与容量阈值（DF-MEM-20261007-CAIRN-01 §三）：C 黄<15GB / 红<8GB；A<100GB 停归档。"""
    import shutil
    out = {}
    for d, letter in (("C:\\", "C"), ("A:\\", "A")):
        try:
            u = shutil.disk_usage(d)
            out[letter] = {"total_gb": round(u.total / 2**30, 1), "free_gb": round(u.free / 2**30, 1),
                           "used_gb": round(u.used / 2**30, 1)}
        except Exception:  # noqa: BLE001
            out[letter] = None
    c = out.get("C") or {}
    free = c.get("free_gb")
    if free is None:
        lvl = "未知"
    elif free < 8:
        lvl = "红（<8GB，须强制冷化并上报工单）"
    elif free < 15:
        lvl = "黄（<15GB，触发一轮冷化）"
    else:
        lvl = "正常"
    a = out.get("A") or {}
    a_lvl = "正常" if (a.get("free_gb") or 0) >= 100 else "停归档（A<100GB）"
    return {"disks": out, "c_level": lvl, "a_level": a_lvl,
            "thresholds": {"c_yellow_gb": 15, "c_red_gb": 8, "a_stop_gb": 100},
            "source": "DF-MEM-20261007-CAIRN-01 §三"}


def r_mem_block():
    """R_mem（第四必填项，HY4 裁决第 4 条/C-24）：取最近一次 mem_audit 的 R_mem 块。
    缺件则如实标 None（不臆造）；口径权威属 cpu-squeeze-c1 席。"""
    files = sorted(glob.glob(str(SEAT / "outbox" / "mem" / "mem_audit_*.json")))
    if not files:
        return {"R_mem_mb": None, "state": "无体检件", "source": None}
    try:
        d = json.loads(pathlib.Path(files[-1]).read_text(encoding="utf-8"))
        r = dict(d.get("R_mem") or {})
        r["source"] = pathlib.Path(files[-1]).name
        return r
    except Exception:  # noqa: BLE001
        return {"R_mem_mb": None, "state": "读取失败", "source": pathlib.Path(files[-1]).name}


def mcp_live():
    ps = ("Get-CimInstance Win32_Process -Filter \"Name='node.exe'\" | "
          "Where-Object { $_.CommandLine -like '*launch.mjs*' } | "
          "ForEach-Object { if ($_.CommandLine -match 'launch\\.mjs\"?\\s+(\\w+)') { $Matches[1] } }")
    out, _ = run(["powershell", "-NoProfile", "-Command", ps])
    return [x for x in out.split() if x]


def idle_from_snapshot():
    files = sorted(glob.glob(str(SEAT / "outbox" / "deskbase" / "desk_snapshot_*.json")))
    if not files:
        return None
    try:
        d = json.loads(pathlib.Path(files[-1]).read_text(encoding="utf-8"))
        return {"at": d.get("generated_at"), "cpu_idle_pct": d["idle"].get("cpu_idle_pct"),
                "mem_idle_pct": d["idle"].get("mem_idle_pct"),
                "processes": len(d.get("processes", []))}
    except Exception:  # noqa: BLE001
        return None


def night_state():
    out, _ = run([PY, str(SEAT / "exp" / "night_window.py"), "--json",
                  str(SEAT / "outbox" / "night_window.json")])
    try:
        d = json.loads((SEAT / "outbox" / "night_window.json").read_text(encoding="utf-8"))
        return {"in_window": d["in_night_window"], "next_boundary": d["next_boundary"],
                "next_in_minutes": d["next_in_minutes"], "near": d["near_boundary"],
                "guidance": d["guidance"]}
    except Exception:  # noqa: BLE001
        return None


def workorders():
    files = sorted(glob.glob(str(SEAT / "ops" / "workorder_*.json")))
    if not files:
        return {"latest": None, "count": 0}
    try:
        d = json.loads(pathlib.Path(files[-1]).read_text(encoding="utf-8"))
        return {"latest": pathlib.Path(files[-1]).name, "count": d.get("count", 0)}
    except Exception:  # noqa: BLE001
        return {"latest": None, "count": 0}


def ci_status(no_net):
    if no_net:
        return None
    out, _ = run(["curl.exe", "-s", "-m", "25", "-H", "Accept: application/vnd.github+json",
                  "https://api.github.com/repos/moonhwm/openplanlink-mirror/actions/runs?per_page=4"],
                 timeout=60)
    try:
        d = json.loads(out)
        return [{"name": r["name"], "status": r["status"], "conclusion": r["conclusion"],
                 "head": r["head_sha"][:7]} for r in d.get("workflow_runs", [])]
    except Exception:  # noqa: BLE001
        return "不可用"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--no-net", action="store_true")
    a = ap.parse_args()

    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    data = {"generated_at_utc": ts, "host_ref": host_ref(),
            "seat": "a2a-node-local",
            "ledger": ledger_stats(), "ops": ops_stats(), "repo": repo_three_way(),
            "mcp_live": mcp_live(), "idle": idle_from_snapshot(), "night": night_state(),
            "R_mem": r_mem_block(), "disk": disk_block(),
            "workorders": workorders(), "ci": ci_status(a.no_net)}

    n, r, i = data["night"] or {}, data["repo"], data["idle"] or {}
    rm = data["R_mem"] or {}
    dk = data["disk"] or {}
    L = ["# 主控台一页纸读数（审计就绪）", "",
         "- 生成时刻（UTC）：%s ｜ 主机：%s ｜ 席位：a2a-node-local" % (ts, data["host_ref"]), "",
         "## 一、证据链", "", "| 项 | 读数 | 结论 |", "|---|---|---|",
         "| 台账（sha256 链） | %s 条 | **%s** |" % (data["ledger"]["entries"], "PASS" if data["ledger"]["chain_ok"] else "FAIL"),
         "| 事件链（ops_event） | %s 条 | **%s** |" % (data["ops"]["events"], "PASS" if data["ops"]["chain_ok"] else "FAIL"),
         "| 仓库三面 | local=%s origin=%s gitcode=%s | **%s** |" % (
             r.get("local"), r.get("origin"), r.get("gitcode"), "一致" if r.get("aligned") else "不一致"),
         "| 工单 | %s（%s 张） | 候安全运营中心指派 |" % (
             data["workorders"]["latest"], data["workorders"]["count"]),
         "", "## 二、运行面", "", "| 项 | 读数 |", "|---|---|",
         "| MCP 在线通道 | %s |" % ("、".join(data["mcp_live"]) or "无"),
         "| 闲置系数（最近快照 %s） | CPU 空闲 %s%% ／ 空闲内存 %s%% ／ 进程 %s |" % (
             i.get("at"), i.get("cpu_idle_pct"), i.get("mem_idle_pct"), i.get("processes")),
         "| **R_mem（第四必填项）** | **%s MB**（%s）｜ 来源 %s |" % (
             rm.get("R_mem_mb"), rm.get("state", "—"), rm.get("source") or "无体检件"),
         "| **磁盘水位（DF-MEM 阈值）** | C 可用 %s GB（%s）｜ A 可用 %s GB（%s） |" % (
             (dk.get("disks") or {}).get("C", {}).get("free_gb") if dk.get("disks") else None, dk.get("c_level"),
             (dk.get("disks") or {}).get("A", {}).get("free_gb") if dk.get("disks") else None, dk.get("a_level")),
         "| 夜间窗口 | %s；距边界 %s 分钟 |" % (
             ("**在窗口内**" if n.get("in_window") else "窗口外"), n.get("next_in_minutes")),
         "| 处置指引 | %s |" % n.get("guidance"), ""]
    if data["ci"]:
        L += ["## 三、CI/CD（最近 4 次）", "", "| 工作流 | 状态 | 结论 | 提交 |", "|---|---|---|---|"]
        if isinstance(data["ci"], list):
            for c in data["ci"]:
                L.append("| %s | %s | %s | %s |" % (c["name"], c["status"], c["conclusion"], c["head"]))
        else:
            L.append("| — | — | %s | — |" % data["ci"])
        L.append("")
    L += ["## 四、声明", "",
          "- 本页为**只读聚合**：不改台账、不写仓库、不动进程；各读数均可在本席工作区复算。",
          "- 取不到的项标 `None`／「不可用」，**不估算**。",
          "- 「主控台」汇聚方式与留存周期属跨席/主权人裁定事项；本页为**可汇聚的最小单元**。", ""]

    text = "\n".join(L) + "\n"
    print(text)
    if a.out_dir:
        d = pathlib.Path(a.out_dir)
        d.mkdir(parents=True, exist_ok=True)
        (d / ("console_%s.md" % ts)).write_text(text, encoding="utf-8")
        (d / ("console_%s.json" % ts)).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                                                  encoding="utf-8")
        print("已写出：%s（md+json）" % d)
    return 0 if (data["ledger"]["chain_ok"] and data["ops"]["chain_ok"]) else 1


if __name__ == "__main__":
    sys.exit(main())
