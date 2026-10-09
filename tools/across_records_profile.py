# -*- coding: utf-8 -*-
"""跨录核查：五录之亮度／帧差逐 1 s 剖面（判"持续提亮"与"第二次活动期"是否平台级）
（引号一律用「」）
"""
import csv, json, pathlib, statistics, sys, time

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
EX = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"
DIRS = [
    ("A 数据虚空", "travel_artifacts_20261009_CAIRN"),
    ("B 数据塔", "travel_artifacts_20261009_CAIRN_B"),
    ("M1 检验室", "travel_artifacts_mark_20261009_CAIRN"),
    ("M2 检验室·再", "travel_artifacts_mark2_20261009_CAIRN"),
    ("INSTRUCT", "travel_artifacts_instruct_20261009_CAIRN"),
]

def load(dirname):
    d = EX/dirname
    cands = sorted(d.glob("frame_stats*.csv"))
    if not cands: return None
    rows = []
    with cands[0].open(encoding="utf-8-sig") as f:
        for r in csv.reader(f):
            if len(r) >= 4 and r[0].startswith("F") and r[0][1:].isdigit():
                rows.append((float(r[1])/1000.0, float(r[2]), float(r[3])))
    return cands[0].name, rows

print("  === 五录逐 1 s 剖面（亮度均 / 帧差 MAD 均）===")
summary = []
for name, dirname in DIRS:
    got = load(dirname)
    if not got:
        print("  %-16s （无数表）" % name); continue
    fn, rows = got
    bins = {}
    for t, lum, mad in rows:
        b = int(t)
        bins.setdefault(b, {"lum": [], "mad": []})
        bins[b]["lum"].append(lum)
        if mad >= 0: bins[b]["mad"].append(mad)
    ks = sorted(bins)
    line = []
    for b in ks:
        l = statistics.mean(bins[b]["lum"])
        line.append("%d:%.1f" % (b, l))
    madline = []
    for b in ks:
        m = statistics.mean(bins[b]["mad"]) if bins[b]["mad"] else -1
        madline.append("%d:%.2f" % (b, m))
    first = statistics.mean(bins[ks[0]]["lum"]); last = statistics.mean(bins[ks[-1]]["lum"])
    # 17–21 s 窗之 MAD 与全录 MAD 中位
    seg = [statistics.mean(bins[b]["mad"]) for b in ks if 17 <= b <= 21 and bins[b]["mad"]]
    allm = [statistics.mean(bins[b]["mad"]) for b in ks if bins[b]["mad"]]
    med = statistics.median(allm) if allm else float("nan")
    segmean = statistics.mean(seg) if seg else float("nan")
    print("\n  【%s】%s ｜ 窗数 %d ｜ 时长约 %d s" % (name, fn, len(ks), ks[-1]+1))
    print("     亮度(逐秒)：" + " ".join(line))
    print("     帧差(逐秒)：" + " ".join(madline))
    print("     ⇒ 亮度 %.2f → %.2f（Δ=%+.2f）｜ 帧差中位 %.3f ｜ 17–21 s 均 %.3f（比 %.2f）" % (
        first, last, last-first, med, segmean, (segmean/med if med and med > 0 else float("nan"))))
    summary.append({"name": name, "csv": fn, "bins": len(ks), "lum_first": round(first,2),
                    "lum_last": round(last,2), "lum_delta": round(last-first,2),
                    "mad_median": round(med,3), "mad_17_21": round(segmean,3),
                    "ratio_17_21": round(segmean/med,2) if med and med > 0 else None})

print("\n  ★ 判读规则：")
print("     若五录皆见「亮度持续上升」且「17–21 s 帧差回升」⇒ 属「平台级渲染阶段」而非世界变化")
print("     若仅 M 系见 ⇒ 属该世界／该会话之特征（须另判）")
out = EX/"across_records_1s_profile_20261009_CAIRN.json"
out.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "seat": "a2a-node-local",
                           "unit": "per-1s-window means", "rows": summary}, ensure_ascii=False, indent=1),
               encoding="utf-8", newline="\n")
print("\n  落盘：%s" % out.name)
