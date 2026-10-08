# -*- coding: utf-8 -*-
"""世界演进之定量判读：逐帧差分（以数值核实"是否静止"，不凭肉眼印象）
输出：相邻帧与时序首末帧之平均绝对差（MAD）、最大差、变化像素占比
"""
import pathlib, sys
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
D = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A共同体_共享交换区\travel_artifacts_20261009_CAIRN")
files = sorted(D.glob("mf_t*.png"), key=lambda p: int(p.stem.replace("mf_t", "")))
imgs = []
for f in files:
    a = np.asarray(Image.open(f).convert("L"), dtype=np.int16)
    imgs.append((f.stem, a))
print("  帧数=%d ｜ 尺寸=%s" % (len(imgs), imgs[0][1].shape if imgs else "—"))
print("  %-10s %-10s %-10s %s" % ("帧对", "MAD", "最大差", "变化像素占比(>8)"))
def stat(a, b):
    d = np.abs(a - b)
    return float(d.mean()), int(d.max()), float((d > 8).mean())
for i in range(len(imgs) - 1):
    n1, a1 = imgs[i]; n2, a2 = imgs[i+1]
    m, mx, pct = stat(a1, a2)
    print("  %-10s %-10.3f %-10d %.4f%%" % ("%s→%s" % (n1.replace("mf_t",""), n2.replace("mf_t","")), m, mx, pct*100))
m, mx, pct = stat(imgs[0][1], imgs[-1][1])
print("  %-10s %-10.3f %-10d %.4f%%" % ("首→末", m, mx, pct*100))
tot = stat(imgs[0][1], imgs[-1][1])
print("\n  ★ 判读：MAD=%.3f（灰度 0–255）｜最大差=%d｜变化像素占比=%.4f%%" % (tot[0], tot[1], tot[2]*100))
if tot[0] < 1.0 and tot[2] < 0.005:
    print("  ⇒ 定性：**画面在 10.77s 内基本静止**（差分近零）⇒ 零输入下**未见世界自组织**")
elif tot[0] < 5.0:
    print("  ⇒ 定性：画面**仅有轻微变化**（可能有镜头微动/光影）⇒ 未见明显自组织")
else:
    print("  ⇒ 定性：画面**有明显变化** ⇒ 须逐帧复查其性质")
