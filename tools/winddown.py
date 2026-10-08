# -*- coding: utf-8 -*-
"""winddown.py —— 夜间窗「预警哨 / 冻结线 / 解冻复查」之落盘机制
（承他席《夜间运维时段细则（商榷稿）》OTL-20261006-02 §三 条款 2–4；令条「临近该时段时妥善终止规划并执行落盘」）

条款对照：
    2. **22:45 预警哨**：停止新规划、在途状态落盘（写入 `esc.winddown`，含在飞清单与断点）
    3. **23:00 冻结线**：禁新阵点火，仅收尾与守护
    4. **08:00 解冻复查**：对照落盘清单逐项恢复，缺项如实登记

本器：
    --record    采集**在途状态清单**（在飞项＋断点哈希）→ 写 `outbox/mem/winddown_<UTC>.json` ＋ 记 `esc.winddown` 事件
    --review    对照最近一次落盘清单**逐项复查**当前状态 → 记 `esc.resume` 事件，**缺项如实列出**
    --dry       仅打印将要记录之清单（不写文件、不记事件）
纪律：**只读采集**；**不移动/不删除**任何文件；**不回显凭据**；取不到即标「未测」。
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
OUTDIR = SEAT / "outbox" / "mem"


def sha16(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()[:16]


def in_flight():
    """采集在途项：a) 台账末条 b) 事件链末条 c) 仓未提交改动 d) 本席 outbox 未定稿产物 e) 未推送提交"""
    items = {}
    led = SEAT / "ledger" / "frontier_ledger.jsonl"
    items["ledger_last"] = "未测"
    if led.exists():
        try:
            last = [l for l in led.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()][-1]
            items["ledger_last"] = {"sha16": hashlib.sha256(last.encode()).hexdigest()[:16],
                                    "n_bytes": len(last)}
        except Exception:  # noqa: BLE001
            items["ledger_last"] = "未测"
    ev = SEAT / "ops" / "ops_event.jsonl"
    items["event_chain"] = "未测"
    if ev.exists():
        try:
            lines = [l for l in ev.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]
            items["event_chain"] = {"n": len(lines),
                                    "last_sha16": hashlib.sha256(lines[-1].encode()).hexdigest()[:16]}
        except Exception:  # noqa: BLE001
            items["event_chain"] = "未测"
    try:
        dirty = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain"],
                               capture_output=True, text=True, encoding="utf-8", errors="replace",
                               timeout=120).stdout.strip()
        ahead = subprocess.run(["git", "-C", str(REPO), "log", "--oneline", "origin/main..HEAD"],
                               capture_output=True, text=True, encoding="utf-8", errors="replace",
                               timeout=120).stdout.strip()
        items["repo"] = {"dirty_lines": len([x for x in dirty.splitlines() if x.strip()]),
                         "unpushed_commits": len([x for x in ahead.splitlines() if x.strip()])}
    except Exception:  # noqa: BLE001
        items["repo"] = "未测"
    pend = []
    for pat in ("outbox/mem/*.json", "outbox/eff/*.md"):
        for p in SEAT.glob(pat):
            try:
                pend.append({"file": str(p.relative_to(SEAT)), "sha16": sha16(p),
                             "mtime": dt.datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")})
            except OSError:
                continue
    items["pending_artifacts"] = pend[:20]
    return items


def log_event(action, target, result, evidence):
    src = SEAT / "exp" / "ops_event.py"
    if not src.exists():
        return "（ops_event.py 未就位 ⇒ 事件未记）"
    p = subprocess.run([sys.executable, str(src), "log", "--action", action, "--target", target,
                        "--result", result, "--evidence", evidence],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (p.stdout or p.stderr or "").strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", action="store_true")
    ap.add_argument("--review", action="store_true")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S +08")
    items = in_flight()
    if a.dry or not (a.record or a.review):
        print("★ 在途状态清单（dry；%s）" % ts)
        print(json.dumps(items, ensure_ascii=False, indent=1)[:2000])
        return 0
    if a.record:
        OUTDIR.mkdir(parents=True, exist_ok=True)
        out = OUTDIR / ("winddown_%s.json" % dt.datetime.now().strftime("%Y%m%dT%H%M%SZ"))
        rec = {"kind": "esc.winddown", "ts": ts, "window": "23:00-08:00(+08)",
               "in_flight": items, "note": "预警哨落盘：在飞清单与断点（承 OTL-20261006-02 §三-2）"}
        out.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        r = log_event("esc.winddown", "night-window", "recorded:%s" % out.name,
                      "in_flight keys=%s" % ",".join(items.keys()))
        print("★ 已落盘：%s（%d B）" % (out.name, out.stat().st_size))
        print("  事件：%s" % r)
        return 0
    if a.review:
        cands = sorted(OUTDIR.glob("winddown_*.json"))
        if not cands:
            print("★ 无落盘清单可供复查 ⇒ **未测**（不得据此判「无缺项」）")
            return 1
        prev = json.loads(cands[-1].read_text(encoding="utf-8"))
        pi = prev.get("in_flight", {})
        diffs = []
        cur = items
        for k in ("ledger_last", "event_chain", "repo"):
            if k in pi and k in cur and pi[k] != cur[k]:
                diffs.append({"item": k, "was": pi[k], "now": cur.get(k)})
        missing = [x for x in (pi.get("pending_artifacts") or [])
                   if x.get("file") not in {y.get("file") for y in (cur.get("pending_artifacts") or [])}]
        r = log_event("esc.resume", "night-window", "reviewed:%s" % cands[-1].name,
                      "changed=%d missing=%d" % (len(diffs), len(missing)))
        print("★ 解冻复查（对照 %s）" % cands[-1].name)
        print("  变动项 %d：%s" % (len(diffs), ", ".join(d["item"] for d in diffs) or "—"))
        print("  **缺项 %d**：%s" % (len(missing), ", ".join(m["file"] for m in missing) or "—"))
        print("  事件：%s" % r)
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
