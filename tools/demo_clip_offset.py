#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
demo_clip_offset.py —— 用算术坐实"四张空白图"的根因；并给出差异实验。 v1.0.0

两条论证
────────
 ★甲 算术：其 `rectShot` 用 `getBoundingClientRect()`（**视口相对**）填 CDP `clip`（**页面坐标**），
        且 `window.scrollY` 收下未用 ⇒ 偏差【恰为 scrollY】。本器用模拟几何把它算出来。
 ★乙 差异：19 张图 = 15 张整页（无 clip）＋ 4 张带 clip；
        结果 **15 张正常、4 张全空白** ⇒ 故障只出现在【带 clip 的那条路】上。
        ⇒ 与甲合起来：**同一条路、同一个量、同一批图**。

★ 本器不打开浏览器、不改其文件；只做算术与读像素统计。
用法: demo_clip_offset.py <evidence 目录>
"""
from __future__ import annotations
import pathlib
import statistics
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    from PIL import Image
except Exception as e:
    print("[ERR] 缺 Pillow：%s" % e); sys.exit(3)

# ── 其 rectShot 的公式（照抄；b 为 getBoundingClientRect，视口相对）──
def theirs(b, pad, vw, vh):
    return {"x": max(0, b["x"] - pad), "y": max(0, b["y"] - pad),
            "w": min(b["w"] + pad * 2, vw), "h": min(b["h"] + pad * 2, vh)}

# ── 修后（把滚动量加回；CDP clip 是页面坐标）──
def fixed(b, pad, vw, vh, sx, sy):
    return {"x": max(0, b["x"] + sx - pad), "y": max(0, b["y"] + sy - pad),
            "w": min(b["w"] + pad * 2, vw), "h": min(b["h"] + pad * 2, vh)}


def main() -> int:
    ev = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else None
    print("═══ 甲 · 算术：clip 原点偏差恰为 scrollY ═══")
    print("  设：元素在视口内 y=300（getBoundingClientRect），页面已下滚 scrollY=800，pad=14")
    b = {"x": 200, "y": 300, "w": 87, "h": 81}
    vw, vh, pad, sx, sy = 1440, 900, 14, 0, 800
    t, f = theirs(b, pad, vw, vh), fixed(b, pad, vw, vh, sx, sy)
    print("   其公式 clip.y = %d   （= b.y - pad = %d - %d）" % (t["y"], b["y"], pad))
    print("   修后   clip.y = %d   （= b.y + scrollY - pad = %d + %d - %d）" % (f["y"], b["y"], sy, pad))
    print("   ★ 偏差 = %d 像素 = scrollY ⇒ **截取框整体上移了一整个滚动量**" % (f["y"] - t["y"]))
    print("   ⇒ 若目标在页面上部（如它拍的四个面板），框会落到【上方内容或空白】上。")
    print()
    print("   ── 三种滚动量下的偏差 ──")
    for s in (0, 200, 800, 2000):
        tt = theirs(b, pad, vw, vh)["y"]
        ff = fixed(b, pad, vw, vh, 0, s)["y"]
        print("     scrollY=%-5d ⇒ 其 clip.y=%-5d ｜ 应为 %-5d ｜ 偏差 %d" % (s, tt, ff, ff - tt))
    print("   ★ 注意 scrollY=0 时两者相同 ⇒ **这解释了为什么「页面没滚动」时看不出问题**；")
    print("     而其四张细节图都是【点击/操作之后】在滚动过的页面上拍的 ⇒ 必错。")

    print()
    print("═══ 乙 · 差异实验：故障只出现在带 clip 的那条路上 ═══")
    if not ev or not ev.is_dir():
        print("  （未给 evidence 目录，跳过）"); return 0
    # 其 _diagnostics.json 里 clip 为真的四步（本席轮90 已读）
    CLIPPED = {"09_qcomm_box.png", "10_born_fixed100.png", "11_gauge.png", "12_forge_intercept.png"}
    rows = []
    for p in sorted(ev.glob("*.png")):
        try:
            with Image.open(p) as im:
                g = im.convert("L")
                px = list(g.getdata())
                sd = statistics.pstdev(px)
                cols = im.convert("RGB").getcolors(maxcolors=200000) or []
            rows.append((p.name, len(cols), round(sd, 2), p.name in CLIPPED))
        except Exception as e:
            rows.append((p.name, -1, -1, p.name in CLIPPED))
    n_clip = sum(1 for r in rows if r[3])
    n_noclip = len(rows) - n_clip
    print("  带 clip 的图 = %d ｜ 不带 clip（整页）的图 = %d" % (n_clip, n_noclip))
    print("  %-30s %8s %9s %8s" % ("文件", "颜色数", "标准差", "带clip"))
    for n, c, sd, isc in rows:
        flag = "★纯色" if c == 1 else ("" if c > 1 else "?")
        print("  %-30s %8s %9s %8s  %s" % (n, c, sd, "是" if isc else "否", flag))
    blank_clip = [r for r in rows if r[3] and r[1] == 1]
    blank_noclip = [r for r in rows if not r[3] and r[1] == 1]
    print()
    print("  ── 判定 ──")
    print("   带 clip 而纯色 = %d / %d" % (len(blank_clip), n_clip))
    print("   不带 clip 而纯色 = %d / %d" % (len(blank_noclip), n_noclip))
    ok = (len(blank_clip) == n_clip) and (len(blank_noclip) == 0)
    print("   ★ 两集【互不重叠】：带 clip 的全坏、不带 clip 的全好 = %s" % ok)
    if ok:
        print("     ⇒ 差异实验成立：**故障被隔离在带 clip 的那条代码路径上**。")
        print("     ⇒ 与甲合参：**同一条路（rectShot）＋同一个量（scrollY）＋同一批图（四张）**。")
    print()
    print("  ★ 本器不打开浏览器、不改其文件；甲为算术、乙为像素统计，两者独立。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
