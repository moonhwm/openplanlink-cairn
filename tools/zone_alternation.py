# -*- coding: utf-8 -*-
"""M 录"强隔帧"之空间分布：对连续 48 帧（2 s），算相邻帧差之逐区域（4×4）MAD
并算"交替指数"＝|偶数对均值−奇数对均值| / (两者之和)，看隔帧交替集中于哪些区域
（引号一律用「」）
"""
import pathlib, re, sys
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
EX = HOME / "WPSDrive" / "29969771" / "WPS云盘" / "月之暗面的Plasma游乐场" / "A2A共同体_共享交换区"
fs = sorted(EX.glob("zones48_f*.bmp"), key=lambda p: int(re.search(r"_f(\d+)_", p.name).group(1)))
print("  帧数=%d" % len(fs))
imgs = [np.asarray(Image.open(p).convert("L"), dtype=np.int16) for p in fs]
H, W = imgs[0].shape
G = 4
hs, ws = H//G, W//G

# 相邻帧差（逐区域）
diffs = []   # 每个元素：4x4 区域 MAD
for i in range(len(imgs)-1):
    d = np.abs(imgs[i+1] - imgs[i]).astype(np.float64)
    z = np.zeros((G, G))
    for r in range(G):
        for c in range(G):
            z[r, c] = d[r*hs:(r+1)*hs, c*ws:(c+1)*ws].mean()
    diffs.append(z)

even = np.mean([diffs[i] for i in range(0, len(diffs), 2)], axis=0)   # 偶数索引对（第1、3、5…对）
odd  = np.mean([diffs[i] for i in range(1, len(diffs), 2)], axis=0)
tot = even + odd
alt = np.where(tot > 1e-9, np.abs(even-odd)/np.maximum(tot, 1e-9), 0.0)

print("\n  === 逐区域（行=上→下，列=左→右）：区域 MAD 与交替指数")
print("  %-6s %s" % ("区域", "偶数对均值／奇数对均值／交替指数"))
for r in range(G):
    for c in range(G):
        print("  r%dc%d   %8.4f ｜ %8.4f ｜ %6.3f %s" % (
            r, c, even[r, c], odd[r, c], alt[r, c],
            "★" if alt[r, c] > 0.25 else ""))
print("\n  全局：偶数对均值 %.4f ｜ 奇数对均值 %.4f ｜ 交替指数 %.3f" % (
    even.mean(), odd.mean(), np.abs(even.mean()-odd.mean())/max(1e-9, even.mean()+odd.mean())))
print("  最强三区：%s" % "、".join("r%dc%d(%.3f)" % (r, c, alt[r, c])
      for r, c in np.dstack(np.unravel_index(np.argsort(-alt, axis=None)[:3], alt.shape))[0]))
# 与"内容分布"对照：用首帧亮度梯度之区域均值
g = np.zeros((G, G))
gx = np.abs(np.diff(imgs[0].astype(np.float64), axis=1))
gy = np.abs(np.diff(imgs[0].astype(np.float64), axis=0))
for r in range(G):
    for c in range(G):
        blk = np.zeros((hs, ws))
        blk[:, :ws-1] += gx[r*hs:(r+1)*hs, c*ws:(c+1)*ws][:, :ws-1]
        blk[:hs-1, :] += gy[r*hs:(r+1)*hs, c*ws:(c+1)*ws][:hs-1, :]
        g[r, c] = blk.mean()
cc = np.corrcoef(alt.ravel(), g.ravel())[0, 1]
print("  ★ 交替指数 与 首帧细节密度（梯度）之区域相关 ρ=%.3f ⇒ %s" % (
    cc, "**交替集中于高细节区（边缘/文字）⇒ 倾向「上采样/锐化之周期性细节更新」**" if cc > 0.4
    else "**交替与细节密度无强相关 ⇒ 非（仅）细节更新所能解释**"))
