# -*- coding: utf-8 -*-
"""视频容器审计：直解各录像之轨道（视频/音频）、样本数、样本总字节、每帧比特
目的：查明 `-64` 之 instruct 录像（3,836.9 KB）为何远大于零输入（~800 KB）——内容差异抑或容器/编码差异
（引号一律用「」）
"""
import hashlib, json, pathlib, struct, sys

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
EX = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"
FILES = [
    ("A 数据虚空（零输入）", EX/"travel_artifacts_20261009_CAIRN"/"travel_v5_video_20261009.mp4"),
    ("B 数据塔（零输入）", EX/"travel_artifacts_20261009_CAIRN_B"/"travel_b_video_20261009.mp4"),
    ("M1 检验室（零输入）", EX/"travel_artifacts_mark_20261009_CAIRN"/"mark_video_20261009.mp4"),
    ("M2 检验室（零输入·再）", EX/"travel_artifacts_mark2_20261009_CAIRN"/"mark2_video_20261009.mp4"),
    ("★INSTRUCT（下过 4 条指令）", EX/"travel_artifacts_instruct_20261009_CAIRN"/"instruct_video_20261009.mp4"),
]

def boxes(buf, start, end):
    i = start
    while i + 8 <= end:
        size, typ = struct.unpack_from(">I4s", buf, i)
        if size == 0: size = end - i
        if size < 8: break
        yield typ.decode("latin1"), i + 8, i + size
        i += size

def find_all(buf, path, start=0, end=None):
    end = len(buf) if end is None else end
    cur = [(start, end)]
    for want in path:
        nxt = []
        for (s, e) in cur:
            for typ, ps, pe in boxes(buf, s, e):
                if typ == want: nxt.append((ps, pe))
        if not nxt: return []
        cur = nxt
    return cur

def full_table(buf, s, e):
    n = struct.unpack_from(">I", buf, s+4)[0]
    return n, s+8

rows = []
for name, p in FILES:
    if not p.exists():
        print("  %-26s （缺）" % name); continue
    buf = p.read_bytes()
    traks = find_all(buf, ["moov", "trak"])
    info = {"file": p.name, "bytes": len(buf), "sha3_16": hashlib.sha3_512(buf).hexdigest()[:16], "tracks": []}
    for ti, (ts, te) in enumerate(traks):
        hdlr = find_all(buf, ["mdia", "hdlr"], ts, te)
        handler = buf[hdlr[0][0]+8:hdlr[0][0]+12].decode("latin1") if hdlr else "?"
        stbl = find_all(buf, ["mdia", "minf", "stbl"], ts, te)
        n_samples = None; total = 0
        if stbl:
            ks = {t: (ps, pe) for t, ps, pe in boxes(buf, *stbl[0])}
            if "stsz" in ks:
                ps, pe = ks["stsz"]
                sample_size = struct.unpack_from(">I", buf, ps+4)[0]
                n_samples = struct.unpack_from(">I", buf, ps+8)[0]
                if sample_size == 0:
                    total = sum(struct.unpack_from(">I", buf, ps+12+4*i)[0] for i in range(n_samples))
                else:
                    total = sample_size * n_samples
            elif "stz2" in ks:
                n_samples = struct.unpack_from(">I", buf, ks["stz2"][0]+8)[0]; total = 0
        kind = {"vide":"视频", "soun":"音频", "hint":"提示"}.get(handler, handler)
        info["tracks"].append({"idx": ti+1, "handler": kind, "samples": n_samples, "bytes": total})
    v = next((t for t in info["tracks"] if t["handler"] == "视频"), None)
    a = [t for t in info["tracks"] if t["handler"] == "音频"]
    info["video_frames"] = v["samples"] if v else None
    info["video_bytes"] = v["bytes"] if v else None
    info["audio_tracks"] = len(a)
    info["audio_bytes"] = sum(t["bytes"] for t in a)
    info["bits_per_frame"] = round((v["bytes"]*8)/v["samples"], 1) if (v and v["samples"]) else None
    info["video_share_pct"] = round(100*(v["bytes"]/len(buf)), 1) if v else None
    rows.append(info)
    print("  %-26s %9d B ｜ 视频帧 %-5s ｜ 视频字节 %-9s ｜ 每帧 %-7s bit ｜ 音频轨 %d（%s B）｜ 视频占比 %s%%" % (
        name, info["bytes"], info["video_frames"], info["video_bytes"],
        info["bits_per_frame"], info["audio_tracks"], info["audio_bytes"], info["video_share_pct"]))

print("\n  ★ 判读规则：")
print("     若 instruct 之「每帧比特」与零输入相近、而「字节差」主要来自「非视频字节（音频/其他盒）」")
print("     ⇒ 体积差为容器/编码或音轨所致 ⇒ **不能据此推断'内容更丰富'**")
print("     若「每帧比特」显著更高 ⇒ 画面复杂度更高 ⇒ 值得进一步查（但本席之帧统计已示 MAD 无差）")
out = EX/"video_container_audit_20261009_CAIRN.json"
out.write_text(json.dumps({"ts": __import__("time").strftime("%Y-%m-%dT%H:%M:%S+0800"), "seat": "a2a-node-local",
                           "purpose": "查 instruct 录像体积异常（3.8MB vs 零输入 ~0.8MB）之来源",
                           "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("\n  落盘：%s" % out.name)
