# -*- coding: utf-8 -*-
"""标记实验之判读：录像帧 vs 首帧标记图
①整体 MAD/ρ ②区域检验：顶栏文字区（是否仍为「有字的白底」）③三色条（RGB 是否保留）④棋盘格（黑白交替是否保留）⑤非对称性（是否镜像）
（引号一律用「」）
"""
import pathlib, sys
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
BASE = HOME / "WPSDrive" / "29969771" / "WPS云盘" / "月之暗面的Plasma游乐场"
SEAT = BASE / "A2A新席_石敢当Cairn_20260928" / "exp"
MD = BASE / "A2A共同体_共享交换区" / "travel_artifacts_mark_20261009_CAIRN"
seed_p = SEAT / "mark_seed_20261009.png"
frames = sorted(MD.glob("mk_f*.bmp"), key=lambda p: p.name)
print("  首帧标记图：%s ｜ 录像帧：%s" % (seed_p.name, [p.name for p in frames]))
S = (864, 480)
def arr(p): return np.asarray(Image.open(p).convert("RGB").resize(S, Image.BILINEAR), dtype=np.int16)
seed = arr(seed_p)
tgt = arr(frames[0])
d = np.abs(seed - tgt)
print("\n  ① 整体：MAD=%.3f ｜ 最大差=%d ｜ 变化像素(>8)=%.2f%% ｜ ρ=%.5f" % (
    d.mean(), d.max(), (d.max(axis=2) > 8).mean()*100,
    np.corrcoef(seed.astype(float).ravel(), tgt.astype(float).ravel())[0, 1]))

# 区域（在 864×480 上的比例坐标）
def region(name, x0, y0, x1, y1):
    a = seed[int(y0*480):int(y1*480), int(x0*864):int(x1*864)]
    b = tgt[int(y0*480):int(y1*480), int(x0*864):int(x1*864)]
    print("    %-16s 首帧 均值RGB=%s σ=%.1f ｜ 录像 均值RGB=%s σ=%.1f ｜ MAD=%.1f" % (
        name, tuple(int(v) for v in a.reshape(-1, 3).mean(0)), float(a.std()),
        tuple(int(v) for v in b.reshape(-1, 3).mean(0)), float(b.std()), float(np.abs(a-b).mean())))
print("\n  ② 区域检验（比例坐标）：")
region("顶栏文字区", 0.03, 0.02, 0.55, 0.12)
region("三色条区", 0.78, 0.76, 0.90, 0.93)
region("棋盘格区", 0.06, 0.52, 0.25, 0.72)
region("整体画面", 0.0, 0.0, 1.0, 1.0)

print("\n  ③ 判读：")
tb_s, tb_v = seed[10:58, 26:475], tgt[10:58, 26:475]
sig_s, sig_v = float(tb_s.std()), float(tb_v.std())
print("     顶栏文字区 σ：首帧 %.1f vs 录像 %.1f ⇒ %s" % (sig_s, sig_v,
      "**仍有高对比结构（文字/内容被保留）**" if sig_v > 0.5*sig_s else "**对比度显著下降 ⇒ 文字可能被抹除/改写**"))
cb_s = seed[365:446, 674:778].reshape(-1, 3).mean(0); cb_v = tgt[365:446, 674:778].reshape(-1, 3).mean(0)
print("     三色条区均值：首帧 %s vs 录像 %s ⇒ %s" % (tuple(int(v) for v in cb_s), tuple(int(v) for v in cb_v),
      "**色彩保留**" if np.abs(cb_s-cb_v).mean() < 40 else "**色彩被改写**"))
print("     （★注：本判读为区域统计之代理指标，非逐像素读字；如实标为代理检验）")
