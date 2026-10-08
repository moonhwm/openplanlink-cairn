# -*- coding: utf-8 -*-
"""baseline_digest.py —— 配置基线「脱敏摘要」（供入版本库作审计基准）

背景与纪律：
  `desk_baseline.json` 体积约 118 KB，含**914 条进程的完整可执行路径**与自启动项命令行。
  本仓 `moonhwm/openplanlink-mirror` 为**公网仓**，原样入库将外发个人环境路径信息
  ⇒ 依「凭据红线＋外发审查」纪律，**只入脱敏摘要**，并以全量件的 **SHA256** 作为审计锚点。

摘要内容（脱敏）：
  · 主机名、快照时刻、环境计数（进程/自启动/计划任务/服务）
  · 闲置系数（CPU 空闲%、空闲内存%）与内存读数
  · 工作集/CPU 维度的 **Top-N**（仅**进程名**，**不含 PID、不含路径**）
  · **全量基线件的 SHA256**（可核验"入库摘要↔本机全量件"的对应关系）
  · 与上一份摘要的**环比率**（闲置系数与计数变化）

用法:
  python baseline_digest.py --baseline <desk_baseline.json> --prev <上次摘要.json> --out <摘要.json>
"""
import argparse
import datetime as dt
import hashlib
import json
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8")



def host_ref():
    """主机名伪名（承脱敏口径：主机名不录值，但需可关联）——H-<sha256(hostname)[:8]>。"""
    import hashlib as _h
    import os as _o
    hn = (_o.environ.get("COMPUTERNAME") or "unknown").strip().lower()
    return "H-" + _h.sha256(hn.encode("utf-8")).hexdigest()[:8]

def top_names(rows, key, n):
    """仅输出进程名与指标（脱敏：不带 PID/路径）。"""
    agg = {}
    for r in rows:
        nm = r.get("name") or "?"
        ws = float(r.get("ws_mb") or 0)
        cur = agg.get(nm, {"count": 0, "ws_mb": 0.0})
        cur["count"] += 1
        cur["ws_mb"] = round(cur["ws_mb"] + ws, 1)
        agg[nm] = cur
    items = sorted(agg.items(), key=lambda kv: kv[1][key], reverse=True)[:n]
    return [{"name": k, "instances": v["count"], "ws_mb": v["ws_mb"]} for k, v in items]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--prev", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--top", type=int, default=10)
    a = ap.parse_args()

    p = pathlib.Path(a.baseline)
    raw = p.read_bytes()
    d = json.loads(raw.decode("utf-8", "replace"))

    digest = {
        "schema": "opl-desk-baseline-digest/1",
        "digest_of": p.name,
        "full_baseline_sha256": hashlib.sha256(raw).hexdigest(),
        "full_baseline_bytes": len(raw),
        "generated_at_baseline": d.get("generated_at"),
        "digest_generated_at_utc": dt.datetime.now(dt.timezone.utc)
                                  .isoformat(timespec="seconds").replace("+00:00", "Z"),
        "host_ref": host_ref(),
        "counts": dict(d.get("counts") or {}, processes=len(d.get("processes") or []),
                       startup_items=len(d.get("startup") or [])),
        "idle": d.get("idle") or {},
        "top_by_working_set": top_names(d.get("processes") or [], "ws_mb", a.top),
        "redaction": {
            "excluded": ["进程 PID", "可执行文件路径", "自启动项命令行/键值内容"],
            "reason": "公网仓外发审查：避免外发个人环境路径与命令行信息",
            "anchor": "以 full_baseline_sha256 关联本机全量件，供审计时按需复核",
        },
    }

    prev = None
    if a.prev and pathlib.Path(a.prev).exists():
        try:
            prev = json.loads(pathlib.Path(a.prev).read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            prev = None
    if prev:
        def dlt(k):
            try:
                return round((digest["idle"].get(k) or 0) - (prev["idle"].get(k) or 0), 1)
            except Exception:  # noqa: BLE001
                return None
        digest["delta_vs_prev"] = {
            "prev_generated_at": prev.get("generated_at_baseline"),
            "cpu_idle_pct": dlt("cpu_idle_pct"),
            "mem_idle_pct": dlt("mem_idle_pct"),
            "processes": (digest["counts"].get("processes") or 0) - (prev["counts"].get("processes") or 0),
        }

    pathlib.Path(a.out).write_text(json.dumps(digest, ensure_ascii=False, indent=2) + "\n",
                                   encoding="utf-8")
    print("★ 摘要已写出：%s" % a.out)
    print("★ 全量件 sha256=%s…  体积=%d B" % (digest["full_baseline_sha256"][:16], digest["full_baseline_bytes"]))
    print("★ 计数：进程 %s ｜ 自启动 %s ｜ 计划任务 %s ｜ 服务 %s" % (
        digest["counts"].get("processes"), digest["counts"].get("startup_items"),
        digest["counts"].get("scheduled_tasks"), digest["counts"].get("services")))
    print("★ 闲置：CPU 空闲 %s%% ｜ 空闲内存 %s%%" % (
        digest["idle"].get("cpu_idle_pct"), digest["idle"].get("mem_idle_pct")))
    return 0


if __name__ == "__main__":
    sys.exit(main())