# -*- coding: utf-8 -*-
"""patch_hostref.py —— ①收紧主机名正则（消误报）②为入仓件引入「主机名伪名」host_ref

口径依据：DF-RELAY-20261006-HY4-01 §一（主机名与卷序列号同列"不录值"；登记命令而非值）。
设计：`host_ref = "H-" + sha256(hostname)[:8]` —— **确定性伪名**：同一主机每次同值，
      既可跨件关联/审计，又**不披露主机名本身**；如需人工对应，映射只入本地附件。
"""
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8")
SEAT = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928")

HOSTREF = '''

def host_ref():
    """主机名伪名（承脱敏口径：主机名不录值，但需可关联）——H-<sha256(hostname)[:8]>。"""
    import hashlib as _h
    import os as _o
    hn = (_o.environ.get("COMPUTERNAME") or "unknown").strip().lower()
    return "H-" + _h.sha256(hn.encode("utf-8")).hexdigest()[:8]
'''

# ① 收紧正则（区分大小写，避免 server-side / win-xxxx 之类误报）
f = SEAT / "exp" / "disclosure_scan.py"
t = f.read_text(encoding="utf-8")
before = t
t = t.replace('("主机名(通用模式)", re.compile(r"(?i)\\b(?:DESKTOP|WIN|PC|SERVER)-[A-Z0-9]{4,}\\b")),',
              '("主机名(通用模式)", re.compile(r"\\b(?:DESKTOP|SERVER|WIN|PC)-[A-Z0-9]{4,}\\b")),')
f.write_text(t, encoding="utf-8")
print("① 正则收紧：%s" % ("已改（去 (?i)，须大写形态）" if t != before else "未匹配（检查锚点）"))

# ② 为入仓脚本注入 host_ref()，并用伪名替换 host/computername 输出
targets = ["console_report.py", "baseline_digest.py"]
for name in targets:
    p = SEAT / "exp" / name
    if not p.exists():
        print("② %s：不存在，跳过" % name)
        continue
    s = p.read_text(encoding="utf-8")
    orig = s
    if "def host_ref(" not in s:
        idx = s.find("\ndef ")
        s = (s[:idx] + HOSTREF + s[idx:]) if idx > 0 else (s + HOSTREF)
    # 替换取值点
    s = s.replace('"host": os.environ.get("COMPUTERNAME", "?"),', '"host_ref": host_ref(),')
    s = s.replace('"host": d.get("host"),', '"host_ref": d.get("host_ref") or "H-unknown",')
    s = s.replace('"host": ps("$env:COMPUTERNAME"),', '"host_ref": host_ref(),')
    s = s.replace('os.environ.get("COMPUTERNAME", "?")', 'host_ref()')
    s = s.replace('d.get("host")', 'd.get("host_ref")')
    p.write_text(s, encoding="utf-8")
    print("② %s：%s" % (name, "已注入/替换" if s != orig else "无可替换点"))
print("完成")
