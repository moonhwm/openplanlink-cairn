# -*- coding: utf-8 -*-
"""gitpush.py —— 推送五步一体器物（2026-10-14 立）

缘起：本席屡以 `| Out-Null` 吞掉 `git add`／`git push` 之输出，致
      「一条坏路径使全批零暂存」与「推送失败而不知其因」（多次）⇒
      判「输出必回显」应与「预编译前置」同为**流程级**约束 ⇒ 故器物化。

五步（承《运行口径》章十、章十一、章十二）：
    ① 席位账件入仓（显式复制 frontier_ledger.jsonl 与 _version_snapshot.json）
    ② 校验行数与首末行
    ③ **显式列名** `git add -- <路径…>`（**绝不 `-A`**）
    ④ commit ＋ push（**输出全量回显**）
    ⑤ 核「未推 0」

★纪律：
    ★1 凡 `git add`／`commit`／`push` 之输出**一律回显**，绝不吞掉
    ★2 加入前逐路径 `Test-Path`（不存在则不加入，并**列名报告**）
    ★3 暂存后**核未含他席件**（`a2a_autonomous|hermes` 之数须为 0）
    ★4 推送后**核未推 0**；非 0 即如实报失败
    ★5 `--dry` 只示计划，不动仓库

用法：
    python gitpush.py --msg "提交说明" --add <仓内相对路径> [--add …] [--dry]
    python gitpush.py --msg "提交说明" --sync-only      # 仅同步账件并按 ①-③ 暂存
"""
import os, pathlib, subprocess, sys

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
SEAT = (HOME / "WPS Cloud" / "WPSDrive" / "29969771" / "WPS云盘" / "月之暗面的Plasma游乐场"
        / "A2A新席_石敢当Cairn_20260928")
CAIRN = HOME / "openplanlink-cairn"
GIT = r"A:\Git\cmd\git.exe"


def run(args, cwd=CAIRN, echo=True):
    r = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if echo:
        for ln in ((r.stdout or "") + (r.stderr or "")).splitlines():
            print("     │ " + ln[:150])
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main() -> int:
    argv = sys.argv[1:]
    dry = "--dry" in argv
    msg = "cairn: 随推"
    adds = []
    i = 0
    while i < len(argv):
        if argv[i] == "--msg" and i + 1 < len(argv):
            msg = argv[i + 1]; i += 2; continue
        if argv[i] == "--add" and i + 1 < len(argv):
            adds.append(argv[i + 1]); i += 2; continue
        i += 1

    print("═══ 推送五步 ｜ 仓 %s ═══" % CAIRN.name)
    print("① 席位账件入仓")
    for rel in ("ledger/frontier_ledger.jsonl", "ledger/_version_snapshot.json"):
        src, dst = SEAT / rel, CAIRN / rel
        if not src.exists():
            print("   ★源不在：%s" % rel); continue
        if not dry:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
        print("   ✓ %s ⇒ %d 行" % (rel, len(src.read_text(encoding='utf-8', errors='replace').splitlines())))

    print("② 校验行数与首末行")
    for rel in ("ledger/frontier_ledger.jsonl",):
        a = (SEAT / rel).read_text(encoding="utf-8", errors="replace").splitlines()
        b = (CAIRN / rel).read_text(encoding="utf-8", errors="replace").splitlines()
        same = len(a) == len(b) and a[0] == b[0] and a[-1] == b[-1]
        print("   席位 %d 行 ｜ 仓内 %d 行 ｜ 首末行一致 ⇒ %s" % (len(a), len(b), "✓" if same else "★不一致"))

    print("③ 显式列名暂存（★绝不 -A）")
    add_list = list(adds) + ["ledger/frontier_ledger.jsonl", "ledger/_version_snapshot.json"]
    present, missing = [], []
    for p in add_list:
        (present if (CAIRN / p).exists() else missing).append(p)
    if missing:
        print("   ★不加入（不在仓内，★列名报告，不吞）：%s" % ", ".join(missing))
    if dry:
        print("   · dry：将加 %d 件 ⇒ %s" % (len(present), ", ".join(present[:8])))
        return 0
    for p in present:
        rc, out = run([GIT, "add", "--", p])
        if rc != 0:
            print("   ★★git add 失败（%s）⇒ 如实报并中止" % p)
            return 3
    rc, out = run([GIT, "diff", "--cached", "--name-only"], echo=False)
    staged = [x for x in out.splitlines() if x.strip()]
    print("   暂存 %d 件" % len(staged))
    peer = [x for x in staged if ("a2a_autonomous" in x or "hermes" in x)]
    print("   ★含他席件 %d 件 ⇒ %s" % (len(peer), "✓" if not peer else "★须剔除：" + ", ".join(peer)))
    if peer:
        return 4
    if not staged:
        print("   ★无暂存 ⇒ 无提交可作（如实报）"); return 0
    for x in staged[:12]:
        print("     · " + x)

    print("④ commit ＋ push（★输出全量回显）")
    rc, _ = run([GIT, "-c", "user.name=守藏(DF-DOC-01)", "-c", "user.email=shou-cang@openplanlink.local",
                 "commit", "-q", "-m", msg])
    if rc != 0:
        print("   ★commit 失败 ⇒ 中止（不推送）"); return 5
    env = dict(os.environ)
    kb = (HOME / ".a2a-hmac-key.bin").read_bytes()
    import base64
    env["OPL_A2A_HMAC_KEY_B64"] = base64.b64encode(kb).decode()
    env["OPL_A2A_HMAC_KEY_ID"] = "opl-a2a-2026q4"
    r = subprocess.run([GIT, "push", "origin", "main"], cwd=str(CAIRN), capture_output=True,
                       text=True, encoding="utf-8", errors="replace", env=env)
    for ln in ((r.stdout or "") + (r.stderr or "")).splitlines():
        print("     │ " + ln[:150])

    print("⑤ 核未推 0")
    rc, out = run([GIT, "log", "origin/main..HEAD", "--oneline"], echo=False)
    n = len([x for x in out.splitlines() if x.strip()])
    print("   未推 %d ⇒ %s" % (n, "✓ 推送成功" if n == 0 else "★推送失败（如实报）"))
    return 0 if n == 0 else 6


if __name__ == "__main__":
    sys.exit(main())
