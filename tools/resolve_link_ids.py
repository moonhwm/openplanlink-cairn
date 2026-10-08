# -*- coding: utf-8 -*-
"""为 Moon 席之 wpsonline 索引（127 件）逐一解析 link_id —— 纯便利件（不拉正文）
- 输入：A2A共同体_共享交换区/wpsonline_index_20261009.json（127 件名／路径）
- 方法：kdocs-cli drive search-files（按基名关键词）→ 精确名字匹配 → 取 file.link_id
- 断点续跑：已解析项存入 map 文件，重跑跳过
- 零回显：不打印 token；仅打印进度与命中率
"""
import json, pathlib, re, subprocess, sys, time

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
CLI = str(pathlib.Path.home() / ".kimi-work" / "bin" / "kdocs-cli.exe")
PLAZA = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场")
EX = PLAZA / "A2A共同体_共享交换区"
SRC = EX / "wpsonline_index_20261009.json"
OUT = EX / "wpsonline_linkid_map_20261009_CAIRN.json"

def cli(*args, timeout=90):
    r = subprocess.run([CLI, *args], capture_output=True, timeout=timeout)
    return (r.stdout or b"").decode("utf-8", "replace")

# 收集 127 件名（递归遍历任意结构）
names = []
def collect(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, str) and v.endswith(".wpsonline"):
                names.append(v)
            else:
                collect(v)
    elif isinstance(o, list):
        for x in o:
            collect(x)
if not SRC.exists():
    print("   × 缺索引 %s" % SRC.name); sys.exit(1)
collect(json.loads(SRC.read_text(encoding="utf-8", errors="replace")))
names = sorted(set(names))
print("  索引件名=%d" % len(names))

m = {}
if OUT.exists():
    try:
        m = json.loads(OUT.read_text(encoding="utf-8"))
    except Exception:
        m = {}
print("  已有映射=%d（续跑）" % len(m.get("items", {})) if isinstance(m.get("items"), dict) else "  已有映射=0")
items = m.get("items", {}) if isinstance(m, dict) else {}

done = ok = 0
t0 = time.time()
for i, full in enumerate(names, 1):
    if full in items and items[full].get("link_id"):
        done += 1; continue
    base = full.split("/")[-1]
    stem = re.sub(r"\.(wpsonline|otl|docx|md|txt)$", "", base)
    kw = stem[:18] if len(stem) >= 4 else stem
    rec = {"link_id": None, "status": "not_found"}
    try:
        sj = json.loads(cli("drive", "search-files", "--args", json.dumps({"keyword": kw})))
        its = (((sj.get("data") or {}).get("data") or {}).get("items") or [])
        for it in its:
            f = it.get("file") or {}
            if f.get("name") == base and f.get("link_id"):
                rec = {"link_id": f["link_id"], "status": "ok", "size": f.get("size"),
                       "path": (it.get("file_src") or {}).get("path")}
                break
        if rec["link_id"] is None and its:
            for it in its:
                f = it.get("file") or {}
                if f.get("link_id") and stem[:10] and stem[:10] in str(f.get("name", "")):
                    rec = {"link_id": f["link_id"], "status": "fuzzy", "size": f.get("size"),
                           "path": (it.get("file_src") or {}).get("path")}
                    break
    except Exception as e:
        rec = {"link_id": None, "status": "error", "err": str(e)[:50]}
    items[full] = rec
    if rec.get("link_id"):
        ok += 1
    if i % 20 == 0 or i == len(names):
        OUT.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"),
                                   "source": SRC.name, "total": len(names), "resolved": sum(1 for v in items.values() if v.get("link_id")),
                                   "seat": "a2a-node-local", "items": items}, ensure_ascii=False, indent=1),
                       encoding="utf-8", newline="\n")
        print("   …%d/%d ｜ 命中=%d ｜ %.0fs" % (i, len(names), sum(1 for v in items.values() if v.get("link_id")), time.time()-t0))
    time.sleep(0.25)

resolved = sum(1 for v in items.values() if v.get("link_id"))
OUT.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "source": SRC.name,
                           "total": len(names), "resolved": resolved, "seat": "a2a-node-local", "items": items},
                          ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("\n  ★ 完成：%d/%d 已解析（新增 %d）｜ %.0fs ｜ 落盘 %s（%d B）" % (
    resolved, len(names), ok, time.time()-t0, OUT.name, OUT.stat().st_size))
