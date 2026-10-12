# -*- coding: utf-8 -*-
"""kj32.py —— 补口径章八第 9 条（长中文脚本须先落文件再跑）（2026-10-13）"""
import hashlib, pathlib, shutil, sys

sys.stdout.reconfigure(encoding="utf-8")
q = pathlib.Path.home()/"openplanlink-cairn"/"mem"/"运行口径_20261012.md"
t = q.read_text(encoding="utf-8")
mk = "## 九、本件之维护"
it = ("9. **★长中文脚本须「先落文件再跑」**（`-1427` 自纠三十二：以 PowerShell here-string 传"
      "含反引号与长中文之 Python 脚本★偶发失败 —— 一夜一次 `exit code 1`、输出乱码「线程未处理」）⇒ "
      "**★一律改用「以 `write` 落 `.py` ⇒ 编译 ⇒ 执行」三步**，★勿以 here-string 直传长中文。\n\n")
n = 0
if "先落文件再跑" not in t and mk in t:
    t = t.replace(mk, it + mk, 1)
    n += 1
q.write_text(t, encoding="utf-8", newline="\n")
dst = (pathlib.Path.home()/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"
       /"A2A新席_石敢当Cairn_20260928"/"ops"/"运行口径_20261012.md")
shutil.copy2(q, dst)


def h(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:16]


lines = q.read_text(encoding="utf-8").splitlines()
print("  ✓ 已补 %d 条（章八第 9）" % n)
print("   ★两处 hash：%s ｜ %s ⇒ %s" % (h(q), h(dst), "★一致" if h(q) == h(dst) else "★不一致"))
print("   ★复算命中：%d 处" % sum(1 for l in lines if "先落文件再跑" in l))
print("   ★口径总行数 %d ｜ ★编号条目 %d" % (len(lines),
      sum(1 for l in lines if l[:1].isdigit() and ". **" in l[:8])))
