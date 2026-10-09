# -*- coding: utf-8 -*-
"""17–21 s「第二次活动期」之性质判别：分区块差（4×4）与亮度剖面
判：若各区块 Δ 相近（低离散）⇒ 整幅曝光／全局变化；若集中于少数区块 ⇒ 局部内容变化
★ 注：抓帧经 MF seek，落于关键帧 ⇒ 时刻为近似（依 `mf_grab` 之日志：16.5s 与 17.0s 皆落 t17）
（引号一律用「」）
"""
import json, pathlib, statistics, sys, time
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
D = pathlib.Path(r"C:\Users\欧阳宏俊\AppData\Local\Temp\m1_second")
EX = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A共同体_共享交换区")
names = ["f_t15.bmp", "f_t17.bmp", "f_t18.bmp", "f_t19.bmp", "f_t20.bmp", "f_t21.bmp", "f_t22.bmp"]
frames = []
for n in names:
    p = D/n
    if not p.exists(): print("  缺 %s" % n); continue
    im = Image.open(p).convert("L")
    a = np.asarray(im, dtype=np.float64)
    frames.append((n, a))
print("  === 全局亮度 ===")
for n, a in frames:
    print("    %-12s 均 %6.2f ｜ 中位 %6.1f ｜ 最小 %5.1f ｜ 最大 %5.1f" % (n, a.mean(), np.median(a), a.min(), a.max()))

print("\n  === 分区块（4×4）亮度均 ===")
def regions(a, k=4):
    h, w = a.shape
    out = []
    for i in range(k):
        for j in range(k):
            out.append(a[i*h//k:(i+1)*h//k, j*w//k:(j+1)*w//k].mean())
    return out
for n, a in frames:
    r = regions(a)
    print("    %-12s %s" % (n, " ".join("%6.1f" % v for v in r)))

print("\n  === 相邻帧之区块差（4×4，均绝对值）===")
rows = []
for i in range(1, len(frames)):
    n0, a0 = frames[i-1]; n1, a1 = frames[i]
    d = np.abs(a1-a0)
    g = d.mean()
    r = regions(d)
    lo = max(r); mn = statistics.mean(r)
    idx = int(np.argmax(r))
    print("    %s→%s：全局均差 %5.2f ｜ 区块最大 %5.2f（第 %d 块）｜ 区块最小 %5.2f ｜ 离散(σ/μ) %4.2f" % (
        n0, n1, g, lo, idx, min(r), (statistics.pstdev(r)/mn if mn > 0 else 0)))
    rows.append({"from": n0, "to": n1, "global_mad": round(g,3), "region_max": round(lo,3),
                 "region_min": round(min(r),3), "argmax_region": idx,
                 "region_cv": round(statistics.pstdev(r)/mn,3) if mn > 0 else None,
                 "regions": [round(v,2) for v in r]})

print("\n  ★ 判读规则：")
print("     区域离散(σ/μ) 小（<0.5）且各区块差相近 ⇒ 全局变化（曝光／整体提亮）")
print("     区域离散大 且集中于少数区块 ⇒ 局部内容变化（物体／细节）")
out = EX/"second_activity_region_analysis_20261009_CAIRN.json"
out.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "seat": "a2a-node-local",
    "note": "★抓帧经 MF seek 落于关键帧 ⇒ 时刻为近似；区块为 4×4",
    "frames": [n for n, _ in frames], "pairs": rows}, ensure_ascii=False, indent=1),
    encoding="utf-8", newline="\n")
print("\n  落盘：%s" % out.name)
