# -*- coding: utf-8 -*-
"""M 录之功率谱（兑现 `-47` 之再追提议）：对相邻帧 MAD 序列作周期图，寻主频
—— 并判别：峰若落在 24 帧之倍数（=1 秒，24fps）附近 ⇒ 疑为编码节律（GOP/帧对），非世界动力学
（引号一律用「」）
"""
import csv, math, pathlib, statistics, sys

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
EX = HOME / "WPSDrive" / "29969771" / "WPS云盘" / "月之暗面的Plasma游乐场" / "A2A共同体_共享交换区"
SRC = {"A 数据虚空": EX/"travel_artifacts_20261009_CAIRN"/"frame_stats_20261009_CAIRN.csv",
       "B 数据塔": EX/"travel_artifacts_20261009_CAIRN_B"/"frame_stats_b_20261009_CAIRN.csv",
       "M 极简检验室": EX/"travel_artifacts_mark_20261009_CAIRN"/"frame_stats_mark_20261009_CAIRN.csv"}

def load(p):
    out = []
    with p.open(encoding="utf-8-sig") as f:
        for r in csv.reader(f):
            if len(r) >= 4 and r[0].startswith("F") and r[0][1:].isdigit() and float(r[3]) >= 0:
                out.append(float(r[3]))
    return out

def periodogram(x, periods):
    n = len(x); mu = statistics.mean(x)
    y = [v-mu for v in x]
    tot = sum(v*v for v in y) or 1.0
    res = []
    for T in periods:
        w = 2*math.pi/T
        re = sum(y[i]*math.cos(w*i) for i in range(n))
        im = sum(y[i]*math.sin(w*i) for i in range(n))
        res.append((T, (re*re+im*im)/(n*tot)))   # 归一化功率
    return res

PER = [p for p in range(2, 121)]
print("  === 周期图（周期 2–120 帧；归一化功率）")
for name, p in SRC.items():
    x = load(p)
    if len(x) < 60:
        print("  %-14s 数据不足（%d）" % (name, len(x))); continue
    P = periodogram(x, PER)
    top = sorted(P, key=lambda t: -t[1])[:6]
    print("\n  【%s】n=%d" % (name, len(x)))
    print("     主峰（周期帧→功率）：%s" % " ｜ ".join("T=%d→%.4f" % (t, v) for t, v in top))
    # 与 24 fps 之整秒倍数比较
    secs = [(t, v) for t, v in top if abs(t % 24) <= 1 or abs(t % 24 - 23) <= 1]
    print("     ★ 落在「24 帧（1 秒）倍数」附近之峰：%s" % (" ｜ ".join("T=%d" % t for t, _ in secs) if secs else "无"))
    print("     ⇒ %s" % ("**疑为编码节律（GOP/帧对，1 秒整数倍）⇒ 非世界动力学**" if secs else
                         "**主频不在整秒倍数 ⇒ 非（或非显式）编码节律**"))
print("\n  ★ 总判读：若三录主频皆不在整秒倍数且功率低平 ⇒ 该「长程相关」更像**低频缓变成分**而非周期振荡")
print("     （**本席只报形态，不断言成因**；如仍不明，保留为「未解释结构」）")
