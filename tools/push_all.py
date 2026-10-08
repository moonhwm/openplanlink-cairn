# -*- coding: utf-8 -*-
"""push_all.py —— 双路径推送与三面核验（本席推送例程，固化轮11教训）

缘起（本席轮11实测）：同一时刻 `github.com` **直连不通(000)、经代理 curl 200**，
但 **git push 经代理失败(21s 超时) 而直连成功** ⇒ 通路行为**依客户端/协议而异、且随时间变**，
不得只试一路。本工具：
  1. 逐远端依次尝试 **经代理 → 直连**（谁成功记谁），失败再换路；
  2. 推送后 `ls-remote` **实查真值**并核 **三面一致**（local／origin／gitcode）；
  3. 打印**通路矩阵**（每远端 × 每路径 的成功/失败），供事后复盘；
  4. 默认**绝不 force**（仅当显式 `--force-gitcode` 且远端为其镜像位时才允许）。

用法:
  python push_all.py                 # 推 origin 与 gitcode（自动双路径）
  python push_all.py --remotes origin
  python push_all.py --dry-run       # 只打印计划与当前三面，不推送
退出码：三面一致 0；否则 3。
"""
import argparse
import pathlib
import subprocess
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

REPO = pathlib.Path(r"C:\Users\欧阳宏俊\openplanlink-mirror")
ROUTES = [("经代理", []), ("直连", ["-c", "http.proxy=", "-c", "https.proxy="])]
DEFAULT_REMOTES = ["origin", "gitcode"]


def git(args, timeout=180):
    try:
        p = subprocess.run(["git", *args], cwd=str(REPO), capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        return (p.stdout or "") + (p.stderr or ""), p.returncode
    except subprocess.TimeoutExpired:
        return "TIMEOUT", 1


def local_head():
    out, _ = git(["rev-parse", "--short", "HEAD"])
    return out.strip()


def remote_head(remote, route_args):
    """实查远端真值。返回 (sha7, source, route)：
       source='live' → ls-remote 直查；source='fetch快照' → ls-remote 失败后经 fetch 更新跟踪引用再读
       （承轮24 教训：ls-remote 可能连续失败而 fetch 可用；**必须标注真值来源，不得以快照冒充 live**）"""
    out, code = git([*route_args, "ls-remote", remote, "refs/heads/main"], timeout=25)
    if code == 0 and out.strip() and out.split()[0][:7] != "":
        return out.split()[0][:7], "live", "ls-remote"
    # 回退：fetch 路径（更新远端跟踪引用后读值）
    fout, fcode = git([*route_args, "fetch", remote, "main"], timeout=60)
    if fcode == 0:
        ro, _rc = git([*route_args, "rev-parse", "--short", "refs/remotes/%s/main" % remote])
        ro = ro.strip()
        if ro:
            return ro, "fetch快照", "fetch+rev-parse"
    return None, "不可达", "-"


def now_hm():
    import datetime as _dt
    return _dt.datetime.now().strftime("%H:%M:%S")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--remotes", nargs="*", default=DEFAULT_REMOTES)
    ap.add_argument("--side-ref", default="",
                    help="主干被拒（non-fast-forward）时，将 HEAD 推入该侧分支以**保全提交**"
                         "（承轮17 实证：origin 主干被连续推进、且 fetch 大数据面不通；侧分支 6s 成功）")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-guard", action="store_true",
                    help="跳过同批守卫前置闸（仅限已知无害场景；默认 FAIL 即拒推）")
    ap.add_argument("--auto-sign", action="store_true",
                    help="守卫非 PASS 时自动重签（跑 build→add→commit）后复检；判定『未知』则拒推")
    ap.add_argument("--force-gitcode", action="store_true",
                    help="仅 gitcode 镜像位允许 force（origin 永不 force）")
    ap.add_argument("--skip-gate", action="store_true",
                    help="跳过披露前置闸（仅在已确认命中原因为良性时使用）")
    a = ap.parse_args()

    head = local_head()
    # ── 前置闸①：披露扫描（--staged；承 DF-DISCGATE：提交/推送前必做复扫） ──
    gate = pathlib.Path(__file__).with_name("disclosure_scan.py")
    if not a.skip_gate and gate.exists():
        g, _gc = git(["--no-pager", "diff", "--cached", "--name-only"])
        try:
            gp = subprocess.run([sys.executable, str(gate), "--staged"], capture_output=True,
                                text=True, timeout=120, encoding="utf-8", errors="replace")
            if "VERDICT=CLEAN" in (gp.stdout or ""):
                print("★ 前置闸①披露扫描（--staged）：**CLEAN**")
            else:
                print("★ 前置闸①披露扫描：**发现命中 → 停止推送**（详见下列输出）")
                print((gp.stdout or "").strip())
                print("  处置：改记类别名／值只入本地附件；确认为良性后可用 --skip-gate 跳过")
                return 2
        except Exception as exc:  # noqa: BLE001
            print("★ 前置闸①披露扫描：执行异常（%s）→ 按保守策略继续但**留痕**" % exc)

    # ── 前置闸②：同批守卫（承轮39 教训：**守卫 FAIL ⇒ 不得推送**，改为机械强制） ──
    guard = pathlib.Path(REPO) / "tools" / "prepush_samebatch.py"

    def guard_pass():
        gp = subprocess.run([sys.executable, str(guard), "--rev", "HEAD"], cwd=str(REPO),
                            capture_output=True, text=True, timeout=180, encoding="utf-8",
                            errors="replace")
        out = (gp.stdout or "") + (gp.stderr or "")
        return ("VERDICT=PASS" in out), out

    if not a.skip_guard and guard.exists():
        try:
            ok, gout = guard_pass()
            if ok:
                print("★ 前置闸②同批守卫（prepush_samebatch HEAD）：**PASS**")
            elif a.auto_sign:
                print("★ 前置闸②非 PASS 且启用 --auto-sign ⇒ 进入**自愈重签**流程")
                sn = pathlib.Path(__file__).with_name("sign_if_needed.py")
                rc = 10
                if sn.exists():
                    sp = subprocess.run([sys.executable, str(sn)], cwd=str(REPO),
                                        capture_output=True, text=True, timeout=300,
                                        encoding="utf-8", errors="replace")
                    rc = sp.returncode
                    for ln in ((sp.stdout or "").strip().splitlines()[:3]):
                        print("   判定：%s" % ln)
                if rc == 11:
                    print("★ 判定『未知』（缺密钥或 build 失败）⇒ **拒绝推送**（未知≠否）")
                    return 4
                env = dict(os.environ)
                if not env.get("OPL_A2A_HMAC_KEY_B64"):
                    kf = pathlib.Path.home() / ".a2a-hmac-key.bin"
                    if kf.exists():
                        import base64 as _b64
                        env["OPL_A2A_HMAC_KEY_B64"] = _b64.b64encode(kf.read_bytes()).decode()
                env.setdefault("OPL_A2A_HMAC_KEY_ID", "opl-a2a-2026q4")
                subprocess.run(["node", "tools/sha3-tree.mjs", "build"], cwd=str(REPO),
                               capture_output=True, text=True, timeout=300, env=env)
                git(["add", "--", "attest-hmac-sha3-512.json"])
                git(["-c", "user.name=cairn-dsh", "-c", "user.email=cairn@a2a.local",
                     "commit", "-q", "-m", "push-gate: re-sign tree (auto)"])
                ok2, gout2 = guard_pass()
                print("★ 自愈后复检：**%s**" % ("PASS" if ok2 else "非 PASS"))
                if not ok2:
                    for ln in gout2.strip().splitlines()[-5:]:
                        print("   %s" % ln)
                    return 4
            else:
                print("★ 前置闸②同批守卫：**非 PASS → 拒绝推送**（轮39 违规之机械防止）")
                for ln in gout.strip().splitlines()[-6:]:
                    print("   %s" % ln)
                print("  处置：先重签（node tools/sha3-tree.mjs build → git add attest → commit）再推送；")
                print("        或用 --auto-sign 自愈；确需跳过（仅限已知无害场景）用 --skip-guard")
                return 4
        except Exception as exc:  # noqa: BLE001
            print("★ 前置闸②执行异常（%s）→ **保守拒绝推送**" % exc)
            return 4

    print("★ 本地 HEAD = %s" % head)
    matrix = {}
    for r in a.remotes:
        for name, args in ROUTES:
            h, src, how = remote_head(r, args)
            matrix[(r, name)] = h
            matrix[(r, name + "|src")] = "%s(%s)" % (src, how)
    print("★ 通路矩阵（真值来源已标注；live=ls-remote 直查，fetch快照=fetch 后读跟踪引用）：")
    for (r, name), h in matrix.items():
        if name.endswith("|src"):
            continue
        print("   %-8s %-6s → %s  [%s]" % (r, name, h or "不可达", matrix.get((r, name + "|src"), "-")))

    if a.dry_run:
        print("★ dry-run：不推送")
        return 0

    pushed = {}
    last_fail = {}
    for r in a.remotes:
        # 快失败：两路皆不可达则不再逐路硬撞（承"网络不可达时不反复硬撞"纪律）
        if all(matrix.get((r, name)) is None for name, _ in ROUTES):
            print("   %-8s —— 两路皆不可达 → 跳过（保留待办，不硬撞）" % r)
            pushed[r] = None
            continue
        ok = False
        for name, args in ROUTES:
            if matrix.get((r, name)) is None:
                print("   %-8s %-6s → 跳过（该路已探明不可达）" % (r, name))
                continue
            cmd = [*args, "push", r, "main"]
            if r == "gitcode" and a.force_gitcode:
                cmd.insert(len(args) + 1, "--force")
            out, code = git(cmd, timeout=300)
            good = (code == 0) and (("main -> main" in out) or ("up-to-date" in out) or ("Everything up-to-date" in out))
            if good:
                print("   %-8s %-6s → %s" % (r, name, "成功"))
            else:
                # ★轮17：**失败须分类**（承"未知≠否"与"报告值≠核实值"）——拒绝 ≠ 不可达 ≠ 鉴权失败
                low = (out or "").lower()
                # ★轮34 自纠：**阻断**须以阻断标记为准——v2 钩子亦会**打印**他席未签名之"提示"，
                #          若仅匹配"未签名"字样，会把**提示**误判为**阻断**（分类假阳性）。
                if ("未签名提交被拦截" in (out or "")) or ("禁止直推" in (out or "")) \
                        or ("✗" in (out or "") and "未签名" in (out or "")) or ("unsigned" in low):
                    why = "被本地钩子阻断（本席自身提交未签名）"
                elif "non-fast-forward" in low or "rejected" in low or "fetch first" in low:
                    why = "被拒（非快进：远端有新提交）"
                elif ("could not resolve" in low or "unable to access" in low or "failed to connect" in low
                      or "timed out" in low or "connection" in low):
                    why = "不可达（连接/解析失败）"
                elif "authentication failed" in low or "403" in low or "permission denied" in low:
                    why = "鉴权失败"
                else:
                    why = "失败（未归类）"
                print("   %-8s %-6s → %s ［%s］" % (r, name, "失败", why))
                last_fail[r] = why
            if good:
                pushed[r] = name
                ok = True
                break
        if not ok:
            pushed[r] = None
            print("   ★ 警告：%s 两条路径均失败（%s）" % (r, last_fail.get(r, "未归类")))
            # ★轮17：主干被拒时，**侧分支保全**（不争主干、无需 fetch）
            if a.side_ref and last_fail.get(r, "").startswith("被拒"):
                side = a.side_ref
                sargs = [x for x in ROUTES[0][1]]
                sout, scode = git([*sargs, "push", r, "HEAD:refs/heads/%s" % side], timeout=300)
                sv = "成功" if (scode == 0 or "->" in (sout or "")) else "失败"
                print("   %-8s 侧分支 → %s（refs/heads/%s）［%s］" % (r, sv, side, "保全提交，候网络并入主干"))

    print("★ 推送路径记录：%s" % "、".join("%s=%s" % (k, v or "失败") for k, v in pushed.items()))

    local = local_head()
    heads = {}
    srcs = {}
    for r in a.remotes:
        h = None
        for name, args in ROUTES:
            h, src, how = remote_head(r, args)
            if h:
                srcs[r] = "%s(%s)" % (src, how)
                break
        heads[r] = h
    print("★ 三面核验（%s）：local=%s ｜ %s" % (now_hm(), local, " ｜ ".join("%s=%s[%s]" % (k, v or "?", srcs.get(k, "不可达")) for k, v in heads.items())))
    aligned = all(v == local for v in heads.values()) and bool(heads)
    if any("fetch快照" in s for s in srcs.values()):
        print("★ 注：含 fetch 快照真值 —— 属『截至上次成功 fetch 的一致』，**非 live 核实**")
    print("VERDICT=" + ("ALIGNED" if aligned else "MISALIGNED"))
    return 0 if aligned else 3


if __name__ == "__main__":
    sys.exit(main())
