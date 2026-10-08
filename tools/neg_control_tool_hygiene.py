#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只在【临时目录】里造副本与坏件；不碰任何席位的真实件；不触网、不删真件。
r"""neg_control_tool_hygiene.py —— 给 tool_hygiene.py 补【负例对照】。 v1.0.0

为什么做它（轮 61，承轮 60）
──────────────────────────────
轮 60 查出：8 件核验器里【只有 1 件有负例对照】⇒ ★ 对其余 7 件，「它印了 PASS」不是它能红的证据。
★ 而其中【最该先补】的是 tool_hygiene.py——★ 因为它的判词「★形式三项全洁」【我每一轮都在引】。

★★ 而做它之前必须先修一处：tool_hygiene.py 原为【硬编码绝对路径】⇒
   ★ 从副本跑它，扫的还是【真席位】⇒ 那样造出的负例【是假的】。
   ⇒ 轮 61 已把路径改为由 __file__ 推 ⇒ ★ 本器才有意义。

做法（三层，全部在临时目录）
──────────────────────────────
  ① 把席位【拷进临时目录】（排除 handshake 等大目录）
  ② 正例：★ 原样跑 ⇒ 期望 PASS（退出码 0）
  ③ 负例甲：往副本的 exp 里塞一个【编译不过的 .py】⇒ 期望 判词 BAD（退出码 1）
  ④ 负例乙：往副本的 exp 里塞一个【JSON 解析不过的 .json】⇒ 期望 判词 BAD（退出码 1）

★ 本器自陈三条盲点
  ① 它只证 tool_hygiene 会【因这两类坏件】而红 ⇒ 不证它对其余类别也会红
  ② 它靠【拷席位】⇒ 若席位大到拷不动，它跑不起来（★ 本轮已排除 handshake）
  ③ ★ 它【不改 tool_hygiene 本体】——故若本体内另有恒真的判据，它【测不到】
"""
from __future__ import annotations
import pathlib
import re
import shutil
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
SKIP = shutil.ignore_patterns("handshake", "__pycache__", "_retired", ".git")


def run_hygiene(root: pathlib.Path):
    r = subprocess.run([PY, str(root / "exp" / "tool_hygiene.py")],
                       capture_output=True, text=True, encoding="utf-8",
                       cwd=str(root), timeout=900)
    out = (r.stdout or "") + (r.stderr or "")
    verdict = "PASS" if "结论：PASS" in out else ("BAD" if "结论：BAD" in out else "?")
    return r.returncode, verdict, out


def main() -> int:
    print("═══ tool_hygiene.py 的负例对照（★ 全在临时目录）═══")
    with tempfile.TemporaryDirectory() as td:
        lab = pathlib.Path(td) / "seat"
        shutil.copytree(SEAT, lab, ignore=SKIP)
        # ★ 断言：实验室不在本席领地内（承轮 42 的规矩）
        lab_r, seat_r = lab.resolve(), SEAT.resolve()
        inside = (seat_r == lab_r) or (seat_r in lab_r.parents)
        print("  ★ 实验室 = %s" % lab_r)
        print("  ★ 本席领地 = %s" % seat_r)
        print("  ★ 断言：实验室不在领地内 ⇒ %s" % ("✅ 成立" if not inside else "★★ 不成立！"))
        if inside:
            return 2
        print()

        results = []

        # ① 正例
        rc, v, _ = run_hygiene(lab)
        results.append(("① 正例（原样副本）", "PASS", v, rc))
        print("  ── ① 正例（原样副本）⇒ 期望 PASS ──  实测 判词 %s ／ 退出码 %d" % (v, rc))

        # ② 负例甲：编译不过的 .py
        bad_py = lab / "exp" / "_neg_broken.py"
        bad_py.write_text("# -*- coding: utf-8 -*-\ndef f(:\n    pass\n", encoding="utf-8")
        rc, v, out = run_hygiene(lab)
        results.append(("② 负例甲（编译不过的 .py）", "BAD", v, rc))
        print("  ── ② 负例甲（塞一个编译不过的 .py）⇒ 期望 BAD ──  实测 判词 %s ／ 退出码 %d" % (v, rc))
        bad_py.unlink()

        # ③ 负例乙：JSON 解析不过的 .json
        bad_json = lab / "exp" / "_neg_broken.json"
        bad_json.write_text('{"a": 1,,}\n', encoding="utf-8")
        rc, v, out = run_hygiene(lab)
        results.append(("③ 负例乙（JSON 解析不过的 .json）", "BAD", v, rc))
        print("  ── ③ 负例乙（塞一个 JSON 解析不过的 .json）⇒ 期望 BAD ──  实测 判词 %s ／ 退出码 %d" % (v, rc))
        bad_json.unlink()

        print()
        print("  ═══ 汇总 ═══")
        ok = True
        for name, want, got, rc in results:
            good = (got == want)
            ok = ok and good
            print("     %-28s 期望 %-5s 实测 %-5s 退出码 %d  %s"
                  % (name, want, got, rc, "✅" if good else "★★ 不符"))
        print("     ⇒ ★ %s" % ("三个方向全部按期望（该器会红也会绿，非恒真）" if ok else "有方向不符 ⇒ 请修"))
        print()
        print("  ── 本器三条盲点 ──")
        print("     ① 只证它因这两类坏件而红 ⇒ 不证它对其余类别也会红")
        print("     ② 靠拷席位 ⇒ 席位太大时跑不起来")
        print("     ③ 不改 tool_hygiene 本体 ⇒ 本体内若另有恒真判据，它测不到")
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
