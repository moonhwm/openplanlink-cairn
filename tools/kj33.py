# -*- coding: utf-8 -*-
"""kj33.py —— 修"两器自比"：给 doc_archive 之条目加 by 字段，且 prev 只取本器所写之末条（2026-10-13）
法源：-1432 定论 —— doc_refresh（第①步）与 doc_archive（第②步）★共用 archive/docs/index.json 之
      history 序列 ⇒ 第②步之 prev = history[-1] 往往是第①步数分钟前所写 ⇒ 必报"有变更"（伪变更）。
本补丁（★最小改动：只动 doc_archive.py；★改动前备份）：
  ① 备份至 exp/_patch_backup_<日期>/doc_archive.py
  ② 在 prev 取值处改为：★只取 history 中 by=="doc_archive" 之末条（旧条目无 by ⇒ 不计入）
  ③ 在自身条目 ent 中加 "by": "doc_archive"
  ④ 编译 + 复验（含"仅动一处/两处"之印认）
（中文串一律用「」）
"""
import pathlib, shutil, sys, time, py_compile

SEAT = pathlib.Path.home()/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"
P = SEAT/"exp"/"doc_archive.py"

OLD_PREV = '    prev = m["history"][-1] if m["history"] else None\n'
NEW_PREV = ('    # ★2026-10-13 修「两器自比」（承 -1432）：doc_refresh 与 doc_archive ★共用同一 history，\n'
            '    #   故 history[-1] 常为 doc_refresh 数分钟前所写 ⇒ 必报伪变更。\n'
            '    #   ⇒ ★只取「本器（by==doc_archive）所写之末条」为 prev；★旧条目无 by ⇒ 不计入。\n'
            '    _own = [e for e in m["history"] if e.get("by") == "doc_archive"]\n'
            '    prev = _own[-1] if _own else None\n')

OLD_ENT = ('    ent = {"ver": ver, "ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "hash": h,\n')
NEW_ENT = ('    ent = {"ver": ver, "by": "doc_archive",\n'
           '           "ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "hash": h,\n')

t = P.read_text(encoding="utf-8")
n = 0
if 'by": "doc_archive"' not in t:
    if OLD_PREV in t:
        t = t.replace(OLD_PREV, NEW_PREV, 1); n += 1
    if OLD_ENT in t:
        t = t.replace(OLD_ENT, NEW_ENT, 1); n += 1
    if n:
        bak = SEAT/"exp"/("_patch_backup_%s" % time.strftime("%Y%m%d"))
        bak.mkdir(parents=True, exist_ok=True)
        shutil.copy2(P, bak/P.name)
        P.write_text(t, encoding="utf-8", newline="\n")
        print("  ✓ 已改 %d 处；备份至 %s" % (n, bak.name))
    else:
        print("  ★未匹配到替换点 ⇒ 未改（如实报）")
else:
    print("  · 已在（无需再改）")

# 复验：编译 + 印认关键行
try:
    py_compile.compile(str(P), doraise=True)
    print("   ★编译 ✓")
except Exception as ex:
    print("   ★编译 ✗：")
    for l in str(ex).splitlines()[:5]:
        print("      " + l[:100])

lines = P.read_text(encoding="utf-8").splitlines()
for i, l in enumerate(lines, 1):
    if '_own = [e for e in m["history"]' in l or 'by": "doc_archive"' in l:
        print("   ★L%-4d ｜ %s" % (i, l.strip()[:96]))
print("   ★含 by 之 doc_archive 自标：%d 处 ｜ 含 _own 之取 prev：%d 处"
      % (sum(1 for l in lines if '"by": "doc_archive"' in l),
         sum(1 for l in lines if "_own = [e for e in" in l)))
