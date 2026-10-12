# -*- coding: utf-8 -*-
"""kj42.py —— 补口径章八第 12 条（推送判据＝origin..HEAD 条数）（2026-10-13）"""
import hashlib, pathlib, shutil, sys

sys.stdout.reconfigure(encoding="utf-8")
q = pathlib.Path.home()/"openplanlink-cairn"/"mem"/"运行口径_20261012.md"
t = q.read_text(encoding="utf-8")
mk = "## 九、本件之维护"
it = ("12. **★推送之判据＝`git log origin/main..HEAD` 之条数，而非匹配 push 输出**（`-1447` 自纠三十七："
      "以「匹配 `main -> main`／`up-to-date`」判推送 ⇒ 网络不通时两者皆无 ⇒ 误报「未推」；且「未推 0」"
      "亦须经此复核）⇒ **★推后必跑 `git log origin/main..HEAD --oneline ｜ 数其条数`，0 为成**；"
      "**★且推送失败先核代理端口（如 `Test-Connection -TcpPort 10081`）与直连之辨（TCP 通 ≠ HTTPS 可用）**。\n\n")
n = 0
if "推送之判据" not in t and mk in t:
    t = t.replace(mk, it + mk, 1)
    n += 1
q.write_text(t, encoding="utf-8", newline="\n")
dst = (pathlib.Path.home()/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"
       /"A2A新席_石敢当Cairn_20260928"/"ops"/"运行口径_20261012.md")
shutil.copy2(q, dst)


def h(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:16]


lines = q.read_text(encoding="utf-8").splitlines()
print("  ✓ 已补 %d 条（章八第 12）" % n)
print("   ★两处 hash：%s ｜ %s ⇒ %s" % (h(q), h(dst), "★一致" if h(q) == h(dst) else "★不一致"))
print("   ★复算命中：%d 处" % sum(1 for l in lines if "推送之判据" in l))
print("   ★口径总行数 %d ｜ ★编号条目 %d" % (len(lines),
      sum(1 for l in lines if l[:1].isdigit() and ". **" in l[:8])))
