# -*- coding: utf-8 -*-
"""时点行审计器（仪器化，防再犯）
- 扫描件内"时点：北京时间 **YYYY-MM-DD HH:MM**"行，与文件 mtime 比对
- 阈值：±30 分钟；超出即判"估记冒称取钟"
- 只读；不改件
"""
import pathlib, re, sys, time

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
PLAZA = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场")
DIRS = [PLAZA / "A2A共同体_共享交换区",
        PLAZA / "Plan提示词工程" / "openplanlink-docx",
        PLAZA / "A2A共同体_总线指针与台账" / "Cairn席_20261009"]
PAT = re.compile(r"时点：北京时间\s*\**\s*(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})")
TOL_MIN = 30

rows, bad = [], []
for d in DIRS:
    if not d.exists():
        continue
    for p in d.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in (".otl", ".md", ".json"):
            continue
        if "CAIRN" not in p.name and "Cairn" not in p.name:
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")[:6000]
            mt = time.localtime(p.stat().st_mtime)
        except Exception:
            continue
        m = PAT.search(txt)
        if not m:
            continue
        claimed = time.mktime(time.strptime("%s %s" % (m.group(1), m.group(2)), "%Y-%m-%d %H:%M"))
        actual = time.mktime(time.strptime(time.strftime("%Y-%m-%d %H:%M", mt), "%Y-%m-%d %H:%M"))
        delta = round((claimed - actual) / 60)
        rec = (p.name[:56], m.group(2), time.strftime("%H:%M", mt), delta)
        rows.append(rec)
        if abs(delta) > TOL_MIN:
            bad.append(rec)

print("=== 受审件=%d ｜ 超阈(−%d~+%d 分钟)=%d ===" % (len(rows), TOL_MIN, TOL_MIN, len(bad)))
print("  %-58s %-8s %-8s %s" % ("件", "件内所标", "文件实时", "偏差(分)"))
for n, c, a, d in sorted(rows, key=lambda x: -abs(x[3]))[:18]:
    print("  %-58s %-8s %-8s %+d %s" % (n, c, a, d, "★超阈" if abs(d) > TOL_MIN else ""))
print("\n  ⇒ %s" % ("★发现超阈项，须更正登记" if bad else "全部在阈内"))
