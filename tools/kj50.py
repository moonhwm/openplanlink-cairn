# -*- coding: utf-8 -*-
"""kj50.py —— 为《运行口径》另立新章「十三、本夜实证补条（四）—— 文本与标识」（2026-10-14 立）

纪律：★只增不改｜★两处副本 hash 须一致｜★另立新章以避编号冲突
★注：本文件字符串内一律用中文引号（承第十二章之教训）
"""
import hashlib, pathlib, shutil, sys

sys.stdout.reconfigure(encoding="utf-8")
HOME = pathlib.Path.home()
Q = HOME / "openplanlink-cairn" / "mem" / "运行口径_20261012.md"
DST = (HOME / "WPS Cloud" / "WPSDrive" / "29969771" / "WPS云盘" / "月之暗面的Plasma游乐场"
       / "A2A新席_石敢当Cairn_20260928" / "ops" / "运行口径_20261012.md")

ITEMS = [
    ("Python 中文文本勿嵌半角双引号",
     "以 Python 书写中文文本（尤其是长句）时，**字符串一律用中文引号「」『』，勿在其内嵌半角双引号** ⇒ "
     "否则字符串提前闭合，致 `SyntaxError`（**本席已二犯**：`kj47.py` 与 `kj49.py`，皆 `invalid character`）"
     "⇒ 且此类错**在编译期即可察**，故**写入后必先 `py_compile` 再运行**。"),
    ("台账记 id 须于重跑后规范化",
     "凡台账记载云端件之 `file_id`，**须于写入后立即取值**；且**凡有重跑，须重新规范化**"
     "（**同名件中优先取「无 `(1)`／`(2)` 者」为正规**）⇒ 否则台账或指向旁支件，"
     "**删重复件即致 id 悬空**（`-1533`：v1 台账前 6 件之 id 实取自 `(1)` 件，已修为 19/19 指正规件）。"),
]


def sha16(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def main() -> int:
    t = Q.read_text(encoding="utf-8")
    mark = "## 十三、本夜实证补条（四）—— 文本与标识（2026-10-14，只增不改）"
    if mark in t:
        print("   · 已含第十三章（无需再补）")
        return 0
    lines = ["", "---", "", mark, "",
             "> 立章之由：**本夜文本与标识之实证所得，宜固化**；**★只增不改**，不动既有章与条目。", ""]
    for i, (name, body) in enumerate(ITEMS, 1):
        lines.append("%d. **★%s**：%s" % (i, name, body))
    lines.append("")
    t2 = t.rstrip("\n") + "\n" + "\n".join(lines)
    Q.write_text(t2, encoding="utf-8", newline="\n")
    DST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Q, DST)
    ok = sha16(Q) == sha16(DST)
    print("   ✓ 已另立第十三章，含 %d 条 ｜ 行数 %d ｜ 两处 hash %s ｜ %s"
          % (len(ITEMS), len(t2.splitlines()), sha16(Q), "★一致" if ok else "★不一致"))
    for i, (n, _) in enumerate(ITEMS, 1):
        print("     %d. %s" % (i, n))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
