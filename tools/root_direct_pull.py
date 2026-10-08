# -*- coding: utf-8 -*-
"""游乐场根 20 件：搜索得 link_id → kdocs 直取 → **即脱敏**（SOP）→ 落盘
- 白名单：仅写本脚本新建之目录；仅改本脚本新建之文件
- 零回显：不打印 token/凭据；脱敏只报计数
"""
import json, pathlib, re, subprocess, sys, time

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
CLI = str(pathlib.Path.home() / ".kimi-work" / "bin" / "kdocs-cli.exe")
PLAZA = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场")
OUT = PLAZA / "Plan提示词工程" / "openplanlink-docx" / "游乐场根_正文副本_20261009_CAIRN"
OUT.mkdir(parents=True, exist_ok=True)

stubs = sorted(PLAZA.glob("*.wpsonline"))
print("  根目录桩=%d 件" % len(stubs))

PATTERNS = [
    ("腾讯云SecretId", re.compile(r"AKID[A-Za-z0-9]{20,}")),
    ("腾讯云签名", re.compile(r"q-signature=[A-Za-z0-9%+/=]{24,}")),
    ("sk-高熵键", re.compile(r"sk-[A-Za-z0-9]{28,}")),
    ("阿里云AK", re.compile(r"\bLTAI[A-Za-z0-9]{16,}\b")),
    ("AWS AK", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("SSH私钥头", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("Bearer长串", re.compile(r"(?i)bearer\s+[A-Za-z0-9_\-\.]{32,}")),
]
PLACEHOLDER = "[凭据已按铁律脱敏]"

def cli(*args, timeout=120):
    r = subprocess.run([CLI, *args], capture_output=True, timeout=timeout)
    return (r.stdout or b"").decode("utf-8", "replace")

rows = []
ok = 0
for s in stubs:
    name = s.name[:-len(".wpsonline")]           # e.g. 00_强制阅读指引_月之暗面游乐场.otl
    kw = re.sub(r"\.(otl|docx|md|txt)$", "", name)[:18]
    found = None
    try:
        sj = json.loads(cli("drive", "search-files", "--args", json.dumps({"keyword": kw})))
        items = (((sj.get("data") or {}).get("data") or {}).get("items") or [])
        for it in items:
            f = it.get("file") or {}
            if f.get("name") == name and f.get("link_id"):
                found = f; break
        if not found and items:
            for it in items:
                f = it.get("file") or {}
                if f.get("link_id") and name[:10] in str(f.get("name", "")):
                    found = f; break
    except Exception as e:
        print("   × %-46s 搜索异常：%s" % (name[:46], str(e)[:40])); continue
    if not found:
        print("   · %-46s 未在云端检索到同名件" % name[:46]); rows.append({"name": name, "status": "not_found"}); continue
    lid = found["link_id"]
    try:
        rj = json.loads(cli("drive", "read-file", "--args", json.dumps({"link_id": lid})))
        content = ((rj.get("data") or {}).get("content") or "")
    except Exception as e:
        print("   × %-46s 读取异常：%s" % (name[:46], str(e)[:40])); rows.append({"name": name, "status": "read_error"}); continue
    if not content:
        print("   · %-46s 读取返回空（code=%s）" % (name[:46], (rj.get("code") if isinstance(rj, dict) else "?"))); rows.append({"name": name, "status": "empty"}); continue
    n = 0; kinds = {}
    for label, rx in PATTERNS:
        content, k = rx.subn(PLACEHOLDER, content); n += k
        if k: kinds[label] = k
    head = ("> 提取席：A2A新席_石敢当Cairn（a2a-node-local）｜来源：**kdocs 云直取**（`search-files` 得 link_id `%s`）｜"
            "提取时间：%s｜**直取即脱敏（SOP）**：本件替换 %d 处凭据形态%s\n\n") % (
            lid, time.strftime("%Y-%m-%d %H:%M"), n, ("（" + "、".join(kinds) + "）") if kinds else "（无命中）")
    p = OUT / (name + "_正文副本_20261009_CAIRN.md")
    p.write_text(head + content, encoding="utf-8", newline="\n")
    ok += 1
    rows.append({"name": name, "status": "ok", "link_id": lid, "chars": len(content), "redacted": n, "path": p.name})
    print("   ★ %-46s ⇒ %7d 字符 ｜ 脱敏 %2d ｜ link_id=%s" % (name[:46], len(content), n, lid))
    time.sleep(0.4)

idx = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "scope": "游乐场根 *.wpsonline",
       "total": len(stubs), "ok": ok, "rows": rows}
ip = OUT / "root_direct_index_20261009_CAIRN.json"
ip.write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("\n  成功=%d/%d ｜ 落盘目录=%s ｜ 索引=%s" % (ok, len(stubs), OUT.name, ip.name))
