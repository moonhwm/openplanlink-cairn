# -*- coding: utf-8 -*-
"""lsprobe.py —— **Linux `ls` 环境监测探针**（承令条「自主执行 Linux ls 命令，持续监测运行环境」）

本机为 Windows，但 **Git 自带 `ls.exe`**（C:\\Program Files\\Git\\usr\\bin\\ls.exe）⇒ 可执行**真 Linux `ls` 语义**。
本器：对**固定目录集**跑标准化 `ls`，**只提取计数与体量**（不回显敏感文件名），追加至
`outbox/mem/ls_probe.jsonl`（含 prev 哈希链），供：
  · **持续监测运行环境**（逐轮可比）
  · **记忆分层"两周滚动验证"之基线**（承令条「以两周为周期滚动验证收益」）

用法：
    python lsprobe.py --run             # 采集一次并落账
    python lsprobe.py --history         # 打印历史（含与上次之差）
    python lsprobe.py --baseline        # 打印首条作基线，并给出下一检查点（+14 天）
纪律：**只读**；`ls` 失败即标「未测」；**不臆造**。
"""
import argparse
import datetime as dt
import hashlib
import json
import pathlib
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
SEAT = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928")
REPO = pathlib.Path(r"C:\Users\欧阳宏俊\openplanlink-mirror")
UPLOAD = pathlib.Path(r"A:\upload")
LOG = SEAT / "outbox" / "mem" / "ls_probe.jsonl"
LS_CANDIDATES = [r"C:\Program Files\Git\usr\bin\ls.exe", r"C:\Program Files (x86)\Git\usr\bin\ls.exe"]


def ls_exe():
    for c in LS_CANDIDATES:
        if pathlib.Path(c).exists():
            return c
    return None


def probe_dir(exe, d):
    """跑 ls -la 取**计数与体量**（不逐名回显）。"""
    if not d.exists():
        return {"dir": str(d), "exists": False}
    p = subprocess.run([exe, "-la", str(d)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if p.returncode != 0:
        return {"dir": str(d), "exists": True, "ls": "未测"}
    lines = [x for x in (p.stdout or "").splitlines() if x.strip()]
    files = dirs = 0
    total_bytes = 0
    for ln in lines[1:]:
        parts = ln.split(None, 8)
        if len(parts) < 9:
            continue
        mode, size = parts[0], parts[4]
        name = parts[8]
        if name in (".", ".."):
            continue
        if mode.startswith("d"):
            dirs += 1
        else:
            files += 1
            try:
                total_bytes += int(size)
            except ValueError:
                pass
    return {"dir": str(d), "exists": True, "entries": files + dirs,
            "files": files, "dirs": dirs, "bytes": total_bytes, "ls_lines": len(lines)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--history", action="store_true")
    ap.add_argument("--baseline", action="store_true")
    a = ap.parse_args()
    exe = ls_exe()
    if not exe:
        print("★ `ls` 不可用 ⇒ **未测**（不得以 dir 冒充 Linux ls）")
        return 1
    targets = [SEAT, SEAT / "exp", SEAT / "archive", SEAT / "outbox", REPO, UPLOAD, UPLOAD / "cairn-cache"]

    if a.history or a.baseline:
        rows = []
        if LOG.exists():
            for ln in LOG.read_text(encoding="utf-8", errors="replace").splitlines():
                if ln.strip():
                    try:
                        rows.append(json.loads(ln))
                    except Exception:  # noqa: BLE001
                        pass
        if not rows:
            print("★ 无历史记录")
            return 0
        if a.baseline:
            first = rows[0]
            t = dt.datetime.strptime(first["ts"], "%Y-%m-%d %H:%M:%S +08")
            print("★ 基线（%s）：%d 个目录" % (first["ts"], len(first["probes"])))
            for pr in first["probes"]:
                if pr.get("exists"):
                    print("   %-70s 条目=%-5s 文件=%-5s 目录=%-4s 体量=%.2f MB"
                          % (pr["dir"][-70:], pr.get("entries"), pr.get("files"), pr.get("dirs"),
                             (pr.get("bytes") or 0) / 1048576.0))
            print("  ⇒ **下一检查点（+14 天）**：%s（承令条「以两周为周期滚动验证」）"
                  % (t + dt.timedelta(days=14)).strftime("%Y-%m-%d"))
            return 0
        print("★ 历史 %d 条：" % len(rows))
        prev = None
        for r in rows:
            tag = ""
            if prev:
                d1 = sum((p.get("bytes") or 0) for p in prev["probes"])
                d2 = sum((p.get("bytes") or 0) for p in r["probes"])
                tag = " ｜ Δ体量=%.2f MB" % ((d2 - d1) / 1048576.0)
            print("   %s ｜ 目录 %d%s" % (r["ts"], len(r["probes"]), tag))
            prev = r
        return 0

    probes = [probe_dir(exe, d) for d in targets]
    prev = ""
    if LOG.exists():
        lines = [x for x in LOG.read_text(encoding="utf-8", errors="replace").splitlines() if x.strip()]
        if lines:
            prev = hashlib.sha256(lines[-1].encode()).hexdigest()[:16]
    rec = {"ts": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S +08"), "ls_exe": exe,
           "probes": probes, "prev": prev,
           "r_mem_mb": round(int(subprocess.run(
               ["powershell", "-NoProfile", "-Command",
                "(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory"],
               capture_output=True, text=True).stdout.strip() or 0) / 1024.0, 1)}
    LOG.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(rec, ensure_ascii=False)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print("★ ls 环境快照（%s）｜ ls=%s ｜ R_mem=%.1f MB" % (rec["ts"], pathlib.Path(exe).name, rec["r_mem_mb"]))
    for pr in probes:
        if pr.get("exists"):
            print("   %-64s 条目=%-5s 文件=%-5s 目录=%-4s 体量=%.2f MB"
                  % (pr["dir"][-64:], pr.get("entries"), pr.get("files"), pr.get("dirs"),
                     (pr.get("bytes") or 0) / 1048576.0))
        else:
            print("   %-64s **不存在**" % pr["dir"][-64:])
    print("  留痕 prev=%s ⇒ %s" % (prev or "（首条）", LOG))
    return 0


if __name__ == "__main__":
    sys.exit(main())
