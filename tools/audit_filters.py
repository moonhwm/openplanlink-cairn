#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只在临时目录制造失败；不触网、不改真实席位件。
r"""audit_filters.py —— 拿我自己的过滤词去撞【失败输出】，看哪些过滤词是瞎的。 v1.0.0

立此器的缘由（轮 26）
────────────────────────
轮 25 查出：我用 `| Select-String 'scanned'` 过滤 dupcheck 的输出，
★ 而失败那一行【不含 scanned】⇒ 被过滤掉 ⇒ 屏幕上只剩一片干净 ⇒ 我据此以为成功。
⇒ 而那道过滤器不是孤例：**我每一轮都在过滤**。
★ 故本器把这件事做成可查的：**对每个（工具 × 我惯用的过滤词），制造一次失败，看那个词是否还显示。**

★ 本器自陈三条盲点
  ① 它测的是【输出文本里有没有那个词】，不测【我有没有据此下错结论】——那需要读我这边的记录；
  ② 它用【我构造的失败】来测，未必覆盖真实的失败形态；
  ③ ★ 它只测【过滤词是否会显示失败】，不测【失败是否被别的方式捕获】（如检查退出码）。
"""
from __future__ import annotations
import json
import pathlib
import re
import subprocess
import sys
import tempfile

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SEAT = pathlib.Path(__file__).resolve().parent.parent
PY = sys.executable

# （标签, 我惯用的过滤词, 制造失败的 argv）
TRIALS = [
    ("dupcheck（轮25 已证盲）", r"scanned",
     None),   # 由外部命令提供，见下
    ("核验声明 verify_seat_location", r"判词|核过|★不符",
     ["exp/verify_seat_location.py", "<<坏声明>>"]),
    ("配方核验 verify_recipe", r"实跑 |判词",
     None),   # 无参即可跑；失败形态另造
    ("工具机检 tool_hygiene", r"结论|扫过",
     ["exp/tool_hygiene.py"]),
    ("封锚 bom_seal", r"SEALED|ALREADY",
     ["exp/bom_seal.py", "<<不存在>>"]),
    ("投放 pilot_publish", r"OK|REFUSE|IDEMPOTENT",
     ["exp/pilot_publish.py", "publish", "<<不存在>>", "<<也不存在>>"]),
]


def run(argv, cwd):
    try:
        r = subprocess.run([PY] + argv, capture_output=True, text=True,
                           encoding="utf-8", cwd=str(cwd), timeout=300)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return -1, "RUNERR %s" % e


def main() -> int:
    print("═══ 过滤词盲区审计 ═══")
    print("  ★ 问法：制造一次失败 ⇒ 我惯用的那个过滤词【还会显示吗】？")
    rows = []

    with tempfile.TemporaryDirectory() as td:
        lab = pathlib.Path(td)
        # 坏声明：合法 JSON 但内容荒谬 ⇒ 核验器应报 BAD
        bad = lab / "bad.json"
        bad.write_text(json.dumps({"schema": "x"}, ensure_ascii=False), encoding="utf-8")

        for label, pat, argv in TRIALS:
            if argv is None:
                continue
            argv = [str(bad) if a == "<<坏声明>>" else a for a in argv]
            rc, out = run(argv, SEAT)
            shown = bool(re.search(pat, out))
            verdict = "★ 过滤词会显示失败" if shown else "★★ 过滤词【看不见】这次失败"
            rows.append((label, pat, rc, shown))
            print()
            print("  ── %s ──" % label)
            print("     过滤词 = %s" % pat)
            print("     退出码 = %d ｜ %s" % (rc, verdict))
            first = next((l.strip() for l in out.splitlines() if l.strip()), "（无输出）")
            print("     首行 = %s" % first[:96])
            # 若退出码非 0 而过滤词不显示 ⇒ 该过滤词是瞎的
            if rc != 0 and not shown:
                print("     ⇒ ★★ 判定：**若我只看这个过滤词，我会把失败读成干净**")

    print()
    print("  ═══ 汇总 ═══")
    blind = [r for r in rows if r[2] != 0 and not r[3]]
    print("     受检 = %d ｜ ★ 失败时过滤词【看不见】= %d" % (len(rows), len(blind)))
    for label, pat, rc, _ in blind:
        print("       ★ %-34s 过滤词 %s" % (label[:34], pat))
    print()
    print("  ── 本器三条盲点（写在器内）──")
    print("     ① 只测【输出里有没有那个词】，不测【我据此下没下错结论】")
    print("     ② 失败形态由我构造，未必覆盖真实形态")
    print("     ③ 不测【失败是否被别的方式捕获】（例如检查退出码）")
    print()
    print("  ★ 结论取向：**凡过滤，必同时看退出码**——★ 过滤词只能用来【少看】，不能用来【判断成功】。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
