# -*- coding: utf-8 -*-
"""kj40.py —— 补口径章五第 11 条（列表与单项字段不一致）（2026-10-13）"""
import hashlib, pathlib, shutil, sys

sys.stdout.reconfigure(encoding="utf-8")
q = pathlib.Path.home()/"openplanlink-cairn"/"mem"/"运行口径_20261012.md"
t = q.read_text(encoding="utf-8")
mk = "## 六、写入口径"
it = ("11. **★`/worlds` 之「列表项」与「单项」字段不一致**（`-1444`：50 世界之列表项 `creationModel` "
      "恒 `None`，而单世界查询（`/worlds` 之 item，见 `-1384`）为 `\"simple\"`）⇒ "
      "**★凡取字段，须先明「取自列表还是单项」**（与「进房响应 `mode=1` 而末态 `mode=None`」同族）。\n\n")
n = 0
if "列表项」与「单项」字段不一致" not in t and mk in t:
    t = t.replace(mk, it + mk, 1)
    n += 1
q.write_text(t, encoding="utf-8", newline="\n")
dst = (pathlib.Path.home()/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"
       /"A2A新席_石敢当Cairn_20260928"/"ops"/"运行口径_20261012.md")
shutil.copy2(q, dst)


def h(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:16]


lines = q.read_text(encoding="utf-8").splitlines()
print("  ✓ 已补 %d 条（章五第 11）" % n)
print("   ★两处 hash：%s ｜ %s ⇒ %s" % (h(q), h(dst), "★一致" if h(q) == h(dst) else "★不一致"))
print("   ★复算命中：%d 处" % sum(1 for l in lines if "列表项」与「单项」字段不一致" in l))
print("   ★口径总行数 %d ｜ ★编号条目 %d" % (len(lines),
      sum(1 for l in lines if l[:1].isdigit() and ". **" in l[:8])))
