# -*- coding: utf-8 -*-
"""物体级追踪之近似：亮掩膜连通域标记 ⇒ 前 K 大连通域之质心／面积／包围盒
比对 M1 vs M2（同 12 时间点）⇒ 判"连通域级路径是否相同"
★ 明标：此为"连通域级"，非"语义物体级"（未做检测器）
（引号一律用「」）
"""
import json, pathlib, re, sys, time
from collections import deque
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
D = pathlib.Path(r"C:\Users\欧阳宏俊\AppData\Local\Temp\struct_cmp")

def components(mask, topk=6):
    """简易连通域（4 邻域，BFS）。返回前 topk 个（按面积）之 {area, cx, cy, w, h}。"""
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    out = []
    ys, xs = np.nonzero(mask)
    for y0, x0 in zip(ys, xs):
        if seen[y0, x0]: continue
        q = deque([(y0, x0)]); seen[y0, x0] = True
        n = 0; sy = 0; sx = 0; ymin = ymax = y0; xmin = xmax = x0
        while q:
            y, x = q.popleft(); n += 1; sy += y; sx += x
            if y < ymin: ymin = y
            if y > ymax: ymax = y
            if x < xmin: xmin = x
            if x > xmax: xmax = x
            for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
                ny, nx = y+dy, x+dx
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True; q.append((ny, nx))
        if n < 30: continue          # 忽略噪声小域
        out.append({"area": n, "cx": round(sx/n/w, 5), "cy": round(sy/n/h, 5),
                    "w": round((xmax-xmin+1)/w, 4), "h": round((ymax-ymin+1)/h, 4)})
    out.sort(key=lambda d: -d["area"])
    return out[:topk]

def load(tag):
    fs = {}
    for p in D.glob(tag + "_*.bmp"):
        m = re.search(r"_t(\d+)\.bmp$", p.name)
        if m: fs[int(m.group(1))] = p
    return fs

A, B = load("M1"), load("M2")
ts = sorted(set(A) & set(B))
print("  === 连通域级比对（亮掩膜 >60；前 6 大域）===")
rows = []
for t in ts:
    ca = components(np.asarray(Image.open(A[t]).convert("L")) > 60)
    cb = components(np.asarray(Image.open(B[t]).convert("L")) > 60)
    same_n = len(ca) == len(cb)
    dcx = max((abs(a["cx"]-b["cx"]) for a, b in zip(ca, cb)), default=None)
    dcy = max((abs(a["cy"]-b["cy"]) for a, b in zip(ca, cb)), default=None)
    da  = max((abs(a["area"]-b["area"])/max(1, a["area"]) for a, b in zip(ca, cb)), default=None)
    print("   t=%2ds ⇒ M1 域数 %d／M2 %d｜最大质心差 x=%.5f y=%.5f｜最大面积相对差=%.4f" % (
        t, len(ca), len(cb), dcx or 0, dcy or 0, da or 0))
    if t in (2, 20):
        print("        M1 前 3 域：" + " ｜ ".join("area=%d (%.4f,%.4f) %sx%s" % (c["area"], c["cx"], c["cy"], c["w"], c["h"]) for c in ca[:3]))
        print("        M2 前 3 域：" + " ｜ ".join("area=%d (%.4f,%.4f) %sx%s" % (c["area"], c["cx"], c["cy"], c["w"], c["h"]) for c in cb[:3]))
    rows.append({"t": t, "n_M1": len(ca), "n_M2": len(cb),
                 "max_dcx": dcx, "max_dcy": dcy, "max_rel_darea": da,
                 "M1_top3": ca[:3], "M2_top3": cb[:3]})

ns = [r for r in rows if r["n_M1"] == r["n_M2"]]
print("\n  === 汇总 ===")
print("   时间点 %d ｜ 域数相同者 %d／%d" % (len(rows), len(ns), len(rows)))
if ns:
    import statistics
    print("   最大质心差：x 均 %.5f 最大 %.5f ｜ y 均 %.5f 最大 %.5f" % (
        statistics.mean(r["max_dcx"] for r in ns), max(r["max_dcx"] for r in ns),
        statistics.mean(r["max_dcy"] for r in ns), max(r["max_dcy"] for r in ns)))
    print("   最大面积相对差：均 %.4f 最大 %.4f" % (
        statistics.mean(r["max_rel_darea"] for r in ns), max(r["max_rel_darea"] for r in ns)))
out = pathlib.Path.home()/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"/"component_level_tracking_20261009_CAIRN.json"
out.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "seat": "a2a-node-local",
    "note": "★连通域级（4 邻域、面积≥30），非语义物体级；比对 M1 vs M2 同刻之域数／质心／面积",
    "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("\n  落盘：%s" % out.name)
