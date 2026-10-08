#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只在本机读席位件并写一个 zip 与两份元数据；不触网。
r"""make_pack.py —— 把本席可交付物打成一个【可被第三方核验】的包。 v1.0.0

纪律（写在代码里）
────────────────────
  ① **清单先于包**：先写 `_pack_manifest.tsv`（相对路径／字节／sha256），再写 zip；
  ② **排除项写明理由**：`_pack_exclude.txt` 逐条记"排除了什么、为什么"；
  ③ **写完回读**：重开 zip 逐条比对清单（条数＋字节＋sha256），任一不符即报错退出；
  ④ **不打包别人仓库**：`handshake\` 一律排除（那是别人的解包树）；
  ⑤ **不打包机主原件**：`inbox\` 一律排除（那是机主投来的 docx 等）；
  ⑥ **不打包缓存/字节码**：`.pyc`、`__pycache__`、`_retired\`；
  ⑦ 只用 stdlib；不新造框架。

用法
──────
  python make_pack.py --plan                 # 只出清单与排除表，不写 zip
  python make_pack.py --apply                # 写 zip ＋ 元数据
  python make_pack.py --verify <zip> <manifest.tsv>
"""
from __future__ import annotations
import argparse
import hashlib
import pathlib
import sys
import zipfile

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SEAT = pathlib.Path(__file__).resolve().parent.parent          # <seat>
DESK = SEAT.parent                                             # 桌面
ARCHIVE_NAME = "_石敢当席_20261002交付归档"
PACK_NAME = "石敢当席_交付包_20261002.zip"

# ★ 排除表：(前缀, 理由)
EXCLUDE = [
    ("handshake/", "别人仓库的解包树（非本席产出；原件在 handshake 下的 .tar.gz 里）"),
    ("inbox/",     "机主投来的原件（docx/媒体）——不属本席产出，且体积大"),
    ("exp/_retired/", "退役并写明理由的器（保留在席位内，不入包）"),
]
EXCLUDE_SUFFIX = (".pyc",)


def sha256_of(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def excluded(rel: str) -> str | None:
    if "__pycache__" in rel or rel.endswith(EXCLUDE_SUFFIX):
        return "字节码缓存（可重生）"
    for pre, why in EXCLUDE:
        if rel.startswith(pre):
            return why
    return None


def collect() -> tuple[list[tuple[str, pathlib.Path]], list[tuple[str, str]]]:
    """返回 (入包项[(包内路径, 本机路径)], 排除项[(路径, 理由)])。"""
    keep, drop = [], []
    roots = [(SEAT, "")]                                   # 席位整棵，按前缀过滤
    extra = DESK / ARCHIVE_NAME                            # 桌面归档夹，另加
    for root, pref in roots:
        for p in sorted(root.rglob("*")):
            if not p.is_file():
                continue
            rel_to_seat = p.relative_to(SEAT).as_posix()
            why = excluded(rel_to_seat)
            if why:
                drop.append((rel_to_seat, why)); continue
            keep.append((pref + rel_to_seat, p))
    if extra.is_dir():
        for p in sorted(extra.rglob("*")):
            if not p.is_file():
                continue
            rel = ("桌面归档夹/" + p.relative_to(extra).as_posix())
            why = excluded(rel)
            if why:
                drop.append((rel, why)); continue
            keep.append((rel, p))
    return keep, drop


def write_meta(keep, drop) -> tuple[pathlib.Path, pathlib.Path]:
    man = SEAT / "exp" / "_pack_manifest.tsv"
    exc = SEAT / "exp" / "_pack_exclude.txt"
    rows = ["relpath\tbytes\tsha256"]
    for arc, p in keep:
        rows.append("%s\t%d\t%s" % (arc, p.stat().st_size, sha256_of(p)))
    man.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    ex = ["# 不入包的东西与理由（逐条）", ""]
    seen = {}
    for rel, why in drop:
        seen.setdefault(why, 0)
        seen[why] += 1
    for why, n in sorted(seen.items(), key=lambda kv: -kv[1]):
        ex.append("- **%d 项** —— %s" % (n, why))
    ex.append("")
    ex.append("## 前 40 条明细")
    for rel, why in drop[:40]:
        ex.append("- `%s` —— %s" % (rel, why))
    exc.write_text("\n".join(ex) + "\n", encoding="utf-8")
    return man, exc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--verify", nargs=2, metavar=("ZIP", "MANIFEST"))
    a = ap.parse_args()

    if a.verify:
        zp, mp = pathlib.Path(a.verify[0]), pathlib.Path(a.verify[1])
        if not zp.is_file() or not mp.is_file():
            print("ERR 缺件：%s / %s" % (zp, mp)); return 2
        rows = [l.split("\t") for l in mp.read_text(encoding="utf-8").splitlines()[1:] if l.strip()]
        print("═══ 回读核验 ═══")
        print("  清单行数 = %d" % len(rows))
        with zipfile.ZipFile(zp) as z:
            names = set(z.namelist())
            bad = []
            for arc, sz, h in rows:
                if arc not in names:
                    bad.append("缺条目：" + arc); continue
                data = z.read(arc)
                if len(data) != int(sz): bad.append("字节不符：" + arc); continue
                if hashlib.sha256(data).hexdigest() != h: bad.append("sha256 不符：" + arc)
            extra = names - {r[0] for r in rows}
        print("  zip 条目 = %d ｜ ★不符 = %d ｜ 多出条目 = %d" % (len(names), len(bad), len(extra)))
        for b in bad[:8]: print("     ★ " + b)
        print("  ⇒ %s" % ("✅ 包与清单逐条相符" if not bad and not extra else "★有出入，见上"))
        return 0 if not bad and not extra else 1

    keep, drop = collect()
    total = sum(p.stat().st_size for _, p in keep)
    print("═══ 打包计划 ═══")
    print("  入包 = %d 件 ／ %.2f MB" % (len(keep), total / 1048576))
    print("  排除 = %d 件" % len(drop))
    by = {}
    for arc, _ in keep:
        top = arc.split("/")[0]
        by[top] = by.get(top, 0) + 1
    for k in sorted(by, key=lambda x: -by[x])[:12]:
        print("     %-28s %5d 件" % (k, by[k]))
    man, exc = write_meta(keep, drop)
    print("  清单 = exp\\%s ｜ 排除表 = exp\\%s" % (man.name, exc.name))

    if not a.apply:
        print("  ★ 这是【计划】：未写 zip。要真打包请加 --apply")
        return 0

    out = SEAT / "outbox" / PACK_NAME
    if out.exists():
        print("  ★ 目标已存在 ⇒ 不覆盖（只增不改）：%s" % out.name); return 1
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for arc, p in keep:
            z.write(p, arc)
    side = out.with_name(out.name + ".sha256")
    side.write_text("%s  %s\n" % (sha256_of(out), out.name), encoding="utf-8", newline="\n")
    print("  已写 = %s ／ %.2f MB" % (out.name, out.stat().st_size / 1048576))
    print("  旁证 = %s" % side.name)
    print("  ★ 下一步请跑：python exp\\make_pack.py --verify \"%s\" \"%s\"" % (out, man))
    return 0


if __name__ == "__main__":
    sys.exit(main())
