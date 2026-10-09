# -*- coding: utf-8 -*-
"""未闭合项三之复验：M 之"间歇性幅度差异"（ρ₁₂≈0.38，T=2）
方法：对五录之逐帧帧差序列算 lag-2 自相关（ρ₁₂）与 lag-1（ρ₁），并算 1 s 窗剖面之 ρ
判：若同世界三录之 ρ₁₂ 皆≈0.38 且相合 ⇒ 属"世界之固定程序"（确定性），而非会话特有
（引号一律用「」）
"""
import csv, json, math, pathlib, statistics, sys, time

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

def series(dirname):
    d = EX/dirname
    cands = sorted(d.glob("frame_stats*.csv"))
    if not cands: return None, None, None
    mad, lum = [], []
    with cands[0].open(encoding="utf-8-sig") as f:
        for r in csv.reader(f):
            if len(r) >= 4 and r[0].startswith("F") and r[0][1:].isdigit():
                m = float(r[3])
                if m >= 0: mad.append(m)
                lum.append(float(r[2]))
    return cands[0].name, mad, lum

def acf(x, lag):
    n = len(x)
    if n <= lag + 2: return float("nan")
    m = statistics.mean(x)
    num = sum((x[i]-m)*(x[i+lag]-m) for i in range(n-lag))
    den = sum((v-m)**2 for v in x)
    return num/den if den > 0 else float("nan")

print("  === 五录之帧差序列自相关（逐帧；lag-1／lag-2／lag-3）===")
rows = []
for name, dirname in DIRS:
    fn, mad, lum = series(dirname)
    if not mad:
        print("  %-16s （无数表）" % name); continue
    r1, r2, r3 = acf(mad, 1), acf(mad, 2), acf(mad, 3)
    # 逐 1 s 窗均（窗内 24 帧）后之 lag-1／lag-2
    w = [statistics.mean(mad[i:i+24]) for i in range(0, len(mad)-23, 24)]
    w1, w2 = acf(w, 1), acf(w, 2)
    print("  %-16s 帧数 %-5d ｜ ρ1=%+.3f ρ2=%+.3f ρ3=%+.3f ｜ 1s窗均(n=%d)：ρ1=%+.3f ρ2=%+.3f" % (
        name, len(mad), r1, r2, r3, len(w), w1, w2))
    rows.append({"name": name, "frames": len(mad), "rho1": round(r1,3), "rho2": round(r2,3),
                 "rho3": round(r3,3), "rho1_1s": round(w1,3), "rho2_1s": round(w2,3),
                 "mad_median": round(statistics.median(mad),4), "mad_mean": round(statistics.mean(mad),4)})

print("\n  ★ 判读规则：")
print("     若 M1／M2／INSTRUCT 三录之 ρ2 皆≈0.38 且相近 ⇒ 属「世界之固定程序」（与 -79 之确定性结论一致）")
print("     若三录之 ρ2 差异大 ⇒ 属「会话特有」，须另寻机制")
print("     若 A／B 之 ρ2 与 M 系不同 ⇒ 亦证「程序依世界而异」")
out = EX/"rho2_recheck_20261009_CAIRN.json"
out.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "seat": "a2a-node-local",
                           "purpose": "未闭合项三之复验：间歇性幅度差异（ρ12≈0.38, T=2）是否属世界之固定程序",
                           "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("\n  落盘：%s" % out.name)
