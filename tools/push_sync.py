# -*- coding: utf-8 -*-
"""push_sync.py —— 「推送即同步」器物（2026-10-14 立）

用途：把席位侧之产出与账件，**按差集**同步入正本仓（openplanlink-cairn），
      并排除含明文密钥之件（交本地推送前闸⑤与 GitHub Push Protection 双重把关）。

纪律（承《运行口径》章十、章十一）：
  ★1 只同步本席自辖之件（以席位 outbox 之名为准）⇒ 不卷他席件
  ★2 加入前逐路径 Test-Path；`git add` 之错误**不得吞掉**
  ★3 含密钥样式之件一律不入仓（列名报告，由人工脱敏）
  ★4 台账（frontier_ledger.jsonl）与快照随推
  ★5 不 commit、不 push（由调用者显式执行，以便闸前复核）

用法：python push_sync.py [--dry]
"""
import hashlib, pathlib, re, subprocess, sys

sys.stdout.reconfigure(encoding="utf-8")
H = pathlib.Path.home()
SEAT = (H / "WPS Cloud" / "WPSDrive" / "29969771" / "WPS云盘" / "月之暗面的Plasma游乐场"
        / "A2A新席_石敢当Cairn_20260928")
CAIRN = H / "openplanlink-cairn"
SRC_DIRS = ["outbox/mem", "outbox/wps_read", "outbox/otl"]
LEDGER = ["ledger/frontier_ledger.jsonl", "ledger/_version_snapshot.json"]
SECRET_PATS = [
    re.compile(r"sk-cp-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"ark-[0-9a-f]{8}-[0-9a-f\-]{20,}"),
    re.compile(r"AKID[A-Za-z0-9]{12,}"),
    re.compile(r"LTAI[A-Za-z0-9]{10,}"),
]
TEXT_EXT = {".md", ".json", ".jsonl", ".txt", ".lean", ".py", ".yml", ".yaml"}


def has_secret(p: pathlib.Path) -> bool:
    if p.suffix.lower() not in TEXT_EXT:
        return False
    try:
        t = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return any(x.search(t) for x in SECRET_PATS)


def main() -> int:
    dry = "--dry" in sys.argv
    copied = skipped = secret = 0
    for sd in SRC_DIRS:
        sd_path = SEAT / sd
        if not sd_path.is_dir():
            continue
        for f in sorted(sd_path.iterdir()):
            if not f.is_file():
                continue
            dst = CAIRN / "notes" / f.name
            if dst.exists() and dst.stat().st_size == f.stat().st_size:
                skipped += 1
                continue
            if has_secret(f):
                secret += 1
                print("   ★含密钥样式、不入仓：%s" % f.name)
                continue
            if dry:
                print("   · 将补：%s（%d B）" % (f.name, f.stat().st_size))
                copied += 1
                continue
            try:
                dst.write_bytes(f.read_bytes())
                ok = dst.stat().st_size == f.stat().st_size
                print("   %s %s（%d B）" % ("✓" if ok else "✗", f.name, dst.stat().st_size))
                copied += 1
            except OSError as e:
                print("   ★失败 %s ⇒ %s" % (f.name, str(e)[:60]))
    for rel in LEDGER:
        src, dst = SEAT / rel, CAIRN / rel
        if not src.exists():
            continue
        if not dry:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
        print("   %s %s ⇒ %d 行" % ("✓" if not dry else "·", rel,
                                    len(dst.read_text(encoding="utf-8", errors="replace").splitlines()) if dst.exists() else 0))
    print("   ══ 汇总：补入 %d 件 ｜ 跳过（同名同大小）%d 件 ｜ ★因密钥未入 %d 件 ══" % (copied, skipped, secret))
    return 0


if __name__ == "__main__":
    sys.exit(main())
