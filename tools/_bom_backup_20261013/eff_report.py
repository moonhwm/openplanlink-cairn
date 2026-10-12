# -*- coding: utf-8 -*-
"""使用效能报告自动生成器（一页纸指标 + 改进项）

依据：守藏席 DF-EFF-20261006-SHOUCANG-01 §九（每次工作汇报须强制附效能报告）
      本席 DF-EFF-20261006-CAIRN-01 §八-1（固化为 tools/eff_report.py）
纪律：只取已实测数据；取不到的项如实标「未测」，绝不估算。

用法:
  python eff_report.py                      # 打印到标准输出
  python eff_report.py --out <路径>          # 同时写文件
  python eff_report.py --since 2026-10-06T03:00   # 统计该时刻后的交换区增量
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import urllib.request

SEAT = r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928"
EXCHANGE = r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A共同体_共享交换区"
REPO = r"C:\Users\欧阳宏俊\openplanlink-mirror"
PLUGINS = r"C:\Users\欧阳宏俊\.dsh\profiles\desktop\plugins"
NODE_HEALTH = "http://127.0.0.1:4173/health"
BUS_ENDPOINTS = [
    "http://120.46.86.165/functions/v1/app",
    "https://openplanlink-a2a-6qbiqa76687.qoder.website/functions/v1/app",
]
# 各通道工具数以 probe_mcp.mjs / probe_one.mjs 实测值登记（唯一真源）
CHANNEL_TOOLS = {"ima": 17, "baidu": 27, "wps": 4, "supabase": 19, "neon": 20}


def run(cmd, cwd=None):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=120,
                           encoding="utf-8", errors="replace")
        return (p.stdout or "").strip(), p.returncode
    except Exception as exc:  # noqa: BLE001
        return "ERR:%s" % exc, 1


def http_code(url, timeout=12):
    """只读连通性探测；HTTPS 证书不可验时回落为不校验证书（仅用于探针，不传数据）。"""
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as exc:  # noqa: BLE001
        return "ERR(%s)" % type(exc).__name__


def ledger_stats():
    out, _ = run([sys.executable, os.path.join(SEAT, "ledger", "cairn_ledger.py"), "verify"])
    n = re.search(r"条目数[：:]\s*(\d+)", out)
    ok = "PASS" in out
    return {"entries": int(n.group(1)) if n else None, "chain_ok": ok}


def mcp_stats():
    ps = ("Get-CimInstance Win32_Process -Filter \"Name='node.exe'\" | "
          "Where-Object { $_.CommandLine -like '*launch.mjs*' } | "
          "ForEach-Object { if ($_.CommandLine -match 'launch\\.mjs\"?\\s+(\\w+)') { $Matches[1] } }")
    out, _ = run(["powershell", "-NoProfile", "-Command", ps])
    live = [x for x in out.split() if x]
    installed = []
    if os.path.isdir(PLUGINS):
        installed = sorted(d for d in os.listdir(PLUGINS) if d.startswith("dsh-plugin-"))
    total = sum(CHANNEL_TOOLS.values())
    online = sum(CHANNEL_TOOLS.get(x, 0) for x in live)
    return {"live": live, "installed": installed, "total_tools": total,
            "online_tools": online,
            "tool_ratio": (online / total) if total else 0.0,
            "channel_ratio": (len(live) / len(CHANNEL_TOOLS)) if CHANNEL_TOOLS else 0.0}


def repo_stats():
    head, _ = run(["git", "log", "-1", "--format=%h %s"], cwd=REPO)
    origin, _ = run(["git", "log", "-1", "--format=%h", "origin/main"], cwd=REPO)
    gitcode, code = run(["git", "log", "-1", "--format=%h", "gitcode/main"], cwd=REPO)
    dirty, _ = run(["git", "status", "--porcelain"], cwd=REPO)
    return {"head": head, "origin": origin,
            "gitcode": gitcode if code == 0 else None,
            "aligned": bool(origin) and origin == (gitcode if code == 0 else None),
            "dirty": len([l for l in dirty.splitlines() if l.strip()])}


def dir_stats(path, suffixes=None):
    files = []
    for root, _dirs, names in os.walk(path):
        for n in names:
            if suffixes and not n.lower().endswith(suffixes):
                continue
            files.append(os.path.join(root, n))
    return files


def exchange_stats(since=None):
    files = dir_stats(EXCHANGE)
    newest = sorted(files, key=lambda p: os.path.getmtime(p), reverse=True)[:3]
    delta = None
    if since:
        t0 = dt.datetime.fromisoformat(since).timestamp()
        delta = len([p for p in files if os.path.getmtime(p) >= t0])
    return {"total": len(files), "newest": newest, "delta": delta}


def archive_stats():
    files = dir_stats(os.path.join(SEAT, "archive"), suffixes=(".otl",))
    return len(files)


def baseline_stats():
    """读本地算力基线（exp/cpu_baseline.py 产出）。"""
    p = os.path.join(SEAT, "outbox", "cpu-baseline-local.json")
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except Exception:  # noqa: BLE001
            return None
    return None


def r_mem_stats():
    """R_mem（内存风险量·必填第四项，HY4 裁决第4条/C-24）：取最近 mem_audit 体检件的 R_mem 块。
    缺件则如实标 None（不臆造）；口径规范层权威属 cpu-squeeze-c1 席。"""
    d = os.path.join(SEAT, "outbox", "mem")
    if not os.path.isdir(d):
        return None
    files = sorted(x for x in os.listdir(d) if x.startswith("mem_audit_") and x.endswith(".json"))
    if not files:
        return None
    try:
        with open(os.path.join(d, files[-1]), encoding="utf-8") as f:
            r = json.load(f).get("R_mem") or {}
        r["source"] = files[-1]
        return r
    except Exception:  # noqa: BLE001
        return None


def cloud_run_stats():
    """读外延算力池回传件（约定名 hw-x-run-*.json；本席只读，不接触账务凭据）。"""
    out = []
    d = os.path.join(SEAT, "outbox")
    if not os.path.isdir(d):
        return out
    for n in sorted(os.listdir(d)):
        if n.startswith("hw-x-run-") and n.endswith(".json"):
            try:
                with open(os.path.join(d, n), encoding="utf-8") as f:
                    out.append(json.load(f))
            except Exception:  # noqa: BLE001
                continue
    return out


def cost_block():
    """固定成本记账（承 DF-START5 §四 丙/戊）：调用 cost_ledger，取回其表格文本。
    取不到即如实标注（不臆造数字）。"""
    for cand in (os.path.join(os.path.dirname(os.path.abspath(__file__)), "cost_ledger.py"),
                 os.path.join(SEAT, "exp", "cost_ledger.py")):
        if os.path.exists(cand):
            o, c = run([sys.executable, cand, "--hours", "6"], cwd=os.path.dirname(cand))
            if c == 0 and o.strip():
                return o.strip()
    return "（cost_ledger.py 未就位或执行失败 → 本块**未测**）"


def mem_block():
    """记忆分层盘点（承 DF-MEM）：调用 mem_tier_scan，取其 JSON 摘要以渲染紧凑表。
    取不到即如实标"未测"。**只读**：本块不触发任何移动/删除。"""
    import tempfile
    for cand in (os.path.join(os.path.dirname(os.path.abspath(__file__)), "mem_tier_scan.py"),
                 os.path.join(SEAT, "exp", "mem_tier_scan.py")):
        if not os.path.exists(cand):
            continue
        with tempfile.TemporaryDirectory() as td:
            jp = os.path.join(td, "tier.json")
            _o, c = run([sys.executable, cand, "--json", jp], cwd=os.path.dirname(cand))
            if c == 0 and os.path.exists(jp):
                try:
                    with open(jp, encoding="utf-8") as f:
                        return json.load(f)
                except Exception:  # noqa: BLE001
                    return None
    return None



def mem_guard_stats():
    """R_mem 破线期失败/重试计数（承 DF-ACK-20261007-CAIRN-06 §四）。取不到即标未测。"""
    cand = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mem_guard.py")
    if not os.path.exists(cand):
        return "（mem_guard.py 未就位 → 本块**未测**）"
    o, c = run([sys.executable, cand, "stats"], cwd=os.path.dirname(cand))
    return o.strip() if (c == 0 and o.strip()) else "（mem_guard stats 执行失败 → 本块**未测**）"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--since")
    a = ap.parse_args()
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    led = ledger_stats()
    mcp = mcp_stats()
    repo = repo_stats()
    ex = exchange_stats(a.since)
    arch = archive_stats()
    baseline = baseline_stats()
    r_mem = r_mem_stats()
    cloud_runs = cloud_run_stats()
    node = http_code(NODE_HEALTH, timeout=6)
    bus = [(u, http_code(u)) for u in BUS_ENDPOINTS]
    cost = cost_block()
    mem = mem_block()

    L = []
    L.append("# A2A新席·石敢当Cairn · 使用效能报告（自动生成）")
    L.append("")
    L.append("- 生成时刻：%s（+08）" % now)
    L.append("- 生成器：`exp/eff_report.py`（零依赖，取值皆实测；取不到即标未测）")
    L.append("- 准则依据：守藏席 DF-EFF-20261006-SHOUCANG-01 §九 ／ 本席 DF-EFF-20261006-CAIRN-01 §八")
    L.append("")
    L.append("## 一、产出与资产")
    L.append("")
    L.append("| 项 | 实测 |")
    L.append("|---|---|")
    if r_mem:
        L.append("| **R_mem（内存风险量·必填第四项）** | **%s MB**（%s）｜ 已击穿 %s ｜ 来源 %s |" % (
            r_mem.get("R_mem_mb"), r_mem.get("state", "—"),
            "、".join(r_mem.get("breached") or []) or "无", r_mem.get("source")))
    else:
        L.append("| **R_mem（内存风险量·必填第四项）** | 未测（无体检件） |")
    L.append("| 插件包（bundle） | %d 件：%s |" % (len(mcp["installed"]), "、".join(mcp["installed"]) or "无"))
    L.append("| 工具装配 / 在线 | **%d / %d**（可用率 %.1f%%） |" % (
        mcp["online_tools"], mcp["total_tools"], mcp["tool_ratio"] * 100))
    L.append("| 已连通通道 | %s（%d/%d） |" % (
        "、".join(mcp["live"]) or "无", len(mcp["live"]), len(CHANNEL_TOOLS)))
    L.append("| 台账条目 | %s 条，链内自洽 %s |" % (
        led["entries"], "PASS" if led["chain_ok"] else "FAIL"))
    L.append("| 归档 .otl | %d 件 |" % arch)
    L.append("| 交换区文件 | %d 件%s |" % (ex["total"],
              ("；指定区间新增 %d 件" % ex["delta"]) if ex["delta"] is not None else ""))
    L.append("")
    L.append("## 二、同步与合规")
    L.append("")
    L.append("| 项 | 实测 |")
    L.append("|---|---|")
    L.append("| 镜像仓 HEAD | `%s` |" % repo["head"])
    L.append("| 双远端一致 | origin=`%s` / gitcode=`%s` → **%s** |" % (
        repo["origin"], repo["gitcode"], "一致" if repo["aligned"] else "不一致"))
    L.append("| 工作树未提交变更 | %d |" % repo["dirty"])
    L.append("| 凭据回显 | 0（生成器不读凭据值，仅统计连通性） |")
    L.append("")
    L.append("## 三、在线面")
    L.append("")
    L.append("| 端 | 实测 |")
    L.append("|---|---|")
    L.append("| A2A 节点健康 | HTTP %s |" % node)
    for u, c in bus:
        L.append("| 总线 %s | HTTP %s |" % (u, c))
    L.append("")
    L.append("## 四、外延算力（本地基线 / 云端对比）")
    L.append("")
    L.append("| 项 | 实测 |")
    L.append("|---|---|")
    if baseline:
        L.append("| 本地基线（SHA3-512 聚合吞吐） | **%.2f MB/s** |" % baseline.get("aggregate_mbps", 0))
        L.append("| 本地并行效率 | %.1f%% |" % (baseline.get("parallel_efficiency", 0) * 100))
        L.append("| 本地稳定性（分段 CV） | %s |" % baseline.get("segment_cv", "—"))
        L.append("| 基线测量时刻 | %s |" % baseline.get("measured_at", "—"))
    else:
        L.append("| 本地基线 | **未测**（运行 `exp/cpu_baseline.py` 生成） |")
    if cloud_runs:
        for c in cloud_runs:
            ratio = (c.get("aggregate_mbps", 0) / baseline["aggregate_mbps"]
                     if baseline and baseline.get("aggregate_mbps") else None)
            L.append("| 云端 %s | 聚合 %.2f MB/s；并行效率 %s；有效占比 %s；同口径比 %s |" % (
                c.get("run_id", "?"), c.get("aggregate_mbps", 0),
                c.get("parallel_efficiency", "—"),
                c.get("active_ratio", "—"),
                ("%.2f×" % ratio) if ratio else "—"))
    else:
        L.append("| 云端对比 | **待凭据**（无 `hw-x-run-*.json`；见 DF-HWX-20261006-CAIRN-02） |")
    L.append("")
    L.append("> 判据：同口径比 ≥ 1.0 且并行效率 ≥ 90%%、有效占比 ≥ 85%% 方视为「榨取有效」；触线即按排期熔断回退。")
    L.append("")
    L.append("## 五、最近来件（交换区）")
    L.append("")
    for p in ex["newest"]:
        L.append("- %s  %s" % (dt.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%m-%d %H:%M"),
                               os.path.basename(p)))
    L.append("")
    L.append("## 五·二、固定成本记账（承 DF-START5 §四 丙/戊：隐性成本显式化 + 给上界）")
    L.append("")
    L.append("> 口径：重签＝窗口内 re-sign 提交数 × 实测单次耗时；提交＝窗口内提交数 × 保守守卫估值；扫描＝显式传入次数 × 实测全仓扫描耗时。")
    L.append("")
    for _ln in cost.splitlines():
        L.append(_ln)
    L.append("")
    L.append("## 五·三、记忆分层盘点（承 DF-MEM：数据生命周期管理；只读）")
    L.append("")
    if mem:
        L.append("- 采样时点：%s ｜ 口径：只读（不移动/删除/改名）｜ 层级用语：`层-*`（承 DF-ALIGN 甲案）" % mem.get("sampled_at", "?"))
        L.append("")
        L.append("| 层 | 文件数 | 字节 |")
        L.append("|---|---|---|")
        for k in ("层-热", "层-温", "层-冷", "层-未分"):
            v = (mem.get("tiers") or {}).get(k)
            if v:
                L.append("| %s | %d | %.2f MB |" % (k, v["n"], v["bytes"] / 1048576.0))
        L.append("")
        L.append("- **冷层占比：%.1f%%**（阈值 >70%% ⇒ 优先冷化/归档%s）"
                 % (mem.get("cold_share_pct", 0.0), "，**已越阈**" if mem.get("cold_share_pct", 0) > 70 else ""))
        L.append("- 重复内容：**%d 组**、可回收 **%.2f MB**（哈希确认；处置**候批**）"
                 % (mem.get("dup_groups", 0), mem.get("dup_wasted_bytes", 0) / 1048576.0))
    else:
        L.append("（mem_tier_scan.py 未就位或执行失败 → 本块**未测**）")
    L.append("")
    L.append("## 五·四、R_mem 破线期运行统计（承 DF-ACK-06 §四：资源性受阻须计数，非仅观察）")
    L.append("")
    for _ln in mem_guard_stats().splitlines():
        L.append(_ln)
    L.append("")
    L.append("## 六、改进项（自动推断）")
    L.append("")
    tips = []
    if mcp["tool_ratio"] < 1.0:
        miss = [k for k in CHANNEL_TOOLS if k not in mcp["live"]]
        tips.append("工具可用率未达 100%%，缺口通道：%s —— 释放条件：OS 级注入对应凭据后重启一次 DSH。" % "、".join(miss))
    else:
        tips.append("工具可用率 100%，维持。")
    if not repo["aligned"]:
        tips.append("双远端不一致 —— 先复读一次（origin/main 与 gitcode/main）：若刚执行过 push_gate，"
                    "可能是双推在途的**瞬时假象**；复读仍不一致再执行 `python tools/push_gate.py` 对齐。")
    else:
        tips.append("双远端一致，维持；禁 force、每次改后重建树证。")
    if repo["dirty"]:
        tips.append("工作树有 %d 处未提交 —— 先 `git add`＋`commit` 再过闸（否则未跟踪文件会被清理）。" % repo["dirty"])
    tips.append("凡「需要重启」之假设，先证伪再行动（本席历史教训：重启路线 0/5）。")
    for i, t in enumerate(tips, 1):
        L.append("%d. %s" % (i, t))
    L.append("")
    L.append("—— 自动生成，未测项不列；数据可在本席工作区复算。")

    text = "\n".join(L) + "\n"
    if a.out:
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(text)
        print("已写出：%s（%d 字节）" % (a.out, len(text.encode("utf-8"))))
    else:
        print(text)


if __name__ == "__main__":
    main()
