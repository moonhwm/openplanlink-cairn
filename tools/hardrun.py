# -*- coding: utf-8 -*-
"""hardrun.py —— 硬超时运行器（承 led_1584 之复盘：网络型重活须包硬超时）（2026-10-14 立）

★缘起：doc_refresh --budget 300 曾 17 分钟未归、输出止于预编译、进程极小 ⇒ 疑网络轮询卡滞。
★用法：python hardrun.py <秒> <脚本路径> [参数…]
★行为：★以 subprocess 启动目标；★到限未归 ⇒ 立即终止（kill）并报 ★HARDTIMEOUT；
       ★归则透传其退出码与输出（★逐行即时转发）。
★守界：★不回显凭据；★本器只包一层超时，不改被包者之任何行为。
"""
import subprocess, sys, threading, time, queue

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)


def _reader(pipe, q):
    for line in pipe:
        q.put(line)
    q.put(None)


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    try:
        limit = int(sys.argv[1])
    except ValueError:
        print("   秒数须为整数：%s" % sys.argv[1]); return 1
    script = sys.argv[2]
    args = sys.argv[3:]
    t0 = time.time()
    p = subprocess.Popen([sys.executable, script] + args,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         encoding="utf-8", errors="replace")
    q = queue.Queue()
    threading.Thread(target=_reader, args=(p.stdout, q), daemon=True).start()
    print("   ★硬超时器：限 %d s ｜ 目标 %s" % (limit, script.split("\\")[-1].split("/")[-1]))
    killed = False
    sentinel = False
    while True:
        try:
            line = q.get(timeout=1.0)
        except queue.Empty:
            line = None
        if line is None:
            if p.poll() is not None:
                break
            # ★读线程之哨兵已至而子进程未归 ⇒ 视同输出终止
            sentinel = True
        elif line:
            print("   | " + line.rstrip("\n")[:140])
            sentinel = False
        # ★限时检查在每一轮皆行（★不因阻塞而失时）
        if p.poll() is None and time.time() - t0 > limit:
            p.kill()
            killed = True
            print("   ★★HARDTIMEOUT（%d s）⇒ 已终止（PID %d）" % (limit, p.pid))
            break
        if p.poll() is not None and sentinel:
            break
    rc = p.wait()
    dt = time.time() - t0
    if killed:
        print("   ★运行结束：HARDTIMEOUT ｜ 用时 %.1f s" % dt)
        return 124
    print("   ★运行结束：退出码 %d ｜ 用时 %.1f s" % (rc, dt))
    return rc


if __name__ == "__main__":
    sys.exit(main())
