# -*- coding: utf-8 -*-
"""文档档案之增量扩展器：按队列（频次＝重要度）逐件拉取入档
用法：python doc_archive_extend.py [--max N] [--budget 秒]
★ 与 doc_archive.py 共用 archive/docs/index.json（可微：节级 sha3；可导：全史 manifest）
（引号一律用「」）
"""
import argparse, hashlib, json, pathlib, re, subprocess, sys, time

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
SEAT = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"
ARCH = SEAT/"archive"/"docs"; ARCH.mkdir(parents=True, exist_ok=True)
CLI = HOME/".kimi-work"/"bin"/"kdocs-cli.exe"
QUEUE = ARCH/"docs_list.json"
IDX = ARCH/"index.json"

# 队列：按"全语料出现频次"排序（出现越多＝越重要）
FREQ = ["cubofOPoRdSw", "clFOjVPjbbOc", "cboAFwILF079", "ceuKopR7LW83", "ci2ybbMcccFi",
        "cgeO17yb4eiI", "cjdFFj5rrZi1", "caBn4BzDaBMO", "cijGVCsbZsGm", "cnuuL0BZDcsc",
        "ceWJWwADwbGp", "ck91uLlXnyDK", "ct82eUr6LT66", "cuLQR5ycgR4J", "co3jGF2ridX9",
        "cplH408hcQMF", "cfUP3XTMb2UG", "cjj1X42H8FMP", "ccmYOO3QvUyd", "cg0IMPqFxDn7",
        "cfBasPki2r06", "coIQr9TX0W1W", "cm4IPhTYznTs", "ctpxZ2X2JxkG", "cndYJKCF7len",
        "cn8TJyXeLyop", "cdnTX6c3i3WF", "cbhgTvnOPGTe", "cp0wHNiF4XVj", "caLl83StO4UI",
        "ciBoOWmoUaDk", "cbfHsqlxCa4V", "ctvWcll0pvgs", "ccVjFCFHR1my", "cqfhnj68m2Mj",
        "cuumpvPlZ5sI", "ctZUzzclIzqO", "cbioamxelCdZ", "clf5rkybW2gm", "ce64WlT2Dk9G"]
if not QUEUE.exists():
    QUEUE.write_text(json.dumps({"note": "按频次排序之待拉队列；出现次数＝引用广度",
                                 "ids": FREQ}, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")

def sha(t, n=24): return hashlib.sha3_512(t.encode("utf-8")).hexdigest()[:n]

def sections(md):
    out, cur, buf = [], "(前言)", []
    for line in md.splitlines():
        m = re.match(r"^(#{1,6})\s+(.*)$", line.strip())
        if m:
            out.append((cur, "\n".join(buf).strip())); cur = m.group(2).strip(); buf = [line]
        else: buf.append(line)
    out.append((cur, "\n".join(buf).strip()))
    return [(t, b) for t, b in out if b.strip()]

def pull(link_id, to=120):
    try:
        p = subprocess.run([str(CLI), "drive", "read-file", "--args", json.dumps({"link_id": link_id})],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=to)
    except subprocess.TimeoutExpired:
        return None, {"err": "超时 %ds" % to}
    out = (p.stdout or "") + (p.stderr or "")
    i = out.find("{")
    if i < 0: return None, {"err": "无 JSON", "head": out[:120]}
    try:
        j, _ = json.JSONDecoder().raw_decode(out[i:])
    except Exception as e:
        return None, {"err": str(e)[:80]}
    d = j.get("data") or {}
    return d.get("content", ""), {"code": j.get("code"), "name": d.get("name"), "file_id": d.get("file_id"),
                                  "drive_id": d.get("drive_id"), "format": d.get("content_format")}

ap = argparse.ArgumentParser()
ap.add_argument("--max", type=int, default=10)
ap.add_argument("--budget", type=float, default=240.0)
a = ap.parse_args()
ids = json.loads(QUEUE.read_text(encoding="utf-8"))["ids"]
manifest = json.loads(IDX.read_text(encoding="utf-8")) if IDX.exists() else {}
t0 = time.time(); done = fail = skipped = 0
print("  ═══ 增量扩展（上限 %d 件／预算 %.0f s）═══" % (a.max, a.budget))
for lid in ids:
    if done >= a.max or (time.time()-t0) > a.budget:
        print("   · 预算/上限到，余 %d 件留待下轮" % (len(ids)-done-fail-skipped)); break
    key = "kd_" + lid[-6:]
    if key in manifest and manifest[key].get("history"):
        skipped += 1; continue
    c, meta = pull(lid)
    if c is None:
        fail += 1; print("   ✗ %s ⇒ %s" % (lid, meta.get("err") or meta.get("head"))); continue
    secs = sections(c); h = sha(c); ver = time.strftime("%Y%m%d_%H%M")
    vd = ARCH/key; vd.mkdir(parents=True, exist_ok=True)
    (vd/("v_%s.md" % ver)).write_text(c, encoding="utf-8", newline="\n")
    (vd/("sections_%s.json" % ver)).write_text(json.dumps({t: sha(b) for t, b in secs}, ensure_ascii=False, indent=1),
                                              encoding="utf-8", newline="\n")
    manifest[key] = {"link_id": lid, "title": meta.get("name") or lid, "history": [{
        "ver": ver, "ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "hash": h, "chars": len(c),
        "lines": len(c.splitlines()), "sections": len(secs), "file_id": meta.get("file_id"),
        "drive_id": meta.get("drive_id"), "changed": True, "diff": None}], "latest": {
        "hash": h, "chars": len(c), "sections": len(secs), "ver": ver}}
    done += 1
    print("   ✓ %-7s %-42s %7d 字 ｜ %3d 节 ｜ %s" % (key, (meta.get("name") or lid)[:42], len(c), len(secs), h))
manifest["_updated"] = time.strftime("%Y-%m-%dT%H:%M:%S+0800")
manifest["_note"] = "可微（节级 sha3）可导（全史 manifest）；工具 kdocs-cli v2.6.13；凭据零落盘"
IDX.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
tot = sum(1 for k, v in manifest.items() if not k.startswith("_") and v.get("history"))
print("\n  ═══ 汇总：本次新增 %d ｜ 失败 %d ｜ 已在档跳过 %d ｜ 耗时 %.1f s ═══" % (done, fail, skipped, time.time()-t0))
print("   档案共 %d 件 ｜ manifest %.1f KB ｜ 队列余 %d 件" % (tot, IDX.stat().st_size/1024, max(0, len(ids)-tot)))
