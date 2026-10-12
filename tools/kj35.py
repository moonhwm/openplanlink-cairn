# -*- coding: utf-8 -*-
"""kj35.py —— 补口径章三第 18 条（云文档为活⇒变更报为真；实质性判在归一）（2026-10-13）"""
import hashlib, pathlib, shutil, sys

sys.stdout.reconfigure(encoding="utf-8")
q = pathlib.Path.home()/"openplanlink-cairn"/"mem"/"运行口径_20261012.md"
t = q.read_text(encoding="utf-8")
mk = "## 四、变更裁决口径"
it = ("19. **★云文档为活 ⇒「变更」报为真；实质性判在归一**（`-1435` 更正 `-1432`／`-1433`／`-1434`："
      "六 key 之相邻两次拉取 sha3 ★5 异 1 同 ⇒ 变更系云端微变，★非「两器自比」）⇒ "
      "**★故「有变更」不必惊；★须再看归一后节级差异是否为 0**（第 3.5 步）；"
      "**★且两器之比法皆为「比 hash」⇒ 与「谁写了 prev」无关**。\n\n")
n = 0
if "云文档为活" not in t and mk in t:
    t = t.replace(mk, it + mk, 1)
    n += 1
q.write_text(t, encoding="utf-8", newline="\n")
dst = (pathlib.Path.home()/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"
       /"A2A新席_石敢当Cairn_20260928"/"ops"/"运行口径_20261012.md")
shutil.copy2(q, dst)


def h(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:16]


lines = q.read_text(encoding="utf-8").splitlines()
print("  ✓ 已补 %d 条（章三第 19）" % n)
print("   ★两处 hash：%s ｜ %s ⇒ %s" % (h(q), h(dst), "★一致" if h(q) == h(dst) else "★不一致"))
print("   ★复算命中：%d 处" % sum(1 for l in lines if "云文档为活" in l))
print("   ★口径总行数 %d ｜ ★编号条目 %d" % (len(lines),
      sum(1 for l in lines if l[:1].isdigit() and ". **" in l[:8])))
