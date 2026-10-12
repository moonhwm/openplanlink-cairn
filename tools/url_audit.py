"""url_audit.py —— 扫本席与共享区之文档 URL 并统计（正则含终止符修正）。"""
import pathlib, re, sys, collections
sys.stdout.reconfigure(encoding="utf-8")
HOME = pathlib.Path.home()
LOC = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"Plan提示词工程"/"openplanlink-docx"
SEAT = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"
EX = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"
# ★修正之正则：终止于空白／中文标点／引号／反引号／右括号；★遇 … 亦终止
URL = re.compile(r"https?://[^\s\u4e00-\u9fff，。；、「」“”'\"`<>\)\]\}…]+")
src = set()
for p in sorted(list(LOC.glob("*.otl")) + list(LOC.glob("*.md"))):
    src |= set(URL.findall(p.read_text(encoding="utf-8", errors="replace")))
mine = collections.Counter()
files = list(EX.glob("*.otl")) + list((SEAT/"notes").rglob("*.otl")) + list((SEAT/"ledger").glob("*.jsonl"))
for p in files:
    for u in URL.findall(p.read_text(encoding="utf-8", errors="replace")): mine[u] += 1
print("  ═══ 修正后之自核 ═══")
print("   底本唯一 URL %d ｜ 我之产出唯一 URL %d（出现 %d 次）" % (len(src), len(mine), sum(mine.values())))
same = [u for u in mine if u in src]; notin = [u for u in mine if u not in src]
print("   ★ 与底本逐字节相同 %d 条" % len(same))
print("   ★ 底本中无 %d 条 ⇒ 分类：" % len(notin))
trunc = [u for u in notin if "…" in u or len(u) < 14]
local_ = [u for u in notin if "127.0.0.1" in u or "localhost" in u]
plat  = [u for u in notin if "aliyuncs.com" in u or "302ai.cn" in u or "kdocs.cn" in u or "github.com" in u or "gitcode.com" in u]
other = [u for u in notin if u not in trunc and u not in local_ and u not in plat]
print("     a) ★截断／过短者 %d" % len(trunc))
for u in trunc[:8]: print("        · 「%s」（%d 字符）" % (u, len(u)))
print("     b) 本机／服务端点 %d" % len(local_))
print("     c) 平台与工程域（aliyun/kdocs/github/gitcode/302ai）%d" % len(plat))
print("     d) 其余（外引素材，须逐条核是否杜撰）%d" % len(other))
for u in other[:10]: print("        · %s" % u[:110])
print("\n  ⇒ 判：%s" % (
  "★存在截断之 URL（须修）" if trunc else "★无截断之 URL"))
