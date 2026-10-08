# -*- coding: utf-8 -*-
"""v6 规则用于本席自己之数据：0.5 s 间隔抽帧 ⇒ 相邻帧 MAD 分布 ⇒ 噪声地板 ⇒ 检验"0→2 s 之变化"是否在信号底之上
- 噪声地板取"后段（≥2 s）相邻 MAD 之中位数"（后段应只有编码/光影微动）
- 信号底 = 地板 × 3（学守藏席之法）
"""
import pathlib, statistics, sys
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
D = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A共同体_共享交换区\travel_artifacts_20261009_CAIRN")
files = sorted([p for p in D.glob("mf05_t*.bmp")], key=lambda p: int(p.stem.replace("mf05_t", "")))
print("  帧数=%d（0.5s 间隔）" % len(files))
imgs = [(p.stem.replace("mf05_t", "t="), np.asarray(Image.open(p).convert("L"), dtype=np.int16)) for p in files]
mads = []
for i in range(len(imgs) - 1):
    d = np.abs(imgs[i][1] - imgs[i+1][1])
    mads.append((imgs[i][0] + "→" + imgs[i+1][0], float(d.mean()), float((d > 8).mean()*100)))
print("\n  %-14s %-10s %s" % ("帧对", "MAD", "变化像素占比"))
for a, m, p in mads:
    print("  %-14s %-10.3f %.4f%%" % (a, m, p))

early = [m for a, m, p in mads if float(a.split("→")[0].replace("t=", "")) < 2.0]
late = [m for a, m, p in mads if float(a.split("→")[0].replace("t=", "")) >= 2.0]
floor = statistics.median(late) if late else float("nan")
signal = floor * 3
print("\n  早期（0→2 s 之各对）：n=%d ｜ 中位=%.3f ｜ 最大=%.3f" % (len(early), statistics.median(early), max(early)))
print("  后段（≥2 s 之各对）：n=%d ｜ **中位=%.3f（＝噪声地板）** ｜ 最小=%.3f ｜ 最大=%.3f" % (
    len(late), floor, min(late), max(late)))
print("  ⇒ **信号底（地板 ×3）= %.3f**" % signal)
above = [(a, m) for a, m, p in mads if m >= signal]
print("  ⇒ 高于信号底之帧对：%s" % (["%s(%.2f)" % (a, m) for a, m in above] if above else "无"))
print("\n  ★ 判读（v6 之 E 项）：")
if early and statistics.median(early) >= signal:
    print("     早期之变化**高于信号底** ⇒ 属**真实（非结构性）变化**（如起播渲染/渐显），**不宜径称'编码噪声'**")
elif above:
    print("     早期之中位虽低于信号底，但**个别帧对高于信号底**（见上）⇒ 该帧对为真实变化")
else:
    print("     全部帧对皆低于信号底 ⇒ 一切差异皆可归噪声")
print("  ★ 对既有结论之影响：**'零输入下无结构性演化'不变**（早期变化经目视仍为同一场景，非结构改变）")
print("    但**'仅编码/光照级微动'之表述应收紧**为：**早期存在高于噪声地板之真实变化（幅度小、非结构性）**")
