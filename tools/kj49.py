# -*- coding: utf-8 -*-
"""kj49.py —— 为《运行口径》另立新章「十二、本夜实证补条（三）—— 器物幂等与留痕」（2026-10-14 立）

纪律：★只增不改｜★两处副本 hash 须一致｜★另立新章以避编号冲突
★注：字符串内一律用中文引号（半角双引号嵌套会致 SyntaxError —— 本轮已犯一次，记之）
用法：python kj49.py
"""
import hashlib, pathlib, shutil, sys

sys.stdout.reconfigure(encoding="utf-8")
HOME = pathlib.Path.home()
Q = HOME / "openplanlink-cairn" / "mem" / "运行口径_20261012.md"
DST = (HOME / "WPS Cloud" / "WPSDrive" / "29969771" / "WPS云盘" / "月之暗面的Plasma游乐场"
       / "A2A新席_石敢当Cairn_20260928" / "ops" / "运行口径_20261012.md")

ITEMS = [
    ("器物须幂等（重跑不得再建）",
     "凡「创建类」器物，重跑前须先查既有产出（如 `list-my-files` 建「名 ⇒ id」表）；"
     "命中同名者**复用其 id 并以写入动作覆盖**，**不得再建** ⇒ "
     "否则重跑即堆积重复件（`-1531`：第二批以 `--limit 19` 重跑，致前 6 件重复创建）。"),
    ("日志须分文件，不得覆盖",
     "凡器物之台账／日志，须**带时间戳分文件**（或以追加方式）保存 ⇒ 不得写同一文件而覆盖前批 ⇒ "
     "否则失前批之原始标识（`-1531`：round 45 之日志被覆盖，前 6 件之原 `file_id` 已失）。"),
    ("写入使版本号递增（可逐次留痕）",
     "WPS 智能文档之 `otl insert-content` **每次写入皆使 `version` 递增**（实测 3 ⇒ 5）⇒ "
     "**「版本追踪」非仅元数据，而是逐次可回溯** ⇒ 凡对外交付件，宜以写入版本号为其留痕之据"
     "（`-1527`／`-1530`／`-1532`）。"),
]


def sha16(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def main() -> int:
    t = Q.read_text(encoding="utf-8")
    mark = "## 十二、本夜实证补条（三）—— 器物幂等与留痕（2026-10-14，只增不改）"
    if mark in t:
        print("   · 已含第十二章（无需再补）")
        return 0
    lines = ["", "---", "", mark, "",
             "> 立章之由：**本夜器物与留痕之实证所得，宜固化**；**★只增不改**，不动既有章与条目。", ""]
    for i, (name, body) in enumerate(ITEMS, 1):
        lines.append("%d. **★%s**：%s" % (i, name, body))
    lines.append("")
    t2 = t.rstrip("\n") + "\n" + "\n".join(lines)
    Q.write_text(t2, encoding="utf-8", newline="\n")
    DST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Q, DST)
    ok = sha16(Q) == sha16(DST)
    print("   ✓ 已另立第十二章，含 %d 条 ｜ 行数 %d ｜ 两处 hash %s ｜ %s"
          % (len(ITEMS), len(t2.splitlines()), sha16(Q), "★一致" if ok else "★不一致"))
    for i, (n, _) in enumerate(ITEMS, 1):
        print("     %d. %s" % (i, n))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
