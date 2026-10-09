# -*- coding: utf-8 -*-
"""灯带区逐帧序列：对既有 48 连续帧，取上／中／下三条带之逐帧平均亮度，检验其隔帧（T=2）振荡
判：若下部带之隔帧结构显著强于上部带 ⇒ 隔帧定位于画面下部（与 `-54` 一致且更强证据）
（引号一律用「」）
"""
import pathlib, re, statistics, sys
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
EX = HOME / "WPSDrive" / "29969771" / "WPS云盘" / "月之暗面的Plasma游乐场" / "A2A共同体_共享交换区"
fs = sorted(EX.glob("zones48_f*.bmp"), key=lambda p: int(re.search(r"_f(\d+)_", p.name).group(1)))
imgs = [np.asarray(Image.open(p).convert("L"), dtype=np.float64) for p in fs]
H, W = imgs[0].shape
bands = {"上带（0–1/3）": (0, H//3), "中带（1/3–2/3）": (H//3, 2*H//3), "下带（2/3–1）": (2*H//3, H)}
print("  帧数=%d ｜ 尺寸=%dx%d" % (len(imgs), W, H))

def spec2(x):
    n = len(x); mu = statistics.mean(x); y = [v-mu for v in x]; tot = sum(v*v for v in y) or 1.0
    re_ = sum(y[i]*np.cos(np.pi*i) for i in range(n))     # T=2 ⇒ cos(pi*i)
    return (re_*re_)/(n*tot)

print("\n  %-16s %-12s %-12s %-10s %-10s %s" % ("带", "序列首值", "序列末值", "逐帧标准差", "T=2 功率", "奇偶差比"))
for name, (y0, y1) in bands.items():
    seq = [float(im.mean()) for im in (a[y0:y1, :] for a in imgs)]
    d = [seq[i+1]-seq[i] for i in range(len(seq)-1)]           # 逐帧差
    even = statistics.median([abs(d[i]) for i in range(0, len(d), 2)])
    odd = statistics.median([abs(d[i]) for i in range(1, len(d), 2)])
    ratio = max(even, odd)/max(1e-9, min(even, odd))
    print("  %-16s %-12.4f %-12.4f %-10.4f %-10.4f %.2f" % (
        name, seq[0], seq[-1], statistics.pstdev(seq), spec2(seq), ratio))
    print("     逐帧差前 10：%s" % " ".join("%+.3f" % v for v in d[:10]))

print("\n  ★ 判读：下带之 T=2 功率与奇偶差比若显著高于上带 ⇒ 隔帧振荡定位于画面下部")
print("     （若各带相近 ⇒ 非带内局部现象，须另解；本席只报数据与判读，不断言机理）")
