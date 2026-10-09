import json, pathlib, re, sys
import numpy as np
from PIL import Image
D = pathlib.Path(r"C:\Users\欧阳宏俊\AppData\Local\Temp\struct_cmp")
def metrics(p):
    a = np.asarray(Image.open(p).convert("L"), dtype=np.float64)
    # ① 直方图熵（8 bit）
    h = np.bincount(a.astype(np.int64).ravel(), minlength=256).astype(np.float64)
    pr = h / h.sum(); pr = pr[pr > 0]
    ent = float(-(pr * np.log2(pr)).sum())
    # ② 梯度能量（Sobel 近似：一阶差分）
    gx = np.abs(np.diff(a, axis=1)).mean(); gy = np.abs(np.diff(a, axis=0)).mean()
    grad = (gx + gy) / 2
    # ③ 亮像素质心（阈值 >60）
    m = a > 60
    if m.sum() > 0:
        ys, xs = np.nonzero(m)
        cx, cy = xs.mean()/a.shape[1], ys.mean()/a.shape[0]
        frac = m.mean()
    else:
        cx = cy = frac = 0.0
    return dict(ent=round(ent,4), grad=round(float(grad),4), cx=round(float(cx),5), cy=round(float(cy),5), frac=round(float(frac),5))
rows = {}
for tag in ("M1", "M2"):
    fs = sorted(D.glob(tag + "_*.bmp"), key=lambda p: float(re.search(r"_(\d+)\.bmp$", p.name).group(1)) if re.search(r"_(\d+)\.bmp$", p.name) else 0)
    rows[tag] = [(p.name, metrics(p)) for p in fs]
print("  === 空间结构指标（逐抓帧）===")
for tag in rows:
    print("   【%s】%d 帧" % (tag, len(rows[tag])))
    for n, m in rows[tag]:
        print("      %-14s 熵=%6.4f 梯度=%5.3f 质心=(%.4f,%.4f) 亮占比=%.4f" % (n, m["ent"], m["grad"], m["cx"], m["cy"], m["frac"]))
if len(rows["M1"]) == len(rows["M2"]) and rows["M1"]:
    print("\n  === 配对差（M1 − M2）===")
    for k in ("ent", "grad", "cx", "cy", "frac"):
        d = [abs(a[1][k] - b[1][k]) for a, b in zip(rows["M1"], rows["M2"])]
        print("     %-5s 平均绝对差=%.6f ｜ 最大=%.6f" % (k, sum(d)/len(d), max(d)))
