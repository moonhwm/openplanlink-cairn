# -*- coding: utf-8 -*-
"""去趋势复算（兑现 `-46` 之待办）：对三录之相邻帧 MAD 序列，先去线性趋势，再算自相关
并同时报"未去趋势"与"去趋势后"两组，以判"长程相关"是否源于趋势（引号一律用「」）
"""
import csv, pathlib, statistics, sys

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
EX = HOME / "WPSDrive" / "29969771" / "WPS云盘" / "月之暗面的Plasma游乐场" / "A2A共同体_共享交换区"
FILES = [("A 数据虚空", EX/"travel_artifacts_20261009_CAIRN"/"frame_stats_20261009_CAIRN.csv"),
         ("B 数据塔", EX/"travel_artifacts_20261009_CAIRN_B"/"frame_stats_b_20261009_CAIRN.csv"),
         ("M 极简检验室", EX/"travel_artifacts_mark_20261009_CAIRN"/"frame_stats_mark_20261009_CAIRN.csv")]

def load(p):
    mad = []
    with p.open(encoding="utf-8-sig") as f:
        for r in csv.reader(f):
            if len(r) >= 4 and r[0].startswith("F") and r[0][1:].isdigit() and float(r[3]) >= 0:
                mad.append(float(r[3]))
    return mad

def ac(x, lag):
    n = len(x)
    if n - lag < 10: return None
    mu = statistics.mean(x); var = sum((v-mu)**2 for v in x)/n
    if var <= 0: return None
    return sum((x[i]-mu)*(x[i+lag]-mu) for i in range(n-lag))/(n-lag)/var

def detrend(x):
    """最小二乘去线性趋势"""
    n = len(x); xs = list(range(n))
    mx = statistics.mean(xs); my = statistics.mean(x)
    sxx = sum((v-mx)**2 for v in xs)
    b = sum((xs[i]-mx)*(x[i]-my) for i in range(n))/sxx if sxx else 0.0
    a = my - b*mx
    return [x[i] - (a + b*i) for i in range(n)], b

print("  === 未去趋势 vs 去趋势后（相邻帧 MAD 序列之自相关）")
print("  %-14s %-9s %-24s %s" % ("录像", "趋势斜率/帧", "未去趋势 ρ1/ρ6/ρ12", "去趋势后 ρ1/ρ6/ρ12"))
res = {}
for name, p in FILES:
    x = load(p)
    d, slope = detrend(x)
    raw = [ac(x, l) for l in (1, 6, 12)]
    det = [ac(d, l) for l in (1, 6, 12)]
    res[name] = (raw, det)
    fmt = lambda v: ("%.3f" % v if v is not None else "—")
    print("  %-14s %-9.5f %-24s %s" % (name, slope,
          "%s/%s/%s" % tuple(fmt(v) for v in raw), "%s/%s/%s" % tuple(fmt(v) for v in det)))

print("\n  === 判读")
for name, (raw, det) in res.items():
    longb = raw[2]; longa = det[2]
    if longb is None or longa is None:
        print("  %-14s 数据不足" % name); continue
    drop = longb - longa
    verdict = ("**长程相关显著下降 ⇒ 该「长程相关」主要源于趋势（提亮）**" if drop > 0.15
               else "**去趋势后长程相关仍在 ⇒ 非趋势所能解释，须另寻结构**" if longa > 0.25
               else "**去趋势前后皆低 ⇒ 无长程周期**")
    print("  %-14s ρ12：%.3f → %.3f（降 %.3f）⇒ %s" % (name, longb, longa, drop, verdict))
print("\n  ★ 结论（对 `-37` 表述之最终处置）")
print("     若三录去趋势后 ρ12 皆低（<0.25）⇒ **可恢复「未见节律性／长程周期」之判定，惟须注明系「去趋势后」**")
print("     若某录去趋势后仍高 ⇒ **须列为「未解释之结构」，不得径称无周期**")
