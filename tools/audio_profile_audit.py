# -*- coding: utf-8 -*-
"""音轨剖面审计（代理指标）：解析各录像音轨之逐样本字节大小（stsz）与时间轴（stts）
代理口径：AAC 帧大小 ≈ 该帧编码所需比特 ⇒ 可作"音频活动"之粗代理（**非解码、非语义**）
重点：instruct 会话之 0–25s 窗（4 条指令下发于 t≈5–20s）vs 同世界零输入（M1／M2）同窗
（引号一律用「」）
"""
import json, pathlib, statistics, struct, sys, time

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
EX = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"
FILES = [
    ("M1 检验室（零输入）", EX/"travel_artifacts_mark_20261009_CAIRN"/"mark_video_20261009.mp4"),
    ("M2 检验室（零输入·再）", EX/"travel_artifacts_mark2_20261009_CAIRN"/"mark2_video_20261009.mp4"),
    ("★INSTRUCT（4 条指令）", EX/"travel_artifacts_instruct_20261009_CAIRN"/"instruct_video_20261009.mp4"),
]

def boxes(buf, s, e):
    i = s
    while i + 8 <= e:
        size, typ = struct.unpack_from(">I4s", buf, i)
        if size == 0: size = e - i
        if size < 8: break
        yield typ.decode("latin1"), i+8, i+size
        i += size

def find_all(buf, path, s=0, e=None):
    e = len(buf) if e is None else e
    cur = [(s, e)]
    for want in path:
        nxt = []
        for (a, b) in cur:
            for typ, ps, pe in boxes(buf, a, b):
                if typ == want: nxt.append((ps, pe))
        if not nxt: return []
        cur = nxt
    return cur

def timescale_of(buf, ts, te):
    mdhd = find_all(buf, ["mdia", "mdhd"], ts, te)
    if not mdhd: return None
    s = mdhd[0][0]; ver = buf[s]
    return struct.unpack_from(">I", buf, s + (20 if ver == 1 else 12))[0]

def read_stsz(buf, stbl):
    ks = {t: (ps, pe) for t, ps, pe in boxes(buf, *stbl)}
    if "stsz" not in ks: return []
    ps, pe = ks["stsz"]
    ss = struct.unpack_from(">I", buf, ps+4)[0]
    n = struct.unpack_from(">I", buf, ps+8)[0]
    if ss: return [ss]*n
    return [struct.unpack_from(">I", buf, ps+12+4*i)[0] for i in range(n)]

def read_stts(buf, stbl):
    ks = {t: (ps, pe) for t, ps, pe in boxes(buf, *stbl)}
    if "stts" not in ks: return []
    ps, pe = ks["stts"]
    n = struct.unpack_from(">I", buf, ps+4)[0]
    out = []
    for i in range(n):
        c, d = struct.unpack_from(">II", buf, ps+8+8*i)
        out.append((c, d))
    return out

print("  === 音轨剖面（代理：逐样本字节；时间由 stts 展开）===")
summary = []
for name, p in FILES:
    if not p.exists(): print("  %-22s （缺）" % name); continue
    buf = p.read_bytes()
    for ts, te in find_all(buf, ["moov", "trak"]):
        hdlr = find_all(buf, ["mdia", "hdlr"], ts, te)
        h = buf[hdlr[0][0]+8:hdlr[0][0]+12].decode("latin1") if hdlr else "?"
        if h != "soun": continue
        tsc = timescale_of(buf, ts, te) or 1
        stbl = find_all(buf, ["mdia", "minf", "stbl"], ts, te)
        sizes = read_stsz(buf, stbl[0]) if stbl else []
        stts = read_stts(buf, stbl[0]) if stbl else []
        # 展开每样本之起止时刻（秒）
        times, tcur = [], 0
        for c, d in stts:
            for _ in range(c):
                times.append(tcur/tsc); tcur += d
        n = min(len(sizes), len(times))
        if n == 0: continue
        dur = times[-1] if times else 0
        # 0–25s 窗之统计（若录像短于此，则取全程）
        win = [sizes[i] for i in range(n) if times[i] <= 25.0]
        w0 = [sizes[i] for i in range(n) if times[i] <= 5.0]
        w1 = [sizes[i] for i in range(n) if 5.0 < times[i] <= 20.0]
        w2 = [sizes[i] for i in range(n) if times[i] > 25.0]
        def st(v): return ("n=%d 中位=%.0f 均=%.1f 最大=%d" % (len(v), statistics.median(v), statistics.mean(v), max(v))) if v else "（空）"
        print("\n  【%s】音轨：样本 %d ｜ 时长 %.1fs ｜ 采样率(时基) %d" % (name, n, dur, tsc))
        print("     0–5s   ：%s" % st(w0))
        print("     5–20s  ：%s" % st(w1))
        print("     >25s   ：%s" % st(w2))
        ratio = (statistics.mean(w1)/statistics.mean(w2)) if (w1 and w2 and statistics.mean(w2) > 0) else None
        print("     5–20s／>25s 均值比 = %s" % (round(ratio, 3) if ratio else "—"))
        summary.append({"file": p.name, "audio_samples": n, "duration_s": round(dur, 1),
                        "mean_0_5": round(statistics.mean(w0), 1) if w0 else None,
                        "mean_5_20": round(statistics.mean(w1), 1) if w1 else None,
                        "mean_gt25": round(statistics.mean(w2), 1) if w2 else None,
                        "ratio_5_20_over_gt25": round(ratio, 3) if ratio else None})
print("\n  ★ 判读规则（**代理，非解码**）：")
print("     若 instruct 之 5–20s 窗（指令期）音频样本均值显著高于其 >25s 窗，且高于同世界零输入之同窗")
print("     ⇒ **音频侧或有反应**（须再验，且不得据此断言'世界已响应'）")
print("     若两窗与零输入皆相近 ⇒ **音频侧亦无异常**（与 `-72`／`-64` 一致）")
out = EX/"audio_profile_audit_20261009_CAIRN.json"
out.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "seat": "a2a-node-local",
                           "proxy": "AAC 帧字节大小 ≈ 音频活动（非解码、非语义）", "rows": summary},
                          ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("\n  落盘：%s" % out.name)
