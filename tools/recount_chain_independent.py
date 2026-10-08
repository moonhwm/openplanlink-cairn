#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只读台账；不写件、不删件、不触网。
r"""独立复算台账链 —— **第二把尺**（轮 103）。 v1.0.0

为什么另写一件（★ 而不是调 cairn_ledger.py）
──────────────────────────────────────────────
轮 102 立了一条原则：★「写 0 要写范围；★ 而写完，★ 最好【换一把尺再量一次】。」
⇒ 那台账那句「★ 链内自洽」是【最承重的一个 0】，故它最该被换尺复核。
★★ 而第二把尺必须【独立】：**本器【不 import cairn_ledger】**——
   ★ 若调它，就是用同一把尺量两次，★ 那不叫复核，叫【复述】。

★ 本器与 cairn_ledger.py 的【不同之处】（★ 这就是"独立"的实质）
  ① 不 import 它，★ 自己从 .jsonl 原文读
  ② 自己实现规范化（sort_keys + 紧凑分隔符），★ 而不是复用它那个 canon()
  ③ ★ 复算【全部】哈希，★ 而它 verify 也复算全部（★ 相同点是必然的：判据须一致才有意义）
  ④ 本器额外做一件它不做的事：★ 逐条报【prev 是否等于上一条的 hash】，★ 并把断点位置写出来

★ 本器自陈三条盲点
  ① 判据（canonical json + sha256）与它【相同】⇒ ★ 故它抓不到【判据本身的错】
  ② 它只查链内自洽 ⇒ ★ 不证"事后未改动"、不证作者、不证独立
  ③ ★ 若两条命令在同一台机上、同一时刻跑，★ 也【不构成独立实现】——★ 真正的独立须【另一席位】
"""
from __future__ import annotations
import hashlib
import json
import pathlib
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SEAT = pathlib.Path(__file__).resolve().parent.parent
LEDGER = SEAT / "ledger" / "frontier_ledger.jsonl"
ZERO = "0" * 64


def canon(core: dict) -> bytes:
    """★ 自己实现一遍（★ 不复用台账器的 canon）：
    sort_keys + 紧凑分隔符 + **ensure_ascii=False** + UTF-8。
    ★ 这是与它【判据相同】的部分——相同是必要的（否则量的不是同一件事），
    ★ 而"独立"体现在【代码路径】。

    ★★ 轮 103 实证：本器首版【漏了 ensure_ascii=False】⇒ 中文被转成 \\uXXXX
      ⇒ 字节不同 ⇒ **352 条 hash 逐条不符** ⇒ ★ 第二把尺报 BAD，而链是好的。
      ⇒ ★ 故这两把尺的不一致，★ 错的是【这一把】——★ 而那是靠【读第一把尺的配方】找出来的。
    """
    return json.dumps(core, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def main() -> int:
    print("═══ 独立复算台账链（★ 第二把尺）═══")
    if not LEDGER.is_file():
        print("  ★ 台账不在：%s" % LEDGER)
        return 2
    rows = []
    for i, line in enumerate(LEDGER.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            rows.append((i, json.loads(line)))
    print("  条目数 = %d" % len(rows))
    print("  ★ 本器不 import cairn_ledger —— ★ 否则就是拿同一把尺量两次")
    print()

    bad_hash, bad_prev, bad_json = [], [], []
    prev_expected = ZERO
    for idx, e in rows:
        if "hash" not in e:
            bad_json.append(idx)
            continue
        core = {k: v for k, v in e.items() if k != "hash"}
        core["prev"] = e.get("prev")            # ★ 与台账器同口径：把 prev 放进 core 再算
        h = hashlib.sha256(canon(core)).hexdigest()
        if h != e["hash"]:
            bad_hash.append((idx, h, e["hash"]))
        # ★ 本器【多做】的一件事：逐条比 prev 与上一条的 hash
        if e.get("prev") != prev_expected:
            bad_prev.append((idx, e.get("prev"), prev_expected))
        prev_expected = e["hash"]

    print("  ── ★ 复算结果 ──")
    print("     ★ hash 与内容相符的 = %d 条" % (len(rows) - len(bad_hash) - len(bad_json)))
    print("     ★★ hash 不符的 = %d 条" % len(bad_hash))
    for idx, got, want in bad_hash[:5]:
        print("        [第 %d 条] 复算 %s… ≠ 记着 %s…" % (idx, got[:16], want[:16]))
    print("     ★ prev 指针相连的 = %d 条 ｜ ★★ 断开 = %d 条" % (len(rows) - 1 - len(bad_prev), len(bad_prev)))
    for idx, got, want in bad_prev[:5]:
        print("        [第 %d 条] prev %s… ≠ 上一条 hash %s…"
              % (idx, str(got)[:16], str(want)[:16]))
    print()
    print("  ★ 链末 hash = %s…" % prev_expected[:24])
    print("  ═══ 判定 ═══")
    ok = (not bad_hash) and (not bad_prev) and (not bad_json)
    print("     ★ 本器结论：★ 链内自洽（★ 复算全部 hash ＋ 逐条 prev 相连）" if ok
          else "     ★★ 本器结论：★ 链内【不自洽】——见上")
    print("     ★★ 与台账器那句对比：★ 若两把尺同答，★ 那个 0 才站得住（★ 轮 102）")
    print("     ★ 本器三条盲点：① 判据与台账器相同 ⇒ 抓不到判据本身的错"
          "② 不证事后未改动／作者／独立 ③ 同机同时刻跑【不算独立实现】——真独立须另一席位")
    print("★ VERDICT=%s" % ("PASS" if ok else "BAD"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
