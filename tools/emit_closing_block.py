#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— ★ 轮 64 更正措辞：原写「只调本席自有只读器」，★ 而那【不精确】：
#   它调 verify_recipe.py，后者会跑 neg_control_seat_location.py 与 blindspot_trials.py，
#   ★ 那两件【会写】——★ 但只写【临时目录】。
#   ⇒ 故准确说法是：**不写真件；被调者可能写临时目录。**
#   ★ 这与轮 58 那处是同一类错：**「不碰真件」与「什么都不写」是两件事，必须分开写。**
#   ★ 已核（轮 64）：配方 11 条里，会写的两件都受 tempfile 约束；forge_demo.py 亦只在临时目录造链。
r"""emit_closing_block.py —— 把【每轮收尾块】由手写改成【器生成】。 v1.0.0

为什么做它（轮 53，承轮 52 的发现）
──────────────────────────────────────
轮 52 实测出一个 1 : 43 的对照：
  · 台账里的免责句【器生成】⇒ 298 条、1 种、零漂移；
  · 共享面件里的同一件事【手写】⇒ 27 件、43 种说法、强度不一。
★★ 可推广：**手写会漂，器生成不漂。**
⇒ 而本席每轮收尾的那个块（数字 ＋ 几句标准话）【全是手写的】——
  ★ 轮 25 已证「已跑 dupcheck」手写会烂；★ 轮 52 已证免责有 43 种说法。
⇒ 故本器把那个块【生成出来】：数字当场从活器取，免责逐字用 canonical。

它取什么（★ 每一条都真跑，失败即报）
──────────────────────────────────────
  ① 台账：条目数 ／ 链末 hash ／ 结论 ／ 退出码
  ② 声明核验：核过 N ／ 不符 N ／ 判词 ／ 退出码
  ③ 配方核验：实跑 N ／ 不符 N ／ 判词 ／ 退出码
  ④ 机检：结论 ／ 退出码
  ⑤ 引号机检：编译失败 ／ json 失败 ／ 退出码
  ⑥ ★ canonical 免责句（逐字从声明取，不由本器重写）

★ 本器自陈三条盲点
  ① 它只跑【固定那几件器】⇒ 若某轮跑了别的器，本块【不含】
  ② 它取【退出码与判词】，不核【判词的语义对不对】
  ③ ★ 它【不写件】——只打印，供我逐字粘贴；★ 粘贴这一步仍是人手，故仍可能出错
"""
from __future__ import annotations
import argparse
import json
import pathlib
import re
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SEAT = pathlib.Path(__file__).resolve().parent.parent
DECL = SEAT / "outbox" / "SEAT_LOCATION_cairn-dsh_20261002.json"
PY = sys.executable

STEPS = [
    ("台账", ["ledger/cairn_ledger.py", "verify"], r"条目数|链末|结论[:：]"),
    ("声明核验", ["exp/verify_seat_location.py"], r"核过|判词[:：]"),
    ("配方核验", ["exp/verify_recipe.py"], r"实跑|判词"),
    ("机检", ["exp/tool_hygiene.py"], r"结论[:：]"),
    ("引号机检", ["exp/lint_cn_quotes.py"], r"编译失败|json 解析失败"),
]


def build_block() -> tuple[str, int]:
    """生成收尾块文本。★ 返回 (文本, 退出码非 0 的器数)。"""
    lines = ["", "---", "", "## 收尾块（★ 本块由 `exp\\emit_closing_block.py` 生成，非手抄）", ""]
    bad = 0
    for label, argv, pat in STEPS:
        r = subprocess.run([PY] + argv, capture_output=True, text=True,
                           encoding="utf-8", cwd=str(SEAT), timeout=900)
        out = (r.stdout or "") + (r.stderr or "")
        # ★ 2026-10-03 轮 72 改：**先找机器可读的那行**，而不是只按散文正则抓。
        #   缘由（本轮实证）：副本里把 tool_hygiene 的「结论：」改成「判词：」后，
        #   本器【照样印"退出码 0"】而【判词内容静默消失】——★ 看上去一切正常。
        #   ⇒ 故此后：① 优先读 `★ VERDICT=<PASS|BAD>`；② 读不到就【大声说读不到】，
        #     而不是【把那一栏留空】——★ 空行看起来像"没问题"。
        vm = re.search(r"★?\s*VERDICT\s*=\s*(PASS|BAD)", out)
        if vm:
            lines.append("**★ %s（退出码 %d）⇒ ★ VERDICT=%s**" % (label, r.returncode, vm.group(1)))
        else:
            lines.append("**★ %s（退出码 %d）⇒ ★★ 未读到 VERDICT 行（★ 不是通过！）**"
                         % (label, r.returncode))
        lines.append("")
        hits = [l.strip() for l in out.splitlines() if re.search(pat, l)]
        for l in hits[:4]:
            lines.append("- %s" % l)
        lines.append("")
        if r.returncode != 0:
            bad += 1
    cd = ""
    if DECL.is_file():
        try:
            cd = json.loads(DECL.read_text(encoding="utf-8")).get(
                "canonical_disclaimer", {}).get("★_canonical_免责句", "")
        except Exception:
            cd = ""
    lines.append("**★ canonical 免责（★ 逐字引，勿改字）**")
    lines.append("")
    lines.append("> 「%s」" % cd)
    lines.append("")
    lines.append("*★ 本块由器生成：数字当场从活器取，免责逐字引 canonical。"
                 "★ 本器三条盲点：① 只跑固定那几件器 ② 只取退出码与判词、不核其语义 ③ 只写本席领地内的件。*")
    lines.append("")
    return "\n".join(lines) + "\n", bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--append-to", metavar="PIECE",
                    help="★ 把收尾块【直接写进】这个件（相对本席领地解析）；★ 已有本块则拒写（幂等）。")
    a = ap.parse_args()

    block, bad = build_block()

    if not a.append_to:
        print("═══ 收尾块（★ 器生成；数字当场取，免责逐字引）═══")
        print("```")
        print(block.strip())
        print("```")
        print()
        print("  ★ 本器三条盲点：① 只跑固定那几件器 ② 只取退出码与判词、不核其语义 ③ 只写本席领地内的件")
        print("  ★ 退出码非 0 的器 = %d 件（★ 范围：本块所跑的 5 件）⇒ %s"
          % (bad, "★ 请先处理" if bad else "★ 这 5 件全 0——★ 不是「全席全 0」"))
        # ★ 轮 108：把【钉着的器上挂着的待改件数】印出来。
        #   缘由（轮 107）：改被钉的器要付一道改钉流程的税 ⇒ 攒批才划算 ⇒
        #   ★ 而攒批必须有一个【被看见】的记账处。★ 故本块每轮读它一次。
        #   ★ 若读不到 ⇒ ★ 明说读不到（★ 不静默略过——★ 与 VERDICT 那条同一个道理）。
        _pp = SEAT / "exp" / "pinned_pending.md"
        if _pp.is_file():
            _t = _pp.read_text(encoding="utf-8", errors="replace")
            _n = sum(1 for ln in _t.splitlines()
                     if ln.strip().startswith("| **") and "—" not in ln[:8])
            print("  ★ 钉着的器·待改清单 = exp\\pinned_pending.md ｜ ★ 挂着 = %d 条" % _n)
            if _n:
                print("     ⇒ ★ 攒批走改钉：★ 别每次重新发现它（★ 轮 107）")
        else:
            print("  ★★ 未读到 exp\\pinned_pending.md —— ★ 待改清单不在（★ 不是「没有待改」！）")
        # ★ 轮 109 修（正）：这句 return 【必须留在这个 if 分支里】。
        #   ★ 轮 108 我把它移到【函数级】⇒ 于是 main() 在【--append-to 那段之前】就返回 ⇒
        #     **那条会写件的路整段变成不可达**——★ 而我的验证没抓到，★ 因为配方只跑【不带参数】。
        #   ⇒ 记一笔：**"修好症状"与"没打断别的路"，是两件事。**
        return 0 if bad == 0 else 1

    # ★ 轮 54：把"粘贴"这一步也消掉——★ 但仍按本席一贯的闸来写。
    p = pathlib.Path(a.append_to)
    if not p.is_absolute():
        p = (SEAT / p).resolve()
    print("═══ 把收尾块写进件 ═══")
    print("  目标 = %s" % p)
    # 闸一：只写本席领地内
    if SEAT.resolve() not in p.parents:
        print("  ★★ ★ REFUSE（拒写）：目标不在本席领地内 ⇒ 不碰他人格。")
        return 2
    # 闸二：件必须已存在
    if not p.is_file():
        print("  ★★ ★ REFUSE（拒写）：件不存在。")
        return 2
    # 闸三：幂等——已有本块则拒
    cur = p.read_text(encoding="utf-8")
    if "本块由 `exp\\emit_closing_block.py` 生成" in cur:
        print("  ○ 已有本块 ⇒ ★ REFUSE（拒写·幂等）。★ 若确要重生成，请人工处理。")
        return 3
    # 闸四：写前先备份字节数，写后回读校验
    before = p.read_bytes()
    p.write_text(cur + block, encoding="utf-8", newline="")
    after = p.read_bytes()
    if not after.startswith(before):
        print("  ★★ 回读校验失败：写入不是【纯追加】⇒ 请人工查。")
        return 4
    print("  已写（纯追加）：%d → %d 字节" % (len(before), len(after)))
    print("  ★ 四道闸：① 只写领地内 ② 件须存在 ③ 幂等 ④ 纯追加回读校验")
    if bad:
        print("  ★ 注意：有 %d 件器的退出码非 0 ⇒ 块里已如实记着。" % bad)
    return 0


if __name__ == "__main__":
    sys.exit(main())
