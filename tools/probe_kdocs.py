# -*- coding: utf-8 -*-
"""probe_kdocs.py —— kdocs 连通性小探针（30 s）（承《运行口径》章二十三第 3 条）（2026-10-14 立）

★用途：以极小请求试连 kdocs（drive list-my-files，page_size=3，限 25 s）⇒
        ★OK ⇒ 可补跑例行①；★TIMEOUT/FAIL ⇒ 如实报并继续暂缓。
★守界：★只读（list 只取 3 条之名与 id 前 6）｜★不回显凭据。
"""
import json, pathlib, subprocess, sys, time

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
H = pathlib.Path.home()
CLI = H / ".kimi-work" / "bin" / "kdocs-cli.exe"


def main() -> int:
    t0 = time.time()
    try:
        r = subprocess.run(
            [str(CLI), "drive", "list-my-files",
             "--args", json.dumps({"page_size": 3}, ensure_ascii=False)],
            capture_output=True, text=True, encoding="utf-8", timeout=25)
    except subprocess.TimeoutExpired:
        print("   ★TIMEOUT（25 s）⇒ kdocs 拉取仍卡滞 ⇒ 例行①继续暂缓 ｜ 用时 %.1f s"
              % (time.time() - t0))
        return 2
    dt = time.time() - t0
    if r.returncode != 0:
        print("   ★FAIL（退出码 %d，%.1f s）：%s" % (r.returncode, dt, r.stderr[:90]))
        return 3
    try:
        items = ((json.loads(r.stdout).get("data") or {}).get("items")) or []
        print("   ✓ OK（%.1f s）⇒ 得 %d 件（首页）｜ 例：%s" % (
            dt, len(items), items[0].get("name")[:36] if items else "（空）"))
        return 0
    except Exception as e:
        print("   ★响应解析失败（%.1f s）：%s" % (dt, str(e)[:80]))
        return 4


if __name__ == "__main__":
    sys.exit(main())
