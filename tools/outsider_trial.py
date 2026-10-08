#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只复制到临时目录并以局外人身份跑；不触网、不改动真实席位。
r"""outsider_trial.py —— 我到底能不能被【不经我】地核验？当一次第三方，实测。 v1.0.0

为什么做它
────────────
我反复写过「第三方不必经本席」。而这句话【我从未验过】——
★ 从没把自己当成一个拿到复制品、在别处跑命令的局外人。

做法
──────
1. 在中立目录（临时）复制一份【可交付的最小集】：exp\ ＋ ledger\ ＋ outbox\ 的件
2. 以【局外人】的身份，逐个跑索引里那七条命令
3. 记录：哪些成功、哪些失败、失败原因（绝对路径？缺依赖？哈希钉？）
4. ★ 特别关注【版本钉/链上钉】在复制品上的行为——若复制品必失败，则本席的防篡改机制
   【恰好挡住了合法核验】。

用法: outsider_trial.py
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

CMDS = [
    ("lint_cn_quotes.py",            ["exp/lint_cn_quotes.py"]),
    ("verify_seat_location.py",      ["exp/verify_seat_location.py"]),
    ("neg_control_seat_location.py", ["exp/neg_control_seat_location.py"]),
    ("forge_demo.py",                ["exp/forge_demo.py"]),
    ("audit_argument_arc.py",        ["exp/audit_argument_arc.py"]),
    ("audit_deferrals.py",           ["exp/audit_deferrals.py"]),
    ("cairn_ledger.py verify",       ["ledger/cairn_ledger.py", "verify"]),
]


def main() -> int:
    print("═══ 局外人实测（中立目录复制品）═══")
    print("  源 = %s" % SEAT)
    with tempfile.TemporaryDirectory() as td:
        lab = pathlib.Path(td) / "copied_seat"
        (lab / "exp").mkdir(parents=True)
        (lab / "ledger").mkdir(parents=True)
        (lab / "outbox").mkdir(parents=True)

        # 复制：只复制件，不复制 handshake（别人仓库）与前几轮的实验目录
        n_py = 0
        for p in (SEAT / "exp").rglob("*"):
            if p.is_file() and p.suffix in (".py", ".mjs") and "__pycache__" not in str(p):
                dst = lab / "exp" / p.relative_to(SEAT / "exp")
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, dst)
                n_py += 1
        for p in (SEAT / "ledger").rglob("*"):
            if p.is_file():
                dst = lab / "ledger" / p.relative_to(SEAT / "ledger")
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, dst)
        n_md = 0
        for p in (SEAT / "outbox").glob("*.md"):
            shutil.copy2(p, lab / "outbox" / p.name)
            n_md += 1
        for p in (SEAT / "outbox").glob("*.json"):
            shutil.copy2(p, lab / "outbox" / p.name)

        print("  复制品 = exp 下 %d 个器 ｜ ledger ｜ outbox %d 个 .md ＋ json" % (n_py, n_md))
        print("  ★ 复制品里【没有】handshake\\、没有本席的 __pycache__、没有任何真实席位引用")
        print()
        print("  ── 以局外人身份逐条跑（CWD = 复制品根）──")
        print("  ★ 而【跑了 ≠ 读的是复制品】：逐条再判它读的是【复制品】还是【原件】")
        ok = fail = 0
        vacuous = []          # ★ 那些"跑通了，但读的是原件"的命令
        details = []
        real = str(SEAT)
        labp = str(lab)
        for label, argv in CMDS:
            r = subprocess.run([sys.executable] + argv, capture_output=True, text=True,
                               encoding="utf-8", cwd=str(lab))
            out = ((r.stdout or "") + (r.stderr or "")).strip()
            first = next((l.strip() for l in out.splitlines() if l.strip()), "（无输出）")
            good = r.returncode == 0
            ok += 1 if good else 0
            fail += 0 if good else 1
            # ★ 判据：输出里若出现【原件绝对路径】而不出现【复制品路径】⇒ 读的是原件 ⇒ 本测试对该条为空
            reads_real = real in out
            reads_lab = labp in out or labp.replace("\\", "/") in out
            tag = "✅" if good else "★"
            if good and reads_real and not reads_lab:
                tag = "○"
                vacuous.append(label)
            print("   %s %-30s 退出码 %d ｜ 读原件=%s 读复制品=%s ｜ %s"
                  % (tag, label, r.returncode, reads_real, reads_lab, first[:52]))
            # 抓取关键判词
            for key in ("判词", "结论", "编译失败", "形态", "⇒ ✅", "⇒ ★"):
                for line in out.splitlines():
                    if key in line:
                        details.append((label, line.strip()[:96]))
                        break
            if not good:
                err = next((l.strip() for l in out.splitlines()
                            if "Error" in l or "ERR" in l or "找不到" in l or "不存在" in l), "")
                if err:
                    details.append((label, "★ " + err[:96]))

        print()
        print("  ── 局外人读到的判词（抽样）──")
        seen = set()
        for label, line in details:
            if (label, line) not in seen:
                seen.add((label, line))
                print("     %-30s %s" % (label[:30], line))

        print()
        print("  ═══ 判定 ═══")
        print("     跑通 = %d ｜ 跑不通 = %d ／ 共 %d 条" % (ok, fail, len(CMDS)))
        if vacuous:
            print("     ○ ★【跑通但读的是原件】= %d 条：%s" % (len(vacuous), "、".join(vacuous)))
            print("       ⇒ ★ 对这些命令，本次「局外人」实测【为空】：它们仍在核对本席原席位，")
            print("         因为声明里的 canonical 是【绝对路径】。")
        truly = ok - len(vacuous)
        print("     ⇒ ★ 真正能被【复制品】跑通的 = %d / %d" % (truly, len(CMDS)))
        if truly == len(CMDS):
            print("     ✅「第三方不必经本席」——【实测成立】")
        else:
            print("     ★ 「第三方不必经本席」——【未完全成立】。")
            print("       ★ 故本席此前那句承诺，在实测前只是【口号】；测完才知道它的确切范围。")
        print("     ★ 本器的边界：只测【复制品在同一台机器上】；换台机器的结果本器【测不到】。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
