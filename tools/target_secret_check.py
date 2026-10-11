# -*- coding: utf-8 -*-
"""专查 GitHub 所点名之文件（纲要副本第 27 行）＋ 精确长令牌扫描
★ 只报类别／长度／首尾 2 字符指纹；值零回显
（引号一律用「」）
"""
import pathlib, re, subprocess, sys

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
REPOS = {"cairn": HOME/"openplanlink-cairn", "mirror": HOME/"openplanlink-mirror"}
EX = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"
TARGET = "纲要.otl_正文副本_20261011_CAIRN.md"
LONGTOK = re.compile(r"(?<![A-Za-z0-9_\-])([A-Za-z0-9_\-]{20,})(?![A-Za-z0-9_\-])")
KW = re.compile(r"(?i)(key|token|secret|api[_-]?key|access[_-]?key|ark|bearer|sk-)")


def fp(v):
    return "%s…%s（长 %d）" % (v[:2], v[-2:], len(v))


for rname, root in REPOS.items():
    if not (root/".git").exists():
        continue
    out = subprocess.run(["git", "-C", str(root), "diff", "--name-only", "origin/main..HEAD"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    files = [x for x in out.splitlines() if x.strip()]
    print("  ═══ %s ═══" % rname)
    tgt = [f for f in files if TARGET in f]
    print("   未经推送范围内含'纲要副本'之文件：%s" % (tgt if tgt else "（不在未推送范围）"))
    for rel in tgt:
        p = root/rel
        t = p.read_text(encoding="utf-8", errors="ignore")
        lines = t.splitlines()
        if len(lines) >= 27:
            l27 = lines[26]
            print("   ★ %s 之 L27：" % rel)
            print("      该行长度 %d ｜ 前 40 字（已遮长串）：%s" % (len(l27), KW.sub("[KW]", LONGTOK.sub(lambda m: "[长令牌]", l27))[:40]))
            for m in LONGTOK.finditer(l27):
                v = m.group(1)
                print("      长令牌：%s ｜ 上下文含关键词=%s" % (fp(v), bool(KW.search(l27))))
        # 全文长令牌统计（含关键词上下文者优先）
        sus = []
        for i, ln in enumerate(lines, 1):
            for m in LONGTOK.finditer(ln):
                v = m.group(1)
                if len(v) >= 24 and KW.search(ln):
                    sus.append((i, len(v), v[:2], v[-2:]))
        print("     全文『长令牌＋关键词同现』共 %d 处（前 6）：" % len(sus))
        for i, l, a, b in sus[:6]:
            print("       L%-5d 长度 %-3d 指纹 %s…%s" % (i, l, a, b))
        if sus:
            # 生成脱敏副本（长令牌＋关键词同现之行，替换长令牌）
            safe_lines = []
            for ln in lines:
                if KW.search(ln):
                    ln = LONGTOK.sub("[凭据已按铁律脱敏]", ln)
                safe_lines.append(ln)
            safe = EX/("脱敏_" + pathlib.Path(rel).name)
            safe.write_text("\n".join(safe_lines) + "\n", encoding="utf-8", newline="\n")
            print("     ⇒ 已生成脱敏版：%s（%.1f KB）" % (safe.name, safe.stat().st_size/1024))
