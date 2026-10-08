# -*- coding: utf-8 -*-
"""dedup_plan.py —— P0「去重」**执行预案**（承 DF-MEM-…-CAIRN-02 §四 P0）

🔴 **本器零文件操作**：不删除、不移动、不改名——**只生成预案**（供候批）。
纪律：先只读评估 → **候批** → 执行 → 复测 → 记账（DF-MEM v0.2 §六）。

设计（可回滚优先）：
  · **保留规则**：同组内按 (mtime 最早 = 原件优先) → 路径最短 → 路径字典序，**确定性**择一保留；
  · **处置方式（建议）**：其余副本**移入 `quarantine/dedup-<UTC>/`（同盘）**，**不删除** ⇒ 回滚＝原路移回；
  · **逐件指纹**：size ＋ sha256 前 16（同组内必相同，作为"同内容"证据）；
  · **验收对齐**：预案给出"预计回收字节"，供 P0 验收标准①比对（目标 ≥ 2.16 MB）。
输出：`--json <路径>` 与 stdout 表（**不回显任何值以外的敏感项**；路径为工作区相对路径）。

用法:
  python dedup_plan.py [--seat <目录>] [--min-size 4096] [--json <路径>]
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")



def norm_sha16(p):
    """CRLF/LF 归一化后的 sha16（承 DF-CCM §七：须内置归一化，否则伪差异会被误判为不同）。"""
    import re as _re
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        data = fh.read()
    h.update(_re.sub(rb"\r\n", b"\n", data))
    return h.hexdigest()[:16]

def sha16(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16]




def collect_rows(seat):
    """收集 (tier, rel, size, age_days) 供孪生告警使用（只读）。"""
    import datetime as _dt
    rows = []
    now = _dt.datetime.now()
    for root, dirs, files in os.walk(seat):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "quarantine")]
        for fn2 in files:
            fp = pathlib.Path(root) / fn2
            try:
                st = fp.stat()
            except OSError:
                continue
            rows.append(("-", str(fp.relative_to(seat)), st.st_size,
                         round((now - _dt.datetime.fromtimestamp(st.st_mtime)).total_seconds() / 86400.0, 1)))
    return rows

def sibling_warnings(rows):
    """孪生命名告警（承 DF-CASVERIFY-20261007-HY4-01 §二；v2 收严）：
    **收严口径**：仅当「去掉末尾副本标记后的基名」与**同目录另一文件的基名完全相等**，
    且二者**尺寸不同**时告警 ⇒ 排除"同基名不同扩展名"（如 .json/.led）之**误报**。
    ⇒ 疑为**互补续卷/不同切分点**，**严禁按重复删除**；本器只告警、不列入可回收。"""
    import re as _re
    bydir = {}
    for tier, rel, size, age in rows:
        d = str(pathlib.PurePath(rel).parent)
        base = pathlib.PurePath(rel).name
        bydir.setdefault(d, {})[base] = size
    marker = _re.compile(r"^(?P<stem>.+?)(?:\((\d+)\)|\s*-\s*副本|\s*副本|_copy|\s*copy)$", _re.I)
    warn = []
    for d, files in bydir.items():
        for base, size in files.items():
            stem_only = base.rsplit(".", 1)[0]
            m = marker.match(stem_only)
            if not m:
                continue
            target = m.group("stem")
            # 要求同目录存在「基名恰为 target」的其它文件（任意扩展名）
            sibs = {b: s for b, s in files.items() if b.rsplit(".", 1)[0] == target}
            if not sibs:
                continue
            sizes = sorted({size} | set(sibs.values()))
            if len(sizes) > 1:
                warn.append({"dir": d, "stem": target, "n": 1 + len(sibs), "sizes": sizes})
    return warn

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seat", default=r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928")
    ap.add_argument("--min-size", type=int, default=4096)
    ap.add_argument("--json")
    a = ap.parse_args()

    seat = pathlib.Path(a.seat)
    by_size = defaultdict(list)
    for root, dirs, files in os.walk(seat):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "quarantine")]
        for fn in files:
            p = pathlib.Path(root) / fn
            try:
                st = p.stat()
            except OSError:
                continue
            if st.st_size >= a.min_size:
                by_size[st.st_size].append((p, st))

    groups = []
    for size, items in by_size.items():
        if len(items) < 2:
            continue
        by_hash = defaultdict(list)
        for p, st in items:
            try:
                by_hash[sha16(p)].append((p, st))
            except OSError:
                continue
        for h, lst in by_hash.items():
            if len(lst) < 2:
                continue
            # 确定性保留：mtime 最早 → 路径最短 → 字典序
            lst.sort(key=lambda x: (x[1].st_mtime, len(str(x[0])), str(x[0])))
            keep, (keep_st) = lst[0][0], lst[0][1]
            drops = [p for p, _ in lst[1:]]
            groups.append({
                "size": size, "sha16": h, "n": len(lst),
                "keep": str(keep.relative_to(seat)),
                "keep_mtime": dt.datetime.fromtimestamp(keep_st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "move_to_quarantine": [str(d.relative_to(seat)) for d in drops],
                "reclaim_bytes": size * len(drops),
            })

    # ── 近重复（CRLF/LF 归一化后相同，但字节不同）——**只报告，绝不自动隔离** ──
    near = {}
    for root, dirs, files in os.walk(seat):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "quarantine")]
        for fn in files:
            p = pathlib.Path(root) / fn
            try:
                st = p.stat()
            except OSError:
                continue
            if st.st_size < a.min_size:
                continue
            try:
                k = norm_sha16(p)
            except OSError:
                continue
            near.setdefault(k, []).append(p)
    near_groups = {k: v for k, v in near.items() if len(v) > 1}
    exact_keys = {g["sha16"] for g in groups}
    near_only = [v for k, v in near_groups.items() if all(
        sha16(x) not in exact_keys for x in v)]
    near_bytes = sum(sum(x.stat().st_size for x in v[1:]) for v in near_only)

    groups.sort(key=lambda g: -g["reclaim_bytes"])
    reclaim = sum(g["reclaim_bytes"] for g in groups)

    md = []
    md.append("# P0 去重执行预案（**零文件操作**，候批）")
    md.append("")
    md.append("- 生成时刻：%s（+08）｜ 目标：`%s`" % (dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), seat.name))
    md.append("- 保留规则：**mtime 最早（原件优先）** → 路径最短 → 字典序（确定性，可复算）")
    md.append("- 处置方式（建议）：移入 **`quarantine/dedup-<UTC>/`（同盘）**，**不删除** ⇒ 回滚＝原路移回")
    md.append("")
    md.append("| 组 | 尺寸(B) | 副本数 | 保留 | 拟隔离 | 预计回收(B) |")
    md.append("|---|---|---|---|---|---|")
    for i, g in enumerate(groups[:20], 1):
        md.append("| %d | %d | %d | `%s` | %d 件 | %d |"
                  % (i, g["size"], g["n"], g["keep"][:52], len(g["move_to_quarantine"]), g["reclaim_bytes"]))
    if len(groups) > 20:
        md.append("| … | … | … | … | … | （余 %d 组略） |" % (len(groups) - 20))
    md.append("")
    md.append("## 验收对齐（对 DF-MEM v0.2 §四 P0）")
    md.append("")
    md.append("- 预计回收：**%.2f MB**（验收标准①：≥ 2.16 MB ⇒ **%s**）"
              % (reclaim / 1048576.0, "达标" if reclaim >= 2.16 * 1048576 else "未达标"))
    md.append("- 组数：**%d**（验收标准②：执行后 `mem_tier_scan` 复测**重复组归零**）" % len(groups))
    md.append("- 回滚：**隔离区原路移回**（不删除 ⇒ 无不可逆风险）")
    md.append("")
    md.append("## 近重复（归一化口径，**只报告**）")
    md.append("")
    md.append("- **CRLF/LF 归一化后相同、字节不同**：**%d 组**，额外占 **%.2f MB**" % (len(near_only), near_bytes / 1048576.0))
    md.append("- 口径声明（承 `DF-CCM` §六.4）：**已按「归一化 sha256 逐件比对」之口径检查**；本类**不属逐字重复**，**不得自动隔离**，仅备网络裁量")
    md.append("")
    md.append("> 🔴 本预案**未执行任何文件操作**；**候批**后按纪律「执行 → 复测 → 记账」推进。")

    text = "\n".join(md)
    print(text)
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps({
            "generated_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "policy": "keep earliest mtime → shortest path → lexicographic; move others to quarantine (no delete)",
            "groups": groups, "n_groups": len(groups),
            "reclaim_bytes": reclaim, "reclaim_mb": round(reclaim / 1048576.0, 3),
            "executed": False,
            "sibling_warnings": sibling_warnings(collect_rows(seat)),
            "sibling_note": "名似副本而哈希不同 ⇒ 疑为互补续卷/不同切分点，**勿按重复删除**（承 DF-CASVERIFY §二）",
            "near_dup_groups": len(near_only),
            "near_dup_extra_bytes": near_bytes,
            "near_dup_note": "CRLF/LF 归一化后相同、字节不同 ⇒ **不属逐字重复，不得自动隔离**（承 DF-CCM §七）",
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("\n★ JSON 已写出：%s（**executed=false**）" % a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
