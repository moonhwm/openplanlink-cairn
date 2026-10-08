#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只在【临时目录】里造副本与坏件；不碰任何席位的真实件；不触网、不删真件。
r"""neg_control_batch.py —— 给【剩余几件核验器】批量补负例对照。 v1.0.0

为什么做它（轮 62，承轮 60／61）
──────────────────────────────────
轮 60 查出：8 件核验器里只有 1 件有负例对照。
轮 61 补了第 1 件（tool_hygiene）⇒ ★ 而它【当场抓出一处真缺陷】（失败时判词不可读）。
⇒ ★★ 故剩下 6 件不是"理论担忧"：★ 这一轮把同一套做法【参数化】，批量覆盖。

做法（每件一层，全部在临时副本里）
──────────────────────────────────
  ① 把席位拷进临时目录（排除 handshake 等大目录）
  ② 对该核验器，跑【正例】⇒ 记判词／退出码
  ③ 注入一个【它本该抓到的坏件】⇒ 再跑 ⇒ 若判词【不变】则该器【恒真嫌疑】
  ④ 撤掉坏件

★ 本器自陈三条盲点
  ① 它只覆盖【能靠"塞一个坏文件"触发】的那几件 ⇒ 需要更复杂破坏的器【本轮不含】
  ② "判词变了没有"按【整段输出文本】比较 ⇒ 若坏件只改数字不改措辞，会被算成"没变"（反之亦然）
  ③ ★ 它只证【这几类坏件】能让它红 ⇒ 不证它对别的类别也会红
"""
from __future__ import annotations
import pathlib
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

# (标签, 器相对路径, 坏件相对路径, 坏件内容, 说明)
CASES = [
    ("引号机检", "exp/lint_cn_quotes.py", "exp/_neg_bad_syntax.py",
     "# -*- coding: utf-8 -*-\ndef f(:\n    pass\n", "塞一个编译不过的 .py"),
    ("引号机检", "exp/lint_cn_quotes.py", "exp/_neg_bad.json",
     '{"a": 1,,}\n', "塞一个 JSON 解析不过的 .json"),
    ("交付稽核", "exp/audit_orphans.py", "exp/_neg_orphan_tool.py",
     "# -*- coding: utf-8 -*-\n# BLAST: NONE\nprint('orphan')\n", "塞一个没人引用的 .py"),
    ("传递性稽核", "exp/audit_blast_transitivity.py", "exp/_neg_caller.py",
     "# -*- coding: utf-8 -*-\n# BLAST: NONE\nimport subprocess\n"
     "subprocess.run(['x','exp/audit_orphans.py'])\n", "塞一个调用别的 .py 的器"),
]


def run(rel: str, root: pathlib.Path):
    r = subprocess.run([PY, str(root / rel)], capture_output=True, text=True,
                       encoding="utf-8", cwd=str(root), timeout=900)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main() -> int:
    print("═══ 批量负例对照（★ 全在临时副本里）═══")
    with tempfile.TemporaryDirectory() as td:
        lab = pathlib.Path(td) / "seat"
        shutil.copytree(SEAT, lab, ignore=SKIP)
        lab_r, seat_r = lab.resolve(), SEAT.resolve()
        if (seat_r == lab_r) or (seat_r in lab_r.parents):
            print("  ★★ 断言失败：实验室在领地内 ⇒ 拒跑")
            return 2
        print("  ★ 实验室 = %s" % lab_r)
        print("  ★ 断言：实验室不在领地内 ⇒ ✅ 成立")
        print()

        # 先取各器的正例基线
        base = {}
        for _, rel, _, _, _ in CASES:
            if rel not in base:
                base[rel] = run(rel, lab)
        print("  ── 正例基线 ──")
        for rel, (rc, out) in base.items():
            print("     %-38s 退出码 %d ｜ 输出 %d 字符" % (rel, rc, len(out)))
        print()

        bad = 0
        for label, rel, badpath, content, why in CASES:
            p = lab / badpath
            p.write_text(content, encoding="utf-8")
            rc, out = run(rel, lab)
            brc, bout = base[rel]
            changed = (out != bout) or (rc != brc)
            mark = "✅ 判词/退出码变了" if changed else "★★ 没变 ⇒ 恒真嫌疑！"
            print("  ── %s ｜ %s ──" % (label, why))
            print("     注入前：退出码 %d ｜ 注入后：退出码 %d ⇒ %s" % (brc, rc, mark))
            if not changed:
                bad += 1
            p.unlink()

        print()
        print("  ═══ 汇总 ═══")
        print("     案例 = %d ｜ ★ 注入坏件后【判词/退出码未变】的 = %d" % (len(CASES), bad))
        print("     ⇒ ★ %s" % ("全部案例都让对应器起了变化（这几类坏件能触发它们）" if bad == 0
                               else "有案例未触发 ⇒ 请人读那几件器"))
        print()
        print("  ── 本器三条盲点 ──")
        print("     ① 只覆盖【能靠塞一个坏文件触发】的那几件")
        print("     ② 按整段输出文本比较 ⇒ 只改数字不改措辞会被算成没变")
        print("     ③ 只证【这几类坏件】能让它红 ⇒ 不证别的类别也会")
        return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
