# -*- coding: utf-8 -*-
"""纲要更新对比：kdocs 直取（10-11）↔ 本地副本（10-09）
输出：新副本 ＋ 差异摘要（按节；并列出前若干条具体差异）
（引号一律用「」）
"""
import difflib, json, pathlib, re, sys, time

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
DOCX = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"Plan提示词工程"/"openplanlink-docx"
SRC = pathlib.Path.home()/"AppData"/"Local"/"Temp"/"kdocs_outline_20261011.txt"

raw = SRC.read_text(encoding="utf-8-sig", errors="replace")
try:
    j, _end = json.JSONDecoder().raw_decode(raw.lstrip())   # ★CLI 输出 JSON 后可能带额外行，故取首个 JSON
    content = (j.get("data") or {}).get("content") or ""
    meta = {k: (j.get("data") or {}).get(k) for k in ("content_format", "drive_id", "file_id", "name", "version", "update_time", "mtime")}
except Exception as e:
    print("  解析失败：%s" % str(e)[:80]); sys.exit(1)
print("  ═══ ① 新取之纲要 ═══")
print("   字数 %d ｜ 行数 %d ｜ 格式 %s" % (len(content), len(content.splitlines()), meta.get("content_format")))
print("   元数据：%s" % json.dumps({k: v for k, v in meta.items() if v}, ensure_ascii=False)[:220])

new = DOCX/("OpenPlanLink全局声明与Agent-to-Agent网络建设纲要.otl_正文副本_20261011_CAIRN.md")
hdr = ("> 提取席：A2A新席_石敢当Cairn（a2a-node-local）｜来源：**kdocs 云直取**"
       "（kdocs-cli v2.6.13 `drive read-file`，link_id `ci2ybbMcccFi`）｜提取时间：%s｜提取方式：本机直取\n"
       "> ★本副本仅存正文；凭据形态一律不落盘\n\n") % time.strftime("%Y-%m-%d %H:%M")
new.write_text(hdr + content, encoding="utf-8", newline="\n")
print("   ★ 新副本：%s（%.1f KB）" % (new.name, new.stat().st_size/1024))

old_c = sorted(DOCX.glob("*纲要*正文副本_20261009_CAIRN-DIRECT.md"))
old = old_c[0] if old_c else None
if not old:
    print("  ⚠ 未找到 10-09 副本，无从对比"); sys.exit(0)
o = old.read_text(encoding="utf-8", errors="replace")
# 去头部引用行后比较
def body(t):
    return [l for l in t.splitlines() if not l.startswith("> ") or "提取席" not in l]
ol, nl = body(o), body(content)
print("\n  ═══ ② 与 10-09 副本之对比 ═══")
print("   旧：%d 行／%d 字 ｜ 新：%d 行／%d 字 ｜ Δ字 %+d" % (len(ol), len(o), len(nl), len(content), len(content)-len(o)))
sm = difflib.SequenceMatcher(None, ol, nl)
add = rep = dele = 0
changes = []
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == "equal": continue
    if tag == "insert":
        add += (j2-j1); changes.append(("＋新增", ol[max(0,i1-1):i1], nl[j1:j2]))
    elif tag == "delete":
        dele += (i2-i1); changes.append(("－删除", ol[i1:i2], nl[j1:j1+1]))
    else:
        rep += max(i2-i1, j2-j1); changes.append(("～修改", ol[i1:i2], nl[j1:j2]))
print("   新增行 %d ｜ 删除行 %d ｜ 修改行 %d ｜ 变更块 %d" % (add, dele, rep, len(changes)))
if not changes:
    print("   ⇒ ★正文与 10-09 版本一致（未见差异）")
else:
    print("\n  ═══ ③ 变更块（前 12，各示前后文各 90 字）═══")
    for k, (t, before, after) in enumerate(changes[:12], 1):
        b = " / ".join(x.strip()[:90] for x in before[-1:]) if before else ""
        a = " / ".join(x.strip()[:90] for x in after[:2])
        print("   %2d. [%s]" % (k, t))
        print("       旧：%s" % (b or "（无）"))
        print("       新：%s" % (a or "（无）"))
    # 受影响的节（按标题粗判）
    heads = [l.strip() for l in nl if re.match(r"^#{2,6}\s", l.strip())]
    print("\n  ═══ ④ 新版之节（前 16）═══")
    for h in heads[:16]:
        print("   " + h[:100])
