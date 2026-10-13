# -*- coding: utf-8 -*-
"""kj44.py —— 补口径章三第 21 条（判"不在"之前须先判"已取到"）（2026-10-13）"""
import hashlib, pathlib, shutil, sys

sys.stdout.reconfigure(encoding="utf-8")
q = pathlib.Path.home()/"openplanlink-cairn"/"mem"/"运行口径_20261012.md"
t = q.read_text(encoding="utf-8")
mk = "## 四、变更裁决口径"
it = ("21. **★判「不在」之前★须先判「已取到」**（`-1461` 自纠三十九：/worlds 因 10054／403 未取到列表，"
      "而我之器即以「items 空」判「不在 50 世界之列」⇒ ★错 —— ★items 空 ≠ 不在）⇒ "
      "**★凡「未命中」之判，先验「取数是否成功」（HTTP 200 且体非空），否则报「取数失败、判无效」**。\n\n")
n = 0
if "判「不在」之前" not in t and mk in t:
    t = t.replace(mk, it + mk, 1)
    n += 1
q.write_text(t, encoding="utf-8", newline="\n")
dst = (pathlib.Path.home()/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"
       /"A2A新席_石敢当Cairn_20260928"/"ops"/"运行口径_20261012.md")
shutil.copy2(q, dst)


def h(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:16]


lines = q.read_text(encoding="utf-8").splitlines()
print("  ✓ 已补 %d 条（章三第 21）" % n)
print("   ★两处 hash：%s ｜ %s ⇒ %s" % (h(q), h(dst), "★一致" if h(q) == h(dst) else "★不一致"))
print("   ★复算命中：%d 处" % sum(1 for l in lines if "判「不在」之前" in l))
print("   ★口径总行数 %d ｜ ★编号条目 %d" % (len(lines),
      sum(1 for l in lines if l[:1].isdigit() and ". **" in l[:8])))
