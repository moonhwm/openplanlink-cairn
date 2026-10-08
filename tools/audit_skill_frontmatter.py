#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
audit_skill_frontmatter.py —— skills/ 库【100% 覆盖】的命名核对。 v1.0.0

为什么要换方法
──────────────
上一轮（audit_skill_naming.py v1.0.0）对 117 个目录**逐个请求**清单，撞限流，覆盖率只 1.7%。
⇒ 本轮改为 **GitHub 打包一次取全**（codeload tar.gz，1.7 MB，1 次请求），
  于是可以把【全部条目】的『目录名 vs SKILL.md frontmatter 的 name』**逐个比对**，覆盖率 100%。
**同一件事，方法不同，覆盖率从 1.7% 变成 100%——这就是"想办法"的差别。**

安全纪律（解包是最容易出事的一步）
──────────────────────────────────
· 拒绝**绝对路径**、含 `..` 的成员、**符号链接/硬链接**（防 tar 路径穿越）；
· 解到本席领地内的独立目录，不碰任何既有件；
· 只读分析，不改被解包内容。

核什么
──────
对 `skills/<目录>/SKILL.md`：
  ① frontmatter 是否存在（首个 `---` 与次个 `---` 之间）；
  ② 其中是否有 `name:`；
  ③ `name` 是否等于**目录名**；不等则记为**名不副实**。
并输出四类：一致 / 不一致 / 无 frontmatter / 无 name 字段。
"""
from __future__ import annotations
import json
import pathlib
import re
import sys
import tarfile

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SEAT = pathlib.Path(__file__).resolve().parent.parent
TARBALL = SEAT / "handshake" / "opl-mirror-main.tar.gz"
DEST = SEAT / "handshake" / "mirror_tar"


def safe_extract(tar: tarfile.TarFile, dest: pathlib.Path):
    """防路径穿越解包：拒绝绝对路径、`..`、符号/硬链接。"""
    dest = dest.resolve()
    bad = []
    members = []
    for m in tar.getmembers():
        name = m.name
        if m.issym() or m.islnk():
            bad.append((name, "符号/硬链接")); continue
        p = (dest / name).resolve()
        if not str(p).startswith(str(dest)):
            bad.append((name, "越出目标目录")); continue
        if name.startswith("/") or ".." in pathlib.PurePosixPath(name).parts:
            bad.append((name, "绝对路径或含 ..")); continue
        members.append(m)
    tar.extractall(dest, members=members, filter="data")   # filter=data：抑制 3.14 弃用警告；本席自检更严
    return bad, len(members)


FM = re.compile(r"^---\s*$")


def parse_name(text: str):
    lines = text.splitlines()
    if not lines or not FM.match(lines[0]):
        return None, False                      # (name, has_frontmatter)
    end = None
    for i in range(1, len(lines)):
        if FM.match(lines[i]):
            end = i
            break
    if end is None:
        return None, False
    for ln in lines[1:end]:
        m = re.match(r"^\s*name\s*:\s*(.+?)\s*$", ln)
        if m:
            v = m.group(1).strip().strip('"').strip("'")
            return v, True
    return None, True                           # 有 frontmatter 但无 name


def main():
    if not TARBALL.exists():
        print("[ERR] 未找到 tarball：%s" % TARBALL)
        return 2
    DEST.mkdir(parents=True, exist_ok=True)
    print("═══ skills/ 命名核对（100% 覆盖·一次取全）═══")
    with tarfile.open(TARBALL, "r:gz") as tar:
        bad, n = safe_extract(tar, DEST)
        print("安全解包：解出 %d 个成员 ｜ ★拒收 %d 个（%s）"
              % (n, len(bad), "、".join(set(w for _x, w in bad)) or "无"))

    roots = [p for p in DEST.iterdir() if p.is_dir()]
    root = roots[0] if roots else DEST
    skills = root / "skills"
    if not skills.is_dir():
        print("[ERR] 未找到 skills/ 目录于 %s" % skills)
        return 2

    dirs = sorted([d for d in skills.iterdir() if d.is_dir()], key=lambda p: p.name)
    same, diff, no_fm, no_name, no_md = [], [], [], [], []
    for d in dirs:
        md = d / "SKILL.md"
        if not md.is_file():
            no_md.append(d.name); continue
        name, has_fm = parse_name(md.read_text(encoding="utf-8", errors="replace"))
        if not has_fm:
            no_fm.append(d.name)
        elif not name:
            no_name.append(d.name)
        elif name == d.name:
            same.append(d.name)
        else:
            diff.append((d.name, name))

    print("\n目录数 = %d" % len(dirs))
    print("【一】name == 目录名        ：%d" % len(same))
    print("【二】★name != 目录名        ：%d" % len(diff))
    for dn, nm in diff:
        print("     目录 %-34s frontmatter name = %s" % (dn, nm))
    print("【三】有 SKILL.md 但无 frontmatter：%d" % len(no_fm))
    for x in no_fm[:15]:
        print("     %s" % x)
    print("【四】有 frontmatter 但无 name  ：%d" % len(no_name))
    for x in no_name[:15]:
        print("     %s" % x)
    print("【五】无 SKILL.md             ：%d" % len(no_md))
    for x in no_md[:15]:
        print("     %s" % x)

    judged = len(same) + len(diff)
    print("\n═══ 覆盖率：%d/%d = %.1f%% 已完成命名判定 ═══" % (judged, len(dirs), 100.0 * judged / max(len(dirs), 1)))
    print("★两类缺口性质不同：无 frontmatter／无 name 是【件本身缺规格】；")
    print("  名不副实是【目录名与自报名打架】——后者才会让下游按名检索时撞车。")

    out = {"audit": "skills-frontmatter-naming", "dirs_total": len(dirs),
           "same": same, "mismatch": [{"dir": a, "name": b} for a, b in diff],
           "no_frontmatter": no_fm, "no_name_field": no_name, "no_skillmd": no_md,
           "coverage_pct": round(100.0 * judged / max(len(dirs), 1), 1)}
    (SEAT / "handshake" / "skills_frontmatter_audit.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("明细已写：handshake/skills_frontmatter_audit.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
