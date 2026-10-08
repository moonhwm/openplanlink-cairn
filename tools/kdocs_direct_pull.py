# -*- coding: utf-8 -*-
"""kdocs 直取：以 kimi-work 版 kdocs-cli v2.6.13 之 drive read-file 拉取全文
参数要点：必填 **link_id**（非 file_id）——官方 references/wps.md 明载。
产物：<原名>_正文副本_20261009_CAIRN-DIRECT.md（只增不改）；零凭据（不外显 token）。
"""
import json, pathlib, subprocess, sys, time

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

CLI = str(pathlib.Path.home() / ".kimi-work" / "bin" / "kdocs-cli.exe")
DOCX = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\Plan提示词工程\openplanlink-docx")

TARGETS = [
    ("A2A算力分配与分布式协同深化案_v0.1_2026-10-05.otl", "cgeO17yb4eiI"),
    ("A2A线收官总账_2026-10-05.otl", "cplH408hcQMF"),
    ("A2A网络全面优化整合架构方案.otl", "cjj1X42H8FMP"),
    ("A2A项目四件套完整文字记录_上.otl", "ccmYOO3QvUyd"),
    ("A2A项目四件套完整文字记录_中.otl", "cg0IMPqFxDn7"),
    ("A2A项目四件套完整文字记录_下.otl", "co3jGF2ridX9"),
    ("WPS十件重读批注_k3-govdoc-seat_2026-10-05.otl", "caBn4BzDaBMO"),
    ("十件文书批注_首件主DOCX母本与协同面发现_DF-MIN-2026-1005-K3-01.otl", "ctpxZ2X2JxkG"),
    ("十件文书批注_四件套中卷_DF-MIN-2026-1005-K3-02.otl", "cp0wHNiF4XVj"),
    ("十件文书批注_四件套上卷_DF-MIN-2026-1005-K3-03.otl", "cm4IPhTYznTs"),
    ("十件文书批注_四件套下卷_DF-MIN-2026-1005-K3-04.otl", "cndYJKCF7len"),
    ("十件文书批注_蓝图跨生态不可读登记暨纲要母本_DF-MIN-2026-1005-K3-05.otl", "cdnTX6c3i3WF"),
    ("算力分配与分布式协同深化报告（暨现代化前沿网站开发实战规划）_DF-ORD-2026-1005-K3-01.otl", "cn8TJyXeLyop"),
    ("OpenPlanLink全局声明与Agent-to-Agent网络建设纲要.otl", "ci2ybbMcccFi"),
]

ok = 0
rows = []
for name, lid in TARGETS:
    out = DOCX / (name + "_正文副本_20261009_CAIRN-DIRECT.md")
    if out.exists() and out.stat().st_size > 800:
        print("  · 已存在，跳过：%s" % out.name[:70]); ok += 1; rows.append((name, "已有", out.stat().st_size)); continue
    t0 = time.time()
    try:
        r = subprocess.run([CLI, "drive", "read-file", "--args", json.dumps({"link_id": lid})],
                           capture_output=True, timeout=120)
        raw = (r.stdout or b"").decode("utf-8", "replace")
        stderr = (r.stderr or b"").decode("utf-8", "replace")
    except Exception as e:
        print("  × %-46s 调用异常：%s" % (name[:46], str(e)[:50])); rows.append((name, "异常", 0)); continue
    try:
        j = json.loads(raw)
    except Exception:
        print("  × %-46s 非 JSON：%s" % (name[:46], (raw[:70] or stderr[:70]).replace("\n", " ")))
        rows.append((name, "非JSON", 0)); continue
    code = j.get("code")
    data = j.get("data") or {}
    content = data.get("content") if isinstance(data, dict) else None
    if code == 0 and content:
        head = ("> 提取席：A2A新席_石敢当Cairn（a2a-node-local）｜来源：**kdocs 云直取**（kdocs-cli v2.6.13 `drive read-file`，link_id `%s`）｜"
                "提取时间：%s｜提取方式：本机直取（非转储、非宿主）｜零凭据\n\n") % (lid, time.strftime("%Y-%m-%d %H:%M"))
        out.write_text(head + content, encoding="utf-8", newline="\n")
        ok += 1
        rows.append((name, "★直取成功", len(content)))
        print("  ★ %-46s ⇒ %7d 字符 ｜ %.2fs" % (name[:46], len(content), time.time()-t0))
    else:
        msg = (j.get("message") or data.get("message") or "")[:60] if isinstance(data, dict) else ""
        print("  × %-46s code=%s ｜ %s" % (name[:46], code, msg))
        rows.append((name, "失败 code=%s" % code, 0))
    time.sleep(0.6)

print("\n  成功/已有=%d/%d" % (ok, len(TARGETS)))
for n, s, c in rows:
    print("   %-8s %7d ｜ %s" % (s, c, n[:56]))
