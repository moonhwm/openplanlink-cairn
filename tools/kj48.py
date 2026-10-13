# -*- coding: utf-8 -*-
"""kj48.py —— 为《运行口径》另立新章「十一、本夜实证补条（续）—— 台账、同步与判账」（2026-10-14 立）

纪律：★只增不改｜★两处副本 hash 须一致｜★另立新章以避编号冲突
用法：python kj48.py
"""
import hashlib, pathlib, shutil, sys

sys.stdout.reconfigure(encoding="utf-8")
HOME = pathlib.Path.home()
Q = HOME / "openplanlink-cairn" / "mem" / "运行口径_20261012.md"
DST = (HOME / "WPS Cloud" / "WPSDrive" / "29969771" / "WPS云盘" / "月之暗面的Plasma游乐场"
       / "A2A新席_石敢当Cairn_20260928" / "ops" / "运行口径_20261012.md")

ITEMS = [
    ("推送即同步（正本腿须含台账本体）",
     "「双通道推送」之 cairn 腿，须含**台账本体**，不得只暂存仓内同名文件而内容未变 ⇒ "
     "**推送五步**：① copy 席位关键账件（台账／快照）入仓 ② 校验行数与首末行 ③ **显式列名** `git add` "
     "④ push ⑤ 核「未推 0」（`-1519`：仓内账曾滞后 170 条、6 日未更新）。"),
    ("五看判账法（两份同类账之关系判定）",
     "须五看并行：① 逐行同一性（前缀）② `hash` 集合关系 ③ `prev` 链位置 ④ 内容集合（`subject`）"
     "⑤ **时点吻合检验**（滞后量是否恰等于时点差）⇒ **单看其一必误**"
     "（`-1517`／`-1518`：本席曾五度修正，前四度皆偏）。"),
    ("同址异文须两版皆留",
     "同一链位置（同 `ts`／同 `prev`）而文本不同者，**两版皆留**，不得择一而弃 ⇒ "
     "并定位其成因（`-1518`：分叉点 #109 之两种 `detail`／`hash`）。"),
    ("分叉处置：先留痕、后换入",
     "两账分叉之处置，须**先**将旧账转存 `archive/` 留痕，**后**换入新账 ⇒ "
     "**非破坏兼收**，完整保留双方历史脉络（`-1519`：旧账 727 行转存后换入席位账 898 行）。"),
    ("占位件只读元数据，不读正文",
     "云盘占位件（`Offline`／`Recall`）**不得读取正文** —— 读取即触发**按需回补**，反增本地占用 ⇒ "
     "凡扫描／计数／去重，一律**以元数据（名／大小／属性）为据**，并标「疑似」而非「确证」"
     "（`-1504`／`-1506`：本席曾因核哈希致盘 C 余量 90.9 GB ⇒ 74.88 GB）。"),
]


def sha16(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def main() -> int:
    t = Q.read_text(encoding="utf-8")
    mark = "## 十一、本夜实证补条（续）—— 台账、同步与判账（2026-10-14，只增不改）"
    if mark in t:
        print("   · 已含第十一章（无需再补）")
        return 0
    lines = ["", "---", "", mark, "",
             "> 立章之由：**本夜 27–34 轮之实证所得，宜固化**；**★只增不改**，不动既有章与条目。", ""]
    for i, (name, body) in enumerate(ITEMS, 1):
        lines.append("%d. **★%s**：%s" % (i, name, body))
    lines.append("")
    t2 = t.rstrip("\n") + "\n" + "\n".join(lines)
    Q.write_text(t2, encoding="utf-8", newline="\n")
    DST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Q, DST)
    ok = sha16(Q) == sha16(DST)
    print("   ✓ 已另立第十一章，含 %d 条 ｜ 行数 %d ｜ 两处 hash %s ｜ %s"
          % (len(ITEMS), len(t2.splitlines()), sha16(Q), "★一致" if ok else "★不一致"))
    for i, (n, _) in enumerate(ITEMS, 1):
        print("     %d. %s" % (i, n))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
