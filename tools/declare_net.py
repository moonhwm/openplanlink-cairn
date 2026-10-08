#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""declare_net.py —— 给能触网的工具补 `# BLAST: NET（条件）` 声明行。 v1.0.0"""
from __future__ import annotations
import pathlib
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

EXP = pathlib.Path(__file__).resolve().parent

# ★ 逐件写明【何时】会触网——声明要带条件，否则等于没说
DECL = {
    "audit_robots_compliance.py": "复核历史取件的 robots（只读 robots.txt）",
    "audit_skill_naming.py":      "（历史件）读远端技能清单",
    "check_handshake52.py":       "探测握手件可达性",
    "fetch_wechat_article.py":    "取公众号正文（经 robots 闸口放行才取）",
    "gen_status_feed.py":         "（历史件）拉取状态源",
    "meow_push.py":               "★仅在 --send ∧ --i-am-authorized ∧ 策略闸 ALLOW 三条件齐备时",
    "policy_abc.py":              "只读 robots.txt（政策的豁免项）",
    "probe_opl_history.py":       "探测仓库历史",
    "probe_qtorrent_card.py":     "探测观测站名片",
    "robots_gate.py":             "只读 robots.txt（为遵守 robots 必须能读）",
    "wechat_probe.py":            "探测公众号可达性",
}


def main() -> int:
    print("═══ 补 BLAST: NET 声明 ═══")
    done = 0
    for name, cond in DECL.items():
        p = EXP / name
        if not p.is_file():
            print("  ★缺件：%s" % name); continue
        t = p.read_text(encoding="utf-8")
        if re.search(r"#\s*BLAST:\s*NET", t):
            print("  — 已有声明：%s" % name); continue
        lines = t.splitlines(keepends=True)
        # 插到【第 2 行之后】（通常第 1 行是 shebang、第 2 行是 coding）
        idx = 2 if len(lines) >= 2 else len(lines)
        decl = "# BLAST: NET —— 本件可发起对外网络调用（%s）。声明供 blast_radius.py 审计。\n" % cond
        lines.insert(idx, decl)
        p.write_text("".join(lines), encoding="utf-8")
        print("  ✅ 已补：%-32s ｜ %s" % (name, cond))
        done += 1
    print("\n  ⇒ 共补 %d 件。★ 声明只是【如实标注能力】，不改变行为。" % done)
    return 0


if __name__ == "__main__":
    sys.exit(main())
