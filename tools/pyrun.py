# -*- coding: utf-8 -*-
"""pyrun.py —— 预编译前置之运行器（2026-10-14 立）

缘起：本席在同一类错（中文串内嵌半角双引号 ⇒ SyntaxError）上**三犯**
      （kj47.py／kj49.py／三面核验脚本）⇒ 判「已入口径 ≠ 已不再犯」
      ⇒ 故把「先 py_compile 再运行」由**自觉**改为**流程**。

用法：
    python pyrun.py <脚本路径> [脚本参数…]

行为：
    ★1 先 py_compile；**有错即止**并显式回显错误（不进入运行）
    ★2 通过后方 exec 运行；运行之 stderr／stdout 原样透传
    ★3 记一行「预编译结果」于标准输出，便于留痕
    ★4 退出码：编译失败 ⇒ 2；运行失败 ⇒ 子脚本之退出码
"""
import py_compile, runpy, subprocess, sys, pathlib

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)


def main() -> int:
    if len(sys.argv) < 2:
        print("用法：python pyrun.py <脚本路径> [脚本参数…]")
        return 1
    target = pathlib.Path(sys.argv[1]).resolve()
    if not target.exists():
        print("   ★目标不在：%s" % target)
        return 2
    # ★1 预编译（前置）
    try:
        py_compile.compile(str(target), doraise=True)
        print("   ★预编译 ✓ 通过：%s" % target.name)
    except py_compile.PyCompileError as e:
        print("   ★★预编译 ✗ 失败（★不进入运行）：")
        print("      %s" % str(e).strip().replace("\n", "\n      ")[:900])
        return 2
    # ★2 运行（以子进程，保参数与退出码）
    r = subprocess.run([sys.executable, str(target)] + sys.argv[2:])
    print("   ★运行结束：退出码 %d" % r.returncode)
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
