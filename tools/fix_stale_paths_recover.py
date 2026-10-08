#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""fix_stale_paths_recover.py —— 修正上一版引入的多余右括号。"""
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8")

EXP = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928\exp")

FILES = [
    "audit_skill_frontmatter.py", "audit_skill_naming.py", "diag_seed.py",
    "extract_media.py", "ignition_gate.py", "intake_20260929.py",
    "tamper_test.py", "tempguard.py", "blast_radius.py", "declare_net.py",
    "falsify_kit_check.py", "verify_netguard_wiring.py", "wire_netguard.py",
    "patch_auditor.py", "patch_feed.py",
]

# 顺序关键：先双 parent，再文件，最后单 parent
RECOVER = [
    ("pathlib.Path(__file__).resolve().parent.parent)", "pathlib.Path(__file__).resolve().parent.parent"),
    ('pathlib.Path(__file__).resolve().parent / "audit_robots_compliance.py")', 'pathlib.Path(__file__).resolve().parent / "audit_robots_compliance.py"'),
    ('pathlib.Path(__file__).resolve().parent / "feed_to_deduce.py")', 'pathlib.Path(__file__).resolve().parent / "feed_to_deduce.py"'),
    ("pathlib.Path(__file__).resolve().parent)", "pathlib.Path(__file__).resolve().parent"),
]

for f in FILES:
    p = EXP / f
    t = p.read_text(encoding="utf-8")
    for old, new in RECOVER:
        t = t.replace(old, new)
    p.write_text(t, encoding="utf-8", newline="\n")
    print("  fixed:", f)
print("  完成")
