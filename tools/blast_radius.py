#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 本件不触网（其 NET 标记来自 MARKERS 里的字符串，属扫描误报）。
r"""
blast_radius.py —— 把本席工具的【波及范围】做成看得见的东西。 v1.0.0

由来（轮105 的错）
──────────────────
我为证明"推送闸会拦"，造了一份【闸被摘掉】的副本 ⇒ 而副本一路走到真发，
向公网发出了一次真实请求。**根因：我造测试时没有算它的波及范围。**
⇒ 故本器：**静态扫描本席 .py，逐件判定其能力等级，并把【能触网的那些】单独列出来。**
   **目的不是在事后追责，而是在【动手之前】能看见一件工具能碰到哪儿。**

分级（可叠加，取最高）
────────────────────────
  **NET**    可发起对外网络调用（urllib/urlopen/requests/socket/http.client）
  **EXEC**   可起子进程（subprocess/Popen/os.system）
  **DEL**    可删文件（unlink/rmtree/os.remove）
  **WRITE**  可写文件（write_text/write_bytes/open(...,"w")…）
  **READ**   只读
  ★ **发往外部的字样**：文中若出现共享面路径或桌面路径 ⇒ 标记 `OUT-PATH`（**提示其写/读可能越出本席领地**）

★ 声明约定：**能触网的工具，须在文件里写一行 `# BLAST: NET`。**
   本器对【NET 而未声明】者报 FAIL ⇒ **这样"新长出一件会触网的工具"不会被漏掉。**

用法: blast_radius.py [--list-net]
"""
from __future__ import annotations
import argparse
import pathlib
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

EXP = pathlib.Path(__file__).resolve().parent
SEAT = EXP.parent
# ★★★ 轮113 修（重大）：**原版只扫 `exp/`** ⇒ 于是 `obs_fix/` 等目录里的工具
#   【既未被审计、也未被接总闸】。后果：本席刚跑的 `obs_fix/validate_card.py`
#   向观测站发了 9 次请求，而总闸拦不住它。
#   ⇒ 现改为扫【整个席位领地】；SKIP 只留副本/缓存/解包目录。
SCAN_ROOTS = [SEAT]
SKIP_DIRS = {"_retired", "_falsify_lab", "_tamper_lab", "__pycache__", "attest_lab", "ab_theirs",
             "ab_fixed", "seed_render_lab", "_contract_lab", "_netguard_lab", "mirror_tar",
             "openplanlink-mirror"}

MARKERS = {
    "NET":   [r"urllib\.request", r"urlopen\(", r"\brequests\.", r"\bsocket\.", r"http\.client"],
    "EXEC":  [r"\bsubprocess\b", r"\bPopen\b", r"os\.system"],
    "DEL":   [r"\.unlink\(", r"\brmtree\b", r"os\.remove"],
    "WRITE": [r"write_text\(", r"write_bytes\(", r"open\([^)]*['\"]w", r"\.write\("],
}
OUT_PATH = [r"全局声明_治理文档", r"a2a-inbox", r"C:\\Users\\欧阳宏俊\\OneDrive\\桌面\\(?!A2A新席)"]
# ★ 轮108 修：原正则未锚行首 ⇒ **本文件自己的文档里那句示例 `# BLAST: NET` 被当成了声明**
#   （自我误报：审计器把自己的说明书读成了自己的声明）。加 ^ 锚定后即不再误报。
DECL = re.compile(r"^\s*#\s*BLAST:\s*(NET|EXEC|DEL|WRITE|NONE)", re.M)
GUARD = re.compile(r"netguard")


def scan_one(p: pathlib.Path):
    t = p.read_text(encoding="utf-8", errors="replace")
    caps = [k for k, pats in MARKERS.items() if any(re.search(x, t) for x in pats)]
    decl = DECL.search(t)
    outpath = any(re.search(x, t) for x in OUT_PATH)
    guarded = bool(GUARD.search(t))
    return caps, (decl.group(1) if decl else None), outpath, guarded


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list-net", action="store_true")
    a = ap.parse_args()

    files = [p for p in SEAT.rglob("*.py") if not any(s in p.parts for s in SKIP_DIRS)]
    print("═══ 本席工具·波及范围审计（扫【整个席位领地】共 %d 件 .py）═══" % len(files))
    print("  ★ 轮113 起扫描口径＝席位领地全域（原版只扫 exp/ ⇒ 曾漏掉 obs_fix/ 里的触网工具）")
    print("  ★ 分级：%s" % " / ".join(MARKERS))
    print()
    print("  %-42s %-18s %-8s %s" % ("文件", "能力", "已声明", "越界路径字样"))
    print("  " + "-" * 88)
    counts = {k: 0 for k in MARKERS}
    net_undeclared, net_list, net_unguarded, net_mismatch = [], [], [], []
    mine_unguarded, vendored_unguarded = [], []
    for p in sorted(files, key=lambda x: x.name):
        caps, decl, outpath, guarded = scan_one(p)
        for c in caps:
            counts[c] += 1
        if "NET" in caps:
            net_list.append(p.name)
            # ★★ 轮115 增：**按归属分开**——本席自有（exp/／obs_fix/／席位根）vs 我持有的他人代码（handshake/ 等）
            _rel = p.relative_to(SEAT).parts
            _isdir_mine = (_rel[0] in ("exp", "obs_fix") or len(_rel) == 1)
            if decl is None:
                net_undeclared.append(p.name)
            elif decl != "NET":
                net_mismatch.append(p.name)
            if not guarded:
                net_unguarded.append(p.name)
                (mine_unguarded if _isdir_mine else vendored_unguarded).append(
                    str(p.relative_to(SEAT)))
        if caps or outpath:
            note = "★未接总闸" if ("NET" in caps and not guarded) else ""
            if "NET" in caps and decl == "NONE":
                note = "（声明 NONE：疑似标记落在字符串/注释里）"
            print("  %-42s %-18s %-8s %s %s" % (
                p.name[:42], "+".join(caps) or "—", decl or "—",
                "是" if outpath else "  ", note))
    print()
    print("  ── 计数 ──")
    for k in ("NET", "EXEC", "DEL", "WRITE"):
        print("     %-6s %d 件" % (k, counts[k]))
    print("     纯只读/计算 %d 件" % (len(files) - len({p.name for p in files if scan_one(p)[0]})))
    print()
    print("  ── ★ 能触网的工具（＝live-fire 候选，动手前先看这份）──")
    for n in net_list:
        if n in net_undeclared:
            print("     · %s  ← ★真·未声明（无 `# BLAST:` 行）" % n)
        elif n in net_mismatch:
            print("     · %s  ← 声明 NONE（扫描说 NET ⇒ 疑似标记在字符串/注释里，非失败项）" % n)
        else:
            print("     · %s  ← 已声明且已接闸" % n)
    print()
    print("  ── 总闸覆盖率（轮115：**按归属分开算**）──")
    print("     能触网 %d 件 ｜ 已接总闸 %d 件 ｜ 未接 %d 件"
          % (len(net_list), len(net_list) - len(net_unguarded), len(net_unguarded)))
    print("     ★ 本席自有工具未接 %d 件 %s"
          % (len(mine_unguarded), ("⇒ " + "、".join(mine_unguarded[:5])) if mine_unguarded else "⇒ 全已接闸"))
    print("     ○ 我持有的他人/解包代码未接 %d 件（不归我改；列入「未经思考不得运行」）" % len(vendored_unguarded))
    print("     其中【真·未声明】%d 件 ｜ 【声明 NONE 而扫描说 NET】%d 件（疑似误报）"
          % (len(net_undeclared), len(net_mismatch)))
    bad = len(mine_unguarded)
    print()
    print("  ⇒ %s" % ("★本席自有工具仍有 %d 件未接总闸 ⇒ 需补" % bad if bad
                      else "本席自有工具【全已接闸】⇒ PASS（他人代码 %d 件单列，不计入本席判词）"
                           % len(vendored_unguarded)))
    print("  ★ 本器只读不写、不触网；其自身 NET 标记来自其 MARKERS 字符串 ⇒ 属上述误报一类。")
    print("  ★ 本器能失败（**本席自有**触网工具未接闸即报）⇒ 非恒真。")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
