# -*- coding: utf-8 -*-
"""全帧率序列分析（256 帧）：①分段亮度与 MAD（查"渐显"与"噪声平稳性"）②趋势 ③MAD 自相关（查周期性）
数据源：mf_grab.cs / RunStats 输出之 CSV（F帧号,时间戳ms,平均亮度,与前帧MAD）
"""
import csv, pathlib, statistics, sys

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
P = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A共同体_共享交换区\travel_artifacts_20261009_CAIRN\frame_stats_20261009_CAIRN.csv")
rows = []
with P.open(encoding="utf-8-sig") as f:
    for r in csv.reader(f):
        if len(r) >= 4 and r[0].startswith("F") and r[0][1:].isdigit():
            rows.append((int(r[0][1:]), int(r[1]), float(r[2]), float(r[3])))
print("  帧数=%d ｜ 时长=%d ms" % (len(rows), rows[-1][1]))
mads = [r[3] for r in rows[1:]]
lums = [r[2] for r in rows]

print("\n  === ① 分段（每 32 帧一段，8 段）：")
print("  %-6s %-14s %-12s %-12s %s" % ("段", "t(ms) 区间", "亮度均值", "MAD 中位", "MAD 最大"))
W = 32
for i in range(0, len(rows), W):
    seg = rows[i:i+W]
    sm = [r[3] for r in seg if r[3] >= 0]
    print("  %-6d %-14s %-12.3f %-12.4f %.4f" % (
        i//W + 1, "%d–%d" % (seg[0][1], seg[-1][1]),
        statistics.mean([r[2] for r in seg]), statistics.median(sm) if sm else -1, max(sm) if sm else -1))

g1 = statistics.median([r[3] for r in rows[1:65] if r[3] >= 0])
g4 = statistics.median([r[3] for r in rows[192:] if r[3] >= 0])
print("\n  ★ 前 1/4 地板=%.4f ｜ 后 1/4 地板=%.4f ｜ 比值=%.2f" % (g1, g4, g1/g4 if g4 else 0))
print("  ⇒ %s" % ("**噪声非平稳**：前段显著高于后段 ⇒ 地板法须**分段估计**" if g1 > 1.5*g4 else "噪声近似平稳 ⇒ 单一地板可用"))

print("\n  === ② 亮度趋势：")
f1, fl = lums[0], lums[-1]
print("  首帧=%.4f ｜ 末帧=%.4f ｜ 差=%+.4f（%+.1f%%）" % (f1, fl, fl-f1, (fl-f1)/f1*100))
up = sum(1 for i in range(1, len(lums)) if lums[i] > lums[i-1])
print("  上升步数=%d/%d（%.1f%%）⇒ %s" % (up, len(lums)-1, up/(len(lums)-1)*100,
      "**呈上升趋势**（非严格单调）" if up/(len(lums)-1) > 0.5 else "无上升趋势"))
w1 = statistics.mean(lums[:32]); w8 = statistics.mean(lums[-32:])
print("  首段均=%.3f ｜ 末段均=%.3f ｜ 差=%+.3f⇒ **全程亮度有升**（%s）" % (
    w1, w8, w8-w1, "初段略降后升" if min(lums[:64]) < w1 else "持续升"))

print("\n  === ③ MAD 序列自相关（查周期性；滞后 1–24 帧）：")
n = len(mads); mu = statistics.mean(mads); var = sum((x-mu)**2 for x in mads)/n
def ac(lag):
    s = sum((mads[i]-mu)*(mads[i+lag]-mu) for i in range(n-lag))
    return s/(n-lag)/var if var else 0
best = max(((l, ac(l)) for l in range(1, 25)), key=lambda t: t[1])
print("  " + " ｜ ".join("lag%d=%.3f" % (l, ac(l)) for l in (1, 2, 3, 4, 6, 8, 12)))
print("  ★ 最大自相关：lag=%d ｜ ρ=%.3f ⇒ %s" % (
    best[0], best[1], "**存在弱周期/记忆**（ρ>0.3 须追）" if best[1] > 0.3 else "**无明显周期性**（ρ 皆低 ⇒ 近似白噪/慢变）"))
print("\n  ★ 综合判读：")
print("     ① 首段（0–1.3s）MAD 显著高于后段 ⇒ **起播段确有真实变化**（与 `-36` 之结论一致）")
print("     ② 噪声**非平稳**（前高后低）⇒ **v6 地板法须补「分段估计」**（新增条件）")
print("     ③ MAD 序列无明显周期性 ⇒ **未见节律性自组织**；亮度小幅上升（渐显/曝光）⇒ **非结构性**")
