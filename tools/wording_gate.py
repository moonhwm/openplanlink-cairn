# -*- coding: utf-8 -*-
"""wording_gate.py —— 「未测」表述纪律之禁词检查（承 DF-CCM §四·本席合规矩阵 #6）

纪律（他席裁定，升格为硬纪律）：
    凡**无入参**之节点，一律记为「未测」；**严禁写为「不可用」，亦严禁写为「可用」**。

本工具用途：对本席产出件做**表述级自检**——找出**对存储/服务节点之可用性断言**，
并标出**是否带"未测/未核实"限定**；命中即提示改为「未测（无入参）」。
性质：**只读、只报告**；**不回显任何值**（只示行号与命中类别）。

用法：
    python wording_gate.py --paths <dir1> [<dir2> ...]
    python wording_gate.py --mine-only        # 仅本席交换区件
退出码：0=未命中（CLEAN）｜1=有命中（须人工判读）｜2=用法错误
"""
import argparse
import datetime as dt
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

SEAT = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928")
EXCHANGE = SEAT.parent / "A2A共同体_共享交换区"
NODES = r"(?:Neon|Supabase|WPS云文档|WPS|ima-skill|ima|百度网盘|百炼|阿里云百炼)"
# T1：登记为**无入参**之节点（§四 之适用对象；现值据 DF-PROV 与 DF-CCM）
NOINPUT = r"(?:Neon|Supabase|百炼|阿里云百炼)"
# T2 基准词：可用性断言若带"实测/实测于/已测/时点"，视为**有据**（但**须带时点**方为完整）
BASIS = re.compile(r"实测|已测|端到端|验证于")
STAMP = re.compile(r"20\d{2}-\d{2}-\d{2}|\d{1,2}:\d{2}")
# 可用性断言（节点后 0–16 字内出现断言词）
ASSERT = re.compile(NODES + r"[^。\n]{0,16}?(可用|不可用|已接入|已打通|已具备调用能力|已就绪|可用节点)")
# 限定词（同句出现则视为合规）
QUALIFY = re.compile(r"未测|未核实|未验证|待核|无入参|pending|不代表")


def scan_file(p):
    hits = []
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return hits
    for i, ln in enumerate(lines, 1):
        m = ASSERT.search(ln)
        if not m:
            continue
        ok = bool(QUALIFY.search(ln))
        tier = "T1" if re.search(NOINPUT, m.group(0)) else "T2"
        basis = bool(BASIS.search(ln))
        stamp = bool(STAMP.search(ln))
        hits.append({"line": i, "kind": m.group(1), "qualified": ok, "tier": tier,
                     "basis": basis, "stamp": stamp,
                     "masked": re.sub(NODES, "<节点>", ln.strip())[:110]})
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", nargs="*", default=None)
    ap.add_argument("--mine-only", action="store_true")
    ap.add_argument("--quiet-clean", action="store_true")
    a = ap.parse_args()

    roots = []
    if a.mine_only or not a.paths:
        roots = [EXCHANGE]
    else:
        roots = [pathlib.Path(x) for x in a.paths]

    files = []
    for r in roots:
        if not r.exists():
            continue
        for ext in ("*.otl", "*.md", "*.txt"):
            files += [f for f in r.rglob(ext) if f.is_file()]
    if a.mine_only:
        files = [f for f in files if "CAIRN" in f.name]

    print("★ 表述纪律检查（%s，北京时间）" % dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("  范围：%d 个文件 ｜ 判据：节点名后 0–16 字内出现可用性断言词 ｜ 限定词白名单：未测/未核实/待核/无入参…" % len(files))
    total, unqual = 0, 0
    for f in sorted(files):
        hs = scan_file(f)
        if not hs:
            continue
        total += len(hs)
        bad = [h for h in hs if (h["tier"] == "T1" and not h["qualified"])]
        unqual += len(bad)
        print("  · %s：%d 处断言（其中**未带限定词 %d 处**）" % (f.name, len(hs), len(bad)))
        for h in bad[:3]:
            print("      行%d ｜ 断言=%s ｜ 片段=%s" % (h["line"], h["kind"], h["masked"]))
    t2 = sum(1 for f in sorted(files) for h in scan_file(f) if h["tier"] == "T2")
    t2_nostamp = sum(1 for f in sorted(files) for h in scan_file(f) if h["tier"] == "T2" and not h["stamp"])
    print("  ⇒ T1（无入参节点）断言 %d 处，其中**未记未测 %d 处** ← §四 违规面" % (total, unqual))
    print("  ⇒ T2（其它节点）断言 %d 处，其中**未带时点 %d 处** ← 本席自课：可用性断言须带时点（提示级）" % (t2, t2_nostamp))
    if total == 0:
        print("  VERDICT=CLEAN（未发现可用性断言）")
    elif unqual == 0:
        print("  VERDICT=QUALIFIED（断言均带限定词 ⇒ 符合 §四）")
    else:
        print("  VERDICT=NEEDS_REVIEW（%d 处须人工判读并改记「未测」）" % unqual)
    return 1 if unqual else 0


if __name__ == "__main__":
    sys.exit(main())
