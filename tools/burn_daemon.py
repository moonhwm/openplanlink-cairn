#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""burn_daemon.py —— 燃烧守护循环：自主运维 token 燃烧（聚焦自进化）。

主权人放行「真可以开始跑了」。本循环以事件驱动+自进化主题轮流打样，
通道：硅基流动(稳定主力) + 留痕 JSONL；速率/配额可参数化。
纯标准库。token 留痕 burn_ledger.jsonl。
"""
import json
import pathlib
import socket
import sys
import time
import urllib.request

socket.setdefaulttimeout(45)  # 全局 socket 硬超时：防网络挂起阻塞守护

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
import hetero_models as HM

LEDGER = pathlib.Path(r"C:\Users\欧阳宏俊\.burn_ledger.jsonl")  # 非云同步路径（避免 WPS 同步锁）
INTERVAL = 90  # 每 90 秒一轮（可调）
MAX_ROUNDS = 0  # 0=不限（背景长跑）

THEMES = [
    "用三句话评述：SDD规范驱动开发如何约束自进化模块的变更纪律",
    "用三句话评述：开源五层协议(AGPL/SSPL/CC-BY-SA/ODbL)对A2A协同的治理意义",
    "用三句话评述：事件驱动架构中死信队列与Saga补偿如何保证最终一致性",
    "用三句话评述：黏菌混合策略(圆桌聚合+Dijkstra图寻)对发散检索的启发",
    "用三句话评述：等幂知识消化(CAS内容寻址)如何避免知识重复存储",
    "用三句话评述：HMAC-SHA3-512包络+ReplayCache对A2A消息防重放的作用",
]


def _maas_burn(prompt):
    """华为云 MAAS 通道燃烧（deepseek-v4-flash、压榨华为算力）。"""
    import json as _j
    envf = pathlib.Path(r"C:\Users\欧阳宏俊\.zcode\workspace\default\a2a-bridge\.env")
    cfg = {}
    for line in envf.read_text(encoding="utf-8").splitlines():
        if line.startswith(("HUAWEI_MAAS_KEY", "HUAWEI_MAAS_BASE")):
            k, _, v = line.partition("=")
            cfg[k] = v.strip()
    body = _j.dumps({"model": "deepseek-v4-flash",
                     "messages": [{"role": "user", "content": prompt}],
                     "max_tokens": 128}).encode("utf-8")
    req = urllib.request.Request(cfg["HUAWEI_MAAS_BASE"] + "/chat/completions", data=body,
                                 headers={"Authorization": "Bearer " + cfg["HUAWEI_MAAS_KEY"],
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            d = _j.loads(r.read().decode("utf-8"))
        return {"model": "deepseek-v4-flash", "tokens": d.get("usage", {}).get("total_tokens", 0)}
    except Exception as e:
        return {"model": "maas", "tokens": 0, "error": str(e)[:60]}


def _burn(prompt):
    r = HM.chat("Qwen/Qwen2.5-7B-Instruct", prompt, max_tokens=128)
    if "error" in r:
        r2 = _maas_burn(prompt)
        if "error" not in r2:
            r = r2
    entry = {"ts": time.time(), "prompt": prompt[:40], "model": r.get("model", ""),
             "tokens": r.get("tokens", 0), "ok": "error" not in r}
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def _stats():
    if not LEDGER.exists():
        return {"rounds": 0, "tokens": 0}
    rows = [json.loads(l) for l in open(LEDGER, encoding="utf-8") if l.strip()]
    return {"rounds": len(rows), "tokens": sum(r.get("tokens", 0) for r in rows)}


def run(max_rounds=MAX_ROUNDS, interval=INTERVAL):
    i = 0
    while max_rounds == 0 or i < max_rounds:
        prompt = THEMES[i % len(THEMES)]
        e = _burn(prompt)
        s = _stats()
        print("  [%d] %s | +%d tok | 累计 %d tok" % (s["rounds"], prompt[:20], e["tokens"], s["tokens"]), flush=True)
        i += 1
        time.sleep(interval)
    return _stats()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=MAX_ROUNDS)
    ap.add_argument("--interval", type=int, default=INTERVAL)
    a = ap.parse_args()
    s = run(a.rounds, a.interval)
    print("★ 燃烧结束 =", s)
