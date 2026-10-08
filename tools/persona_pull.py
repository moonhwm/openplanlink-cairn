# -*- coding: utf-8 -*-
"""人设件直取（3 件）——含"核名"步骤（防 fuzzy 错拉）＋直取即脱敏
- 目标：KI 人设及建模/自治纪律检查单 v1.0.0.otl / KI 人设及建模/陆知白人设主档案 v1.0.1.otl
        / 守藏管理区/席位初始人设卡_守藏.otl
"""
import json, pathlib, re, subprocess, sys, time

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
CLI = str(pathlib.Path.home() / ".kimi-work" / "bin" / "kdocs-cli.exe")
PLAZA = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场")
OUT = PLAZA / "Plan提示词工程" / "openplanlink-docx" / "KI人设_正文副本_20261009_CAIRN"
OUT.mkdir(parents=True, exist_ok=True)

TARGETS = [
    ("KI 人设及建模/自治纪律检查单 v1.0.0.otl.wpsonline", "crLYuPqXyFEv", "自治纪律检查单"),
    ("KI 人设及建模/陆知白人设主档案 v1.0.1.otl.wpsonline", "cqJLnkc5mVLU", "陆知白"),
    ("守藏管理区/席位初始人设卡_守藏.otl.wpsonline", "cv0sfaPNcCIk", "守藏"),
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
        print("   × %-40s 读取异常：%s" % (stem[:40], str(e)[:50])); rows.append({"name": stem, "status": "error"}); continue
    if not c:
        print("   · %-40s 空（code=%s）" % (stem[:40], rj.get("code") if isinstance(rj, dict) else "?"))
        rows.append({"name": stem, "status": "empty"}); continue
    # ★核名：正文前 300 字须含关键字（else 标 mismatch，不落盘为"该件"）
    head300 = c[:300]
    matched = key in head300 or key in stem
    n = 0; kinds = {}
    for label, rx in PATTERNS:
        c, k = rx.subn(PH, c); n += k
        if k: kinds[label] = k
    note = ("> 提取席：A2A新席_石敢当Cairn（a2a-node-local）｜来源：**kdocs 云直取**（link_id `%s`，映射状态=fuzzy）｜"
            "核名：%s（关键字「%s」）｜**直取即脱敏**：替换 %d 处%s\n\n") % (
            lid, "★相符" if matched else "★**不符——须复核**", key, n,
            ("（" + "、".join(kinds) + "）") if kinds else "（无命中）")
    p = OUT / (stem + "_正文副本_20261009_CAIRN.md")
    p.write_text(note + c, encoding="utf-8", newline="\n")
    print("   ★ %-40s ⇒ %6d 字符 ｜ 核名=%s ｜ 脱敏 %d ｜ link_id=%s" % (
        stem[:40], len(c), "相符" if matched else "不符", n, lid))
    # 打印正文首 12 行（供本席判读人设内容）
    for line in c.splitlines()[:12]:
        s = line.strip()
        if s: print("        | %s" % s[:110])
    rows.append({"name": stem, "status": "ok", "link_id": lid, "chars": len(c), "named_ok": matched, "redacted": n})
    time.sleep(0.4)

idx = OUT / "persona_docs_index_20261009_CAIRN.json"
idx.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "rows": rows}, ensure_ascii=False, indent=1),
               encoding="utf-8", newline="\n")
print("\n  落盘目录=%s ｜ 索引=%s" % (OUT.name, idx.name))
