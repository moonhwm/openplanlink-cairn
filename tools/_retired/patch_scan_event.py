# -*- coding: utf-8 -*-
"""patch_scan_event.py —— ①disclosure_scan 全仓扫描后自动记事件 ②cost_ledger 自动读事件计次

闭环目标（承 DF-START5 §四 丙/戊）：
  扫描（贵）→ 自动入事件链 → 成本记账自动计次 → 效能报告自动显示上界
"""
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8")
SEAT = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928")

# ── ① 扫描器：全仓扫描后记事件 ──
f = SEAT / "exp" / "disclosure_scan.py"
t = f.read_text(encoding="utf-8")
if "def log_scan_event(" not in t:
    helper = '''

def log_scan_event(scope, hits):
    """全仓扫描后**自动记事件**（供成本记账自动计次）。仅在全仓模式调用；失败不影响扫描结果。"""
    try:
        import json as _j
        import subprocess as _sp
        _sp.run([sys.executable, str(pathlib.Path(__file__).with_name("ops_event.py")), "log",
                 "--action", "disclosure.scan", "--target", str(scope),
                 "--result", "hits=%d" % hits],
                capture_output=True, timeout=30)
    except Exception:  # noqa: BLE001
        pass
'''
    idx = t.find("\ndef main(")
    if idx > 0:
        t = t[:idx] + helper + t[idx:]
        f.write_text(t, encoding="utf-8")
        print("① 已注入 log_scan_event()")
    else:
        print("① 锚点 def main( 未找到")
else:
    print("① 已存在")

# 在全仓扫描的输出处调用（识别 report-only/全仓分支的收尾）
t = f.read_text(encoding="utf-8")
if "log_scan_event(" in t and "log_scan_event(scope" not in t:
    for anchor in ('print("处置提示：', 'print("VERDICT=', 'return 1 if (net or cred) else 0'):
        if anchor in t:
            ins = "    log_scan_event(\"full-repo\", len(rows) if 'rows' in dir() else 0)\n"
            t = t.replace(anchor, ins + anchor, 1)
            f.write_text(t, encoding="utf-8")
            print("① 已在收尾处插入调用（锚点 %s）" % anchor[:18])
            break
    else:
        print("① 收尾锚点未命中（手工确认）")

# ── ② 记账器：自动读事件计次 ──
g = SEAT / "exp" / "cost_ledger.py"
s = g.read_text(encoding="utf-8")
if "def scan_count_from_events(" not in s:
    fn = '''

def scan_count_from_events(hours):
    """从事件链 ops/ops_event.jsonl 统计窗口内 disclosure.scan 次数（自动计次，替占位值）。"""
    import json as _j
    import datetime as _dt
    p = pathlib.Path(r"C:\\Users\\欧阳宏俊\\WPSDrive\\29969771\\WPS云盘\\月之暗面的Plasma游乐场\\A2A新席_石敢当Cairn_20260928\\ops\\ops_event.jsonl")
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
'''
    idx = s.find("\ndef main(")
    s = s[:idx] + fn + s[idx:]
    s = s.replace('    ap.add_argument("--scans", type=int, default=0, help="窗口内全仓扫描次数（显式传入）")',
                  '    ap.add_argument("--scans", type=int, default=-1, help="窗口内全仓扫描次数；-1=自动读事件链")')
    s = s.replace("    out, _ = git([\"log\", \"--since=%g hours ago\" % a.hours, \"--format=%H|%s\"])",
                  "    scans = scan_count_from_events(a.hours) if a.scans < 0 else a.scans\n"
                  "    scans_src = \"自动(事件链)\" if a.scans < 0 else \"显式传入\"\n"
                  "    if scans is None:\n        scans = 0\n        scans_src = \"未测(事件链不可读)\"\n"
                  "    out, _ = git([\"log\", \"--since=%g hours ago\" % a.hours, \"--format=%H|%s\"])")
    s = s.replace("    scan_cost = a.scans * SCAN_SEC", "    scan_cost = scans * SCAN_SEC")
    s = s.replace('print("| 全仓披露扫描 | %d | %.1fs（实测） | %.1fs |" % (a.scans, SCAN_SEC, scan_cost))',
                  'print("| 全仓披露扫描 | %d（%s） | %.1fs（实测） | %.1fs |" % (scans, scans_src, SCAN_SEC, scan_cost))')
    g.write_text(s, encoding="utf-8")
    print("② 已改造 cost_ledger（自动读事件计次）")
else:
    print("② 已存在")
