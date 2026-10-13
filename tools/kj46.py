# -*- coding: utf-8 -*-
"""kj46.py —— 补口径章八第 13 条（termtable --paths 单值须传目录）（2026-10-14）"""
import hashlib, pathlib, shutil, sys

sys.stdout.reconfigure(encoding="utf-8")
q = pathlib.Path.home()/"openplanlink-cairn"/"mem"/"运行口径_20261012.md"
t = q.read_text(encoding="utf-8")
mk = "## 九、本件之维护"
it = ("13. **★术语闸器 `termtable.py` 之 `--paths` ★不支持多值**（`-1472` 实测：传两个 `--paths` 仍报「范围：1 文件」）"
      "⇒ **★须传「目录」，或逐件调用**；**★且该器之三态须辨：`CLEAN`／`QUALIFIED`（可定稿）与 `UNMEASURED`（exit 2＝未测）"
      "—— 未测不得当 CLEAN**。\n\n")
n = 0
if "termtable.py` 之 `--paths`" not in t and mk in t:
    t = t.replace(mk, it + mk, 1)
    n += 1
q.write_text(t, encoding="utf-8", newline="\n")
dst = (pathlib.Path.home()/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"
       /"A2A新席_石敢当Cairn_20260928"/"ops"/"运行口径_20261012.md")
shutil.copy2(q, dst)


def h(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:16]


lines = q.read_text(encoding="utf-8").splitlines()
print("  ✓ 已补 %d 条（章八第 13）" % n)
print("   ★两处 hash：%s ｜ %s ⇒ %s" % (h(q), h(dst), "★一致" if h(q) == h(dst) else "★不一致"))
print("   ★复算命中：%d 处" % sum(1 for l in lines if "不支持多值" in l))
print("   ★口径总行数 %d ｜ ★编号条目 %d" % (len(lines),
      sum(1 for l in lines if l[:1].isdigit() and ". **" in l[:8])))
