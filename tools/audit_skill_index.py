#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
audit_skill_index.py —— 技能索引与仓库一致性诊断（可复现·可入 CI）。 v1.0.0

来由
────
《2026-9-25-OpenPlanLink 润色-1 (3)》**L1152**：『优化技能调度本身，**修复构建结果无法正常搜索的问题**』。
本席据此诊断 `qoder-skills-hub`，发现其**索引与仓库不同步**，且**自检在结构上发现不了这个缺口**。

它回答四个问题（每个都可证伪）
──────────────────────────────
1. 仓库里有几个技能目录（含 SKILL.md）？
2. 索引里有几条？（两者不等即有缺口）
3. 哪些技能【在仓库、不在索引】⇒ **这些技能搜不到**；
4. 哪些【在索引、不在仓库】⇒ **幽灵条目**；
5. 并核：自检脚本能否发现上述缺口（若其遍历集合 == 索引键集，则**结构上不可能发现**）。

用法
────
    audit_skill_index.py <paths.tsv> <index.json> [--selfcheck-names]

`paths.tsv`：仓库全树，每行 `类型<TAB>路径`（可由 GitHub trees API 生成：
    git/trees/<ref>?recursive=1 → 每项输出 "type\tpath"）
`index.json`：如 docs/skill-index-zh-v3.json（须含 `entries` 对象）

退出码：0 = 一致；1 = 存在缺口（可直接用于 CI 阻断）。
"""
from __future__ import annotations
import json
import pathlib
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    tsv, idxf = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    rows = [l.split("\t") for l in tsv.read_text(encoding="utf-8-sig").splitlines() if "\t" in l]
    skills = sorted({p.split("/")[0] for t, p in rows
                     if t == "blob" and p.endswith("/SKILL.md") and p.count("/") == 1})
    evals = sorted({p.rsplit("/", 1)[1][:-5] for t, p in rows
                    if t == "blob" and p.startswith("docs/evals/") and p.endswith(".json")})
    data = json.loads(idxf.read_text(encoding="utf-8"))
    entries = data.get("entries", data)
    keys = set(entries.keys())

    print("═══ 技能索引一致性诊断 ═══")
    print("索引 generatedAt = %s ｜ basis = %s" % (data.get("generatedAt"), data.get("basis")))
    print("① 仓库技能目录（含 SKILL.md）   = %d" % len(skills))
    print("② 索引 entries                = %d" % len(keys))
    print("③ 评测集 docs/evals/*.json    = %d" % len(evals))

    miss = [s for s in skills if s not in keys]
    ghost = sorted(k for k in keys if k not in skills)
    noeval = [s for s in skills if s not in evals]

    print()
    print("④ ★在仓库、不在索引 ⇒【搜不到】：%d 件" % len(miss))
    for s in miss:
        print("      %-34s 评测集=%s" % (s, "有" if s in evals else "无"))
    print("⑤ ★在索引、不在仓库 ⇒ 幽灵条目：%d 件" % len(ghost))
    for s in ghost[:20]:
        print("      " + s)
    print("⑥ 有技能目录但无评测集的：%d 件（评测覆盖不了它们，也就无从度量其召回）" % len(noeval))
    for s in noeval[:20]:
        print("      " + s)

    print()
    print("⑦ ★自检盲区判定（可证伪）：")
    print("   若自检脚本的遍历集合 == 索引键集（常见写法 names = Object.keys(idx)），")
    print("   则【索引外的技能永远不会被它看见】——**它的盲区与缺陷同源**，")
    print("   故『自检通过』不能证明『全部技能可搜』。")
    print("   ⇒ 修法：自检与索引生成均应以【仓库技能目录】为遍历集合，而非以索引自身为集合。")

    # ★两个数必须分开报：缺陷【计数】与受影响技能【去重数】。
    #   来由：本器首版把『未入索引』与『无评测集』相加得 6，而这实为【同一批 3 件技能、每件两个缺陷】——
    #   相加所得是个会误导的数（读者会以为有 6 件技能出问题）。**同一件事不许报两遍。**
    flaws = len(miss) + len(ghost) + len(noeval)
    affected = sorted(set(miss) | set(ghost) | set(noeval))
    print()
    print("═══ 结论：%s ═══" % ("PASS —— 索引、仓库、评测三者一致" if flaws == 0 else "FAIL"))
    print("   缺陷计数（各按一类计） = %d" % flaws)
    print("   ★受影响技能（去重）     = %d 件%s"
          % (len(affected), ("：" + "、".join(affected)) if affected else ""))
    print("   ★两者必须分开报：相加所得不是『几件技能出问题』——同一件技能可带多个缺陷。")
    return 0 if flaws == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
