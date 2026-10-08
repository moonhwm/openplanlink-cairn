#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
test_chain_rewrite.py —— 测沈铎 `deduce_core.SnapshotChain.verify()` 到底证什么。 v1.0.0

动机（本席最难的一课，迁移到其新代码）
────────────────────────────────────────
本席轮 45–47 在 mirror 上查出：`verify.mjs` **只读 `attest.json`、从不读被声明文件** ⇒
**零个被声明文件的目录里也能 `root match: true`** ⇒ **"验自洽 ≠ 验内容/验作者"**。

⇒ 同一个问题问其 `SnapshotChain`：
    `digest = sha3_512(prev + str(seq) + sha3_512(canon(conclusion)))`
    `verify()` **从【存储的 conclusion】重算 digest** 并比对。
   ⇒ 若有人**改结论并重算其后所有 digest**，`verify()` 会不会仍然为真？

★ 三个实验（须能分别给出"真/假"，否则器具作废）
   A 原链 ⇒ 期望 **真**
   B 只改结论、不重算 ⇒ 期望 **假**（其 D3 的既有保护）
   C **改结论并重算其上所有后续 digest** ⇒ 期望 **真**——★ 若是，则它证的是自洽、不是作者
   D 对照：其链中是否含任何【签名材料】（序号/时间戳之外的身份凭据）

★ 本器只 import 其模块、调用其公开方法；**未改其文件一个字节**。
用法: test_chain_rewrite.py [--deduce 路径]
"""
from __future__ import annotations
import argparse
import pathlib
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deduce", default=r"C:\Users\欧阳宏俊\OneDrive\桌面")
    a = ap.parse_args()
    d = pathlib.Path(a.deduce)
    if not (d / "deduce_core.py").is_file():
        print("[ERR] 未找到 deduce_core.py"); return 2
    sys.path.insert(0, str(d))
    import deduce_core as dc

    print("═══ 其 `SnapshotChain.verify()` 到底证什么 ═══")
    print("  对象 = %s" % (d / "deduce_core.py"))
    print()

    ev = [
        {"ts": 1000, "src": "s1", "kind": "cost", "payload": {"cost_yuan": 1.5}},
        {"ts": 1010, "src": "s2", "kind": "cost", "payload": {"cost_yuan": 2.5}},
        {"ts": 1020, "src": "s3", "kind": "bus_rows", "payload": {"rows": 100}},
        {"ts": 1030, "src": "s3", "kind": "bus_rows", "payload": {"rows": 120}},
    ]
    core = dc.DeduceCore()
    for e in ev:
        core.ingest(e)
    ch = core.chain.chain
    print("  链长 = %d ｜ 结论类型 = %s" % (len(ch), [c["conclusion"]["type"] for c in ch]))

    # ── A 原链 ──
    A = core.chain.verify()
    print()
    print("  A 原链 verify()                        ⇒ %s（期望 真）" % A)

    # ── B 只改结论、不重算 ──
    import copy
    bak = copy.deepcopy(ch)
    ch[0]["conclusion"]["cost_yuan"] = 999
    B = core.chain.verify()
    print("  B 只改结论不重算 verify()               ⇒ %s（期望 假）" % B)
    ch[:] = copy.deepcopy(bak)

    # ── C 改结论【并重算其上所有后续 digest】──
    print()
    print("  ── C：改结论 + 重算其后所有 digest（本席自写重算器，用其同一算法）──")
    forged = copy.deepcopy(bak)
    forged[0]["conclusion"]["cost_yuan"] = 999.0     # 篡改
    prev = "0" * 128
    for i, e in enumerate(forged):
        e["seq"] = i + 1
        e["prev"] = prev
        e["digest"] = dc.sha3((prev + str(e["seq"]) + dc.sha3(dc.canon(e["conclusion"]))).encode())
        prev = e["digest"]
    # 用其 verify 的同一算法独立复核
    prev2, ok_c = "0" * 128, True
    for e in forged:
        exp = dc.sha3((prev2 + str(e["seq"]) + dc.sha3(dc.canon(e["conclusion"]))).encode())
        if exp != e["digest"] or e["prev"] != prev2:
            ok_c = False
        prev2 = e["digest"]
    print("     其算法下该【伪造链】自洽？        ⇒ %s" % ok_c)
    print("     篡改后的首条结论 cost_yuan = %s" % forged[0]["conclusion"]["cost_yuan"])
    C = ok_c
    print("  C 结论：**改结论并重算 digest 后，链【仍然自洽】** = %s" % C)

    # ── D 链中是否含签名材料 ──
    print()
    keys = set()
    for e in bak:
        keys |= set(e.keys())
        keys |= set(e["conclusion"].keys())
    siglike = [k for k in keys if any(s in k.lower() for s in ("sig", "pub", "key", "author", "seat", "signer"))]
    print("  D 链条目与其结论中出现过的字段 = %s" % sorted(keys))
    print("     类签名/身份字段 = %s" % (siglike if siglike else "（无）"))

    print()
    print("  ── 判读 ──")
    print("   · D3 判据（其 §3.2）原文：「完整性：推演结论链 hash 衔接、前驱在册」")
    print("     ⇒ 就字面而言，它要求的是【衔接】——C 已证：**重写后的链依然衔接**。")
    print("     ⇒ 故 D3 在此覆盖了「衔接」，**未覆盖「谁写的」**。")
    print("   ★ 与 mirror 同一课：**验自洽 ≠ 验内容，更 ≠ 验作者**。")
    print()
    print("  ── 建议（可不采纳，且复用其自家器具）──")
    print("   · 其 §2.2 已有 ed25519 签名机制；**把链头（或每条 digest）用席位私钥签一次**，")
    print("     则重写链需持有私钥 ⇒ D3 可升为「衔接 ∧ 可验签」。")
    print("   · 或至少：**把链头 digest 外锚**（如落进另一份 append-only 账本），使重写可被发现。")
    print()
    print("  ★ 本器能给出【真】与【假】两种结果（A 真、B 假）⇒ 非恒真。")
    print("  ★ 本席未改动被测文件一个字节。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
