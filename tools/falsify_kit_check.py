#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""falsify_kit_check.py —— 证伪测试：把闸摘掉后，套件的第④e项【必须报 FAIL】。 v1.0.0

为什么
──────
轮105 我给同侪验证套件加了第④e项「控制存活性·推送闸会拦」。
★ 而**一个不会失败的检查，等于没有检查**（本席旧规）。
⇒ 故本器做【证伪】：**造一份把闸摘掉的 meow_push 副本**，
  用与套件【同一条断言】去跑，**断言它必须 FAIL**；再跑原件，**断言它必须 PASS**。
★ 实验室在 exp/_falsify_lab（副本），跑完清理；**原件一字不动**。
"""
from __future__ import annotations
import pathlib
import shutil
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

EXP = pathlib.Path(__file__).resolve().parent
LAB = EXP / "_falsify_lab"
ARGS = ["--nick", "占位", "--msg", "x", "--send", "--i-am-authorized"]


def assert_like_kit(pyfile: pathlib.Path):
    """★ 与套件第④e项【完全相同】的断言。"""
    r = subprocess.run([sys.executable, str(pyfile)] + ARGS, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=120)
    out = (r.stdout or "") + (r.stderr or "")
    return (r.returncode == 5) and ("拦下" in out), r.returncode, ("拦下" in out)


def main() -> int:
    print("═══ 证伪：第④e项 是否真会失败 ═══")
    if LAB.exists():
        shutil.rmtree(LAB, ignore_errors=True)
    LAB.mkdir(parents=True, exist_ok=True)
    # 副本需与原件同目录依赖（auth_policy / auth_split）
    for dep in ("auth_policy.py", "auth_split.py"):
        if (EXP / dep).is_file():
            shutil.copy2(EXP / dep, LAB / dep)

    orig = EXP / "meow_push.py"
    print("\n  ── ① 原件（闸在）──")
    ok, rc, has = assert_like_kit(orig)
    print("     断言(rc==5 ∧ 含拦下) = %s ｜ 退出码=%s ｜ 含拦下判词=%s" % (ok, rc, has))
    if not ok:
        print("     ★原件竟未通过 ⇒ 套件第④e项的前提不成立"); return 1

    print("\n  ── ② 摘掉闸的副本（应判 FAIL）──")
    src = orig.read_text(encoding="utf-8")
    # ★ 把策略闸的有效条件改成恒假 ⇒ 闸失效
    patched = src.replace('if verdict != "ALLOW":', 'if False:  # 证伪：闸被摘掉')
    if patched == src:
        print("     ★未能摘掉闸（未找到目标行）⇒ 证伪不成立"); return 1
    # ★★★★★ v1.1.0 修（重要）：**必须同时把真发分支也钉死**，否则副本会一路走到网络。
    #   轮105 初版只摘了闸 ⇒ 副本真的向 api.chuckfang.com 发出了【一次真实 HTTP 请求】
    #   （昵称用占位符「占位」）——**我造测试时没算它的波及范围**。本行即为此而加。
    patched2 = patched.replace('if not (a.send and a.i_am_authorized):', 'if True:  # 证伪：钉死神，绝不触网')
    if patched2 == patched:
        print("     ★未能钉死真发分支 ⇒ 拒绝运行（避免又一次真实外发）"); return 1
    lab = LAB / "meow_push_nogate.py"
    lab.write_text(patched2, encoding="utf-8")
    ok2, rc2, has2 = assert_like_kit(lab)
    print("     断言(rc==5 ∧ 含拦下) = %s ｜ 退出码=%s ｜ 含拦下判词=%s" % (ok2, rc2, has2))
    print("     ⇒ %s" % ("★如预期 FAIL" if not ok2 else "★★竟然仍 PASS ⇒ 第④e项是恒真检查！"))
    print("     ★ 本副本【双重钉死】（闸摘掉 ∧ 真发分支为真）⇒ 构造上不触网。")

    verdict = ok and (not ok2)
    print("\n  ── 判定 ──")
    print("  原件 PASS ∧ 摘闸副本 FAIL = %s" % verdict)
    print("  ⇒ %s" % ("第④e项【会失败】⇒ 它不是恒真检查" if verdict else "★结论不成立"))
    print("\n  ★ 实验室在 %s（已清理）；原件未动。" % LAB.name)
    shutil.rmtree(LAB, ignore_errors=True)
    return 0 if verdict else 1


if __name__ == "__main__":
    sys.exit(main())
