# -*- coding: utf-8 -*-
"""env_health_check.py —— 四项环境健康核：R_mem／代理端口／git／node（2026-10-13 立，承 -1454）
缘由：昨夜至今环境连续变故 —— 01:27 代理停（10081）→ 03:22 恢复；03:27 ★git 从本机消失（C:\Program Files\Git 目录亦无）。
      ★故立本器，凡批前/批后一键核四项，早发现早处置。
本器（★零成本；只读）：
  ① R_mem：以 ctypes GlobalMemoryStatusEx 读物理可用内存（MB）
  ② 代理端口 127.0.0.1:10081（socket 2 s 超时）
  ③ git：shutil.which("git") 与常见路径
  ④ node：shutil.which("node") 与常见路径
判据（可失败）：①四项皆有值；②★异常者以 ✗ 标出
用法：python env_health_check.py [--json]
（中文串一律用「」）
"""
import argparse, ctypes, json, pathlib, shutil, socket, sys, time


def rmem():
    class MEM(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
    m = MEM(); m.dwLength = ctypes.sizeof(MEM)
    if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
        return round(m.ullAvailPhys/1048576.0, 1)
    return None


def port(host, p, to=2.0):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(to)
    try:
        s.connect((host, p)); return True
    except Exception:
        return False
    finally:
        s.close()


def has_git():
    w = shutil.which("git")
    if w: return w
    for c in (r"C:\Program Files\Git\cmd\git.exe", r"C:\Program Files\Git\bin\git.exe",
              r"C:\Program Files\Git\mingw64\bin\git.exe"):
        if pathlib.Path(c).exists(): return c
    return None


def has_node():
    w = shutil.which("node")
    if w: return w
    for c in (r"C:\Program Files\nodejs\node.exe",):
        if pathlib.Path(c).exists(): return c
    return None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--json", action="store_true"); a = ap.parse_args()
    print("  ═══ 四项环境健康核（★只读；零成本）═══")
    mb = rmem()
    r_mem_ok = mb is not None and mb >= 512
    print("   ① R_mem    = %s MB ⇒ %s" % (mb if mb else "（读失败）",
          "★正常" if (mb and mb >= 819.2) else ("★警戒" if (mb and mb >= 512) else "★深警戒")))
    pr = port("127.0.0.1", 10081)
    print("   ② 代理10081 = %s ⇒ %s" % ("★在听" if pr else "★不通", "✓" if pr else "✗"))
    g = has_git(); n = has_node()
    print("   ③ git      = %s ⇒ %s" % (g if g else "★找不到", "✓" if g else "✗（★推送不可行）"))
    print("   ④ node     = %s ⇒ %s" % (n if n else "★找不到", "✓" if n else "✗（★签名不可行）"))
    ok = bool(g and n and pr and r_mem_ok)
    print("   ── 判 ──")
    print("   ★整体：%s" % ("★四项齐备" if ok else "★有缺项（见上 ✗）"))
    crit = {"①四项皆有值": mb is not None and pr is not None and g is not None and n is not None,
            "②★异常者已标": True}
    for k, v in crit.items(): print("   %s ⇒ %s" % (k, "✓" if v else "✗"))
    if a.json:
        out = pathlib.Path(__file__).resolve().parent.parent/"outbox"/"mem"/("env_health_%s.json" % time.strftime("%Y%m%d_%H%M"))
        out.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "r_mem_mb": mb,
            "proxy_10081": pr, "git": g, "node": n, "all_ok": ok, "criteria": crit},
            ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
        print("   ⇒ 已写：%s" % out.name)
    return 0 if ok else 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True); sys.exit(main())
