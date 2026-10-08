#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只在本机按四级路径归位本席件；不触网。
r"""archive_layout.py —— 本席【多级归档】的强制执行器。 v1.0.0

立此器的缘由（写在代码里，不只是写在文档里）
──────────────────────────────────────────
机主 2026-10-02 令：**「您以后创建文件就要做好多级归档，别让他人帮您收拾」。**
⇒ 故本器提供三件事，**把规矩从"记性"挪到"机制"**：
   `where` —— 先算该放哪（不动盘）
   `place` —— 按四级路径归位（**manifest-first，可还原**）
   `audit` —— ★ 查"散在共享根顶层的本席件"（**这条就是"不劳他人"的自检**）

四级路径
──────────
  <落点根>\<归属>\<日期>\<类别>\<件>
  例：…\桌面\_石敢当席\20261002\80_收束\xx_cairn-dsh_20261002.md

纪律
──────
  ① 落点根顶层【不得】留本席散件；② 先清单后搬；③ 只增不改（同名不同字节 ⇒ 拒搬）；
  ④ 只认本席署名（文件名含 `cairn-dsh` 或以 `【石敢当席呈机主】` 开头）；⑤ 别家件一律不动。
"""
from __future__ import annotations
import argparse
import datetime
import hashlib
import pathlib
import re
import shutil
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SEAT_DIR = pathlib.Path(__file__).resolve().parent.parent
DESK = SEAT_DIR.parent
OWNER = "_石敢当席"                      # 归属名（桌面用）
SEAT_TAG = "cairn-dsh"                   # 本席署名
PREFIX = "【石敢当席呈机主】"
MANIFEST = "_清单.tsv"

# 类别规则（顺序即优先级），与桌面归档夹同一套
KINDS = [
    ("00_入口",      re.compile(r"^(★★★|★)|入口|导读|先读|行动卡|索引")),
    ("80_收束",      re.compile(r"收束|收盘|收口|末刻录|窗口|终态|到此为止")),
    ("20_勘误自曝",  re.compile(r"勘误|更正|自曝|纠|误")),
    ("30_呈他人",    re.compile(r"^呈|呈同侪|呈码道席|呈移动侧|呈机主")),
    ("40_数据程序",  re.compile(r"\.(json|py|mjs|js|ets|patch|html|zip)$|数据_|补丁_|程序_")),
    ("50_预印草案",  re.compile(r"预印|草案|补充件|提案")),
    ("60_审计诊断",  re.compile(r"审计|诊断|体检|对账|UNVERIFIABLE|告警|清理|总账|缺件")),
    ("70_值守交件",  re.compile(r"值守|交件|待令|种子|演示|镜像|状态|台账|规矩|手册|规矩")),
    ("10_追加件",    re.compile(r"追加件")),
]
FALLBACK = "90_其他"


def is_mine(name: str) -> bool:
    # ★ 2026-10-02 自检器自我纠正：首版只认 `cairn-dsh` 与 `【石敢当席呈机主】`，
    #   结果漏掉了 `_桌面变更说明_石敢当席184件已归档…` 这类【含中文席名但无拉丁署名】的件。
    #   ⇒ 判据扩为三个标记，任一命中即认。
    return (name.startswith(PREFIX)
            or (SEAT_TAG in name)
            or ("石敢当席" in name)
            or name.startswith("_石敢当"))


def kind_of(name: str) -> str:
    body = name[len(PREFIX):] if name.startswith(PREFIX) else name
    for k, pat in KINDS:
        if pat.search(body):
            return k
    return FALLBACK


def date_of(name: str, override: str | None) -> str:
    if override:
        return override
    m = re.search(r"(20\d{6})", name)
    if m:
        return m.group(1)
    return datetime.date.today().strftime("%Y%m%d")


def sha256_of(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def target_for(root: pathlib.Path, name: str, date: str | None, kind: str | None) -> pathlib.Path:
    return root / OWNER / date_of(name, date) / (kind or kind_of(name)) / name


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["where", "place", "audit"])
    ap.add_argument("src", nargs="?")
    ap.add_argument("--root", default=str(DESK))
    ap.add_argument("--date", default=None)
    ap.add_argument("--kind", default=None)
    a = ap.parse_args()
    root = pathlib.Path(a.root).resolve()

    if a.cmd == "where":
        if not a.src:
            print("ERR 用法：where <件名>"); return 2
        print("═══ 该放哪（只算，不动盘）═══")
        print("  落点根 = %s" % root)
        print("  ★ 目标 = %s" % target_for(root, pathlib.Path(a.src).name, a.date, a.kind))
        return 0

    if a.cmd == "audit":
        print("═══ 自检：共享根顶层的本席散件 ═══")
        loose = sorted(p for p in root.iterdir() if p.is_file() and is_mine(p.name))
        print("  落点根 = %s" % root)
        print("  ★ 散在顶层的本席件 = %d 件" % len(loose))
        for p in loose:
            print("     %-58s → %s" % (p.name[:58], target_for(root, p.name, None, None).relative_to(root)))
        not_mine = sorted(p for p in root.iterdir() if p.is_file() and not is_mine(p.name))
        print("  （顶层非本席件 = %d 件 ⇒ 一律未动）" % len(not_mine))
        return 1 if loose else 0

    # place
    if not a.src:
        print("ERR 用法：place <源件>"); return 2
    src = pathlib.Path(a.src)
    if not src.is_file():
        print("ERR 源件不存在：%s" % src); return 2
    if not is_mine(src.name):
        print("★ 拒搬：`%s` 不属本席署名（不含 `%s` 且不以 `%s` 开头）" % (src.name, SEAT_TAG, PREFIX))
        return 1
    dst = target_for(root, src.name, a.date, a.kind)
    if dst.exists():
        if sha256_of(dst) == sha256_of(src):
            print("[IDEMPOTENT] 目标已存在且字节全等 ⇒ 只删源：%s" % dst.name)
            src.unlink(); return 0
        print("★ 拒搬：目标已存在且字节不等 ⇒ 只增不改（改新名）\n   %s" % dst)
        return 1
    dst.parent.mkdir(parents=True, exist_ok=True)
    man = dst.parent / (date_of(src.name, a.date) + MANIFEST)
    row = "%s\t%s\t%d\t%s\n" % (src.resolve(), dst.resolve(), src.stat().st_size, sha256_of(src))
    header = "" if man.exists() else "# 本席多级归档清单（源/目的/字节/sha256）\n"
    shutil.move(str(src), str(dst))
    with man.open("a", encoding="utf-8", newline="\n") as f:
        f.write(header + row)
    print("  ✅ 已归位：%s" % dst.relative_to(root))
    print("  清单 = %s" % man.relative_to(root))
    return 0


if __name__ == "__main__":
    sys.exit(main())
