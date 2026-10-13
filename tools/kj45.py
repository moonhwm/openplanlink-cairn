# -*- coding: utf-8 -*-
"""kj45.py —— 快照重基线（只增不改）＋ 缺口独立记录（2026-10-14）
缘由：WPS365 重装致云盘根变更，席位回退至云端副本（台账 844 条）；而快照仍记 848 条
      ⇒ ledger_write 之闸检报「差 行 −4」并拒写。
本器（★只增不改：原值全部保留于 *_before_rebase 字段）：
  ① 读 ledger/_version_snapshot.json ⇒ 记原 lines/last_hash/size 于 before_rebase 字段
  ② 以现台账实况（844 条／末 hash／size）置为新基线
  ③ 写缺口独立记录 outbox/mem/sync_gap_20261014.md
（中文串一律用「」）
"""
import hashlib, json, pathlib, sys, time

sys.stdout.reconfigure(encoding="utf-8")
SEAT = (pathlib.Path.home()/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"
        /"A2A新席_石敢当Cairn_20260928")
SNAP = SEAT/"ledger"/"_version_snapshot.json"
LED = SEAT/"ledger"/"frontier_ledger.jsonl"

# ① 原快照
old = json.loads(SNAP.read_text(encoding="utf-8-sig"))
print("  原快照：lines=%s ｜ last_hash=%s… ｜ size=%s" % (old.get("lines"), str(old.get("last_hash"))[:14], old.get("size")))

# ② 台账实况
raw = LED.read_bytes()
lines = [l for l in raw.decode("utf-8", "replace").splitlines() if l.strip()]
last = json.loads(lines[-1])
print("  台账实况：%d 条 ｜ size=%d ｜ 末 hash=%s…" % (len(lines), len(raw), str(last.get("hash"))[:14]))

new = dict(old)
new["lines_before_rebase"] = old.get("lines")
new["last_hash_before_rebase"] = old.get("last_hash")
new["size_before_rebase"] = old.get("size")
new["mtime_before_rebase"] = old.get("mtime")
new["rebase_at"] = time.strftime("%Y-%m-%dT%H:%M:%S+0800")
new["rebase_reason"] = "WPS365 重装致云盘根变更；席位回退至云端副本（844 条）；快照 848 条对应之 #845–#848 未能下载"
new["lines"] = len(lines)
new["last_hash"] = last.get("hash")
new["size"] = len(raw)
new["mtime"] = time.strftime("%Y-%m-%dT%H:%M:%S+0800")
SNAP.write_text(json.dumps(new, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("  ✓ 快照已重基线（原值存于 *_before_rebase）")

# ③ 缺口独立记录
gap = SEAT/"outbox"/"mem"
gap.mkdir(parents=True, exist_ok=True)
p = gap/"sync_gap_20261014.md"
p.write_text(
    "# 同步缺口记录（2026-10-14）\n\n"
    "- **事故**：新版 WPS365 安装后，云盘挂载根由 `…\\WPSDrive\\29969771\\WPS云盘\\` 改为\n"
    "  `…\\WPS Cloud\\WPSDrive\\29969771\\WPS云盘\\` ⇒ 旧根被弃空、新根重下云端副本。\n"
    "- **席位回退**：台账由 ★996 条（10-13 03:34）回退为 ★844 条（10-12 20:03）。\n"
    "- **缺口（如实，不伪造）**：\n"
    "  - **#845–#848**（4 条）：快照曾记 `lines=848`／`last_hash=a60493ec…`，但下载物仅 844 条 ⇒ ★未能取回；\n"
    "  - **#849–#996**（约 148 条）：昨夜（10-12 20:03 → 10-13 03:34）之全部记录，含 `-1443`～`-1462` 诸件；\n"
    "  - **合计约 152 条**。\n"
    "- **恢复途径皆绝**：回收站 0 项｜WPS 缓存（`syncfolderbackup`／`cachebackup`／`cachedata`）皆空｜\n"
    "  全盘三份账本（云盘 844 条@10-12 20:17；`Documents\\kimi\\quant-lab\\output\\cairn-recon` 10-11 16:25；\n"
    "  `Documents\\openplanlink-cairn` 10-11 10:06）皆无 10-13 增量。\n"
    "- **已救援**：① junction（旧根 → 新根），既有脚本无需改动；② 自 `openplanlink-cairn` 补入席位\n"
    "  `exp` 112 件（3,177→3,225），含昨夜全部器物；③ 自 `cairn\\mem` 恢复口径至席位\n"
    "  `ops\\运行口径_20261012.md`（17,553 B／152 行／★68 条）。\n"
    "- **处置**：以 ★844 条为基点续写；快照已重基线（原 `lines=848` 等值保留于 `*_before_rebase` 字段）；\n"
    "  **缺口永久标注、绝不冒充**。\n",
    encoding="utf-8", newline="\n")
print("  ✓ 缺口记录：" + p.name)
print("  新快照：lines=%s ｜ last_hash=%s…" % (new["lines"], str(new["last_hash"])[:14]))
