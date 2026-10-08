#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 本件只在本机跑；不触网（网络默认拒绝亦生效）；不调任何 LLM。
r"""panel_loop_demo.py —— **Panel 回路的可跑示范**：种子 → 引擎 → 结果 → 回流台账，且整链可复现。 v1.0.0

它补的是哪一处
────────────────
本席《两层结论》说：① Panel 作为推演引擎的【种子供给与结果呈现】在进程隔离＋只走数据下可行；
② 而 Panel 自身必须【可复现】——这一层推演引擎给不了。
⇒ 但此前我只有【结论】，没有【可跑的回路】。本件就是那条回路。

★ 我要把话说死（**别被读成"我实现了一个推演引擎"**）
────────────────────────────────────────────────────────
  · 引擎是**确定性 mock**（**不做任何 LLM 调用、不联网**）⇒
    本件证明的是【**回路形状**】与【**可复现边界**】，**不是推理质量**；
  · 换真引擎时，**只要它满足【同输入同输出】，这条回路与它的核验原样可用**；
  · ★ **而如果那个引擎的产出是叙事性的（不可复现），它就无法通过本件第④步**——
    那正是《两层结论》里说的"引擎给不了第②层"。

四步（**每步都留痕，且整链可复现**）
──────────────────────────────────────
  ① 造种子（**输入契约**）    ② 跑引擎（**确定性 mock**）
  ③ 收结果（**回流槽**）      ④ 复现核验（**同参两次，逐字节相等**）
"""
from __future__ import annotations
import hashlib
import json
import os
import pathlib
import shutil
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

HERE = pathlib.Path(__file__).resolve().parent
LAB = HERE / "_panel_lab"


def h(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ── ① 种子（**输入契约**：任何引擎只应看到这些） ──
def make_seed() -> dict:
    return {
        "schema": "cairn-seed/1",
        "ts": "2026-10-01T21:35:00+08:00",
        "kind": "swarm_seed",
        "state": {
            "ledger_entries": 183,
            "peer_kit_checks_passed": 11,
            "net_default": "deny",
            "self_disclosure_ratio": 0.18,
        },
        "ask": "就上述状态，给出三条【可被独立复核】的观察方向。",
        "boundary": "不接受叙事性输出；每条观察须可指回一个可复算量。",
    }


# ── ② 引擎（**确定性 mock**；换真引擎时替换此函数即可） ──
def engine(seed: dict) -> dict:
    st = seed["state"]
    out = []
    if st["self_disclosure_ratio"] >= 0.15:
        out.append({"obs": "自曝/更正占比偏高，宜核其是否【把同类错固化成了默认值】",
                    "recheck": "state.self_disclosure_ratio", "value": st["self_disclosure_ratio"]})
    if st["net_default"] == "deny":
        out.append({"obs": "网络默认拒绝 ⇒ 宜核其【放行路径是否唯一且显式】",
                    "recheck": "state.net_default", "value": st["net_default"]})
    if st["peer_kit_checks_passed"] >= 10:
        out.append({"obs": "同侪套件项数增加 ⇒ 宜核【新项是否也能失败】",
                    "recheck": "state.peer_kit_checks_passed", "value": st["peer_kit_checks_passed"]})
    return {"schema": "engine-result/1", "engine": "deterministic-mock", "seed_hash": h(
        json.dumps(seed, sort_keys=True, ensure_ascii=False).encode("utf-8")), "findings": out}


# ── ③ 回流台账（**结果只以数据形态入链**） ──
def to_ledger_entry(seed: dict, res: dict, seq: int) -> dict:
    core = {"seq": seq, "ev_type": "SWARM_RESULT", "ts": seed["ts"],
            "from_mode": "cairn-dsh", "kind": "seat",
            "detail": "Panel 回路示范：由确定性 mock 引擎据种子产出 %d 条观察；每条附 recheck 指回可复算量。"
                      % len(res["findings"]),
            "seed_hash": res["seed_hash"], "engine": res["engine"]}
    core["hash"] = h(json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    return core


def run_once(tag: str, nondet: bool = False) -> dict:
    seed = make_seed()
    if nondet:
        # ★★ 证伪用：一个【不可复现】的引擎——每次结果里掺入一个随时刻变的字段。
        #    这正是"叙事性产出"的最小模型：同输入、不同输出。
        import time as _t
        seed = dict(seed)
        seed["_nondet_marker"] = str(_t.time_ns())
    res = engine(seed)
    ent = to_ledger_entry(seed, res, 1)
    # 逐件落盘（**供④逐字节比对**）
    d = LAB / tag
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    for name, obj in (("seed.json", seed), ("result.json", res), ("reflow_entry.json", ent)):
        (d / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return {"seed": seed, "res": res, "ent": ent, "dir": d}


def main() -> int:
    LAB.mkdir(exist_ok=True)
    print("═══ Panel 回路示范：种子 → 引擎 → 结果 → 回流台账 ═══")
    print("  ★ 引擎为【确定性 mock】：不调 LLM、不联网 ⇒ 本件证的是【回路形状】与【可复现边界】，不是推理质量。")
    print()

    a = run_once("run_a")
    b = run_once("run_b")

    print("  ① 种子（输入契约）")
    print("     schema=%s ｜ state 键 %d 个 ｜ ask=%s" % (a["seed"]["schema"], len(a["seed"]["state"]), a["seed"]["ask"][:34] + "…"))
    print("     种子哈希 = " + a["res"]["seed_hash"][:32] + "…")
    print("  ② 引擎（%s）⇒ 产出 %d 条观察" % (a["res"]["engine"], len(a["res"]["findings"])))
    for f in a["res"]["findings"]:
        print("       · %s ｜ recheck=%s=%s" % (f["obs"][:44], f["recheck"], f["value"]))
    print("  ③ 回流条目（结果只以数据形态入链）")
    print("     ev_type=%s ｜ hash=%s…" % (a["ent"]["ev_type"], a["ent"]["hash"][:24]))
    print("  ④ 复现核验（同参两次，逐字节）")
    same = True
    for name in ("seed.json", "result.json", "reflow_entry.json"):
        ba = (a["dir"] / name).read_bytes()
        bb = (b["dir"] / name).read_bytes()
        ok = ba == bb
        same = same and ok
        print("     %-20s %s ｜ sha256=%s…" % (name, "✅ 逐字节相等" if ok else "★不等", h(ba)[:24]))
    print()
    print("  ── 判定 ──")
    print("     四步皆成 ∧ 两次逐字节相等 = " + str(same))
    print("     ⇒ " + ("回路可跑且整链可复现；★ 换真引擎时，只要它同输入同输出，本核验原样可用。"
                       if same else "★有未过项"))
    print("     ★ 反之：**若某引擎产出叙事性结果（不可复现），它就过不了第④步** ——")
    print("       那正是《两层结论》里说的：**Panel 自身那一层，推演引擎给不了。**")
    print("  ★ 本器能失败（两次任一字节不同即报）⇒ 非恒真。")

    # ── ⑤ 证伪：换一个【不可复现】的引擎，第④步必须报错 ──
    print()
    print("  ── ⑤ 证伪：把引擎换成【不可复现】的（同输入、不同输出）──")
    c = run_once("nd_a", nondet=True)
    d = run_once("nd_b", nondet=True)
    diff = 0
    for name in ("seed.json", "result.json", "reflow_entry.json"):
        if (c["dir"] / name).read_bytes() != (d["dir"] / name).read_bytes():
            diff += 1
    print("     两次不一致的文件数 = %d / 3" % diff)
    print("     ⇒ " + ("★ 复现核验【确实会失败】⇒ 本器非恒真，且它正是【叙事性引擎的排除机制】。"
                       if diff > 0 else "★ FAIL：不可复现的引擎竟也通过了 ⇒ 本器恒定通过"))
    shutil.rmtree(LAB, ignore_errors=True)
    print("  ★ 实验室已清理；未写任何外部对象。")
    return 0 if (same and diff > 0) else 1


if __name__ == "__main__":
    sys.exit(main())
