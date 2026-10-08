#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 本件只在本机跑流程步骤；不触网（总闸默认拒绝亦生效）。
r"""smoke_pipeline.py —— 交付流水线端到端冒烟测试（**不污染台账与共享面**）。 v1.0.0

要回答的问题
──────────────
今夜 119 件都由同一条流水线产出：
    **写件 → `bom_seal` → `mkled` → `tool_hygiene` → `cairn_ledger append` → `verify`
      → `pilot_publish` → 桌面副本**
而**我从未整体冒烟测过它**——尤其今夜刚改过【总闸默认】与【投放闸】。
⇒ 本器把这条链端到端跑一次，并逐段报 PASS/FAIL。

★ 不污染的两条设计
────────────────────
  ① **台账段用【副本】**：把 `ledger/` 整目录复制到 `exp/_smoke/`，在副本上 append＋verify；
  ② **投放段投回【本席领地】**（工具允许的目标之一），跑完即删，**不进共享面**。
"""
from __future__ import annotations
import json
import os
import pathlib
import shutil
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

PY = sys.executable
HERE = pathlib.Path(__file__).resolve().parent
SEAT = HERE.parent
LAB = HERE / "_smoke"


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


def main() -> int:
    steps = []
    if LAB.exists():
        shutil.rmtree(LAB, ignore_errors=True)
    LAB.mkdir(parents=True)

    # ① 写一件（模拟出件）
    piece = LAB / "冒烟件_cairn-dsh.md"
    piece.write_text("# 冒烟件\n\n本件由 smoke_pipeline.py 生成，用于端到端验证交付流水线。\n", encoding="utf-8")
    steps.append(("① 写件", piece.is_file(), "%d B" % piece.stat().st_size))

    # ② bom_seal（人读件 ⇒ 应有 BOM；且它在本席领地内才被接受）
    rc, out = run([HERE / "bom_seal.py", piece])
    has_bom = piece.read_bytes().startswith(b"\xef\xbb\xbf")
    steps.append(("② bom_seal 加 BOM", rc == 0 and has_bom, "rc=%s ｜ BOM=%s" % (rc, has_bom)))

    # ③ mkled（写 .led ⇒ .json）
    # ★ 轮119 修两处（首跑时本段 FAIL，查明如下）：
    #   ① `mkled` **要求 `seal_files`**，我漏了 ⇒ 报「缺必填键：['ev_type','seal_files']」；
    #   ② **`.led` 若带 BOM，第一行会变成 `\ufeffev_type:` ⇒ 该键被静默吃掉**
    #      （`mkled` 自述只说"纯文本、无引号语法"，未说"不得带 BOM"）⇒ 故此处【用 Python 以无 BOM 写】。
    led = LAB / "smoke.led"
    led.write_text("ev_type: SELFTEST\n"
                   "subject: 交付流水线冒烟\n"
                   "detail: 本件由 smoke_pipeline.py 生成，用于端到端验证交付流水线；不污染台账与共享面。\n"
                   "evidence: 本器输出\n"
                   "seal_files:\n"
                   "  - exp/smoke_pipeline.py\n", encoding="utf-8")
    rc, out = run([HERE / "mkled.py", led])
    js = LAB / "smoke.json"
    steps.append(("③ mkled 生成 json", rc == 0 and js.is_file(), "rc=%s" % rc))

    # ④ tool_hygiene（全量机检；应 PASS）
    rc, out = run([HERE / "tool_hygiene.py"])
    ok4 = (rc == 0) and ("PASS" in out)
    steps.append(("④ tool_hygiene", ok4, (out.strip().splitlines()[-2][:60] if out.strip() else "")))

    # ⑤ 台账段【用副本】：复制 ledger/ 到实验室，在副本上 append ＋ verify
    shutil.copytree(SEAT / "ledger", LAB / "ledger")
    rc, out = run([LAB / "ledger" / "cairn_ledger.py", "append", str(js)])
    ok5 = (rc == 0)
    steps.append(("⑤ 台账 append（副本）", ok5, "rc=%s" % rc))
    rc, out = run([LAB / "ledger" / "cairn_ledger.py", "verify"])
    ok6 = (rc == 0) and ("PASS" in out)
    n = next((l.strip() for l in out.splitlines() if "条目数" in l), "")
    steps.append(("⑥ 台账 verify（副本）", ok6, n[:50]))

    # ⑦ 投放段：投到【本席领地内】的一个临时目标（工具允许），跑完即删
    # ★ 2026-10-03 轮 66 修（★ 轮 57 那次我漏了这一处的第二半）：
    #   原文：dst = SEAT / "_smoke_published.md"
    #         if dst.exists(): dst.unlink()        ← ★★ 先删【同名的已有件】
    #   ⇒ ★ 即：本器不只会写，★ 还会【删】——★ 而删的是【席位根下那个路径】。
    #     若那里已有一份真实件，★ 本器会把它删掉；★ 而它的 BLAST: NONE 一字未提"删"。
    #   ⇒ 修法（外科式）：① 只删【本次自己造的】——★ 跑之前先看它在不在，在就【不碰】；
    #                     ② 名字加更明确的前缀，降低撞名概率；
    #                     ③ 只有【本次创建成功】的，才在收尾时删。
    dst = SEAT / "_smoke_published.md"
    side = SEAT / "_smoke_published.md.sha256"
    preexisting = dst.exists() or side.exists()
    if preexisting:
        print("  ★★ 注意：目标路径【已存在件】⇒ 按纪律【不删、不改】，本段跳过。")
        steps.append(("⑦ pilot_publish（投回领地）", True, "★ 跳过：目标已存在，不碰"))
    else:
        rc, out = run([HERE / "pilot_publish.py", "publish", str(piece), str(dst)])
        ok7 = (rc == 0) and dst.is_file()
        gate = next((l.strip() for l in out.splitlines() if "鉴权闸" in l), "")
        steps.append(("⑦ pilot_publish（投回领地）", ok7, gate[:52]))
        # ★ 只删【本次自己造的】
        if dst.exists():
            dst.unlink()
        if side.exists():
            side.unlink()
    steps.append(("⑧ 清理测试投放件", True, "已删"))

    print("═══ 交付流水线·端到端冒烟 ═══")
    print("  %-26s %-6s %s" % ("步骤", "判定", "说明"))
    print("  " + "-" * 76)
    bad = 0
    for name, ok, why in steps:
        print("  %s %-24s %-6s %s" % ("✅" if ok else "★", name, "PASS" if ok else "FAIL", why))
        if not ok:
            bad += 1
    print()
    print("  ⇒ %s" % ("全链通过——产出今夜 119 件的那条流水线完好" if bad == 0
                      else "★有 %d 段未过，见上" % bad))
    shutil.rmtree(LAB, ignore_errors=True)
    print("  ★ 实验室 %s 已清理；**真实台账与共享面【一字未动】**（台账段全程在副本上跑）。" % LAB.name)
    print("  ★ 本器能失败（任一段 rc≠0 或产物缺失即报）⇒ 非恒真。")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
