# -*- coding: utf-8 -*-
"""连通域之"位置匹配"复算（承 -95 之方法学限制）
以质心最近优先贪心配对，替代"面积排序逐位配对"⇒ 判 t=26 s 之异常是否确由配对方式所致
（引号一律用「」）
"""
import json, pathlib, re, sys, time
from collections import deque
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
D = pathlib.Path(r"C:\Users\欧阳宏俊\AppData\Local\Temp\struct_cmp")

def components(mask, min_area=30):
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    out = []
    ys, xs = np.nonzero(mask)
    for y0, x0 in zip(ys, xs):
        if seen[y0, x0]: continue
        q = deque([(y0, x0)]); seen[y0, x0] = True
        n = 0; sy = 0; sx = 0
        while q:
            y, x = q.popleft(); n += 1; sy += y; sx += x
            for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
                ny, nx = y+dy, x+dx
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True; q.append((ny, nx))
        if n >= min_area:
            out.append({"area": n, "cx": sx/n/w, "cy": sy/n/h})
    return out

def match(a, b):
    """贪心：按质心距离最近优先配对（一对一）"""
    pairs = []
    used = set()
    cand = sorted((( (x["cx"]-y["cx"])**2 + (x["cy"]-y["cy"])**2, i, j)
                   for i, x in enumerate(a) for j, y in enumerate(b)))
    ia, ib = set(), set()
    for d, i, j in cand:
        if i in ia or j in ib: continue
        ia.add(i); ib.add(j); pairs.append((i, j, d**0.5))
    return pairs

def load(tag):
    fs = {}
    for p in D.glob(tag + "_*.bmp"):
        m = re.search(r"_t(\d+)\.bmp$", p.name)
        if m: fs[int(m.group(1))] = p
    return fs

A, B = load("M1"), load("M2")
ts = sorted(set(A) & set(B))
print("  === 位置匹配（质心最近优先）之配对结果 ===")
rows = []
for t in ts:
    ca = components(np.asarray(Image.open(A[t]).convert("L")) > 60)
    cb = components(np.asarray(Image.open(B[t]).convert("L")) > 60)
    ps = match(ca, cb)
    if not ps:
        print("   t=%2ds 无配对" % t); continue
    dc = [((ca[i]["cx"]-cb[j]["cx"])**2 + (ca[i]["cy"]-cb[j]["cy"])**2)**0.5 for i, j, _ in ps]
    da = [abs(ca[i]["area"]-cb[j]["area"])/max(1, ca[i]["area"]) for i, j, _ in ps]
    unmatched = abs(len(ca) - len(cb))
    print("   t=%2ds ⇒ 域 %d/%d ｜ 配对 %d ｜ 最大质心距 %.5f ｜ 最大面积相对差 %.4f%s" % (
        t, len(ca), len(cb), len(ps), max(dc), max(da), ("｜未配对 %d" % unmatched) if unmatched else ""))
    rows.append({"t": t, "n_M1": len(ca), "n_M2": len(cb), "matched": len(ps),
                 "max_centroid_dist": round(max(dc), 6), "max_rel_area_diff": round(max(da), 5)})

mx = max(r["max_centroid_dist"] for r in rows)
ma = max(r["max_rel_area_diff"] for r in rows)
print("\n  === 汇总（位置匹配）===")
print("   时间点 %d ｜ 最大质心距之最大者 = %.6f ｜ 最大面积相对差 = %.5f" % (len(rows), mx, ma))
print("   ⇒ 若「最大质心距」全局 ≤0.001 ⇒ 说明 -95 之 t=26 s 异常确系「面积排序配对」所致")
out = pathlib.Path.home()/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"/"component_position_matching_20261009_CAIRN.json"
out.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "seat": "a2a-node-local",
    "method": "质心最近优先贪心一对一配对（替代面积排序逐位配对）",
    "note": "承 -95 之方法学限制；连通域级非语义物体级", "rows": rows},
    ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("  落盘：%s" % out.name)
