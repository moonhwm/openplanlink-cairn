# -*- coding: utf-8 -*-
"""kj39.py —— 补口径章三第 20 条（模型建议须以本机实况校验）（2026-10-13）"""
import hashlib, pathlib, shutil, sys

sys.stdout.reconfigure(encoding="utf-8")
q = pathlib.Path.home()/"openplanlink-cairn"/"mem"/"运行口径_20261012.md"
t = q.read_text(encoding="utf-8")
mk = "## 四、变更裁决口径"
it = ("20. **★模型之建议须以「本机实况」校验，不可尽信**（`-1441`：302 `gpt-5` 之「导演」建议"
      "「改用 Chrome 启动客户端」—— 建议合理而★本机无 Chrome（亦无 Firefox／Opera／Brave，"
      "唯 Edge 且其不可用））⇒ **★凡模型给出之「动作建议」，须先核其前提在本机是否成立**。\n\n")
n = 0
if "模型之建议须以" not in t and mk in t:
    t = t.replace(mk, it + mk, 1)
    n += 1
q.write_text(t, encoding="utf-8", newline="\n")
dst = (pathlib.Path.home()/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"
       /"A2A新席_石敢当Cairn_20260928"/"ops"/"运行口径_20261012.md")
shutil.copy2(q, dst)


def h(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:16]


lines = q.read_text(encoding="utf-8").splitlines()
print("  ✓ 已补 %d 条（章三第 20）" % n)
print("   ★两处 hash：%s ｜ %s ⇒ %s" % (h(q), h(dst), "★一致" if h(q) == h(dst) else "★不一致"))
print("   ★复算命中：%d 处" % sum(1 for l in lines if "模型之建议须以" in l))
print("   ★口径总行数 %d ｜ ★编号条目 %d" % (len(lines),
      sum(1 for l in lines if l[:1].isdigit() and ". **" in l[:8])))
