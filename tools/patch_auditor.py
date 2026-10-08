#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""patch_auditor.py —— 修正 audit_robots_compliance.py 两处（v1.0.0 → v1.1.0）。 v1.0.0

修正内容（承轮 74 自查）：
  ① 豁免 /robots.txt 本身——为遵守 robots 必须先能读它；RFC 9309 以其可读为前提；
     v1.0.0 据此判它为"违规"，属【器具过严】。
  ② 把「robots 未声明（404）」独立成类——v1.0.0 把它错并入「已预查」，属【标签错误】。
"""
from __future__ import annotations
import pathlib
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

P = pathlib.Path(__file__).resolve().parent / "audit_robots_compliance.py"

OLD_START = 'print("═══ 全量审计：今晚外部取件 vs 各主机 robots ═══")'
OLD_END = 'if len(unpre) > 6:\n    print("       · …（其余 %d 条同类）" % (len(unpre) - 6))'

NEW = '''# ★ v1.1.0 修正两处（承轮 74 自查）：
#   ① 豁免 /robots.txt 本身——为遵守 robots 必须先能读它；RFC 9309 亦以其可读为前提。
#      故本器对 /robots.txt 一律记「豁免」，不计入违规。
#   ② 把「robots 未声明」独立成类——v1.0.0 把它错并入「已预查」，属标签错误，已改。
print("═══ 全量审计：今晚外部取件 vs 各主机 robots（v1.1.0）═══")
print("  图例：★违规＝未预查 且 判为禁 ｜ ◐未预查但准 ｜ ✓已预查 ｜ ○robots未声明 ｜ ⊘豁免")
print()
viol, unpre, okc, undecl = [], [], 0, []
cache = {}
for host, path, prechecked in FETCHES:
    if host not in cache:
        st, txt = fetch("https://%s/robots.txt" % host)
        cache[host] = (st, parse_robots(txt) if st == 200 else None)
    st, rules = cache[host]
    if path == "/robots.txt":
        tag, verdict = "⊘豁免", "为遵守 robots 必须可读（RFC 9309 前提）"
    elif rules is None:
        tag, verdict = "○未声明", "robots %s ⇒ 无限制声明" % (st if st else "取不到")
        undecl.append((host, path, prechecked))
    else:
        allowed_now = allowed(rules, path)
        verdict = "准" if allowed_now else "★禁"
        if allowed_now is False and not prechecked:
            tag = "★违规"; viol.append((host, path))
        elif allowed_now is False and prechecked:
            tag = "✓已预查(故未取内容)"
        elif allowed_now is True and not prechecked:
            tag = "◐未预查但准"; unpre.append((host, path))
        else:
            tag = "✓已预查"; okc += 1
    print("  %-16s %-52s ⇒ %s" % (tag, host + path, verdict))

print()
print("  ── 汇总 ──")
print("   取件条目 = %d" % len(FETCHES))
print("   ★违规（未预查 且 判为禁）= %d 条" % len(viol))
for h, p in viol:
    print("       · https://%s%s" % (h, p))
print("   ◐未预查但现判为准 = %d 条" % len(unpre))
for h, p in unpre:
    print("       · https://%s%s" % (h, p))
print("   ○robots 未声明 = %d 条（其中取件前未查者 %d 条）"
      % (len(undecl), sum(1 for _, _, pc in undecl if not pc)))
for h, p, pc in undecl:
    print("       · https://%s%s  ｜ 取件前查过？%s" % (h, p, "是" if pc else "★否"))'''


def main() -> int:
    t = P.read_text(encoding="utf-8")
    i, j = t.find(OLD_START), t.find(OLD_END)
    if i < 0 or j < 0:
        print("[ERR] 锚点未找到"); return 1
    j += len(OLD_END)
    t = t[:i] + NEW + t[j:]
    P.write_text(t, encoding="utf-8")
    print("[OK] 已修正 %s（两处：豁免 robots.txt 本身；未声明独立成类）" % P.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
