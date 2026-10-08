# -*- coding: utf-8 -*-
"""凭据卫生全扫 v2 —— **白名单制**（事故整改版）
事故根因：首版以「是否含本席关键词」判定归属（黑名单思路），而导入快照与主权人件恰不含该关键词 ⇒ 越界自动脱敏。

v2 原则（硬约束）：
  1) **只扫描/只落手于白名单目录**（本席封闭产出面）；
  2) 白名单外一律**只登记、不落手**（连读都只做只读登记）；
  3) 白名单内含**排除表**：`exp/`（工具源）、`ledger/`（台账）、任何 `*.py`、`*.jsonl`、`handshake/`（导入快照）、`inbox/`（主权人件）一律 **NEVER-REDACT**；
  4) 默认 **DRY-RUN**；须显式 `--apply` 才写盘；写盘前打印将改清单。

用法：
  python cred_hygiene_sweep_v2.py            # 预演（默认）
  python cred_hygiene_sweep_v2.py --apply    # 生效（仅白名单内、且不在排除表）
"""
import pathlib, re, sys

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
APPLY = "--apply" in sys.argv

PLAZA = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场")
WHITELIST = [
    PLAZA / "A2A共同体_共享交换区",          # 本席产出（件名含 CAIRN 者）
]
WHITELIST_PATTERNS = ["*CAIRN*", "*_正文副本_20261009_CAIRN*"]
EXCLUDE_DIR_PARTS = {"exp", "ledger", "handshake", "inbox", "archive", "cold", ".git"}
EXCLUDE_SUFFIX = {".py", ".pyc", ".jsonl", ".ps1", ".sh", ".js", ".ts", ".exe", ".dll"}

PATTERNS = [
    ("腾讯云SecretId", re.compile(r"AKID[A-Za-z0-9]{20,}")),        # 收紧：20+
    ("腾讯云签名", re.compile(r"q-signature=[A-Za-z0-9%+/=]{24,}")),
    ("sk-高熵键", re.compile(r"sk-[A-Za-z0-9]{28,}")),               # 收紧：28+
    ("阿里云AK", re.compile(r"\bLTAI[A-Za-z0-9]{16,}\b")),
    ("AWS AK", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("SSH私钥头", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("Bearer长串", re.compile(r"(?i)bearer\s+[A-Za-z0-9_\-\.]{32,}")),
]
PLACEHOLDER = "[凭据已按铁律脱敏]"

targets = []
for root in WHITELIST:
    if not root.exists():
        continue
    for pat in WHITELIST_PATTERNS:
        for p in root.glob(pat):
            if not p.is_file():
                continue
            if any(part in EXCLUDE_DIR_PARTS for part in p.parts):
                print("   ⛔ 排除表中，跳过：%s" % p.name[:70]); continue
            if p.suffix.lower() in EXCLUDE_SUFFIX:
                print("   ⛔ 后缀排除，跳过：%s" % p.name[:70]); continue
            targets.append(p)
targets = sorted(set(targets))

print("=== 白名单制扫描（%s） ===" % ("生效 APPLY" if APPLY else "预演 DRY-RUN"))
print("   白名单目标：%d 件" % len(targets))
hits = 0
for p in targets:
    try:
        t = p.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print("   × 读失败 %s：%s" % (p.name[:40], str(e)[:40])); continue
    n = 0; kinds = {}
    for name, rx in PATTERNS:
        k = len(rx.findall(t))
        if k:
            n += k; kinds[name] = k
    if n:
        hits += n
        print("   ★ %-62s 命中 %d：%s" % (p.name[:62], n, "、".join(kinds)))
        if APPLY:
            for name, rx in PATTERNS:
                t = rx.sub(PLACEHOLDER, t)
            p.write_text(t, encoding="utf-8", newline="\n")
            print("        ⇒ 已脱敏并写回")
print("   合计命中=%d ｜ %s" % (hits, "已写回" if APPLY else "未写盘（预演）"))
print("   ⇒ %s" % ("★零残留" if hits == 0 else "★有残留，请复核"))
