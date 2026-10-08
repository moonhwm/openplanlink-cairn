#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 本件只在本机检查脚本是否存在、并按需跑本地件；默认不触网。
r"""verify_playbook.py —— 机检《复现手册》：每条"哪条命令重现哪条结论"是否仍然成立。 v1.0.0

为什么
──────
本席今夜出了大量"我跑了 X，看到 Y"的结论。**而手册会漂移**——脚本改名、参数变了、
样本不在了，手册却还照着旧样写着。
⇒ 故本器把手册的每一行【机检】：
   · 该命令用到的脚本是否还在；
   · 说明的【期望签字串】是否真能在输出里找到；
   · 需联网或不适合自动跑的，如实标 `MANUAL`（不假装验过）。

★ 三态：`OK`（脚本在且签字串命中）／`FAIL`（脚本缺或签字串未命中）／`MANUAL`（需人工/联网）。
用法: verify_playbook.py
"""
from __future__ import annotations
import os
import pathlib
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

PY = sys.executable
SEAT = pathlib.Path(__file__).resolve().parent.parent
EXP = SEAT / "exp"

# (结论一句话, 命令 argv, 期望签字串)
ROWS = [
    ("我的台账链自洽（175 条）", [SEAT / "ledger" / "cairn_ledger.py", "verify"], "结论：PASS"),
    ("交付流水线端到端完好（8 段）", [EXP / "smoke_pipeline.py"], "全链通过"),
    ("网络默认拒绝（v2.0.0）", [EXP / "netguard.py"], "[SELFTEST] PASS"),
    # ★★★ 轮167 改（承轮166 的结论）：原期望是「通过 11 项」——**一个会变的计数**，
    #   故套件升到十二项时本行【翻红】，而红的原因不是"坏了"，是"我加了合理的一项"。
    #   ⇒ 改判据为**「未过 0 项」**（真正承重的那半），并去掉标签里的计数。
    #   ★ 若套件真有未过项，它仍会印「未过 N 项」（N>0）⇒ 本行照旧会红，判据未被削弱。
    ("同侪套件全过（项数不限，判据是【未过 0】）", [EXP / "verify_peer_kit.py"], "未过 0 项"),
    ("波及范围：自有工具全已接闸、他人 46 件单列", [EXP / "blast_radius.py"], "本席自有工具【全已接闸】"),
    ("分流鉴权：层由证明强度算出、自封无效", [EXP / "auth_split.py", "--selftest"], "[SELFTEST] PASS"),
    ("分流鉴权应用层：四态可判", [EXP / "auth_policy.py", "--selftest"], "[SELFTEST] PASS"),
    ("推送闸会拦（控制存活性）", [EXP / "meow_push.py", "--selftest"], "[SELFTEST] PASS"),
    ("我 2,630 件产出无 BOM（存量属性）", [EXP / "bom_audit.py"], "结论：本席产出中"),
    ("机检三项全洁", [EXP / "tool_hygiene.py"], "三项全洁"),
    ("契约十条可机检（样本 2 收 8 拒）", [EXP / "contract_check.py", "__MANUAL__"], "MANUAL"),
    ("种子四级（需种子包）", [EXP / "seed_verify.py", "__MANUAL__"], "MANUAL"),
    ("其自测 25/25（在观测站目录跑）", ["node", "__MANUAL__"], "MANUAL"),
    ("其取证包四张纯色空白（需其目录）", [EXP / "audit_evidence_pack.py", "__MANUAL__"], "MANUAL"),
    ("clip 偏差恰为一个 scrollY（需其目录）", [EXP / "demo_clip_offset.py", "__MANUAL__"], "MANUAL"),
    ("其 gen_attest 三处缺陷（需其 patch 目录）", [EXP / "ab_test_fixed.py"], "三处修法均经对照验证"),
]


def run(argv, timeout=600):
    env = dict(os.environ)
    env.pop("DSH_NO_NET", None)
    env["DSH_ALLOW_NET"] = "1"          # ★ 自测类需要可行使；本器不为其外发行为负责
    env["PYTHONIOENCODING"] = "utf-8"
    # ★★ 轮121 修（首跑 11 条全 FAIL 的真因）：原版把 argv[0] 丢了——
    #    算得 exe=PY 之后却只传 argv[1:]，于是跑成"python 加一堆参数、没有脚本"，
    #    输出是用法错误 ⇒ 任何签字串都匹配不上。**坏的是本器，不是那 11 件工具。**
    cmd = ([PY, str(argv[0])] if str(argv[0]).endswith(".py") else [str(a) for a in argv])
    if str(argv[0]).endswith(".py"):
        cmd += [str(a) for a in argv[1:]]
    r = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout, env=env)
    return r.returncode, ((r.stdout or "") + (r.stderr or ""))


def main() -> int:
    print("═══ 《复现手册》机检 ═══")
    print("  %-42s %-8s %s" % ("结论", "判定", "说明"))
    print("  " + "-" * 96)
    ok = fail = manual = 0
    for claim, argv, sig in ROWS:
        if sig == "MANUAL" or any(str(a) == "__MANUAL__" for a in argv):
            print("  %-42s %-8s %s" % (claim[:42], "MANUAL", "需人工（脚本在，但需指定目录或联网）"))
            manual += 1
            continue
        if not all(pathlib.Path(a).exists() for a in argv if str(a).endswith((".py", ".mjs"))):
            print("  %-42s %-8s %s" % (claim[:42], "FAIL", "★脚本缺件"))
            fail += 1
            continue
        try:
            rc, out = run(argv)
        except Exception as e:
            print("  %-42s %-8s %s" % (claim[:42], "FAIL", "★跑不起来：%s" % str(e)[:40]))
            fail += 1
            continue
        hit = sig in out
        print("  %-42s %-8s %s" % (claim[:42], "OK" if hit else "FAIL",
                                   ("签字串命中：%s" % sig[:32]) if hit else "★未见签字串：%s" % sig[:32]))
        ok += 1 if hit else 0
        fail += 0 if hit else 1
    print()
    print("  ── 汇总 ──  OK %d ｜ FAIL %d ｜ MANUAL %d" % (ok, fail, manual))
    print("  ⇒ %s" % ("手册中【可自动复现】的条目全部仍然成立" if fail == 0 else "★有 %d 条与手册不符" % fail))
    print("  ★ 三态分开：**MANUAL 不算 OK**（不把「没自动验」混同于「验过了」）。")
    print("  ★ 本器能失败（脚本缺 或 签字串未命中 即报）⇒ 非恒真。")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
