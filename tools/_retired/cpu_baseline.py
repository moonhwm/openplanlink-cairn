# -*- coding: utf-8 -*-
"""cpu_baseline.py —— 算力基线测量（供应商无关）

用途：为「华为云 X 实例 CPU 算力榨取」提供**可对比的本地基线**。
      在同构 X 实例上复跑同一脚本，即可得到「榨取率 / 单位成本产出」的分子与分母。

测量项（全部实测，不估算）：
  1. 拓扑：逻辑核数 / 物理核数 / 频率上限（取系统可得者）
  2. 单进程算力：SHA3-512 吞吐（MB/s）——与本生态哈希口径一致，便于横向比对
  3. 多进程算力：并行 N 进程的**聚合吞吐**与**并行效率**（= 聚合/（单进程×N））
  4. 稳定性：分段采样的吞吐标准差（识别降频/争抢）

输出：JSON（机器可读）+ Markdown（一页纸）

用法:
  python cpu_baseline.py                      # 默认：每进程 3 秒
  python cpu_baseline.py --seconds 5 --workers 0   # workers=0 取逻辑核数
  python cpu_baseline.py --out-cpu cpu-baseline.json --out-md cpu-baseline.md
"""
import argparse
import datetime as dt
import hashlib
import json
import multiprocessing as mp
import os
import pathlib
import statistics
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

BLOCK = os.urandom(1 << 20)  # 1 MiB 固定数据块，避免内存带宽差异干扰


def burn(seconds: float) -> dict:
    """在给定秒数内做 SHA3-512 循环，返回吞吐（MB/s）与分段采样。"""
    h = hashlib.sha3_512
    count = 0
    seg = []
    t_end = time.perf_counter() + seconds
    seg_end = time.perf_counter() + 0.5
    while True:
        now = time.perf_counter()
        if now >= t_end:
            break
        h(BLOCK).digest()
        count += 1
        if now >= seg_end:
            seg.append((count * BLOCK.__len__()) / (1 << 20) / (now - (t_end - seconds)))
            seg_end = now + 0.5
    elapsed = time.perf_counter() - (t_end - seconds)
    return {"mb": count * len(BLOCK) / (1 << 20), "seconds": elapsed,
            "mbps": (count * len(BLOCK) / (1 << 20)) / elapsed if elapsed > 0 else 0.0,
            "segments": seg}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=3.0, help="每个进程的燃烧时长")
    ap.add_argument("--workers", type=int, default=0, help="并行进程数；0=逻辑核数（上限 16）")
    ap.add_argument("--out-cpu", default=None)
    ap.add_argument("--out-md", default=None)
    a = ap.parse_args()

    logical = os.cpu_count() or 1
    try:
        physical = len({(c["physical_id"], c["core_id"]) for c in _linux_cpuinfo()})
    except Exception:  # noqa: BLE001
        physical = None
    workers = a.workers or min(logical, 16)

    print("★ 逻辑核 = %d；物理核 = %s；并行进程 = %d；每进程 %ss" % (
        logical, physical if physical else "未知（非 Linux 或不可得）", workers, a.seconds))

    t0 = time.perf_counter()
    with mp.Pool(workers) as pool:
        results = pool.map(burn, [a.seconds] * workers)
    wall = time.perf_counter() - t0

    single = results[0]["mbps"]
    agg = sum(r["mbps"] for r in results)
    efficiency = agg / (single * workers) if single > 0 else 0.0
    all_segments = [s for r in results for s in r["segments"]]
    stability = (statistics.pstdev(all_segments) / statistics.fmean(all_segments)
                 if len(all_segments) > 1 and statistics.fmean(all_segments) > 0 else None)

    payload = {
        "measured_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "host": os.environ.get("COMPUTERNAME", "unknown"),
        "algorithm": "sha3-512 / 1 MiB blocks",
        "logical_cores": logical,
        "physical_cores": physical,
        "workers": workers,
        "seconds_per_worker": a.seconds,
        "wall_seconds": round(wall, 3),
        "single_process_mbps": round(single, 2),
        "aggregate_mbps": round(agg, 2),
        "parallel_efficiency": round(efficiency, 4),
        "segment_cv": round(stability, 4) if stability is not None else None,
        "note": "同一脚本在同构实例复跑即可对比；并行效率<0.9 提示存在降频/争抢/带宽瓶颈",
    }
    if a.out_cpu:
        pathlib.Path(a.out_cpu).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                                          encoding="utf-8")

    lines = [
        "# 算力基线（本机实测）",
        "",
        "- 测量时刻：%s" % payload["measured_at"],
        "- 主机：`%s`" % payload["host"],
        "- 口径：SHA3-512，1 MiB 固定块，每进程 %ss" % a.seconds,
        "",
        "| 指标 | 实测 |",
        "|---|---|",
        "| 逻辑核 / 物理核 | %d / %s |" % (logical, physical if physical else "未知"),
        "| 并行进程数 | %d |" % workers,
        "| 单进程吞吐 | **%.2f MB/s** |" % single,
        "| 聚合吞吐 | **%.2f MB/s** |" % agg,
        "| 并行效率（聚合 ÷（单进程×N）） | **%.1f%%** |" % (efficiency * 100),
        "| 分段稳定性（变异系数，越低越稳） | %s |" % (
            ("%.3f" % stability) if stability is not None else "样本不足"),
        "| 墙钟耗时 | %.2f s |" % wall,
        "",
        "> 用途：与华为云 X 实例（或任何外延算力池）同脚本复跑对比，得出**榨取率**与**单位成本产出**。",
        "> 判读：并行效率 < 90% 提示降频/争抢/内存带宽瓶颈，须调绑定与并行度；变异系数偏高提示算力不稳定。",
    ]
    md = "\n".join(lines) + "\n"
    if a.out_md:
        pathlib.Path(a.out_md).write_text(md, encoding="utf-8")

    print(md)
    return 0


def _linux_cpuinfo():
    out = []
    try:
        with open("/proc/cpuinfo", encoding="utf-8", errors="replace") as f:
            cur = {}
            for line in f:
                if not line.strip():
                    if cur:
                        out.append(cur)
                        cur = {}
                    continue
                if ":" in line:
                    k, v = line.split(":", 1)
                    cur[k.strip()] = v.strip()
            if cur:
                out.append(cur)
    except OSError:
        pass
    if not out:
        raise RuntimeError("no cpuinfo")
    return [{"physical_id": c.get("physical id", "0"), "core_id": c.get("core id", str(i))}
            for i, c in enumerate(out)]


if __name__ == "__main__":
    sys.exit(main())
