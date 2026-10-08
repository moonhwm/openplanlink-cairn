#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""fix_stale_paths.py —— 把遗留脚本硬编码旧席位路径改为 __file__ 自定位。用法：dry | apply"""
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

SEAT_ROOT = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928")
EXP = SEAT_ROOT / "exp"

OLD_SEAT = r"C:\Users\欧阳宏俊\OneDrive\桌面\A2A新席_石敢当Cairn_20260928"
OLD_EXP = OLD_SEAT + r"\exp"

# (文件名, 旧绝对路径, pathlib.Path(...) 里的新表达式)
FIXES = [
    ("audit_skill_frontmatter.py", OLD_SEAT, "__file__).resolve().parent.parent"),
    ("audit_skill_naming.py", OLD_SEAT, "__file__).resolve().parent.parent"),
    ("diag_seed.py", OLD_SEAT, "__file__).resolve().parent.parent"),
    ("extract_media.py", OLD_SEAT, "__file__).resolve().parent.parent"),
    ("ignition_gate.py", OLD_SEAT, "__file__).resolve().parent.parent"),
    ("intake_20260929.py", OLD_SEAT, "__file__).resolve().parent.parent"),
    ("tamper_test.py", OLD_SEAT, "__file__).resolve().parent.parent"),
    ("tempguard.py", OLD_SEAT, "__file__).resolve().parent.parent"),
    ("blast_radius.py", OLD_EXP, "__file__).resolve().parent"),
    ("declare_net.py", OLD_EXP, "__file__).resolve().parent"),
    ("falsify_kit_check.py", OLD_EXP, "__file__).resolve().parent"),
    ("verify_netguard_wiring.py", OLD_EXP, "__file__).resolve().parent"),
    ("wire_netguard.py", OLD_EXP, "__file__).resolve().parent"),
    ("patch_auditor.py", OLD_EXP + r"\audit_robots_compliance.py", '__file__).resolve().parent / "audit_robots_compliance.py"'),
    ("patch_feed.py", OLD_EXP + r"\feed_to_deduce.py", '__file__).resolve().parent / "feed_to_deduce.py"'),
]

mode = sys.argv[1] if len(sys.argv) > 1 else "dry"
changed = 0
for fname, old, new in FIXES:
    p = EXP / fname
    if not p.exists():
        print("  ○ 不在:", fname)
        continue
    text = p.read_text(encoding="utf-8")
    if old not in text:
        print("  ○ 旧路径未命中:", fname)
        continue
    pat = re.compile(r'(pathlib\.Path\()(r?)"' + re.escape(old) + r'"\)')
    new_text, n = pat.subn(r"\g<1>" + new + ")", text)
    if n == 0:
        print("  ○ 正则未命中:", fname)
        continue
    changed += 1
    print("  %s %s（%d 处）" % ("[apply]" if mode == "apply" else "[dry]", fname, n))
    if mode == "apply":
        p.write_text(new_text, encoding="utf-8", newline="\n")

print("  共 %d 个脚本%s" % (changed, " 已修改" if mode == "apply" else "（dry-run）"))
