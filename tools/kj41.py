# -*- coding: utf-8 -*-
"""kj41.py —— 补口径章八两条（seal_files 不得为空；长命令分段）（2026-10-13）"""
import hashlib, pathlib, shutil, sys

sys.stdout.reconfigure(encoding="utf-8")
q = pathlib.Path.home()/"openplanlink-cairn"/"mem"/"运行口径_20261012.md"
t = q.read_text(encoding="utf-8")
mk = "## 九、本件之维护"
it = ("10. **★`mkled` 之 `seal_files` ★不得为空**（`-1450` 实测：`[]` 被闸拒、报 "
      "`[ERR] 缺必填键或为空：['seal_files']`）⇒ **★凡记账件必附至少一个 seal 文件**（如 `运行口径_20261012.md`）。\n\n"
      "11. **★长命令宜分段；崩溃后先探 shell**（`-1447` 实录：一条多步命令致 Windows Job runner "
      "崩溃 `3221226091`＝`0xC0000409`，且其后两次调用同错、约 1h50m 后方恢复）⇒ "
      "**★①多步命令拆为短命令；②若现 `3221226091` 类错，先以最简命令（如打一句 'shell-ok'）探活，再续工**。\n\n")
n = 0
if "不得为空」" not in t and mk in t:
    t = t.replace(mk, it + mk, 1)
    n += 1
q.write_text(t, encoding="utf-8", newline="\n")
dst = (pathlib.Path.home()/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"
       /"A2A新席_石敢当Cairn_20260928"/"ops"/"运行口径_20261012.md")
shutil.copy2(q, dst)


def h(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:16]


lines = q.read_text(encoding="utf-8").splitlines()
print("  ✓ 已补 %d 条（章八第 10-11）" % n)
print("   ★两处 hash：%s ｜ %s ⇒ %s" % (h(q), h(dst), "★一致" if h(q) == h(dst) else "★不一致"))
print("   ★复算命中（不得为空）：%d 处" % sum(1 for l in lines if "不得为空」" in l))
print("   ★复算命中（长命令宜分段）：%d 处" % sum(1 for l in lines if "长命令宜分段" in l))
print("   ★口径总行数 %d ｜ ★编号条目 %d" % (len(lines),
      sum(1 for l in lines if l[:1].isdigit() and ". **" in l[:8])))
