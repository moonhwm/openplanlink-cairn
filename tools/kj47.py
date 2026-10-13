# -*- coding: utf-8 -*-
"""kj47.py —— 为《运行口径》另立新章「十、本夜实证补条」（2026-10-14 立）

纪律：★只增不改（不动既有章与条目）｜★两处副本 hash 须一致｜★另立新章以避编号冲突
      （★实查：既有件各章各自编号、最大号仅 21 ⇒ 不宜续号）
用法：python kj47.py
"""
import hashlib, pathlib, shutil, sys

sys.stdout.reconfigure(encoding="utf-8")
HOME = pathlib.Path.home()
Q = HOME / "openplanlink-cairn" / "mem" / "运行口径_20261012.md"
DST = (HOME / "WPS Cloud" / "WPSDrive" / "29969771" / "WPS云盘" / "月之暗面的Plasma游乐场"
       / "A2A新席_石敢当Cairn_20260928" / "ops" / "运行口径_20261012.md")

ITEMS = [
    ("名义大小 ≠ 本地实占", "云盘占位件（WPS／OneDrive）之 `st_size` 为名义值；判本地是否真占空间，"
     "须以 `GetCompressedFileSize` 或 `Offline/Recall` 属性为据 ⇒ "
     "凡磁盘清理类结论，不得以名义大小之求和为凭（`-1506`：游乐场根名义 38 GB 而本地实占仅 34.9 MB）。"),
    ("提交须显式列名", "`git add` 须逐件列明（`git add -- <本席之件>`），不用 `-A` ⇒ "
     "否则将卷入他席未提交之工作区改动（`-1507`：本席曾误将他席 7 件卷入提交）。"),
    ("签名 URL 不入公共仓", "凡含带签名之云存储链接（COS／OSS／S3 presigned）之件，须先去签名参数方入公共仓 ⇒ "
     "否则被 GitHub Push Protection 拦（`-1507`）。"),
    ("未见产出须先核时序", "凡某器似未产出之件，须先核其流程时序（是否尚有后续步骤未完）再判缺陷 ⇒ "
     "不得以某一时刻未见即断未写（`-1510`：曾误判 `doc_archive` 之登记腿为缺陷，实为观测过早）。"),
    ("节级差异以标题序列为主判据", "节标识为内容 hash，对节内微变敏感 ＋ 切分偏移 ⇒ "
     "等量之「新增 N／删除 N／变动 0」多为伪差异 ⇒ 须以节标题序列复核（`-1509`）。"),
    ("避 junction 遍历", "只读扫描／计数／检索等大批量遍历，须直连实体路径"
     "（如 `WPS Cloud` 下之实体，而非 `WPSDrive` 之 junction 别名）⇒ 实测 2.4 倍开销"
     "（`-1501`：`doc_refresh` 扫描腿 639 s ⇒ 112.7 s，降 5.7 倍）。"),
    ("呈批区与禁区须三分", "作合规类判定时，标签应为三值：全权自治区／呈批区／禁区 ⇒ "
     "二分（是否呈批区）必致「呈批区」与「禁区」混淆（`-1489`：三区版准确率 80.0%、Brier 0.0971，优于二分版）。"),
    ("LLM 响应须健壮抽取", "取 JSON 前须剥 markdown 围栏、取首 `{` 至末 `}`；并注意 provider 兼容"
     "（`response_format` 或不支持；超时宜 300 s）（`-1488`／`-1489`）。"),
    ("极显著之 p 记法", "Z 约 8 以上时，双精度下 `1−Φ(Z)` 下溢为 0 ⇒ 须记 `p < 1e-30`（或给 `log10_p`），"
     "不得记 `0.0`（`-1487`）。"),
    ("检索类结论三要件", "切分口径 ＋ 语料纯净 ＋ 样本量，三者缺一则结论不可靠 ⇒ 并须随附可复算脚本"
     "（`-1493`／`-1495`／`-1496`：四版实证曾三度翻转结论）。"),
]


def sha16(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def main() -> int:
    t = Q.read_text(encoding="utf-8")
    mark = "## 十、本夜实证补条（2026-10-14，只增不改）"
    if mark in t:
        print("   · 已含新章（无需再补）"); return 0
    lines = ["", "---", "", mark, "",
             "> 立章之由：**本夜诸实证所得，宜固化**；**★只增不改**，不动既有章与条目。", ""]
    for i, (name, body) in enumerate(ITEMS, 1):
        lines.append("%d. **★%s**：%s" % (i, name, body))
    lines.append("")
    t2 = t.rstrip("\n") + "\n" + "\n".join(lines)
    Q.write_text(t2, encoding="utf-8", newline="\n")
    DST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Q, DST)
    ok = sha16(Q) == sha16(DST)
    print("   ✓ 已另立新章「十、本夜实证补条」，含 %d 条" % len(ITEMS))
    print("   ★行数 %d ｜ 两处 hash %s ｜ %s" % (len(t2.splitlines()), sha16(Q), "★一致" if ok else "★不一致"))
    for i, (n, _) in enumerate(ITEMS, 1):
        print("     %d. %s" % (i, n))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
