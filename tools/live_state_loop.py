#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
live_state_loop.py —— 有界·本机·只写文件的状态刷新循环（「实时推演」的那一半）。 v1.0.0

定位与界线（★ 先读这段）
──────────────────────────
目标要「**开放为实时推演**」。本席已能按 Star-Office-UI 的 schema 产出状态件，但那是**静态**的。
⇒ 本器补上"实时"：**按固定间隔重算状态、写状态件、并追加一条历史**。

★ **这不是"起服务"**：
    · **不监听任何端口、不联网、不接受连接**；
    · **只读本机台账、只写本席 outbox 两个文件**（`state_cairn-dsh.json` 与 `state_history.jsonl`）。
  ⇒ 故它**不增加任何网络暴露面**，与"起服务需先议"是两回事（此点已于轮 64/65 报告写明）。

★ 有界（三道闸，防"忘了关"）
    ① 到 23:00（目标窗口末）自动退出；
    ② 最多 ITER_CAP 次；
    ③ 任何异常不吞：打印后按 fail-fast 退出，不静默续跑。

用法: live_state_loop.py [--interval 60] [--until 23:00]
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import pathlib
import subprocess
import sys
import time

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = pathlib.Path(__file__).resolve().parent.parent
GEN = ROOT / "exp" / "gen_staroffice_state.py"
EMIT = ROOT / "exp" / "emit_status_js.py"
STATE = ROOT / "outbox" / "state_cairn-dsh.json"
HIST = ROOT / "outbox" / "state_history.jsonl"
# ★★ 轮132 增：**实时互操作件**——与共享面上那份【冻结样例】分开命名。
#   为何分开：共享面上那份是【只增不改、可验字节】的档案件；
#   而"活的"文件每次刷新都会变 ⇒ 同一个文件不可能既冻结可验又实时变化。
#   ⇒ 故：`cairn-status.js`（冻结样例，已投放、不动）／`cairn-status-live.js`（本器每次刷新即重写）。
LIVE = ROOT / "outbox" / "cairn-status-live.js"
ITER_CAP = 400


def once() -> dict:
    r = subprocess.run([sys.executable, str(GEN), "--out", str(STATE)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    if r.returncode != 0:
        raise RuntimeError("gen 失败：%s" % ((r.stderr or r.stdout or "")[-200:]))
    st = json.loads(STATE.read_text(encoding="utf-8"))
    with HIST.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"t": dt.datetime.now().isoformat(timespec="seconds"),
                            "progress": st["progress"], "state": st["state"]}, ensure_ascii=False) + "\n")
    # ★★ 轮132：顺手重发【实时】互操作件（同 schema、同 CAIRN_STATUS 名；不触网、不开端口）
    re = subprocess.run([sys.executable, str(EMIT), "--out", str(LIVE)],
                        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    if re.returncode != 0:
        raise RuntimeError("emit 失败：%s" % ((re.stderr or re.stdout or "")[-200:]))
    return st


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=60)
    ap.add_argument("--until", default="23:00")
    a = ap.parse_args()
    hh, mm = (int(x) for x in a.until.split(":"))
    stop_at = dt.datetime.now().replace(hour=hh, minute=mm, second=0, microsecond=0)

    print("═══ 状态刷新循环（有界·本机·不监听）═══")
    print("  间隔 = %ds ｜ 至 %s 自动退出 ｜ 上限 %d 次" % (a.interval, a.until, ITER_CAP))
    print("  写：%s" % STATE.name)
    print("  追加：%s" % HIST.name)
    if not HIST.exists():
        HIST.write_text("", encoding="utf-8")
    n = 0
    while n < ITER_CAP and dt.datetime.now() < stop_at:
        n += 1
        try:
            st = once()
        except Exception as e:
            print("  ★第 %d 次失败，fail-fast：%s" % (n, str(e)[:160]))
            return 1
        print("  [%02d] %s ｜ progress=%d%% ｜ %s" % (n, st["updated_at"], st["progress"], st["detail"][:64]))
        sys.stdout.flush()
        if n < ITER_CAP and dt.datetime.now() < stop_at:
            time.sleep(a.interval)
    print("  ⇒ 退出：跑满 %d 次或已到 %s（%d 次，历史 %d 行）"
          % (n, a.until, n, sum(1 for _ in HIST.read_text(encoding="utf-8").splitlines())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
