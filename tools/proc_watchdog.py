#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""proc_watchdog.py —— 进程健康守护：实时维护关键进程不被杀、死即拉起。

按机主令「实时维护各进程健康运行不被杀」。监护对象：
  node       = python a2a_node.py（A2A 节点 127.0.0.1:4173）
  burn       = python burn_daemon.py（燃烧循环）
  heartbeat  = python heartbeat_daemon.py 600（心跳守护）
  zcode      = ZCode.exe（Moon 席生态 GUI）
  kimi       = Kimi.exe（Kimi 桌面）
检查周期 60s；进程缺即重启；留痕 proc_watchdog.jsonl。纯标准库。
"""
import json
import os
import pathlib
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

ROOT = r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928"
PY = r"C:\Users\欧阳宏俊\AppData\Local\Programs\Python\Python312\python.exe"
LOG = pathlib.Path(r"C:\Users\欧阳宏俊\.proc_watchdog.jsonl")
INTERVAL = 60

TARGETS = [
    {"name": "node", "kind": "cmd", "prog": PY, "args": [ROOT + r"\exp\a2a_node.py"],
     "env": {"SERVERCHAN_SENDKEY": os.environ.get("SERVERCHAN_SENDKEY", "")}},
    {"name": "burn", "kind": "cmd", "prog": PY, "args": [ROOT + r"\exp\burn_daemon.py", "--interval", "15"]},
    {"name": "heartbeat", "kind": "cmd", "prog": PY, "args": [ROOT + r"\exp\heartbeat_daemon.py", "600"]},
    {"name": "zcode", "kind": "lnk", "lnk": r"C:\Users\欧阳宏俊\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\ZCode.lnk"},
    {"name": "kimi", "kind": "lnk", "lnk": r"C:\Users\欧阳宏俊\OneDrive\桌面\Kimi.lnk"},
    {"name": "zodaccess", "kind": "prog", "prog": "zodaccess"},
]

# 进程名（tasklist 探测用，不含 .exe）
PROCNAME = {"node": "python", "burn": "python", "heartbeat": "python",
            "zcode": "ZCode", "kimi": "Kimi", "zodaccess": "zodaccess"}


def _alive(name):
    """进程存活探测（python 类按命令行关键字、GUI 按进程名）。"""
    try:
        out = subprocess.run(["tasklist", "/FO", "CSV"], capture_output=True, timeout=30,
                             encoding="utf-8", errors="replace").stdout
    except Exception:
        return True  # 探测失败不杀不重启（保守）
    if not out:
        return True
    if name in ("node", "burn", "heartbeat"):
        return any("python" in line.lower() for line in out.splitlines())
    return any(line.lower().startswith('"%s' % name.lower()) for line in out.splitlines())


def _start(t):
    """启动目标（cmd 直启 / lnk 经 explorer）。"""
    try:
        if t["kind"] == "cmd":
            env = dict(os.environ)
            env.update(t.get("env", {}))
            subprocess.Popen([t["prog"]] + t["args"], env=env,
                             creationflags=subprocess.CREATE_NO_WINDOW)
        elif t["kind"] == "prog":
            subprocess.Popen([t["prog"]], creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            subprocess.Popen(["explorer.exe", t["lnk"]])
        return True
    except Exception as e:
        _log(t["name"], "start_fail", str(e))
        return False


def _log(name, action, detail=""):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": time.time(), "name": name, "action": action, "detail": detail},
                           ensure_ascii=False) + "\n")


def run(interval=INTERVAL):
    while True:
        for t in TARGETS:
            name = t["name"]
            if not _alive(name):
                _log(name, "down_restart")
                ok = _start(t)
                print("[%s] %s 缺失→重启 %s" % (time.strftime("%H:%M:%S"), name, "OK" if ok else "FAIL"), flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=INTERVAL)
    a = ap.parse_args()
    print("★ proc_watchdog 启动：每 %d 秒巡检 %s" % (a.interval, [t['name'] for t in TARGETS]), flush=True)
    run(a.interval)
