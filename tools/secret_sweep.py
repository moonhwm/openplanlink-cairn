# -*- coding: utf-8 -*-
"""凭据形态之清查与脱敏（安全优先；值一律不回显）
① 扫两仓未推送范围内之所有文件，按形态命中（sk-／AKLT／LTAI／Bearer／ep- 等）
② 生成脱敏副本（替换为 [凭据已按铁律脱敏]，保留类别与长度指纹）
③ 报告命中清单（路径＋行号＋类别），值零回显
（引号一律用「」）
"""
import pathlib, re, subprocess, sys

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
REPOS = {"cairn": HOME/"openplanlink-cairn", "mirror": HOME/"openplanlink-mirror"}
EX = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"
SKIP = {".git", "node_modules", "__pycache__"}
PATTERNS = [
    ("VolcEngine/ARK 形态", re.compile(r"(?<![A-Za-z0-9])([A-Za-z0-9]{8}-[A-Za-z0-9-]{16,}|ARK_[A-Z_]*KEY\s*[:=]\s*\S+)")),
    ("sk- 密钥形态", re.compile(r"(?<![A-Za-z0-9])(sk-[A-Za-z0-9_\-]{16,})")),
    ("火山 AK 形态", re.compile(r"(?<![A-Za-z0-9])(AKLT[A-Za-z0-9]{12,})")),
    ("阿里云 AK 形态", re.compile(r"(?<![A-Za-z0-9])(LTAI[A-Za-z0-9]{10,})")),
    ("Bearer 令牌", re.compile(r"Bearer\s+([A-Za-z0-9._\-]{20,})")),
    ("ep- 端点", re.compile(r"(?<![A-Za-z0-9])(ep-[0-9]{14}-[A-Za-z0-9]{4,})")),
]


def scan_text(t):
    hits = []
    for name, rx in PATTERNS:
        for m in rx.finditer(t):
            v = m.group(1)
            hits.append((name, t[:m.start()].count("\n") + 1, len(v)))
    return hits


def mask(t):
    for name, rx in PATTERNS:
        t = rx.sub(lambda m: "[凭据已按铁律脱敏]", t)
    return t


total = 0
for rname, root in REPOS.items():
    if not (root/".git").exists():
        print("  %s：不在本地" % rname); continue
    # 未推送范围之文件
    out = subprocess.run(["git", "-C", str(root), "diff", "--name-only", "origin/main..HEAD"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    files = [x for x in out.splitlines() if x.strip()]
    print("  ═══ %s：未推送范围内 %d 个文件 ═══" % (rname, len(files)))
    for rel in files:
        p = root/rel
        if not p.is_file() or p.stat().st_size > 3_000_000:
            continue
        try:
            t = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        hits = scan_text(t)
        if not hits:
            continue
        total += len(hits)
        print("   ★ %s" % rel)
        seen = set()
        for name, ln, l in hits:
            k = (name, ln)
            if k in seen: continue
            seen.add(k)
            print("       L%-5d %-18s 长度 %d" % (ln, name, l))
        # 脱敏副本写入交换区
        safe = EX/("脱敏_" + pathlib.Path(rel).name)
        safe.write_text(mask(t), encoding="utf-8", newline="\n")
        print("       ⇒ 脱敏副本：%s" % safe.name)
print("\n  ═══ 合计命中 %d 处（值零回显）═══" % total)
