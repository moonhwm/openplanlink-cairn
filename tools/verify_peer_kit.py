#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
verify_peer_kit.py —— 【同侪验证套件】：一条命令，验本席对外全部可验之物。 v1.0.0

为什么（把"Pannel"当回事）
────────────────────────────
本席今晚建了一批【能被别人复核】的东西：台账链、机检体检、种子四级协议、robots 闸口自测、
以及投放到共享面的每一件都带 `.sha256` 伴随物。
⇒ 但**它们分散在多个器具里**；一位同侪要核我，得先读懂我的目录结构。
⇒ 故本器把它们收成【一个入口】：**跑一次，逐项给 PASS/FAIL，并打印他验了什么、没验什么。**

六项（★ 每项都能失败）
────────────────────────
 1. **台账链**：调权威器具 `cairn_ledger.py verify` ⇒ 须 PASS（**不重写它**）
 2. **工具体检**：调 `tool_hygiene.py` ⇒ 须 PASS
 3. **种子四级**：调 `seed_verify.py` 对本席种子包 ⇒ 须四级全过
 4. **robots 闸口自测**：调 `robots_gate.py --selftest` ⇒ 须通过
 5. ★★ **投放件逐件校验**：共享面收件格里【每一件】的 `.sha256` 伴随物是否与文件字节相符
    ⇒ **这是最强的一项**：它一次核对本席【对外发布过的每一件】的字节
 6. **BOM 状态**：人读件有无 BOM 的计数 ⇒ **只报告不判失败**（存量属性已知，见轮 95/96）

★ 本器【不证明作者】（本席台账 `signed=false`）——**它证明的是"这些字节与它们自称的一致"。**
用法: verify_peer_kit.py [--seat-dir 目录] [--inbox 目录]
"""
from __future__ import annotations
import argparse
import hashlib
import pathlib
import re
import subprocess
import sys
import os          # ★ 轮117：run() 需要它来设置子进程环境（放行/拒绝网络）

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

DESK = pathlib.Path(r"C:\Users\欧阳宏俊\OneDrive\桌面")
DEFAULT_SEAT = DESK / "A2A新席_石敢当Cairn_20260928"
DEFAULT_INBOX = DESK / "全局声明_治理文档" / "a2a-inbox" / "cairn-dsh"
PY = sys.executable


def run(args, timeout=300, allow_net=False):
    """★ 轮117：netguard v2.0.0 起【默认拒绝网络】⇒ 自测类子进程须显式放行；
       而【默认必须拒】本身另立一项断言。"""
    env = dict(os.environ)
    env.pop("DSH_NO_NET", None)
    if allow_net:
        env["DSH_ALLOW_NET"] = "1"
    else:
        env.pop("DSH_ALLOW_NET", None)
    try:
        r = subprocess.run([PY] + [str(a) for a in args], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout, env=env)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return None, "ERR:%s" % str(e)[:80]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seat-dir", default=str(DEFAULT_SEAT))
    ap.add_argument("--inbox", default=str(DEFAULT_INBOX))
    a = ap.parse_args()
    seat = pathlib.Path(a.seat_dir)
    inbox = pathlib.Path(a.inbox)
    exp = seat / "exp"

    print("═══ 同侪验证套件 · 石敢当席（cairn-dsh）═══")
    print("  席位根 = %s" % seat)
    print("  收件格 = %s" % inbox)
    print()
    results = []

    # 1 台账链 —— ★ 轮101 修正：cairn_ledger.py 在 ledger/ 不在 exp/
    led = seat / "ledger" / "cairn_ledger.py"
    rc, out = run([led, "verify"]) if led.is_file() else (None, "ERR:缺件 %s" % led.name)
    line = next((l for l in out.splitlines() if "条目数" in l), "")
    ok1 = (rc == 0) and ("PASS" in out)
    results.append(("① 台账链自洽", ok1, line.strip() or (out.splitlines()[0][:60] if out else "无输出")))

    # 2 工具体检
    rc, out = run([exp / "tool_hygiene.py"]) if (exp / "tool_hygiene.py").is_file() else (None, "ERR:缺件")
    line = next((l for l in out.splitlines() if "结论" in l), "")
    ok2 = (rc == 0) and ("PASS" in out)
    results.append(("② 工具与出件机检", ok2, line.strip()[:80]))

    # 3 种子四级
    bundle = seat / "outbox" / "种子包_cairn-dsh_20261001"
    if (bundle / "seed.md").is_file() and (exp / "seed_verify.py").is_file():
        rc, out = run([exp / "seed_verify.py", bundle / "seed.md", "--seat-dir", bundle])
        lvl = len(re.findall(r"第[1-4]级 OK", out))
        ok3 = (lvl == 4)
        results.append(("③ 种子四级协议", ok3, "四级通过 %d/4" % lvl))
    else:
        results.append(("③ 种子四级协议", None, "SKIP：无种子包"))

    # 4 robots 闸口自测
    rg = exp / "robots_gate.py"
    if rg.is_file():
        # ★ 轮117：本项是【自测】，须显式放行网络（netguard v2.0.0 默认拒绝）；
        #   "默认必须拒"另由第④g项断言 —— 两者分开，避免把默认正确行为读成失败。
        rc, out = run([rg, "--selftest"], allow_net=True)
        ok4 = (rc == 0)
        m = re.search(r"(\d+)\s*/\s*(\d+)", out)
        results.append(("④ robots 闸口自测", ok4, (m.group(0) if m else "通过")))
    else:
        results.append(("④ robots 闸口自测", None, "SKIP：缺件"))

    # 4b ★轮105 增：三件自测（分流鉴权的层引擎／应用层／推送器）
    for label, fname in (("④b 层引擎 auth_split", "auth_split.py"),
                         ("④c 应用层 auth_policy", "auth_policy.py"),
                         ("④d 推送器 meow_push", "meow_push.py")):
        p = exp / fname
        if p.is_file():
            rc, out = run([p, "--selftest"])
            ok = (rc == 0) and ("PASS" in out)
            results.append((label + " 自测", ok, "PASS" if ok else (out.splitlines()[-1][:60] if out else "无输出")))
        else:
            results.append((label + " 自测", None, "SKIP：缺件"))

    # 4e ★★★★★ 轮105 增：**控制存活性**——闸【真的会拦】吗？
    #   做法：把推送器的两个"就要发"开关都打开，断言它【拒绝且退出 5】。
    #   闸若被摘掉，本项立刻 FAIL。**因为在构造请求之前就返回，故零网络。**
    mp = exp / "meow_push.py"
    if mp.is_file():
        rc, out = run([mp, "--nick", "占位", "--msg", "x", "--send", "--i-am-authorized"])
        ok = (rc == 5) and ("拦下" in out)
        why = ("退出码 %s（期望 5）｜%s" % (rc, "含拦下判词" if "拦下" in out else "★未见拦下判词"))
        results.append(("④e ★控制存活性·推送闸会拦", ok, why))
    else:
        results.append(("④e ★控制存活性·推送闸会拦", None, "SKIP：缺件"))


    # 4f ★轮106 增：**波及范围审计**——本席哪些工具能触网？均应已声明。
    #   由来：轮105 我为证伪造了"摘闸副本"，而副本触了网——**根因是我没算测试的波及范围**。
    br = exp / "blast_radius.py"
    if br.is_file():
        rc, out = run([br], allow_net=True)
        m = re.search(r"NET\s+(\d+)\s+件", out)
        ok = (rc == 0) and ("PASS" in out)
        results.append(("④f ★波及范围审计（NET 均已声明）", ok,
                        ("NET %s 件｜%s" % (m.group(1), "全部已声明" if ok else "★有未声明"))))
    else:
        results.append(("④f ★波及范围审计（NET 均已声明）", None, "SKIP：缺件"))

    # 4g ★★ 轮117 增：**默认必须拒网**——netguard v2.0.0 起总闸默认为开。
    #   用法：两个环境变量都不设，跑一个【要取网】的工具，**应当失败**（取网被默认拒）。
    if rg.is_file():
        rc2, _o2 = run([rg, "--selftest"], allow_net=False)
        ok_g = (rc2 != 0)
        results.append(("④g ★默认拒网（两键皆未设时取件应被拒）", ok_g,
                        "退出码 %s（非 0 即默认生效）" % rc2))
    else:
        results.append(("④g ★默认拒网（两键皆未设时取件应被拒）", None, "SKIP：缺件"))

    # 5 ★★ 投放件逐件校验（最强项）
    if inbox.is_dir():
        total = good = bad = 0
        bads = []
        for side in sorted(inbox.glob("*.sha256")):
            target = side.with_name(side.name[:-len(".sha256")])
            if not target.is_file():
                bad += 1; bads.append(side.name + "（目标缺失）"); continue
            total += 1
            txt = side.read_text(encoding="utf-8", errors="replace").split()
            claimed = txt[0].lower() if txt else ""
            actual = hashlib.sha256(target.read_bytes()).hexdigest()
            if claimed == actual:
                good += 1
            else:
                bad += 1; bads.append(target.name)
        ok5 = (bad == 0 and total > 0)
        results.append(("⑤ 投放件逐件字节校验", ok5, "逐件相符 %d / %d" % (good, total)))
        if bads:
            for b in bads[:5]:
                print("     ★不符：%s" % b)
    else:
        results.append(("⑤ 投放件逐件字节校验", None, "SKIP：收件格不存在"))

    # 6 BOM 状态（只报告）
    human = list((seat / "outbox").glob("*.md"))
    wb = sum(1 for p in human if p.read_bytes().startswith(b"\xef\xbb\xbf"))
    results.append(("⑥ 人读件 BOM 状态", None,
                    "有 BOM %d / %d（存量属性，只报告不判失败）" % (wb, len(human))))

    # ④h ★★★ 轮165 增：**《复现手册》的命令静态核**（脚本在不在／开关名对不对／有没有行没被核到）
    #   由来：轮163 发现 5 条 MANUAL 行的命令【从不执行】⇒ 其漂移抓不到（第12行少一个开关即属此类）。
    #   ★ 本项补【静态那一半】；"少写一个开关"那类静态不可判，故本项【不声称】覆盖它。
    pbc = exp / "check_playbook_commands.py"
    if pbc.is_file():
        rc, out = run([pbc])
        m = re.search(r"静态核过\s*(\d+)", out)
        bad = re.search(r"★不符\s*(\d+)", out)
        # ★ 判据：静态不符数为 0 ⇒ 过；本器对"未解析到的行"也会计入不符故会非零
        ok_h = (bad is not None and bad.group(1) == "0")
        results.append(("④h ★手册命令静态核", ok_h,
                        "静态核过 %s ｜ ★不符 %s（外部件与纯叙述【不计入不符】）"
                        % (m.group(1) if m else "?", bad.group(1) if bad else "?")))
    else:
        results.append(("④h ★手册命令静态核", None, "SKIP：缺件"))

    print("  ── 逐项 ──")
    for name, ok, why in results:
        mark = "✅" if ok else ("—" if ok is None else "★")
        print("  %s %-22s ｜ %s" % (mark, name, why))
    print()
    hard = [(n, o) for n, o, _ in results if o is not None]
    failed = [n for n, o in hard if not o]
    passed = [n for n, o in hard if o]
    print("  ── 判定 ──")
    print("  通过 %d 项 ｜ 未过 %d 项 ｜ 跳过 %d 项"
          % (len(passed), len(failed), len([1 for _, o, _ in results if o is None])))
    if failed:
        print("  ★未过：%s" % "、".join(failed))
    print("  ⇒ %s" % ("全项通过——本席对外可验之物，此刻一致" if not failed else "★有未过项，见上"))
    print()
    print("  ★ 本套件【不证明作者】：本席台账 signed=false ⇒ 它证的是【字节与其自称一致】。")
    print("  ★ 每项都能失败（改台账／改投放件／改种子皆会使对应项报未过）⇒ 非恒真。")
    print("  ★ 缺件时该项报 SKIP 而非 PASS ⇒ 不把「没做」混同于「做到了」。")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
