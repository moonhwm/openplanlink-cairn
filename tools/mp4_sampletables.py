# -*- coding: utf-8 -*-
"""直解 MP4 样本表（纯标准库）：取视频轨之 stss（关键帧）、ctts（合成偏移，判 B 帧）、stts（时长）、stsz（大小）
目的：判 M 录之"隔帧（T=2）结构"是否为编码层（B 帧／GOP 节律）所致
（引号一律用「」）
"""
import pathlib, struct, sys

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
EX = HOME / "WPSDrive" / "29969771" / "WPS云盘" / "月之暗面的Plasma游乐场" / "A2A共同体_共享交换区"
FILES = [("M 极简检验室", EX/"travel_artifacts_mark_20261009_CAIRN"/"mark_video_20261009.mp4"),
         ("A 数据虚空", EX/"travel_artifacts_20261009_CAIRN"/"travel_v5_video_20261009.mp4"),
         ("B 数据塔", EX/"travel_artifacts_20261009_CAIRN_B"/"travel_b_video_20261009.mp4")]

def boxes(buf, start, end):
    """遍历 [start,end) 内的顶层 box：(type, payload_start, payload_end)"""
    i = start
    while i + 8 <= end:
        size, typ = struct.unpack_from(">I4s", buf, i)
        if size == 0: size = end - i
        if size < 8: break
        yield typ.decode("latin1"), i + 8, i + size
        i += size

def find(buf, path, start=0, end=None):
    """按路径（如 ['moov','trak','mdia','minf','stbl']）找第一个匹配之 payload 区间"""
    end = len(buf) if end is None else end
    cur = [(start, end)]
    for want in path:
        nxt = []
        for (s, e) in cur:
            for typ, ps, pe in boxes(buf, s, e):
                if typ == want:
                    nxt.append((ps, pe))
        if not nxt: return None
        cur = nxt
    return cur[0]

def full_table(buf, s, e):
    """通用 full box：version/flags(4) + count(4) + entries"""
    ver = buf[s]; n = struct.unpack_from(">I", buf, s+4)[0]
    return ver, n, s+8

for name, p in FILES:
    if not p.exists():
        print("  %-14s × 文件不在" % name); continue
    buf = p.read_bytes()
    print("\n  === %s（%s，%.1f KB）" % (name, p.name, len(buf)/1024))
    stbl = find(buf, ["moov", "trak", "mdia", "minf", "stbl"])
    if not stbl:
        print("     × 未找到 stbl（可能非 mp4 或结构不同）"); continue
    s, e = stbl
    kinds = {}
    for typ, ps, pe in boxes(buf, s, e):
        kinds[typ] = (ps, pe)
    print("     stbl 内 box：%s" % "、".join(sorted(kinds)))
    # stsz
    if "stsz" in kinds:
        ps, pe = kinds["stsz"]; ver, n, off = full_table(buf, ps, pe)
        sample_size = struct.unpack_from(">I", buf, ps+4)[0]
        cnt = struct.unpack_from(">I", buf, ps+8)[0]
        print("     样本数（stsz）= %d" % cnt)
    # stss（关键帧）
    if "stss" in kinds:
        ps, pe = kinds["stss"]; ver, n, off = full_table(buf, ps, pe)
        idx = [struct.unpack_from(">I", buf, off + 4*i)[0] for i in range(n)]
        gaps = [idx[i+1]-idx[i] for i in range(len(idx)-1)]
        print("     ★ 关键帧（stss）：%d 个 ⇒ 索引 %s%s" % (n, idx[:8], " …" if n > 8 else ""))
        if gaps:
            uniq = sorted(set(gaps))
            print("       关键帧间隔：%s（唯一值 %s）" % (gaps[:8], uniq[:6]))
    else:
        print("     ★ 无 stss ⇒ 全为关键帧（或未标同步样本）")
    # ctts（合成偏移 ⇒ B 帧）
    if "ctts" in kinds:
        ps, pe = kinds["ctts"]; ver, n, off = full_table(buf, ps, pe)
        offs = [struct.unpack_from(">i", buf, off + 4*i)[0] for i in range(min(n, 12))]
        neg = any(o < 0 for o in offs)
        print("     ★ 合成偏移（ctts）前 %d 项：%s ⇒ %s" % (
            len(offs), offs, "**存在负偏移／乱序 ⇒ 有 B 帧（双向预测）**" if neg or any(o > 0 for o in offs) else "无偏移 ⇒ 无 B 帧"))
    else:
        print("     ★ 无 ctts ⇒ 无合成偏移 ⇒ 无 B 帧（仅 I/P）")
    # stts（时长表）
    if "stts" in kinds:
        ps, pe = kinds["stts"]; ver, n, off = full_table(buf, ps, pe)
        first = struct.unpack_from(">II", buf, off) if n else (0, 0)
        print("     stts：条目 %d ｜ 首条（样本数=%d，时长=%d 时基）" % (n, first[0], first[1]))
print("\n  ★ 判读规则：若「关键帧间隔」或「ctts 偏移」之节律与 T=2 相关（如全为 1 或 2 之结构），")
print("     则 M 录之隔帧结构**可能属编码层**；若关键帧间隔远大于 2（如 24）且无 B 帧，则**编码层解释不成立**，")
print("     该结构须归内容／渲染层（**本席仍标「未解释」，除非证据足以定论**）")
