# -*- coding: utf-8 -*-
"""kj31.py —— 补口径章五第 10 条（环境动作池可经 prompt 点名扩充）＋验两处 hash（2026-10-13）"""
import hashlib, pathlib, shutil, sys

sys.stdout.reconfigure(encoding="utf-8")
q = pathlib.Path.home()/"openplanlink-cairn"/"mem"/"运行口径_20261012.md"
t = q.read_text(encoding="utf-8")
mk = "## 六、写入口径"
it = ("10. **★环境动作池可经 `prompt` 点名扩充**（`-1426` 可复现实验：建世界之 `prompt` 未点名 ⇒ "
      "`environmentActions=[]`（v8「夜游回望」）；★点名 `open_close_door` ⇒ "
      "`['open_close_door']`（v9「夜色游乐场」））⇒ **★欲使某环境动作可选，须在建世界之 `prompt` 中点名之**；"
      "**★而 `characterActions` 恒为四项（`dash`／`jump`／`crouch`／`attack`），不受 `prompt` 影响**。\n\n")
n = 0
if "可经 `prompt` 点名扩充" not in t and mk in t:
    t = t.replace(mk, it + mk, 1)
    n += 1
q.write_text(t, encoding="utf-8", newline="\n")
dst = (pathlib.Path.home()/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"
       /"A2A新席_石敢当Cairn_20260928"/"ops"/"运行口径_20261012.md")
shutil.copy2(q, dst)


def h(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:16]


print("  ✓ 已补 %d 条（章五第 10）" % n)
print("   ★两处 hash：%s ｜ %s ⇒ %s" % (h(q), h(dst), "★一致" if h(q) == h(dst) else "★不一致"))
print("   ★复算命中：%d 处" % sum(1 for l in q.read_text(encoding="utf-8").splitlines()
                                 if "可经 `prompt` 点名扩充" in l))
lines = q.read_text(encoding="utf-8").splitlines()
print("   ★口径总行数 %d ｜ ★编号条目 %d" % (len(lines),
      sum(1 for l in lines if l[:1].isdigit() and ". **" in l[:8])))
