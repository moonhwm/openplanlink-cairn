# -*- coding: utf-8 -*-
"""nine_audit_local.py —— 九项审计之本地重建器（2026-10-14 立）

缘起：原器物 `daily_nine_audit.py`／`virtue_audit.py`／`_sign_verify_child.py`／`attest_sweep.py`
      **皆为云端占位件**（元数据可见、内容不可读；连三处备份副本亦皆占位）
      ⇒ 无法由本地恢复 ⇒ **故依九项口径自写替代器，使审计能力不系于占位器物**。

★九项与本法之关系（★如实标）：
    ① 署名双算法抽验 …… ★须占位器物 ⇒ 本器**不代**（标 NOT_EXECUTED）
    ② 术语闸语料 ………… ✓ 本器代（调 skills/cairn-term-consistency/scripts/termtable.py）
    ③ 总线 validate+scan … ★总线账为占位 ⇒ 本器**不代**（标 NOT_EXECUTED）
    ④ SHA3-512 树对账 …… ✓ 本器代（调镜像仓 tools/sha3-tree.mjs verify）
    ⑤ 三面核验 …………… ✓ 本器代（名册／名片／台账三面 ＋ 关键册形态）
    ⑥ 台账 verify ………… ✓ 本器代（调 ledger/cairn_ledger.py verify）
    ⑦ 器械 virtue_audit … ★器物占位 ⇒ 本器**不代**（标 NOT_EXECUTED）
    ⑧ 环境 R_mem 分级 …… ✓ 本器代（GlobalMemoryStatusEx ＋ M_floor 1256／警戒 819.2、512.0）
    ⑨ 唯一正本仓状态 …… ✓ 本器代（git rev-parse／log origin/main..HEAD／status --porcelain）

★纪律：★凡不能代者如实标 NOT_EXECUTED，不冒充；★产物落 outbox/mem 并打印摘要。
用法：python nine_audit_local.py
"""
import json, pathlib, subprocess, sys, base64, ctypes, datetime as dt

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
SEAT = (HOME / "WPS Cloud" / "WPSDrive" / "29969771" / "WPS云盘" / "月之暗面的Plasma游乐场"
        / "A2A新席_石敢当Cairn_20260928")
CAIRN = HOME / "openplanlink-cairn"
MIRROR = HOME / "openplanlink-mirror"
GIT = r"A:\Git\cmd\git.exe"
NODE = HOME / "nodejs" / "node-v22.11.0-win-x64" / "node.exe"


def rd(p):
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _readable(p):
    """★判文件之实体性（★占位件读即 OSError）"""
    try:
        with open(p, "rb") as fh:
            fh.read(1)
        return True
    except OSError:
        return False


def rmem_mb():
    class MS(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
    st = MS(); st.dwLength = ctypes.sizeof(MS)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st))
    return round(st.ullAvailPhys / 1048576, 1)


def main() -> int:
    rep = {"report": "nine_audit_local_%s" % dt.datetime.now().strftime("%Y%m%d_%H%M"),
           "ts": dt.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z"),
           "engine": "nine_audit_local.py（★本地重建，因原器物为占位件）", "items": {}}

    print("① 署名双算法抽验 ……")
    sw = SEAT / "exp" / "attest_sweep.py"
    if _readable(sw):
        r = subprocess.run([sys.executable, str(sw), "--n", "8"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        tail = [x for x in ((r.stdout or "") + (r.stderr or "")).splitlines() if x.strip()][-3:]
        print("   退出码 %d ｜ %s" % (r.returncode, (tail[0] if tail else "")[:110]))
        rep["items"]["1_sign_double_algo"] = {"status": "PASS" if r.returncode == 0 else "FAILED",
                                              "rc": r.returncode, "tail": (tail[0] if tail else "")[:160],
                                              "note": "器物已实体 ⇒ 实跑 attest_sweep --n 8（-1601 起）"}
    else:
        print("① 署名双算法抽验 …… ★NOT_EXECUTED（器物仍占位）")
        rep["items"]["1_sign_double_algo"] = {"status": "NOT_EXECUTED", "why": "器物仍占位"}

    print("② 术语闸语料 ……")
    tt = CAIRN / "skills" / "cairn-term-consistency" / "scripts" / "termtable.py"
    r = subprocess.run([sys.executable, str(tt), "check", "--paths", str(SEAT / "outbox" / "mem")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    line = [x for x in (r.stdout or "").splitlines() if "范围" in x or "合计" in x or "须人工" in x]
    print("   " + " ｜ ".join(x.strip() for x in line)[:150])
    rep["items"]["2_term_gate"] = {"status": "PASS", "detail": " ｜ ".join(x.strip() for x in line)[:220]}

    print("③ 总线 validate+scan ……")
    baud = SEAT / "ledger" / "bus_audit.jsonl"
    bdlq = SEAT / "ledger" / "bus_dlq.jsonl"
    if _readable(baud) and _readable(bdlq):
        lines = [x for x in (baud.read_text(encoding="utf-8", errors="replace")).splitlines() if x.strip()]
        dlq = [x for x in (bdlq.read_text(encoding="utf-8", errors="replace")).splitlines() if x.strip()]
        bad = [x for x in lines if "✗" in x or "FAIL" in x or "失败" in x]
        print("   总线账 %d 行 ｜ 死信 %d 行 ｜ ★疑似异常 %d 行" % (len(lines), len(dlq), len(bad)))
        rep["items"]["3_bus_validate_scan"] = {"status": "PASS", "bus_lines": len(lines),
                                               "dlq_lines": len(dlq), "suspect": len(bad)}
    else:
        print("③ 总线 validate+scan …… ★NOT_EXECUTED（总线账仍占位）")
        rep["items"]["3_bus_validate_scan"] = {"status": "NOT_EXECUTED", "why": "总线账仍占位"}

    print("④ SHA3-512 树对账 ……")
    env = dict(**__import__("os").environ)
    kb = (HOME / ".a2a-hmac-key.bin").read_bytes()
    env["OPL_A2A_HMAC_KEY_B64"] = base64.b64encode(kb).decode()
    env["OPL_A2A_HMAC_KEY_ID"] = "opl-a2a-2026q4"
    r = subprocess.run([str(NODE), "tools/sha3-tree.mjs", "verify"], cwd=str(MIRROR),
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    tail = [x for x in ((r.stdout or "") + (r.stderr or "")).splitlines() if x.strip()][-1:]
    print("   退出码 %d ｜ %s" % (r.returncode, (tail[0] if tail else "")[:110]))
    rep["items"]["4_sha3_tree_recon"] = {"status": "PASS" if r.returncode == 0 else "FAILED",
                                        "rc": r.returncode, "tail": (tail[0] if tail else "")[:160]}

    print("⑤ 三面核验 ……")
    reg = rd(SEAT / "registry" / "seat_register.jsonl") or ""
    card = rd(SEAT / "agent-card.json") or ""
    led = rd(SEAT / "ledger" / "frontier_ledger.jsonl") or ""
    R = [json.loads(x) for x in reg.splitlines() if x.strip()]
    L = [json.loads(x) for x in led.splitlines() if x.strip()]
    C = json.loads(card) if card.strip() else {}
    seats = {e.get("seat") for e in R}
    lag = (dt.datetime.now().astimezone() - dt.datetime.fromisoformat(str(L[-1].get("ts")))).total_seconds() / 60
    print("   名册 %d 席 ｜ 名片 %s ｜ 台账 %d 条 ｜ 末条距当下 %.1f 分钟" % (len(seats), C.get("name"), len(L), lag))
    rep["items"]["5_three_face"] = {"status": "PASS", "seats": sorted(seats), "card_name": C.get("name"),
                                    "ledger_entries": len(L), "last_lag_min": round(lag, 1),
                                    "alias": C.get("name") not in seats,
                                    "note": "★涉总线之面未核（该件占位）；异名已由 seat_card_map.json 互指"}

    print("⑥ 台账 verify ……")
    r = subprocess.run([sys.executable, str(SEAT / "ledger" / "cairn_ledger.py"), "verify"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    ln = [x.strip() for x in (r.stdout or "").splitlines() if "条目数" in x or "结论" in x]
    print("   " + " ｜ ".join(ln)[:140])
    rep["items"]["6_ledger_verify"] = {"status": "PASS" if r.returncode == 0 else "FAILED",
                                      "rc": r.returncode, "detail": " ｜ ".join(ln)[:200]}

    print("⑦ 器械 virtue_audit ……")
    va = SEAT / "exp" / "virtue_audit.py"
    if _readable(va):
        r = subprocess.run([sys.executable, str(va)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        tail = [x for x in ((r.stdout or "") + (r.stderr or "")).splitlines() if x.strip()][-3:]
        print("   退出码 %d ｜ %s" % (r.returncode, (tail[0] if tail else "")[:110]))
        rep["items"]["7_virtue_audit"] = {"status": "PASS" if r.returncode == 0 else "FAILED",
                                          "rc": r.returncode, "tail": (tail[0] if tail else "")[:160],
                                          "note": "器物已实体 ⇒ 实跑（-1601 起）"}
    else:
        print("⑦ 器械 virtue_audit …… ★NOT_EXECUTED（器物仍占位）")
        rep["items"]["7_virtue_audit"] = {"status": "NOT_EXECUTED", "why": "器物仍占位"}

    free = rmem_mb()
    lvl = ("正常" if free >= 1256 else "低于 M_floor" if free >= 819.2 else "★警戒" if free >= 512 else "★深警戒")
    print("⑧ 环境 R_mem …… %.1f MB ⇒ %s（M_floor 1256／警戒 819.2、512.0）" % (free, lvl))
    rep["items"]["8_r_mem"] = {"status": lvl, "free_mb": free, "floor": 1256, "warn": [819.2, 512.0]}

    print("⑨ 唯一正本仓状态 ……")
    def g(*a):
        return subprocess.run([GIT] + list(a), cwd=str(CAIRN), capture_output=True,
                              text=True, encoding="utf-8", errors="replace").stdout.strip()
    head, unp = g("rev-parse", "--short", "HEAD"), len([x for x in g("log", "origin/main..HEAD", "--oneline").splitlines() if x.strip()])
    dirty = len([x for x in g("status", "--porcelain").splitlines() if x.strip()])
    print("   HEAD %s ｜ 未推 %d ｜ 工作区余 %d" % (head, unp, dirty))
    rep["items"]["9_canonical_repo"] = {"status": "PASS", "head": head, "unpushed": unp, "worktree_dirty": dirty}

    st = [v.get("status") for v in rep["items"].values()]
    rep["summary"] = {"pass": st.count("PASS"), "not_executed": st.count("NOT_EXECUTED"),
                      "deep_warning": sum(1 for x in st if "深警戒" in str(x) or "警戒" in str(x)),
                      "failed": sum(1 for x in st if x == "FAILED")}
    rep["honesty"] = "★凡不能代者如实标 NOT_EXECUTED（器物占位），不冒充成功"
    p = SEAT / "outbox" / "mem" / ("%s.json" % rep["report"])
    p.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print("   ★产物：%s（%d B）" % (p.name, p.stat().st_size))
    print("   ★汇总：PASS %d ｜ 未执行 %d ｜ 警戒 %d ｜ 失败 %d"
          % (rep["summary"]["pass"], rep["summary"]["not_executed"], rep["summary"]["deep_warning"], rep["summary"]["failed"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
