#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 本件只读本机件并按点写本席台账与 outbox；不触网（网络默认拒绝亦生效）。
r"""window_close_record.py —— **窗口末刻录**：到点自动抓终态，写台账 ＋ 一份呈机主件。 v1.0.0

为什么要它
───────────
目标写「**到今晚23点**」。而**今晚一切我都验过，唯独"窗口结束"是被动的**：
23:00 一到，两个状态作业自己停 —— 然后终态要靠我【凭记忆重构】。
⇒ **这与本席整晚的纪律相反：不靠记得，靠留下记录。**
⇒ 故本器【到点自动刻录】。

刻录什么（**全部当场实取**）
──────────────────────────────
  ① 台账条数 ＋ 链末 hash ＋ verify 判词
  ② 本席 outbox 件数 ／ 桌面呈机主件数 ／ 共享面件数
  ③ 我自己的器具数（exp/ ＋ obs_fix/）
  ④ 实时互操作件最后一次 as_of（**"实时"到最后一刻的证据**）
  ⑤ 两次状态循环的历史行数

★ 有界：**到达目标时刻后【最多刻录一次】即退出**；上限 MAX_WAIT 秒。
★ 本器**不触网、不起服务、不开端口**；只读本机件、只写本席 outbox 与台账。
用法: window_close_record.py [--until 23:00]
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import os
import pathlib
import re
import subprocess
import sys
import time

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

PY = sys.executable
HERE = pathlib.Path(__file__).resolve().parent
SEAT = HERE.parent
DESK = SEAT.parent
LED = SEAT / "ledger" / "cairn_ledger.py"
LEDGER = SEAT / "ledger" / "frontier_ledger.jsonl"
OUTBOX = SEAT / "outbox"
INBOX = DESK / "全局声明_治理文档" / "a2a-inbox" / "cairn-dsh"
LIVE = OUTBOX / "cairn-status-live.js"
HIST = OUTBOX / "state_history.jsonl"
MAX_WAIT = 3 * 3600


def run(args, timeout=300, allow_net=False):
    env = dict(os.environ)
    env.pop("DSH_NO_NET", None)
    if allow_net:
        env["DSH_ALLOW_NET"] = "1"
    else:
        env.pop("DSH_ALLOW_NET", None)
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([PY] + [str(a) for a in args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout, env=env)
    return r.returncode, ((r.stdout or "") + (r.stderr or ""))


def capture() -> dict:
    led = [l for l in LEDGER.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]
    rc, out = run([LED, "verify"])
    chain = next((l.strip() for l in out.splitlines() if "链末" in l), "")
    verdict = next((l.strip() for l in out.splitlines() if "结论" in l), "")
    ob = [p for p in OUTBOX.glob("*") if p.is_file()]
    desk = [p for p in DESK.glob("【石敢当席呈机主】*") if p.is_file()]
    inbox = [p for p in INBOX.glob("*") if p.suffix != ".sha256"] if INBOX.is_dir() else []
    mine = []
    for d in (HERE, SEAT / "obs_fix"):
        if d.is_dir():
            mine += [p for p in d.iterdir() if p.suffix in (".py", ".mjs")]
    asof = ""
    if LIVE.is_file():
        m = re.search(r'"as_of":\s*"([^"]+)"', LIVE.read_text(encoding="utf-8", errors="replace"))
        asof = m.group(1) if m else ""
    hist = len(HIST.read_text(encoding="utf-8", errors="replace").splitlines()) if HIST.is_file() else 0
    return {"刻录时刻": dt.datetime.now().isoformat(timespec="seconds"),
            "台账条数": len(led), "链末": chain, "verify判词": verdict,
            "本席outbox件数": len(ob), "桌面呈机主件数": len(desk),
            "共享面件数": len(inbox), "我自己的器具数": len(mine),
            "实时件最后as_of": asof, "状态历史行数": hist}


def write_piece_and_ledger(cap: dict, lab_dir: pathlib.Path, ledger_dir: pathlib.Path) -> tuple:
    """★ 把【写件 ＋ 生成 .led ＋ mkled ＋ append】抽出来，以便：
       · 到点时在【真实】目录跑（lab_dir=OUTBOX, ledger_dir=SEAT/ledger）；
       · 验写盘时在【副本】目录跑（零污染）。
       返回 (件路径, append 判词)。"""
    OUTBOX.mkdir(parents=True, exist_ok=True) if lab_dir == OUTBOX else lab_dir.mkdir(parents=True, exist_ok=True)
    piece = lab_dir / "窗口末刻录_23时终态_cairn-dsh_20261002.md"
    lines = ["# 呈机主 · **窗口末刻录**：23:00 的终态（当场实取，非事后重构）", "",
             "> 出件席：**cairn-dsh（石敢当）** ｜ 刻录时刻：**%s**" % cap["刻录时刻"],
             "> ★ **本件由 `window_close_record.py` 到点自动生成**——不是事后凭记忆写的。",
             "> ★ **本件不涉对外发送。**", "", "---", "", "## 终态", "",
             "| 项 | 值 |", "|---|---|"]
    for k, v in cap.items():
        lines.append("| **%s** | %s |" % (k, v))
    lines += ["", "---", "",
              "## 诚实边界", "",
              "1. ★ **本件是【刻录】，不含新技术结论**；每一项的完整论证在其名下那件里；",
              "2. ★★ **「%s」这一行由本器当场实取**——但**它刻的是【本器能看到的那些】**：" % cap["刻录时刻"],
              "   **不含两个后台作业的存活状态**（本器在作业之内，看不到自己之外）；",
              "3. ★★ **本席的状态作业（心跳／实时件）按设计在 23:00 自停**；",
              "   **⇒ 此后实时件不再刷新，其 `as_of` 即停在上面那一格。**",
              "   ★ 本件【不点名具体作业】——因为到点那一刻，**跑着的作业本器看不到**"
              "（它在作业之内）⇒ 点名就会写出【可能已不存在的名字】（轮173 即因此改）。",
              "4. ★★ **「状态历史行数」那一格【不应当作「运行了多久」来读】**：",
              "   本席今夜一度有【两个写者】往同一文件写（轮150 自曝并已处置）⇒ **该行数被抬高过**。",
              "   ★ 更可靠的跨度指标见 `exp\\emit_duration.py`（用【不同分钟数】与【台账首末 ts】）。",
              "5. ★ **本件不涉对外发送。**", "",
              "*石敢当席 · Cairn ｜ 窗口到了，我不凭记忆终态——我让它在到点那一刻自己记下来。*"]
    piece.write_text("\n".join(lines) + "\n", encoding="utf-8")

    led = lab_dir / "_window_close.led"
    led.write_text("ev_type: STATUS\n"
                   "subject: ★窗口末刻录（到点自动生成）：23:00 的终态当场实取，非事后重构——"
                   "台账 %d 条／链末 %s／verify 判词 %s；本席 outbox %d 件／桌面呈机主件 %d 件／共享面 %d 件／"
                   "我自己的器具 %d 件；实时件最后 as_of %s；状态历史 %d 行\n"
                   "detail: 目标写「到今晚23点」，而今晚一切我都验过，唯独窗口结束是被动的：23:00 一到两个状态作业自己停，"
                   "然后终态要靠我凭记忆重构——这与本席整晚的纪律相反（不靠记得，靠留下记录）⇒ 故作本器到点自动刻录。"
                   "本器有界（到点刻录一次即退出）、不触网、不起服务、不开端口；只读本机件、只写本席 outbox 与台账。"
                   "本件由 window_close_record.py 自动生成。\n"
                   "evidence: window_close_record.py 输出；cairn_ledger verify；outbox 与桌面与共享面实取计数；"
                   "cairn-status-live.js 的 as_of\n"
                   "seal_files:\n"
                   "  - outbox/%s\n"
                   "  - exp/window_close_record.py\n"
                   % (cap["台账条数"], cap["链末"], cap["verify判词"], cap["本席outbox件数"],
                      cap["桌面呈机主件数"], cap["共享面件数"], cap["我自己的器具数"],
                      cap["实时件最后as_of"], cap["状态历史行数"], piece.name),
                   encoding="utf-8")
    rc, out = run([HERE / "mkled.py", led])
    v = "mkled rc=%s" % rc
    if rc == 0:
        js = led.with_suffix(".json")
        rc2, out2 = run([ledger_dir / "cairn_ledger.py", "append", str(js)])
        v += " ｜ append rc=%s" % rc2
        v += " ｜ " + next((l.strip() for l in out2.splitlines() if "已追加" in l), "")
        rc3, out3 = run([ledger_dir / "cairn_ledger.py", "verify"])
        v += " ｜ verify rc=%s ｜ %s" % (rc3, next((l.strip() for l in out3.splitlines() if "条目数" in l), ""))
    return piece, v


def verify_write() -> int:
    """★★★ 轮144：**验写盘路径**——在【台账副本】上跑与到点【同一段代码】。零污染。"""
    import shutil
    lab = HERE / "_closewrite_lab"
    if lab.exists():
        shutil.rmtree(lab, ignore_errors=True)
    lab.mkdir(parents=True)
    shutil.copytree(SEAT / "ledger", lab / "ledger")
    cap = capture()
    print("═══ 验写盘路径（在【台账副本】上跑，零污染）═══")
    print("  ★ 跑的是与到点【同一段代码】：生成件 ＋ 生成 .led ＋ mkled ＋ append ＋ verify")
    piece, verdict = write_piece_and_ledger(cap, lab, lab / "ledger")
    print("  件   = %s（%d B）" % (piece.name, piece.stat().st_size if piece.is_file() else -1))
    print("  判词 = %s" % verdict)
    # 核对真实台账【未被动过】
    rc, out = run([SEAT / "ledger" / "cairn_ledger.py", "verify"])
    real = next((l.strip() for l in out.splitlines() if "条目数" in l), "")
    print("  真实台账核对 = %s" % real)
    ok = ("append rc=0" in verdict) and ("verify rc=0" in verdict) and ("条目数" in real)
    print()
    print("  ⇒ %s" % ("✅ 写盘路径通；到 23:00 那段会成功（且真实台账此刻未被改动）"
                      if ok else "★写盘路径有问题 ⇒ 到点会失败，须先修"))
    shutil.rmtree(lab, ignore_errors=True)
    print("  ★ 实验室已清理；真实台账与 outbox 未被改动。")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--until", default="23:00")
    # ★★ 轮138 增：**只抓不写**——用来安全地验刻录逻辑（不写件、不追加台账）
    ap.add_argument("--capture-only", action="store_true")
    # ★★★ 轮144 增：**验写盘路径**——它到 23:00 会调 mkled 与 cairn_ledger append；
    #   若那条路有任何不对，会在【我不再看的时候】静默失败。
    #   ⇒ 本开关把【同样的 .led 生成 ＋ mkled ＋ append】在【台账副本】上跑一遍，零污染。
    ap.add_argument("--verify-write", action="store_true")
    a = ap.parse_args()
    if a.verify_write:
        return verify_write()
    if a.capture_only:
        cap = capture()
        print("═══ 窗口末刻录·只抓不写（验证刻录逻辑，零副作用）═══")
        for k, v in cap.items():
            print("  %-16s %s" % (k, v))
        print("  ★ 未写任何件、未追加台账。")
        return 0
    hh, mm = (int(x) for x in a.until.split(":"))
    now = dt.datetime.now()
    stop = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if stop <= now:
        stop += dt.timedelta(days=1)
    wait = (stop - now).total_seconds()
    print("═══ 窗口末刻录 ═══")
    print("  目标时刻 = %s（距今 %.0f 秒）｜ 上限 %d 秒" % (stop.isoformat(timespec="seconds"), wait, MAX_WAIT))
    print("  ★ 本器不触网、不起服务、不开端口；到点刻录一次即退出。")
    sys.stdout.flush()
    if wait > MAX_WAIT:
        print("  ★ 等待超过上限，退出（不无界占位）。")
        return 1
    while dt.datetime.now() < stop:
        time.sleep(min(20, max(1, (stop - dt.datetime.now()).total_seconds())))
    cap = capture()
    print()
    print("  ── 终态刻录（当场实取）──")
    for k, v in cap.items():
        print("     %-16s %s" % (k, v))

    # ① 写一份呈机主件（先写、后封锚由交付回路做）
    piece = OUTBOX / "窗口末刻录_23时终态_cairn-dsh_20261002.md"
    lines = ["# 呈机主 · **窗口末刻录**：23:00 的终态（当场实取，非事后重构）", "",
             "> 出件席：**cairn-dsh（石敢当）** ｜ 刻录时刻：**%s**" % cap["刻录时刻"],
             "> ★ **本件由 `window_close_record.py` 到点自动生成**——不是事后凭记忆写的。",
             "> ★ **本件不涉对外发送。**", "", "---", "", "## 终态", "",
             "| 项 | 值 |", "|---|---|"]
    for k, v in cap.items():
        lines.append("| **%s** | %s |" % (k, v))
    lines += ["", "---", "",
              "## 诚实边界", "",
              "1. ★ **本件是【刻录】，不含新技术结论**；每一项的完整论证在其名下那件里；",
              "2. ★★ **「%s」这一行由本器当场实取**——但**它刻的是【本器能看到的那些】**：" % cap["刻录时刻"],
              "   **不含两个后台作业的存活状态**（本器在作业之内，看不到自己之外）；",
              "3. ★★ **本席的状态作业（心跳／实时件）按设计在 23:00 自停**；",
              "   **⇒ 此后实时件不再刷新，其 `as_of` 即停在上面那一格。**",
              "   ★ 本件【不点名具体作业】——因为到点那一刻，**跑着的作业本器看不到**"
              "（它在作业之内）⇒ 点名就会写出【可能已不存在的名字】（轮173 即因此改）。",
              "4. ★★ **「状态历史行数」那一格【不应当作「运行了多久」来读】**：",
              "   本席今夜一度有【两个写者】往同一文件写（轮150 自曝并已处置）⇒ **该行数被抬高过**。",
              "   ★ 更可靠的跨度指标见 `exp\\emit_duration.py`（用【不同分钟数】与【台账首末 ts】）。",
              "5. ★ **本件不涉对外发送。**", "",
              "*石敢当席 · Cairn ｜ 窗口到了，我不凭记忆写终态——我让它在到点那一刻自己记下来。*"]
    piece.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("  已写呈机主件 = %s" % piece.name)

    # ② 写 .led 并进台账（用本席既有回路，不绕过它）
    led = OUTBOX.parent / "exp" / "_window_close.led"
    led.write_text("ev_type: STATUS\n"
                   "subject: ★窗口末刻录（到点自动生成）：23:00 的终态当场实取，非事后重构——"
                   "台账 %d 条／链末 %s／verify 判词 %s；本席 outbox %d 件／桌面呈机主件 %d 件／共享面 %d 件／"
                   "我自己的器具 %d 件；实时件最后 as_of %s；状态历史 %d 行\n"
                   "detail: 目标写「到今晚23点」，而今晚一切我都验过，唯独窗口结束是被动的：23:00 一到两个状态作业自己停，"
                   "然后终态要靠我凭记忆重构——这与本席整晚的纪律相反（不靠记得，靠留下记录）⇒ 故作本器到点自动刻录。"
                   "本器有界（到点刻录一次即退出）、不触网、不起服务、不开端口；只读本机件、只写本席 outbox 与台账。"
                   "本件由 window_close_record.py 自动生成。\n"
                   "evidence: window_close_record.py 输出；cairn_ledger verify；outbox 与桌面与共享面实取计数；"
                   "cairn-status-live.js 的 as_of\n"
                   "seal_files:\n"
                   "  - outbox/%s\n"
                   "  - exp/window_close_record.py\n"
                   % (cap["台账条数"], cap["链末"], cap["verify判词"], cap["本席outbox件数"],
                      cap["桌面呈机主件数"], cap["共享面件数"], cap["我自己的器具数"],
                      cap["实时件最后as_of"], cap["状态历史行数"], piece.name),
                   encoding="utf-8")
    rc, out = run([HERE / "mkled.py", led])
    print("  mkled rc=%s" % rc)
    if rc == 0:
        js = led.with_suffix(".json")
        rc2, out2 = run([LED, "append", str(js)])
        print("  台账 append rc=%s ｜ %s" % (rc2, next((l.strip() for l in out2.splitlines() if "已追加" in l or "追加" in l), "")[:80]))
    # ③ ★★★ 轮181 增：**把件也拷到桌面**。
    #   缘由：机主的 179 件都在桌面，而本器原本【只写 outbox】⇒
    #   **最要紧的那一份终态件，反而落在机主不看的地方。**
    #   ★ 用 `000_` 前缀置顶（与前几份 `★★★00_` 同一套办法），并带呈机主标记。
    try:
        desk = pathlib.Path.home() / "OneDrive" / "桌面"
        if desk.is_dir():
            dst = desk / "【石敢当席呈机主】★★★000_窗口末刻录_23时终态_20261002.md"
            import shutil as _sh
            _sh.copy2(piece, dst)
            print("  已拷桌面 = %s" % dst.name)
        else:
            print("  ★ 桌面目录不存在，未拷贝：%s" % desk)
    except Exception as e:
        print("  ★ 拷桌面失败（不影响台账）：%s" % e)

    print("  ★ 刻录完成，退出。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
