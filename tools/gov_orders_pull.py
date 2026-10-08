# -*- coding: utf-8 -*-
"""按新目标取三件相关令件（TRIDIG 三维 / EVOLVE 演化）——含核名＋直取即脱敏
link_id 来源：本席 127 件映射（wpsonline_linkid_map_20261009_CAIRN.json）
"""
import json, pathlib, re, subprocess, sys, time

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
CLI = str(pathlib.Path.home() / ".kimi-work" / "bin" / "kdocs-cli.exe")
PLAZA = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场")
OUT = PLAZA / "Plan提示词工程" / "openplanlink-docx" / "治理令件_正文副本_20261009_CAIRN"
OUT.mkdir(parents=True, exist_ok=True)

TARGETS = [
    ("守藏管理区/119号令执行件_DF-ORD-2026-1005-TRIDIG-01.otl.wpsonline", "cdLfGEG7ABQo", "TRIDIG"),
    ("守藏管理区/110号令执行件_DF-ORD-2026-1004-EVOLVE-01.otl.wpsonline", "cqU5VPSMDloo", "EVOLVE"),
    ("守藏管理区/111号令执行件_DF-ORD-2026-1004-EVOLVE-02.otl.wpsonline", "coA1pYNJddbs", "EVOLVE"),
]
PATTERNS = [("腾讯云SecretId", re.compile(r"AKID[A-Za-z0-9]{20,}")),
            ("sk-高熵键", re.compile(r"sk-[A-Za-z0-9]{28,}")),
            ("阿里云AK", re.compile(r"\bLTAI[A-Za-z0-9]{16,}\b")),
            ("Bearer长串", re.compile(r"(?i)bearer\s+[A-Za-z0-9_\-\.]{32,}"))]
PH = "[凭据已按铁律脱敏]"

def cli(*args, timeout=120):
    r = subprocess.run([CLI, *args], capture_output=True, timeout=timeout)
    return (r.stdout or b"").decode("utf-8", "replace")

rows = []
for full, lid, key in TARGETS:
    stem = re.sub(r"\.wpsonline$", "", full.split("/")[-1])
    try:
        rj = json.loads(cli("drive", "read-file", "--args", json.dumps({"link_id": lid})))
        c = ((rj.get("data") or {}).get("content") or "")
    except Exception as e:
        print("   × %-38s 异常：%s" % (stem[:38], str(e)[:40])); continue
    if not c:
        print("   · %-38s 空（code=%s）" % (stem[:38], rj.get("code") if isinstance(rj, dict) else "?")); continue
    matched = key in c[:400]
    n = 0; kinds = {}
    for label, rx in PATTERNS:
        c, k = rx.subn(PH, c); n += k
        if k: kinds[label] = k
    note = ("> 提取席：A2A新席_石敢当Cairn（a2a-node-local）｜kdocs 云直取（link_id `%s`）｜核名：%s（「%s」）｜"
            "直取即脱敏：%d 处%s\n\n") % (lid, "★相符" if matched else "★不符须复核", key, n,
                                        ("（" + "、".join(kinds) + "）") if kinds else "（无命中）")
    p = OUT / (stem + "_正文副本_20261009_CAIRN.md")
    p.write_text(note + c, encoding="utf-8", newline="\n")
    print("   ★ %-38s ⇒ %6d 字符 ｜ 核名=%s ｜ 脱敏 %d" % (stem[:38], len(c), "相符" if matched else "不符", n))
    for line in c.splitlines()[:14]:
        s = line.strip()
        if s: print("        | %s" % s[:112])
    rows.append({"name": stem, "link_id": lid, "chars": len(c), "named_ok": matched, "redacted": n})
    time.sleep(0.4)

(OUT / "gov_orders_index_20261009_CAIRN.json").write_text(
    json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "rows": rows}, ensure_ascii=False, indent=1),
    encoding="utf-8", newline="\n")
print("\n  落盘目录=%s" % OUT.name)
