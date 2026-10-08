#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只在本机桌面内搬动本席自有件；不触网。
r"""desktop_archive.py —— 把桌面上本席（石敢当席）的散件归档，**每步可还原**。 v1.0.0

规矩（本器自己遵守的）
────────────────────────
  ① **先写清单再搬**：清单逐条记 源／目的／字节／sha256 ⇒ 可 `--undo` 完整还原；
  ② **只碰本席自有件**：文件名必须以【石敢当席呈机主】开头；别家席位与共享面【一律不动】；
  ③ **不删任何东西**：本器只会 `move`，且目的已存在时【拒搬】（不覆盖）；
  ④ **不碰**：`.lnk`／`.url`／`desktop.ini` 等桌面快捷方式（它们不以本席前缀开头，故天然排除）；
  ⑤ **落点必须在本席归档夹内**：搬前断言目的绝对路径以归档夹绝对路径开头。

用法
──────
  python desktop_archive.py --plan                 # 只分类、只出计划（不动盘）
  python desktop_archive.py --apply                # 真搬，并写清单
  python desktop_archive.py --undo <清单.tsv>      # 按清单还原
"""
from __future__ import annotations
import argparse
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

PREFIX = "【石敢当席呈机主】"
ARCHIVE = "_石敢当席_20261002交付归档"

# 分类规则（**顺序即优先级**）：(子夹, 正则)
RULES = [
    ("00_入口与收束",       re.compile(r"^(★★★|★)")),
    ("20_勘误与自曝",       re.compile(r"(勘误|更正|自曝)")),
    ("30_呈他人与移动侧",   re.compile(r"^(呈同侪|呈码道席|呈移动侧|呈机主)")),
    # ★ 轮198 补：首跑时 90_其他 有 32 件，而其族属很清楚 ⇒ 拆成三夹，别把三成东西丢进"其他"
    ("50_预印稿与草案",     re.compile(r"^(预印稿|草案|补充件)")),
    ("60_审计与诊断",       re.compile(r"(审计|诊断|体检|对账|UNVERIFIABLE|告警|清理|总账)")),
    ("70_值守与交件",       re.compile(r"(值守日志|交件单|待令即行|^种子_|^演示件_|重大发现|镜像双审计|KimiBuild|席位侧数据接口|^实时件_|命名审计)")),
    ("40_数据与程序",       re.compile(r"\.(json|py|mjs|ets|js)$|^(数据_|补丁_|程序_)")),
    ("10_追加件",           re.compile(r"^追加件_")),
    ("00_入口与收束",       re.compile(r"(收束|末刻录|窗口)")),      # 二次归入入口夹
]
FALLBACK = "90_其他"


def classify(name: str) -> str:
    body = name[len(PREFIX):] if name.startswith(PREFIX) else name
    for folder, pat in RULES:
        if pat.search(body):
            return folder
    return FALLBACK


def sha256_of(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--desk", default=None, help="桌面绝对路径；默认 %%USERPROFILE%%\\OneDrive\\桌面")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--undo", default=None)
    a = ap.parse_args()

    desk = pathlib.Path(a.desk) if a.desk else (pathlib.Path.home() / "OneDrive" / "桌面")
    desk = desk.resolve()
    if not desk.is_dir():
        print("ERR 桌面目录不存在：%s" % desk)
        return 2
    arch = (desk / ARCHIVE).resolve()
    print("═══ 本席桌面归档 ═══")
    print("  桌面 = %s" % desk)
    print("  归档夹 = %s" % arch.name)

    # ── undo ──
    if a.undo:
        man = pathlib.Path(a.undo)
        if not man.is_file():
            print("ERR 清单不存在：%s" % man); return 2
        n = ok = 0
        for line in man.read_text(encoding="utf-8").splitlines():
            if line.startswith("#") or not line.strip():
                continue
            src, dst, size, _h = line.split("\t")
            n += 1
            sp, dp = pathlib.Path(src), pathlib.Path(dst)
            if sp.exists():
                print("  跳过（源已在）：%s" % sp.name); continue
            if not dp.is_file():
                print("  ★ 缺件（无法还原）：%s" % dp.name); continue
            sp.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dp), str(sp))
            ok += 1
        print("  还原 %d / %d" % (ok, n))
        return 0

    # ── 分类 ──
    mine = sorted(p for p in desk.iterdir() if p.is_file() and p.name.startswith(PREFIX))
    print("  本席散件 = %d 件" % len(mine))
    buckets: dict[str, list[pathlib.Path]] = {}
    for p in mine:
        buckets.setdefault(classify(p.name), []).append(p)
    total = 0
    for folder in sorted(buckets):
        print("     %-22s %4d 件" % (folder, len(buckets[folder])))
        total += len(buckets[folder])
    print("  合计 = %d 件" % total)

    if a.plan or not a.apply:
        if not a.apply:
            print()
            print("  ★ 这是【计划】：未动盘。要真搬请加 --apply")
        return 0

    # ── 真搬 ──
    arch.mkdir(parents=True, exist_ok=True)
    man = desk / (ARCHIVE + "_搬移清单.tsv")
    rows, moved, refused = [], 0, []
    for folder in sorted(buckets):
        sub = (arch / folder)
        sub.mkdir(parents=True, exist_ok=True)
        # ★ 落点断言：子夹必须在归档夹内
        if not str(sub.resolve()).startswith(str(arch)):
            print("  ★ 落点越界，拒绝：%s" % sub); return 3
        for p in buckets[folder]:
            dst = (sub / p.name)
            if dst.exists():
                refused.append(p.name); continue
            size, digest = p.stat().st_size, sha256_of(p)
            shutil.move(str(p), str(dst))
            rows.append("%s\t%s\t%d\t%s" % (p.resolve(), dst.resolve(), size, digest))
            moved += 1
    man.write_text("# 本席桌面归档搬移清单（--undo 可完整还原）\n" + "\n".join(rows) + "\n",
                   encoding="utf-8")
    print()
    print("  已搬 = %d 件" % moved)
    if refused:
        print("  ★ 拒搬（目的已存在，不覆盖）= %d 件：%s" % (len(refused), "、".join(refused[:5])))
    print("  清单 = %s（%d 行）" % (man.name, len(rows)))
    left = [p.name for p in desk.iterdir() if p.is_file() and p.name.startswith(PREFIX)]
    print("  桌面根剩余本席散件 = %d 件 %s" % (len(left), ("（★未清空：" + "、".join(left[:3]) + "）") if left else "⇒ 已清空"))
    print("  ★ 本器不删任何东西；未命中 PREFIX 的文件【一律未动】。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
