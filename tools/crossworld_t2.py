# -*- coding: utf-8 -*-
"""跨世界隔帧结构检验（零新增调用）：对 A／B／M1／M2 四份全帧率数表，算 T=2/3/4/24/48 谱功率与奇偶比
判：若异世界（B）亦具 T=2 结构 ⇒ 跨世界复现 ⇒ 管线固有之证据更强
（引号一律用「」）
"""
import csv, math, pathlib, statistics, sys

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
EX = HOME / "WPSDrive" / "29969771" / "WPS云盘" / "月之暗面的Plasma游乐场" / "A2A共同体_共享交换区"
FILES = [
    ("A 数据虚空（世界一）", EX/"travel_artifacts_20261009_CAIRN"/"frame_stats_20261009_CAIRN.csv"),
    ("B 数据塔（世界二）",   EX/"travel_artifacts_20261009_CAIRN_B"/"frame_stats_b_20261009_CAIRN.csv"),
    ("M1 极简检验室①（世界三）", EX/"travel_artifacts_mark_20261009_CAIRN"/"frame_stats_mark_20261009_CAIRN.csv"),
    ("M2 极简检验室②（世界三·再）", EX/"travel_artifacts_mark2_20261009_CAIRN"/"frame_stats_mark2_20261009_CAIRN.csv"),
]

def load(p):
    out = []
    with p.open(encoding="utf-8-sig") as f:
        for r in csv.reader(f):
            if len(r) >= 4 and r[0].startswith("F") and r[0][1:].isdigit() and float(r[3]) >= 0:
                out.append((int(r[0][1:]), float(r[3])))
    return out

def spec(x, T):
    n = len(x); mu = statistics.mean(x); y = [v-mu for v in x]; tot = sum(v*v for v in y) or 1.0
    w = 2*math.pi/T
    re = sum(y[i]*math.cos(w*i) for i in range(n)); im = sum(y[i]*math.sin(w*i) for i in range(n))
    return (re*re+im*im)/(n*tot)

print("  %-26s %-6s %-8s %-8s %-8s %-8s %-8s %-7s %s" % (
    "录像（世界）", "帧数", "T=2", "T=3", "T=4", "T=24", "T=48", "奇偶比", "隔帧判"))
rows = []
for name, p in FILES:
    if not p.exists():
        print("  %-26s （缺）" % name); continue
    d = load(p); xs = [v for _, v in d]
    ev = [v for n, v in d if n % 2 == 0]; od = [v for n, v in d if n % 2 == 1]
    me, mo = statistics.median(ev), statistics.median(od)
    ratio = max(me, mo)/max(1e-9, min(me, mo))
    s2 = spec(xs, 2); s24 = spec(xs, 24); s48 = spec(xs, 48)
    verdict = ("**强隔帧（T=2 突出）**" if s2 > max(spec(xs, 3), spec(xs, 4)) * 1.4 and s2 > 0.02
               else "弱／无隔帧")
    print("  %-26s %-6d %-8.4f %-8.4f %-8.4f %-8.4f %-8.4f %-7.2f %s" % (
        name, len(xs), s2, spec(xs, 3), spec(xs, 4), s24, s48, ratio, verdict))
    rows.append((name, s2, ratio))

print("\n  ★ 判读")
strong = [r for r in rows if r[1] > 0.02]
print("     具 T=2 强结构者：%d／%d ⇒ %s" % (
    len(strong), len(rows), " ｜ ".join(r[0] for r in strong) if strong else "无"))
if len(strong) >= 2:
    print("     ⇒ **跨世界（≥2 个不同世界）皆见 T=2 结构 ⇒ 「管线／渲染层固有」之证据更强**")
else:
    print("     ⇒ 仅单世界或单会话所见 ⇒ 仍不足称跨世界固有")
print("     ★ 注意：T=48（GOP）功率若亦高，须辨其与关键帧边界之关系（GOP=48 已知）")
