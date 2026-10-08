# -*- coding: utf-8 -*-
"""性质检验：产物录像 t=0 帧 vs 本席提供之首帧 vs 平台回显之首帧 —— 像素级比对
判：若近乎逐位相同 ⇒ 录像系「首帧驱动之生成片段」，非「世界状态实录」⇒ 对世界动力学无判别力
（本脚本内之引号一律用「」）
"""
import pathlib, sys
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
BASE = HOME / "WPSDrive" / "29969771" / "WPS云盘" / "月之暗面的Plasma游乐场"
SEAT = BASE / "A2A新席_石敢当Cairn_20260928" / "exp"
EXD = BASE / "A2A共同体_共享交换区" / "travel_artifacts_20261009_CAIRN"
ITEMS = [
    ("录像 t=0 帧", EXD / "mf_t0.png"),
    ("录像 t=10 帧", EXD / "mf_t10.png"),
    ("本席提供之首帧（v5 第一人称）", SEAT / "persona_luzhibai_v5_firstperson_20261009.png"),
    ("平台回显之首帧（v5 world）", SEAT / "persona_v5_world_firstframe_20261009.png"),
]
SIZE = (864, 480)

def arr(p):
    return np.asarray(Image.open(p).convert("RGB").resize(SIZE, Image.BILINEAR), dtype=np.int16)

ok = [(n, p) for n, p in ITEMS if p.exists()]
for n, p in ITEMS:
    print("  %-30s %s" % (n, "存在 %.2f MB" % (p.stat().st_size / 1048576) if p.exists() else "× 不存在"))
print("\n  === 两两比对（统一缩放 864×480）===")
cache = {n: arr(p) for n, p in ok}
print("  %-26s %-26s %-9s %-8s %-10s %s" % ("A", "B", "MAD", "最大差", "变化像素%", "相关系数"))
best = None
for i in range(len(ok)):
    for j in range(i + 1, len(ok)):
        na, nb = ok[i][0], ok[j][0]
        a, b = cache[na], cache[nb]
        d = np.abs(a - b)
        mad = float(d.mean()); mx = int(d.max()); pct = float((d.max(axis=2) > 8).mean() * 100)
        cc = float(np.corrcoef(a.astype(np.float64).ravel(), b.astype(np.float64).ravel())[0, 1])
        print("  %-26s %-26s %-9.3f %-8d %-10.3f %.5f" % (na[:26], nb[:26], mad, mx, pct, cc))
        if best is None or mad < best[2]:
            best = (na, nb, mad, cc)

print("\n  === 判读 ===")
if best:
    na, nb, mad, cc = best
    print("  最相似之一对：%s ↔ %s ｜ MAD=%.3f ｜ ρ=%.5f" % (na, nb, mad, cc))
    if cc > 0.99 and mad < 5:
        print("  ⇒ **高度一致** ⇒ 该产物录像极可能为「**首帧驱动之生成片段**」而非「世界实时状态之实录」")
        print("     ⇒ **对「世界动力学／涌现」无判别力**（与 `-30` 三厂商一致；与 `-25` 之「未闭合」相容）")
    elif cc > 0.95:
        print("  ⇒ **高度相关但非逐位相同** ⇒ 录像**由首帧派生并经再渲染**（补全／重绘）")
    else:
        print("  ⇒ 相关性不足 ⇒ **不能断定为首帧驱动**（须另设实验）")
