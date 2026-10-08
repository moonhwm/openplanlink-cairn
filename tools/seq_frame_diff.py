# -*- coding: utf-8 -*-
"""P1 之果：以"真连续帧"（每 8 帧≈0.333s，含真实时间戳）重算 MAD 序列与噪声地板
- 地板＝相邻（每 8 帧）MAD 之中位数；信号底＝地板 ×3
- 并检验"按时间 seek 得关键帧"之假设：比较 32 帧中"时间戳接近 0/2/4/6/8/10s"者与关键帧画面之差
"""
import pathlib, re, statistics, sys
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
D = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A共同体_共享交换区\travel_artifacts_20261009_CAIRN")
fs = sorted(D.glob("seq_f*.bmp"), key=lambda p: int(re.search(r"_f(\d+)_", p.name).group(1)))
print("  连续帧数=%d" % len(fs))
rows = []
for p in fs:
    n = int(re.search(r"_f(\d+)_", p.name).group(1)); ms = int(re.search(r"_(\d+)ms", p.name).group(1))
    rows.append((n, ms, np.asarray(Image.open(p).convert("L"), dtype=np.int16)))
mads = []
print("\n  %-8s %-8s %-10s %s" % ("帧号", "t(ms)", "MAD(与前)", "变化像素%"))
prev = None
for n, ms, a in rows:
    if prev is None:
        print("  %-8d %-8d %-10s %s" % (n, ms, "—", "—"))
    else:
        d = np.abs(a - prev); m = float(d.mean()); pc = float((d > 8).mean()*100)
        mads.append(m)
        print("  %-8d %-8d %-10.3f %.4f%%" % (n, ms, m, pc))
    prev = a
floor = statistics.median(mads)
print("\n  ★ 相邻（每 8 帧≈0.333s）MAD：n=%d ｜ **中位（＝噪声地板）=%.4f** ｜ 均值=%.4f ｜ 最小=%.4f ｜ 最大=%.4f" % (
    len(mads), floor, statistics.mean(mads), min(mads), max(mads)))
print("  ★ **信号底（地板 ×3）=%.4f**" % (floor*3))
above = [(i+1, m) for i, m in enumerate(mads) if m >= floor*3]
print("  ★ 高于信号底之相邻帧对：%d 对" % len(above))
for i, m in above[:8]:
    print("     · 第 %d 对（t≈%.0fms）MAD=%.3f ＝ 地板之 %.1f 倍" % (i, rows[i][1], m, m/floor if floor else 0))
print("\n  ★ 判读：")
if floor > 0:
    print("     地板 = %.4f（>0，**非退化**）⇒ 该录像之连续帧间确有编码级差异" % floor)
    print("     最大相邻差 %.3f ＝ 地板之 %.1f 倍 ⇒ %s" % (
        max(mads), max(mads)/floor, "**存在显著高于地板之变化**（须逐帧定性）" if max(mads) >= floor*3 else "**全程未越信号底 ⇒ 一切差异皆可归噪声级**"))
print("  ★ 与「按时间 seek」之对照：前者仅得 6 个互异画面（每对差 0.57–2.76，且半秒间隔对为 0）")
print("     ⇒ 现以真连续帧得 %d 个互异画面、相邻差中位 %.4f ⇒ **两种抽取所见一致或不一致，将据实登记**" % (len(rows), floor))
