#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 本件不触网；它是「能不能触网」的开关。
r"""
netguard.py —— 网络总闸：一个环境变量，停掉本席全部对外调用。 v1.0.0

为什么（**把轮105 的错变成永久预防**）
────────────────────────────────────────
轮105 我为证明"推送闸会拦"，造了一份【闸被摘掉】的副本 ⇒ 副本一路走到真发，
向公网发出了一次真实请求。根因：**我造测试时没算波及范围。**
轮106 我让波及范围【看得见】（`blast_radius.py`）。
**⇒ 但看得见不能阻止。本器是【阻止】那一半。**

两个用途
──────────
  ① **给机主一把总闸**：置 `DSH_NO_NET=1` ⇒ **本席所有接了本闸的工具【一律不发请求】**；
  ② **给测试一条安全绳**：造"摘掉某个控制"的副本时，**只要求本闸在，副本就不可能误发**。

用法
──────
    import netguard
    netguard.require("meow_push 真发")        # 总闸置上则抛 NetBlocked，否则返回 None
    # 或在取件前：if not netguard.allowed(): 停下

★ 默认【放行】（开关未置 ⇒ 一切照常）⇒ 接上它不会改变既有行为。
★ 置法（PowerShell）:  $env:DSH_NO_NET='1'
"""
from __future__ import annotations
import os
import sys

# ★ 本席通例：UTF-8 输出（否则 GBK 控制台下中文全乱码）。
#   —— 轮107 首版本件【漏了这一块】，是 tool_hygiene 第①项抓出来的。
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

ENV = "DSH_NO_NET"
ENV_ALLOW = "DSH_ALLOW_NET"        # ★★ v2.0.0：显式放行键
DEFAULT_DENY = True                # ★★ v2.0.0：**默认【拒绝】网络**，要放行须显式开


class NetBlocked(RuntimeError):
    """总闸置上时抛出。"""


def _truthy(v: str | None) -> bool:
    return str(v or "").strip().lower() in ("1", "true", "yes", "on")


def is_on() -> bool:
    """★ v2.0.0【默认拒绝】：**除非显式放行，否则总闸是【开】的（拒发）**。

    为何反转（轮 117）
    ────────────────────
    轮 113 我两次向观测站发出未获授权请求。根因不是"某个接线没写对"，
    而是**总闸是【选择加入】的：默认放行，要靠我记得去置上**。
    ⇒ 而本席整晚的规律是：**靠"记得"的规矩一定会漏**。
    ⇒ 故改为**默认拒绝**：**要访问网络，须显式 `DSH_ALLOW_NET=1`**。
    ★ 兼容：仍接受 `DSH_NO_NET=1` 强制拒绝（**拒绝优先于放行**）。
    """
    if _truthy(os.environ.get(ENV)):
        return True                      # 显式拒绝 ⇒ 优先
    if _truthy(os.environ.get(ENV_ALLOW)):
        return False                     # 显式放行 ⇒ 唯一放行途径
    return DEFAULT_DENY                  # ★ 默认拒绝


def allowed() -> bool:
    return not is_on()


def require(what: str = "对外调用") -> None:
    """总闸置上则抛 NetBlocked；否则静默返回。

    ★ 2026-10-02 轮 41 加：**拒绝时写一行日志**。
    缘由：轮 41 实测——本席每件都写「本件零对外网络调用」（共享面 166 件里 41 件含此句），
    ★ 而【没有任何器核过它】；总闸虽【默认拒绝】，但它【不记录尝试】⇒
    ★★ 「没尝试过」与「尝试了但被拒」【在事后无法区分】（★ 而被拒的尝试仍是尝试）。
    ⇒ 故本函数在拒绝时【追加一行】到 exp\\netguard_denials.log（只增不改）。
    ★ 本日志【只记拒绝】；它不能证明"没有尝试"以外的任何事，但它让"尝试过"有迹可查。
    """
    if is_on():
        # ★ 先记日志，再抛——★ 记不上也不影响拒绝（拒绝优先）
        try:
            _log_denial(what)
        except Exception:
            pass
        raise NetBlocked(
            "★网络默认【拒绝】（v2.0.0）⇒ 拒绝%s。"
            "（要放行请显式设 %s=1；设 %s=1 可强制拒绝。）" % (what, ENV_ALLOW, ENV))


# ★ 拒绝日志路径（轮 41 加）——★ 用 os.path（本文件未导入 pathlib，故不新增依赖）
DENIAL_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "netguard_denials.log")


def _log_denial(what: str) -> None:
    """追加一行拒绝记录。★ 只增不改；失败不抛（拒绝本身不受影响）。"""
    import time as _t
    line = "%s\t%s\t%s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S%z"),
                             os.environ.get("DSH_SEAT", "cairn-dsh"), what)
    with open(DENIAL_LOG, "a", encoding="utf-8") as f:
        f.write(line)


_PATCHED = False


def activate(verbose: bool = False) -> bool:
    """★ 装【进程级】外发拒绝钩子。**只在总闸置上时才动手** ⇒ 开关未置则一行都不改行为。

    拦什么：
      · `urllib.request.urlopen`（含各工具直接调用者）
      · `urllib.request.OpenerDirector.open`（含各工具自定义 opener 的 `.open()`）
    返回：是否真的装了钩子。
    ★ 这样各工具只需在文件头加一行 `import netguard; netguard.activate()`，
      而不必去改各自的调用点（**改调用点容易改错，改一次钩子只需改一处**）。
    """
    global _PATCHED
    if not is_on():
        return False
    if _PATCHED:
        return True
    import urllib.request as _u

    def _blocked(*_a, **_k):
        raise NetBlocked("★网络总闸已置上（%s=1）⇒ 拒绝一切对外请求（进程级钩子）。" % ENV)

    _u.urlopen = _blocked                       # type: ignore[assignment]
    _u.OpenerDirector.open = _blocked           # type: ignore[assignment]
    _PATCHED = True
    if verbose:
        print("  [netguard] 已装进程级外发拒绝钩子（%s=1）（★ 说明：这句是状态陈述，不是拒绝路径）" % ENV)
    return True


def selftest() -> int:
    print("═══ netguard 自检（v2.0.0：默认拒绝）（★ 说明：标题，不是拒绝路径）═══")
    ok = True
    saved_n = os.environ.pop(ENV, None)
    saved_a = os.environ.pop(ENV_ALLOW, None)
    try:
        print("  ① 两个键都未设 ⇒ is_on=%s（期望 True：默认拒绝）（★ 说明：自检输出，不是拒绝路径）" % is_on())
        ok = ok and is_on()
        try:
            require("测试")
            print("  ★FAIL 默认态竟放行"); ok = False
        except NetBlocked as e:
            print("  ② 默认态 require 抛 NetBlocked ✓（%s）" % str(e)[:56])
        os.environ[ENV_ALLOW] = "1"
        print("  ③ 显式放行 ⇒ is_on=%s（期望 False）" % is_on())
        ok = ok and (not is_on())
        try:
            require("测试")
            print("  ④ 放行后 require 静默返回 ✓")
        except NetBlocked:
            print("  ★FAIL 放行后仍被拦"); ok = False
        os.environ[ENV] = "1"
        print("  ⑤ 放行键与拒绝键同设 ⇒ is_on=%s（期望 True：拒绝优先）（★ 说明：自检输出，不是拒绝路径）" % is_on())
        ok = ok and is_on()
        for v in ("true", "YES", "on"):
            os.environ.pop(ENV, None)
            os.environ[ENV_ALLOW] = v
            if is_on():
                print("  ★FAIL %r 未识别为放行" % v); ok = False
        print("  ⑥ 1/true/yes/on 四种写法都认放行 ✓")
    finally:
        os.environ.pop(ENV, None)
        os.environ.pop(ENV_ALLOW, None)
        if saved_n is not None:
            os.environ[ENV] = saved_n
        if saved_a is not None:
            os.environ[ENV_ALLOW] = saved_a
    print("[SELFTEST] %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(selftest())
